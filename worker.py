# worker.py
# Der Lauf im Hintergrund. Ein Job zur Zeit.
#
# Warum überhaupt: ein Lauf über 2'500 Kunden dauert Stunden. Der Sachbearbeiter
# soll das Browserfenster schliessen können, ohne dass der Lauf stirbt, und nach
# einem Absturz soll nicht alles von vorn beginnen.
#
# Die SQLite-Verbindung des Laufs entsteht im Arbeitsthread und gehört ihm
# allein. Wer von aussen den Fortschritt lesen will, öffnet eine eigene
# Verbindung — dafür steht die Datenbank im WAL-Modus.

import logging
import shutil
import threading
from pathlib import Path

import mail
from db import Datenbank
from pipeline import STANDARD_ARBEITER, STANDARD_TIMEOUT_SEKUNDEN, Lauf

logger = logging.getLogger(__name__)

# Ein Nutzer, ein Job (03_ENTSCHEIDUNGEN.md C). Die Sperre verhindert, dass zwei
# Starts im selben Prozess aneinander vorbeilaufen.
_START_SPERRE = threading.Lock()

# Jobs, an denen in diesem Prozess gerade ein Thread arbeitet. Die Prüfung
# `self.laeuft` kennt nur den eigenen Worker — ein Doppelklick auf «Auftrag
# fortsetzen» baut aber einen zweiten Worker für denselben Job. Ohne diese
# Liste liefen beide, fragten Kunden doppelt ab und stiessen am Ende auf
# idx_kunde_nr.
_LAUFENDE_JOBS = set()


def auftragsordner(ablage, job_id: int) -> Path:
    """Der eigene Ordner eines Jobs: `<ablage>/auftrag_<nummer>/`."""
    return Path(ablage) / f'auftrag_{job_id}'


class LaeuftBereits(Exception):
    """Es läuft schon ein Auftrag. Die Meldung ist für den Nutzer bestimmt."""


