# pipeline.py
# Ein Lauf: Eingabedatei → Provider → Datenbank → drei Ausgabedateien.
#
# Sechs Kunden werden gleichzeitig abgefragt (03_ENTSCHEIDUNGEN.md C). Parallel
# ist nur das Warten auf die Datenquelle — Entscheidung und Datenbank laufen im
# sammelnden Thread. Damit bleibt die Fortschrittszahl exakt und die
# SQLite-Verbindung in einem Thread.
#
# Drei Dinge macht dieser Lauf gegenüber dem alten Ablauf zusätzlich:
#   - jeder Kandidat wird mit Score und Entscheid gespeichert, nicht nur der
#     gewählte (02_DATENVERTRAG.md §5)
#   - ein hängender Provider wird nach 90 Sekunden abgeschnitten; der Kunde
#     landet dann in Datei ③ (03_ENTSCHEIDUNGEN.md C)
#   - ein abgestürzter Lauf kann fortgesetzt werden, ohne einen Kunden doppelt
#     abzufragen oder auszulassen

import logging
import threading
import time
from concurrent.futures import (FIRST_COMPLETED, ThreadPoolExecutor,
                                TimeoutError as FutureTimeout, wait)
from pathlib import Path

import pandas as pd

from data_cleaner import (DataCleaner, ausgabeordner_fuer, leere_ablage,
                          schreibe_ausgabedateien)
from place_provider import candidate_aus_zeile, leere_ausgabezeile

logger = logging.getLogger(__name__)

# 03_ENTSCHEIDUNGEN.md C
STANDARD_TIMEOUT_SEKUNDEN = 90
STANDARD_ARBEITER = 6

# Wie oft der Lauf beim Warten nachsieht, ob abgebrochen wurde. Bestimmt, wie
# schnell der Abbruch greift (Abnahmekriterium: unter 5 Sekunden).
TAKT_SEKUNDEN = 0.2

# Pflichtspalten Modus A (02_DATENVERTRAG.md §1)
PFLICHTSPALTEN = ('SearchString', 'PLZ', 'KundenNr')

# Ausgabedatei → Wert der Spalte kunde.ergebnis (02_DATENVERTRAG.md §5)
ERGEBNIS_JE_DATEI = {
    'fertig_fuer_erp': 'fertig',
    'zur_pruefung': 'pruefung',
    'nicht_moeglich': 'nicht_moeglich',
}

# Ausgabedatei → Wert der Spalte kandidat.entscheid (02_DATENVERTRAG.md §5)
ENTSCHEID_JE_DATEI = {
    'fertig_fuer_erp': 'gewaehlt',
    'zur_pruefung': 'vorgeschlagen',
    'nicht_moeglich': 'vorgeschlagen',
    'aussortiert': 'abgelehnt',
}

# Interne Spalte: verbindet eine Ausgabezeile mit dem Candidate, aus dem sie
# stammt. Steht nicht im Datenvertrag und landet nicht in der CSV, weil beim
# Schreiben nur die Vertragsspalten ausgewählt werden.
KANDIDAT_NR = '_kandidat_nr'


class Abgebrochen(Exception):
    """Der Lauf wurde vom Nutzer gestoppt."""


