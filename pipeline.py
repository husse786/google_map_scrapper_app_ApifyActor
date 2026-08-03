# pipeline.py
# Ein Lauf: Eingabedatei → Provider → Datenbank → drei Ausgabedateien.
#
# Der Lauf arbeitet die Kunden nacheinander ab. Ein Hintergrund-Thread mit
# Wiederaufnahme und Abbruch ist Phase 3; hier läuft alles im Vordergrund.
#
# Zwei Dinge macht dieser Lauf gegenüber dem alten Ablauf zusätzlich:
#   - jeder Kandidat wird mit Score und Entscheid gespeichert, nicht nur der
#     gewählte (02_DATENVERTRAG.md §5)
#   - ein hängender Provider wird nach 90 Sekunden abgeschnitten; der Kunde
#     landet dann in Datei ③ (03_ENTSCHEIDUNGEN.md C)

import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from pathlib import Path

import pandas as pd

from data_cleaner import (DataCleaner, ausgabeordner_fuer, leere_ablage,
                          schreibe_ausgabedateien)
from place_provider import leere_ausgabezeile

logger = logging.getLogger(__name__)

# 03_ENTSCHEIDUNGEN.md C: Timeout pro API-Aufruf.
STANDARD_TIMEOUT_SEKUNDEN = 90

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


class Lauf:
    """Führt einen kompletten Durchgang aus: anreichern, entscheiden, schreiben."""

    def __init__(self, provider, datenbank, cleaner: DataCleaner = None,
                 timeout_sekunden: int = STANDARD_TIMEOUT_SEKUNDEN):
        self.provider = provider
        self.datenbank = datenbank
        self.cleaner = cleaner or DataCleaner()
        self.timeout_sekunden = timeout_sekunden

    # ------------------------------------------------------------------
    # Der Lauf
    # ------------------------------------------------------------------

    def ausfuehren(self, eingabe_pfad: str, ausgabe_ordner: str = None,
                   email: str = None) -> dict:
        """
        Arbeitet eine Eingabedatei im Modus A ab.

        Returns:
            {'job_id': int, 'status': str, 'kunden_total': int,
             'kunden_erledigt': int, 'dateien': {...}, 'doppelte_kundennummern': int}
        """
        eingabe = Path(eingabe_pfad)
        df = pd.read_csv(eingabe, sep=';', encoding='utf-8-sig', dtype=str).fillna('')

        fehlend = [s for s in PFLICHTSPALTEN if s not in df.columns]
        if fehlend:
            raise ValueError('In der Eingabedatei fehlen die Spalten: '
                             + ', '.join(fehlend))

        # Ein Kunde, eine Zeile. Kommt eine KundenNr mehrfach vor, zählt die
        # erste Zeile; sonst würde idx_kunde_nr den Lauf abbrechen.
        kunden = list(df.groupby('KundenNr', sort=False))
        doppelte = len(df) - len(kunden)
        if doppelte:
            logger.warning(f'{doppelte} Zeilen mit bereits vorhandener KundenNr '
                           f'übersprungen.')

        job_id = self.datenbank.job_anlegen('A', eingabe.name,
                                            kunden_total=len(kunden), email=email)
        self.datenbank.status_setzen(job_id, 'LAEUFT')
        logger.info(f'Job {job_id}: {len(kunden)} Kunden aus {eingabe.name}.')

        gesamt = leere_ablage()
        erledigt = 0
        try:
            for kunden_nr, gruppe in kunden:
                self._einen_kunden(job_id, str(kunden_nr), gruppe.iloc[0], gesamt)
                erledigt += 1
                # Nach jedem Kunden, nicht am Ende (02_DATENVERTRAG.md §6).
                self.datenbank.fortschritt_setzen(job_id, erledigt)
        except Exception as fehler:
            logger.exception('Lauf abgebrochen')
            self.datenbank.status_setzen(job_id, 'FEHLER', str(fehler))
            raise

        ziel = ausgabe_ordner or ausgabeordner_fuer(eingabe)
        dateien = schreibe_ausgabedateien(gesamt, ziel)
        self.datenbank.status_setzen(job_id, 'FERTIG')

        return {
            'job_id': job_id,
            'status': 'FERTIG',
            'kunden_total': len(kunden),
            'kunden_erledigt': erledigt,
            'dateien': dateien,
            'doppelte_kundennummern': doppelte,
        }

    # ------------------------------------------------------------------
    # Ein Kunde
    # ------------------------------------------------------------------

    def _einen_kunden(self, job_id: int, kunden_nr: str, stamm, gesamt: dict) -> None:
        search_string = str(stamm.get('SearchString', '')).strip()
        plz = str(stamm.get('PLZ', '')).strip()
        stadt = str(stamm.get('Stadt', '')).strip()

        kandidaten = self._kandidaten_holen(search_string, plz)
        gruppe = self._als_gruppe(kunden_nr, search_string, plz, stadt, kandidaten)

        ablage = self.cleaner.entscheide_kunde(kunden_nr, gruppe)

        datei = self._gewaehlte_datei(ablage)
        kopfzeile = ablage[datei][0]
        kunde_id = self.datenbank.kunde_schreiben(
            job_id, kunden_nr,
            search_string=search_string, plz=plz, stadt=stadt,
            ergebnis=ERGEBNIS_JE_DATEI[datei],
            qualitaet=kopfzeile['qualitaet'],
            grund=kopfzeile['grund'])

        self._kandidaten_speichern(kunde_id, kandidaten, ablage)

        for schluessel, zeilen in ablage.items():
            gesamt[schluessel].extend(zeilen)

    def _kandidaten_holen(self, search_string: str, plz: str) -> list:
        """
        Fragt den Provider, aber nicht länger als der Timeout erlaubt.

        Die Grenze gilt für jeden Provider, nicht nur für Apify: ein Aufruf, der
        nicht zurückkommt, darf einen Lauf über 2'500 Kunden nicht blockieren.
        Zeitüberschreitung wird wie ein leeres Ergebnis behandelt, ohne Retry
        (03_ENTSCHEIDUNGEN.md C).
        """
        ausfuehrer = ThreadPoolExecutor(max_workers=1)
        auftrag = ausfuehrer.submit(self.provider.fetch_by_text, search_string, plz)
        try:
            return list(auftrag.result(timeout=self.timeout_sekunden))
        except FutureTimeout:
            logger.warning(f'Keine Antwort innerhalb von {self.timeout_sekunden} '
                           f'Sekunden für "{search_string}", wird als leeres '
                           f'Ergebnis behandelt.')
            auftrag.cancel()
            return []
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

    def _kandidaten_speichern(self, kunde_id: int, kandidaten: list,
                              ablage: dict) -> None:
        """Jeder Kandidat kommt in die Datenbank, mit Score und Entscheid."""
        if not kandidaten:
            return

        eintraege = []
        for datei, zeilen in ablage.items():
            for zeile in zeilen:
                nummer = zeile.get(KANDIDAT_NR, -1)
                if nummer < 0:
                    continue  # Zeile ohne Kandidat (kein Ergebnis, Eingabe unbrauchbar)
                eintraege.append((kandidaten[nummer], zeile['score'],
                                  ENTSCHEID_JE_DATEI[datei], zeile['grund']))

        if eintraege:
            self.datenbank.kandidaten_schreiben(kunde_id, eintraege)