class Worker:
    """Startet, überwacht und stoppt genau einen Lauf im Hintergrund."""

    def __init__(self, provider, datenbank_pfad: str,
                 timeout_sekunden: float = STANDARD_TIMEOUT_SEKUNDEN,
                 arbeiter: int = STANDARD_ARBEITER, modus: str = 'A'):
        self.provider = provider
        self.datenbank_pfad = str(datenbank_pfad)
        self.timeout_sekunden = timeout_sekunden
        self.arbeiter = arbeiter
        self.modus = modus

        self._thread = None
        self._abbruch = threading.Event()
        self.job_id = None
        self.ergebnis = None
        self.fehler = None

    # ------------------------------------------------------------------
    # Starten
    # ------------------------------------------------------------------

    def starten(self, eingabe_pfad: str, ausgabe_ordner: str = None,
                email: str = None, kunden_total: int = 0,
                ablage: str = None) -> int:
        """
        Startet einen neuen Lauf im Hintergrund und kehrt sofort zurück.

        Läuft bereits einer, wird der Start mit einem Hinweis abgewiesen —
        auch dann, wenn der andere Lauf aus einem früheren Programmstart stammt.

        `kunden_total` ist die Zahl, die der Aufrufer schon kennt — die
        Statusanzeige soll nicht eine Sekunde lang „0 von 0" zeigen. Der Lauf
        setzt sie gleich darauf auf den verbindlichen Wert.

        `ablage`: ist sie angegeben, wird die Eingabedatei in den eigenen
        Ordner des Jobs verschoben (`<ablage>/auftrag_<nummer>/`). Die
        Ergebnisdateien entstehen neben der Eingabe (02_DATENVERTRAG.md §2),
        also ebenfalls dort. Zwei Läufe mit gleichem Dateinamen überschreiben
        sich damit nicht mehr gegenseitig.
        """
        with _START_SPERRE:
            self._pruefen_ob_frei()
            # Der Job entsteht hier und nicht erst im Thread: sonst könnte ein
            # zweiter Start in der Lücke dazwischen durchrutschen.
            with Datenbank(self.datenbank_pfad) as datenbank:
                job_id = datenbank.job_anlegen(self.modus,
                                               Path(eingabe_pfad).name,
                                               kunden_total=kunden_total,
                                               email=email)
                datenbank.status_setzen(job_id, 'LAEUFT')
                if ablage is not None:
                    try:
                        eingabe_pfad = self._in_auftragsordner(
                            eingabe_pfad, ablage, job_id)
                    except OSError as fehler:
                        logger.error(f'Eingabe für Job {job_id} nicht ablegbar: {fehler}')
                        datenbank.status_setzen(
                            job_id, 'FEHLER',
                            'Die hochgeladene Datei liess sich nicht ablegen. '
                            'Bitte die Datei noch einmal hochladen.')
                        raise
            self._starten(job_id, eingabe_pfad, ausgabe_ordner)
        return job_id

    @staticmethod
    def _in_auftragsordner(eingabe_pfad: str, ablage: str, job_id: int) -> str:
        ziel_ordner = auftragsordner(ablage, job_id)
        ziel_ordner.mkdir(parents=True, exist_ok=True)
        ziel = ziel_ordner / Path(eingabe_pfad).name
        shutil.move(str(eingabe_pfad), str(ziel))
        return str(ziel)

    def fortsetzen(self, job_id: int, eingabe_pfad: str,
                   ausgabe_ordner: str = None) -> int:
        """Nimmt einen Lauf wieder auf, der im Zustand LAEUFT stehengeblieben ist."""
        with _START_SPERRE:
            if self.laeuft:
                raise LaeuftBereits(
                    f'Es läuft bereits ein Auftrag (Nummer {self.job_id}). '
                    f'Bitte warten oder ihn abbrechen.')
            if job_id in _LAUFENDE_JOBS:
                raise LaeuftBereits(
                    f'Der Auftrag Nummer {job_id} wird bereits fortgesetzt. '
                    f'Bitte warten oder ihn abbrechen.')
            self._starten(job_id, eingabe_pfad, ausgabe_ordner)
        return job_id

    def _pruefen_ob_frei(self) -> None:
        if self.laeuft:
            raise LaeuftBereits(
                f'Es läuft bereits ein Auftrag (Nummer {self.job_id}). '
                f'Bitte warten oder ihn abbrechen.')

        with Datenbank(self.datenbank_pfad) as datenbank:
            offen = datenbank.offener_job()
        if offen:
            raise LaeuftBereits(
                f'Es liegt noch ein unerledigter Auftrag vor (Nummer {offen["id"]}, '
                f'Datei "{offen["dateiname"]}", {offen["kunden_erledigt"]} von '
                f'{offen["kunden_total"]} Kunden). Bitte ihn fortsetzen oder '
                f'abbrechen, bevor ein neuer startet.')

    def _starten(self, job_id: int, eingabe_pfad: str, ausgabe_ordner: str) -> None:
        self._abbruch = threading.Event()
        self.job_id = job_id
        self.ergebnis = None
        self.fehler = None
        _LAUFENDE_JOBS.add(job_id)
        self._thread = threading.Thread(
            target=self._arbeiten, args=(job_id, eingabe_pfad, ausgabe_ordner),
            name=f'lauf-{job_id}', daemon=True)
        self._thread.start()

    def _arbeiten(self, job_id: int, eingabe_pfad: str, ausgabe_ordner: str) -> None:
        # Die Verbindung gehört diesem Thread. SQLite lässt sie nicht wandern.
        #
        # Der Job existiert bereits — beim ersten Start hat ihn `starten`
        # angelegt, beim Fortsetzen steht er seit dem Absturz da. Für den Lauf
        # ist das derselbe Fall: weitermachen bei dem, was noch offen ist.
        datenbank = Datenbank(self.datenbank_pfad)
        try:
            lauf = Lauf(self.provider, datenbank,
                        timeout_sekunden=self.timeout_sekunden,
                        arbeiter=self.arbeiter, abbruch=self._abbruch,
                        modus=self.modus)
            self.ergebnis = lauf.fortsetzen(job_id, eingabe_pfad, ausgabe_ordner)
        except Exception as fehler:
            self.fehler = fehler
            logger.exception(f'Job {job_id} ist gescheitert')
        finally:
            self._bescheid_geben(datenbank, job_id)
            datenbank.schliessen()
            with _START_SPERRE:
                _LAUFENDE_JOBS.discard(job_id)

    def _bescheid_geben(self, datenbank: Datenbank, job_id: int) -> None:
        """
        Mail zum Ende des Laufs — bei FERTIG, ABGEBROCHEN und FEHLER.

        Der Versand darf den Lauf unter keinen Umständen nachträglich kippen:
        Was hier schiefgeht, landet im Protokoll und sonst nirgends.
        """
        try:
            job = datenbank.job_lesen(job_id)
            if not job or job['status'] not in mail.BETREFF_JE_STATUS:
                return
            dateien = (self.ergebnis or {}).get('dateien')
            mail.sende_abschlussmail(job, dateien)
        except Exception as fehler:
            logger.error(f'Bescheid zu Job {job_id} nicht möglich: {fehler}')

    # ------------------------------------------------------------------
    # Abbrechen und warten
    # ------------------------------------------------------------------

    def abbrechen(self) -> None:
        """
        Stoppt den Lauf. Kehrt sofort zurück.

        Zwei Dinge werden gestoppt: die Schleife über die Kunden und der
        Aufruf, der gerade bei der Datenquelle läuft. Ohne das Zweite rechnet
        Apify weiter und stellt in Rechnung, was niemand mehr abholt.
        """
        self._abbruch.set()
        abbrechen_beim_provider = getattr(self.provider, 'abbrechen', None)
        if callable(abbrechen_beim_provider):
            try:
                abbrechen_beim_provider()
            except Exception as fehler:
                logger.warning(f'Die Datenquelle liess sich nicht stoppen: {fehler}')

    def warten(self, timeout: float = None) -> bool:
        """Wartet, bis der Lauf zu Ende ist. True, wenn er zu Ende ist."""
        if not self._thread:
            return True
        self._thread.join(timeout)
        return not self._thread.is_alive()

    @property
    def laeuft(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def fortschritt(self) -> dict:
        """
        Stand des Laufs, gelesen aus der Datenbank.

        Aus der Datenbank und nicht aus dem Gedächtnis, damit die Anzahl auch
        nach einem Neustart des Programms stimmt.
        """
        if not self.job_id:
            return None
        with Datenbank(self.datenbank_pfad) as datenbank:
            return datenbank.fortschritt_lesen(self.job_id)


def offener_lauf(datenbank_pfad: str) -> dict:
    """
    Der Lauf, der beim letzten Mal nicht zu Ende gekommen ist.

    Beim Programmstart aufrufen: steht dort ein Job, wurde er von einem Absturz
    unterbrochen und kann fortgesetzt werden (02_DATENVERTRAG.md §6).
    """
    with Datenbank(datenbank_pfad) as datenbank:
        return datenbank.offener_job()