class Lauf:
    """Führt einen kompletten Durchgang aus: anreichern, entscheiden, schreiben."""

    def __init__(self, provider, datenbank, cleaner: DataCleaner = None,
                 timeout_sekunden: float = STANDARD_TIMEOUT_SEKUNDEN,
                 arbeiter: int = STANDARD_ARBEITER, abbruch: threading.Event = None):
        self.provider = provider
        self.datenbank = datenbank
        self.cleaner = cleaner or DataCleaner()
        self.timeout_sekunden = timeout_sekunden
        self.arbeiter = max(1, int(arbeiter))
        self.abbruch = abbruch or threading.Event()

    # ------------------------------------------------------------------
    # Der Lauf
    # ------------------------------------------------------------------

    def ausfuehren(self, eingabe_pfad: str, ausgabe_ordner: str = None,
                   email: str = None) -> dict:
        """Arbeitet eine Eingabedatei im Modus A ab. Legt einen neuen Job an."""
        eingabe = Path(eingabe_pfad)
        kunden = self._kunden_lesen(eingabe)

        job_id = self.datenbank.job_anlegen('A', eingabe.name,
                                            kunden_total=len(kunden), email=email)
        self.datenbank.status_setzen(job_id, 'LAEUFT')
        logger.info(f'Job {job_id}: {len(kunden)} Kunden aus {eingabe.name}, '
                    f'{self.arbeiter} parallel.')
        return self._abarbeiten(job_id, eingabe, kunden, ausgabe_ordner)

    def fortsetzen(self, job_id: int, eingabe_pfad: str,
                   ausgabe_ordner: str = None) -> dict:
        """
        Setzt einen abgestürzten Lauf fort.

        Bereits verarbeitete Kunden stehen in der Tabelle `kunde` und werden
        nicht erneut abgefragt. Ihre Entscheidung wird aus den gespeicherten
        Kandidaten neu hergeleitet — dieselbe Fachlogik, dieselben Daten, also
        dasselbe Ergebnis, nur ohne Kosten bei der Datenquelle.
        """
        job = self.datenbank.job_lesen(job_id)
        if not job:
            raise ValueError(f'Einen Auftrag mit der Nummer {job_id} gibt es nicht.')

        eingabe = Path(eingabe_pfad)
        kunden = self._kunden_lesen(eingabe)
        if job['status'] != 'LAEUFT':
            self.datenbank.status_setzen(job_id, 'LAEUFT')

        logger.info(f'Job {job_id} wird fortgesetzt.')
        return self._abarbeiten(job_id, eingabe, kunden, ausgabe_ordner)

    # ------------------------------------------------------------------

    def _kunden_lesen(self, eingabe: Path) -> list:
        df = pd.read_csv(eingabe, sep=';', encoding='utf-8-sig', dtype=str).fillna('')

        fehlend = [s for s in PFLICHTSPALTEN if s not in df.columns]
        if fehlend:
            raise ValueError('In der Eingabedatei fehlen die Spalten: '
                             + ', '.join(fehlend))

        # Ein Kunde, eine Zeile. Kommt eine KundenNr mehrfach vor, zählt die
        # erste Zeile; sonst würde idx_kunde_nr den Lauf abbrechen.
        gruppen = list(df.groupby('KundenNr', sort=False))
        self._doppelte = len(df) - len(gruppen)
        if self._doppelte:
            logger.warning(f'{self._doppelte} Zeilen mit bereits vorhandener '
                           f'KundenNr übersprungen.')
        return [(str(nr), gruppe.iloc[0]) for nr, gruppe in gruppen]

    def _abarbeiten(self, job_id: int, eingabe: Path, kunden: list,
                    ausgabe_ordner: str) -> dict:
        # Die Gesamtzahl steht erst jetzt fest — beim Fortsetzen genauso wie
        # beim ersten Lauf.
        self.datenbank.kunden_total_setzen(job_id, len(kunden))

        # Was schon in der Datenbank steht, wird nicht noch einmal geholt.
        bereits = {k['kunden_nr']: k for k in self.datenbank.kunden_lesen(job_id)}
        entscheidungen = {}

        for kunden_nr, _ in kunden:
            if kunden_nr in bereits:
                entscheidungen[kunden_nr] = self._aus_datenbank(bereits[kunden_nr])

        erledigt = len(entscheidungen)
        self.datenbank.fortschritt_setzen(job_id, erledigt)
        if erledigt:
            logger.info(f'Job {job_id}: {erledigt} Kunden lagen bereits vor.')

        offen = [(nr, stamm) for nr, stamm in kunden if nr not in bereits]

        try:
            erledigt = self._offene_abarbeiten(job_id, offen, entscheidungen, erledigt)
        except Abgebrochen:
            self.datenbank.status_setzen(job_id, 'ABGEBROCHEN')
            logger.info(f'Job {job_id} abgebrochen nach {erledigt} Kunden.')
            return {
                'job_id': job_id, 'status': 'ABGEBROCHEN',
                'kunden_total': len(kunden), 'kunden_erledigt': erledigt,
                'dateien': None, 'doppelte_kundennummern': self._doppelte,
            }
        except Exception as fehler:
            logger.exception('Lauf abgebrochen')
            self.datenbank.status_setzen(job_id, 'FEHLER', str(fehler))
            raise

        # Die Ausgabe folgt der Reihenfolge der Eingabedatei, nicht der
        # Reihenfolge, in der die Arbeiter fertig geworden sind.
        gesamt = leere_ablage()
        for kunden_nr, _ in kunden:
            for datei, zeilen in entscheidungen[kunden_nr].items():
                gesamt[datei].extend(zeilen)

        ziel = ausgabe_ordner or ausgabeordner_fuer(eingabe)
        dateien = schreibe_ausgabedateien(gesamt, ziel)
        self.datenbank.status_setzen(job_id, 'FERTIG')

        return {
            'job_id': job_id, 'status': 'FERTIG',
            'kunden_total': len(kunden), 'kunden_erledigt': erledigt,
            'dateien': dateien, 'doppelte_kundennummern': self._doppelte,
        }

    def _offene_abarbeiten(self, job_id: int, offen: list, entscheidungen: dict,
                           erledigt: int) -> int:
        """
        Holt die offenen Kunden mit mehreren Arbeitern gleichzeitig.

        Parallel läuft nur `_kandidaten_holen`, also das Warten auf die
        Datenquelle. Entscheidung, Datenbank und Fortschritt bleiben in diesem
        Thread — deshalb stimmt die Fortschrittszahl jederzeit, und deshalb
        braucht die SQLite-Verbindung keine Sperre.
        """
        if not offen:
            return erledigt

        # Es sind nie mehr Abfragen unterwegs als das Doppelte der Arbeiterzahl.
        # Ohne diese Grenze würden bei 2'500 Kunden alle Abfragen sofort in die
        # Warteschlange gelegt; fertige Ergebnisse lägen dann unter Umständen
        # lange herum, bevor sie in der Datenbank landen — und ein Absturz
        # würde sie mitnehmen.
        fenster = self.arbeiter * 2
        nachschub = iter(offen)
        arbeiter = ThreadPoolExecutor(max_workers=self.arbeiter)
        auftraege = {}
        unerledigt = set()

        def nachfuellen():
            while len(unerledigt) < fenster:
                naechster = next(nachschub, None)
                if naechster is None:
                    return
                kunden_nr, stamm = naechster
                auftrag = arbeiter.submit(
                    self._kandidaten_holen,
                    str(stamm.get('SearchString', '')).strip(),
                    str(stamm.get('PLZ', '')).strip())
                auftraege[auftrag] = (kunden_nr, stamm)
                unerledigt.add(auftrag)

        try:
            nachfuellen()
            while unerledigt:
                if self.abbruch.is_set():
                    raise Abgebrochen()
                fertig, rest = wait(unerledigt, timeout=TAKT_SEKUNDEN,
                                    return_when=FIRST_COMPLETED)
                unerledigt = set(rest)
                for auftrag in fertig:
                    if self.abbruch.is_set():
                        raise Abgebrochen()
                    kunden_nr, stamm = auftraege.pop(auftrag)
                    entscheidungen[kunden_nr] = self._einen_kunden(
                        job_id, kunden_nr, stamm, auftrag.result())
                    erledigt += 1
                    # Nach jedem Kunden, nicht am Ende (02_DATENVERTRAG.md §6).
                    self.datenbank.fortschritt_setzen(job_id, erledigt)
                nachfuellen()
        finally:
            # Nicht warten: ein hängender Aufruf darf den Abbruch nicht aufhalten.
            arbeiter.shutdown(wait=False, cancel_futures=True)

        return erledigt

    # ------------------------------------------------------------------
    # Ein Kunde
    # ------------------------------------------------------------------

    def _einen_kunden(self, job_id: int, kunden_nr: str, stamm, kandidaten: list) -> dict:
        """Entscheidet einen Kunden und schreibt ihn samt Kandidaten weg."""
        search_string = str(stamm.get('SearchString', '')).strip()
        plz = str(stamm.get('PLZ', '')).strip()
        stadt = str(stamm.get('Stadt', '')).strip()

        gruppe = self._als_gruppe(kunden_nr, search_string, plz, stadt, kandidaten)
        ablage = self.cleaner.entscheide_kunde(kunden_nr, gruppe)

        datei = self._gewaehlte_datei(ablage)
        kopfzeile = ablage[datei][0]

        self.datenbank.kunde_mit_kandidaten_schreiben(
            job_id, kunden_nr,
            self._kandidaten_eintraege(kandidaten, ablage),
            search_string=search_string, plz=plz, stadt=stadt,
            ergebnis=ERGEBNIS_JE_DATEI[datei],
            qualitaet=kopfzeile['qualitaet'],
            grund=kopfzeile['grund'])

        return ablage

    def _aus_datenbank(self, kunde: dict) -> dict:
        """
        Stellt die Entscheidung eines bereits verarbeiteten Kunden wieder her.

        Kein Netzzugriff: die Kandidaten liegen in der Datenbank. Die
        Fachlogik ist dieselbe wie beim ersten Mal, also fällt dieselbe
        Entscheidung — Zeile für Zeile.
        """
        kandidaten = [candidate_aus_zeile(z)
                      for z in self.datenbank.kandidaten_lesen(kunde['id'])]
        gruppe = self._als_gruppe(kunde['kunden_nr'], kunde['search_string'] or '',
                                  kunde['plz'] or '', kunde['stadt'] or '', kandidaten)
        return self.cleaner.entscheide_kunde(kunde['kunden_nr'], gruppe)

    def _kandidaten_holen(self, search_string: str, plz: str) -> list:
        """
        Fragt den Provider, aber nicht länger als der Timeout erlaubt.

        Die Grenze gilt je Aufruf und für jeden Provider, nicht nur für Apify:
        ein Aufruf, der nicht zurückkommt, darf einen Lauf über 2'500 Kunden
        nicht blockieren. Zeitüberschreitung wird wie ein leeres Ergebnis
        behandelt, ohne Retry (03_ENTSCHEIDUNGEN.md C).
        """
        ausfuehrer = ThreadPoolExecutor(max_workers=1)
        auftrag = ausfuehrer.submit(self.provider.fetch_by_text, search_string, plz)
        ende = time.monotonic() + self.timeout_sekunden
        try:
            while True:
                if self.abbruch.is_set():
                    return []
                rest = ende - time.monotonic()
                if rest <= 0:
                    logger.warning(f'Keine Antwort innerhalb von '
                                   f'{self.timeout_sekunden} Sekunden für '
                                   f'"{search_string}", wird als leeres Ergebnis '
                                   f'behandelt.')
                    auftrag.cancel()
                    return []
                try:
                    return list(auftrag.result(timeout=min(TAKT_SEKUNDEN, rest)))
                except FutureTimeout:
                    continue
        except Exception as fehler:
            logger.error(f'Datenquelle meldet einen Fehler für "{search_string}": '
                         f'{fehler}')
            return []
        finally:
            # Nicht warten: ein hängender Aufruf soll den Lauf nicht festhalten.
            ausfuehrer.shutdown(wait=False)

    @staticmethod
    def _als_gruppe(kunden_nr: str, search_string: str, plz: str, stadt: str,
                    kandidaten: list) -> pd.DataFrame:
        """
        Baut die Kundengruppe, die die Fachlogik erwartet.

        Aufbau wie die bisherige angereicherte CSV: Stammdaten links, ein
        Kandidat je Zeile rechts. Ohne Kandidaten entsteht eine einzige Zeile mit
        leeren Trefferfeldern — genau das, was die Fachlogik als "kein Ergebnis"
        liest.
        """
        stamm = {'KundenNr': kunden_nr, 'SearchString': search_string,
                 'PLZ': plz, 'Stadt': stadt}

        if not kandidaten:
            zeilen = [{**stamm, **leere_ausgabezeile(), KANDIDAT_NR: -1}]
        else:
            zeilen = [{**stamm, **kandidat.als_ausgabezeile(), KANDIDAT_NR: nummer}
                      for nummer, kandidat in enumerate(kandidaten)]

        return pd.DataFrame(zeilen)

    @staticmethod
    def _gewaehlte_datei(ablage: dict) -> str:
        """
        Welche der drei Hauptdateien hat den Kunden bekommen?

        Die Invariante aus 02_DATENVERTRAG.md §2 sagt: genau eine. Trifft das
        nicht zu, ist die Fachlogik defekt und der Lauf bricht ab, statt eine
        halbe Wahrheit in die Datenbank zu schreiben.
        """
        gefuellt = [datei for datei in ERGEBNIS_JE_DATEI if ablage[datei]]
        if len(gefuellt) != 1:
            raise RuntimeError(
                f'Der Kunde landete in {len(gefuellt)} Ausgabedateien statt in '
                f'genau einer: {gefuellt or "keiner"}.')
        return gefuellt[0]

    @staticmethod
    def _kandidaten_eintraege(kandidaten: list, ablage: dict) -> list:
        """Jeder Kandidat mit seinem Score und dem Entscheid über ihn."""
        if not kandidaten:
            return []

        eintraege = []
        for datei, zeilen in ablage.items():
            for zeile in zeilen:
                nummer = zeile.get(KANDIDAT_NR, -1)
                if nummer < 0:
                    continue  # Zeile ohne Kandidat (kein Ergebnis, Eingabe unbrauchbar)
                eintraege.append((kandidaten[nummer], zeile['score'],
                                  ENTSCHEID_JE_DATEI[datei], zeile['grund']))
        return eintraege
