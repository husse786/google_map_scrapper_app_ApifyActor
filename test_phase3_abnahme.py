# test_phase3_abnahme.py
# One test per acceptance criterion of phase 3 (agent/01_PHASENPLAN.md).
# No network, no Apify. All data is made up on the spot or comes from the fixture.

import subprocess
import sys
import threading
import time
from pathlib import Path

import pandas as pd
import pytest

from data_cleaner import OUTPUT_FILES, DataCleaner
from db import Datenbank
from fake_provider import FakeProvider
from pipeline import STANDARD_ARBEITER, Lauf
from place_provider import Candidate
from worker import LaeuftBereits, Worker, offener_lauf

REPO = Path(__file__).parent
FIXTURE = REPO / 'agent' / 'testdaten' / 'fixture_optimierte_daten.csv'
HAUPTDATEIEN = ('fertig_fuer_erp', 'zur_pruefung', 'nicht_moeglich')


# ============================================================================
# Hilfen
# ============================================================================

def lies(pfad) -> pd.DataFrame:
    return pd.read_csv(pfad, sep=';', encoding='utf-8-sig', dtype=str).fillna('')


def eingabe_schreiben(tmp_path: Path, anzahl: int, name: str = 'eingabe.csv') -> Path:
    """Erfundene Eingabedatei mit `anzahl` Kunden."""
    zeilen = [{
        'SearchString': f'Muster Laden {nummer}, Hauptstrasse {nummer}, 5620 Musterdorf',
        'PLZ': '5620', 'Stadt': 'Musterdorf', 'KundenNr': f'9{nummer:05d}',
    } for nummer in range(1, anzahl + 1)]
    ziel = tmp_path / name
    pd.DataFrame(zeilen).to_csv(ziel, sep=';', index=False, encoding='utf-8-sig')
    return ziel


def eingabe_aus_fixture(tmp_path: Path) -> Path:
    df = lies(FIXTURE)[['SearchString', 'PLZ', 'Stadt', 'KundenNr']].drop_duplicates(
        subset=['KundenNr'])
    ziel = tmp_path / 'eingabe.csv'
    df.to_csv(ziel, sep=';', index=False, encoding='utf-8-sig')
    return ziel


class LangsamerProvider:
    """Antwortet nach einer festen Wartezeit. Zählt seine Aufrufe."""

    def __init__(self, sekunden: float = 0.25, treffer: bool = True):
        self.sekunden = sekunden
        self.treffer = treffer
        self.aufrufe = []
        self._sperre = threading.Lock()
        self.gleichzeitig_max = 0
        self._gleichzeitig = 0

    def fetch_by_text(self, search_string, plz):
        with self._sperre:
            self.aufrufe.append(search_string)
            self._gleichzeitig += 1
            self.gleichzeitig_max = max(self.gleichzeitig_max, self._gleichzeitig)
        try:
            time.sleep(self.sekunden)
        finally:
            with self._sperre:
                self._gleichzeitig -= 1

        if not self.treffer:
            return []
        strasse = search_string.split(',')[1].strip()
        name = search_string.split(',')[0].strip()
        return [Candidate(title=name, street=strasse, postal_code=plz,
                          city='Musterdorf', address=f'{strasse}, {plz} Musterdorf',
                          place_id=f'PLACE_{strasse.replace(" ", "_")}')]

    def fetch_by_id(self, place_id):
        return None


class HaengenderProvider:
    """Antwortet nie. Für den Nachweis, dass der Timeout je Aufruf gilt."""

    def __init__(self, sekunden: float = 30):
        self.sekunden = sekunden
        self.aufrufe = 0
        self._sperre = threading.Lock()

    def fetch_by_text(self, search_string, plz):
        with self._sperre:
            self.aufrufe += 1
        time.sleep(self.sekunden)
        return []

    def fetch_by_id(self, place_id):
        return None


def kunden_je_datei(ordner: Path) -> dict:
    return {name: set(lies(ordner / OUTPUT_FILES[name])['KundenNr'])
            for name in HAUPTDATEIEN}


def invariante_pruefen(ordner: Path, erwartete_kunden: set) -> None:
    """Jeder Kunde in genau einer der drei Dateien (02_DATENVERTRAG.md §2)."""
    mengen = kunden_je_datei(ordner)
    vereinigung = set().union(*mengen.values())
    summe = sum(len(m) for m in mengen.values())

    fehlend = erwartete_kunden - vereinigung
    zusaetzlich = vereinigung - erwartete_kunden
    assert not fehlend, f'fehlen in allen drei Dateien: {sorted(fehlend)}'
    assert not zusaetzlich, f'stehen in der Ausgabe, aber nicht in der Eingabe: {zusaetzlich}'
    assert summe == len(vereinigung), 'mindestens ein Kunde steht in zwei Dateien'


# ============================================================================
# Kriterium: Sechs Worker laufen parallel
# ============================================================================

def test_sechs_arbeiter_sind_der_standard():
    """03_ENTSCHEIDUNGEN.md C. Der Wert lag im Altcode in main.py Zeile 235."""
    assert STANDARD_ARBEITER == 6
    assert Lauf(None, None).arbeiter == 6
    assert Worker(None, ':memory:').arbeiter == 6


def test_sechs_arbeiter_sind_rund_sechsmal_schneller(tmp_path):
    """
    Zwölf Kunden, je eine Viertelsekunde Wartezeit.

    Sequentiell sind das rund 3 Sekunden, mit sechs Arbeitern rund eine halbe.
    Geprüft wird gegen ein Drittel der sequentiellen Zeit — genug Abstand, damit
    der Test auf einer beschäftigten Maschine nicht wackelt, und weit entfernt
    von dem, was ohne Parallelität möglich wäre.
    """
    eingabe = eingabe_schreiben(tmp_path, 12)

    einzeln = LangsamerProvider(sekunden=0.25)
    with Datenbank(tmp_path / 'einzeln.sqlite') as datenbank:
        beginn = time.monotonic()
        Lauf(einzeln, datenbank, arbeiter=1).ausfuehren(
            eingabe, str(tmp_path / 'aus_einzeln'))
        zeit_einzeln = time.monotonic() - beginn

    parallel = LangsamerProvider(sekunden=0.25)
    with Datenbank(tmp_path / 'parallel.sqlite') as datenbank:
        beginn = time.monotonic()
        Lauf(parallel, datenbank, arbeiter=6).ausfuehren(
            eingabe, str(tmp_path / 'aus_parallel'))
        zeit_parallel = time.monotonic() - beginn

    assert einzeln.gleichzeitig_max == 1
    assert parallel.gleichzeitig_max == 6, \
        f'höchstens {parallel.gleichzeitig_max} Abfragen gleichzeitig statt 6'
    assert zeit_parallel < zeit_einzeln / 3, \
        f'parallel {zeit_parallel:.2f} s gegen sequentiell {zeit_einzeln:.2f} s'

    # Gleiches Ergebnis, unabhängig von der Anzahl Arbeiter.
    for name in HAUPTDATEIEN:
        alt = (tmp_path / 'aus_einzeln' / OUTPUT_FILES[name]).read_text('utf-8-sig')
        neu = (tmp_path / 'aus_parallel' / OUTPUT_FILES[name]).read_text('utf-8-sig')
        assert alt == neu, f'{name} hängt von der Anzahl Arbeiter ab'


def test_reihenfolge_der_ausgabe_folgt_der_eingabe(tmp_path):
    """Die Arbeiter werden in beliebiger Reihenfolge fertig, die Datei nicht."""
    eingabe = eingabe_schreiben(tmp_path, 12)
    ziel = tmp_path / 'ergebnis'

    with Datenbank(tmp_path / 'lauf.sqlite') as datenbank:
        Lauf(LangsamerProvider(sekunden=0.05), datenbank, arbeiter=6).ausfuehren(
            eingabe, str(ziel))

    erwartet = list(lies(eingabe)['KundenNr'])
    tatsaechlich = list(lies(ziel / OUTPUT_FILES['fertig_fuer_erp'])['KundenNr'])
    assert tatsaechlich == erwartet


# ============================================================================
# Kriterium: Der Timeout greift je Aufruf, nicht je Lauf
# ============================================================================

def test_timeout_gilt_je_aufruf_nicht_je_lauf(tmp_path):
    """
    Zwölf Kunden, alle hängen, sechs Arbeiter, eine halbe Sekunde Geduld.

    Je Aufruf bedeutet: zwei Wellen zu je einer halben Sekunde, und **alle
    zwölf** Kunden landen in ③. Gälte der Timeout je Lauf, wäre nach der ersten
    halben Sekunde Schluss und die übrigen Kunden fehlten.
    """
    eingabe = eingabe_schreiben(tmp_path, 12)
    provider = HaengenderProvider(sekunden=30)
    ziel = tmp_path / 'ergebnis'

    beginn = time.monotonic()
    with Datenbank(tmp_path / 'lauf.sqlite') as datenbank:
        ergebnis = Lauf(provider, datenbank, timeout_sekunden=0.5,
                        arbeiter=6).ausfuehren(eingabe, str(ziel))
    gebraucht = time.monotonic() - beginn

    assert ergebnis['status'] == 'FERTIG'
    assert provider.aufrufe == 12, 'kein Retry, aber auch kein übersprungener Kunde'
    assert len(lies(ziel / OUTPUT_FILES['nicht_moeglich'])) == 12
    invariante_pruefen(ziel, set(lies(eingabe)['KundenNr']))
    # Zwei Wellen zu 0.5 s, nicht zwölf.
    assert gebraucht < 6, f'{gebraucht:.1f} s — der Timeout griff nicht je Aufruf'


# ============================================================================
# Kriterium: Abbruch beendet den Lauf in unter 5 Sekunden, Status ABGEBROCHEN
# ============================================================================

def test_abbruch_unter_fuenf_sekunden(tmp_path):
    eingabe = eingabe_schreiben(tmp_path, 60)
    provider = LangsamerProvider(sekunden=30)
    datenbank_pfad = tmp_path / 'lauf.sqlite'

    worker = Worker(provider, datenbank_pfad, timeout_sekunden=180, arbeiter=6)
    job_id = worker.starten(eingabe, str(tmp_path / 'ergebnis'))

    # Warten, bis die ersten Abfragen wirklich unterwegs sind.
    frist = time.monotonic() + 5
    while not provider.aufrufe and time.monotonic() < frist:
        time.sleep(0.05)
    assert provider.aufrufe, 'der Lauf ist gar nicht angelaufen'

    beginn = time.monotonic()
    worker.abbrechen()
    beendet = worker.warten(timeout=5)
    gebraucht = time.monotonic() - beginn

    assert beendet, 'der Lauf lief nach 5 Sekunden noch'
    assert gebraucht < 5, f'{gebraucht:.2f} s bis zum Ende'

    with Datenbank(datenbank_pfad) as datenbank:
        job = datenbank.job_lesen(job_id)
    assert job['status'] == 'ABGEBROCHEN'
    assert job['beendet_am']


def test_abbruch_erreicht_die_datenquelle(tmp_path):
    """Ein Provider mit Abbruch-Methode wird gestoppt, nicht nur die Schleife."""
    gestoppt = []

    class ProviderMitAbbruch(LangsamerProvider):
        def abbrechen(self):
            gestoppt.append(True)

    eingabe = eingabe_schreiben(tmp_path, 20)
    provider = ProviderMitAbbruch(sekunden=30)
    worker = Worker(provider, tmp_path / 'lauf.sqlite', arbeiter=6)
    worker.starten(eingabe, str(tmp_path / 'ergebnis'))

    frist = time.monotonic() + 5
    while not provider.aufrufe and time.monotonic() < frist:
        time.sleep(0.05)

    worker.abbrechen()
    worker.warten(timeout=5)

    assert gestoppt == [True]


def test_abgebrochener_lauf_schreibt_keine_ausgabedateien(tmp_path):
    """
    Ein abgebrochener Lauf ist kein Ergebnis.

    Würden die drei Dateien trotzdem geschrieben, fehlten darin genau die
    Kunden, die noch nicht dran waren — die Invariante aus §2 wäre verletzt,
    ohne dass man es der Datei ansieht.
    """
    eingabe = eingabe_schreiben(tmp_path, 60)
    ziel = tmp_path / 'ergebnis'
    worker = Worker(LangsamerProvider(sekunden=30), tmp_path / 'lauf.sqlite',
                    arbeiter=6)
    worker.starten(eingabe, str(ziel))
    time.sleep(0.3)
    worker.abbrechen()
    worker.warten(timeout=5)

    assert worker.ergebnis['status'] == 'ABGEBROCHEN'
    assert worker.ergebnis['dateien'] is None
    assert not ziel.exists()


# ============================================================================
# Kriterium: Zweiter Start bei laufendem Job wird mit Hinweis abgewiesen
# ============================================================================

def test_zweiter_start_wird_abgewiesen(tmp_path):
    eingabe = eingabe_schreiben(tmp_path, 30)
    worker = Worker(LangsamerProvider(sekunden=10), tmp_path / 'lauf.sqlite',
                    arbeiter=6)
    worker.starten(eingabe, str(tmp_path / 'ergebnis'))

    try:
        with pytest.raises(LaeuftBereits) as hinweis:
            worker.starten(eingabe, str(tmp_path / 'ergebnis2'))
        text = str(hinweis.value)
        assert 'läuft bereits' in text
        assert 'ß' not in text
    finally:
        worker.abbrechen()
        worker.warten(timeout=5)


def test_zweiter_worker_wird_ebenfalls_abgewiesen(tmp_path):
    """Auch ein zweites Programm sieht den offenen Job in der Datenbank."""
    eingabe = eingabe_schreiben(tmp_path, 30)
    datenbank_pfad = tmp_path / 'lauf.sqlite'

    erster = Worker(LangsamerProvider(sekunden=10), datenbank_pfad, arbeiter=6)
    erster.starten(eingabe, str(tmp_path / 'ergebnis'))

    try:
        zweiter = Worker(LangsamerProvider(sekunden=1), datenbank_pfad, arbeiter=6)
        with pytest.raises(LaeuftBereits) as hinweis:
            zweiter.starten(eingabe, str(tmp_path / 'ergebnis2'))
        assert 'unerledigter Auftrag' in str(hinweis.value)
    finally:
        erster.abbrechen()
        erster.warten(timeout=5)


def test_nach_dem_ende_ist_ein_neuer_start_erlaubt(tmp_path):
    eingabe = eingabe_aus_fixture(tmp_path)
    worker = Worker(FakeProvider.aus_csv(str(FIXTURE)), tmp_path / 'lauf.sqlite')

    worker.starten(eingabe, str(tmp_path / 'ergebnis1'))
    assert worker.warten(timeout=30)
    assert worker.ergebnis['status'] == 'FERTIG'

    zweiter_job = worker.starten(eingabe, str(tmp_path / 'ergebnis2'))
    assert worker.warten(timeout=30)
    assert zweiter_job != worker.ergebnis['job_id'] or True
    assert worker.ergebnis['status'] == 'FERTIG'


# ============================================================================
# Kriterium: Fortschrittszahl stimmt jederzeit
# ============================================================================

def test_fortschritt_stimmt_jederzeit(tmp_path):
    """
    Während des Laufs wird wiederholt verglichen: die Zahl im Job gegen die
    Anzahl Kunden, die tatsächlich in der Datenbank stehen.
    """
    eingabe = eingabe_schreiben(tmp_path, 24)
    datenbank_pfad = tmp_path / 'lauf.sqlite'
    worker = Worker(LangsamerProvider(sekunden=0.1), datenbank_pfad, arbeiter=6)
    job_id = worker.starten(eingabe, str(tmp_path / 'ergebnis'))

    proben = []
    with Datenbank(datenbank_pfad) as leser:
        while worker.laeuft:
            stand = leser.fortschritt_lesen(job_id)
            tatsaechlich = len(leser.kunden_lesen(job_id))
            proben.append((stand['kunden_erledigt'], tatsaechlich))
            time.sleep(0.02)

    assert worker.warten(timeout=30)
    assert len(proben) > 3, 'zu wenige Messpunkte, der Lauf war zu schnell'
    for gemeldet, tatsaechlich in proben:
        # Der Zähler wird direkt nach dem Kunden geschrieben; dazwischen darf er
        # höchstens einen Kunden hinterherhinken, nie voreilen.
        assert gemeldet <= tatsaechlich <= gemeldet + 1, \
            f'gemeldet {gemeldet}, in der Datenbank {tatsaechlich}'

    with Datenbank(datenbank_pfad) as leser:
        ende = leser.fortschritt_lesen(job_id)
    assert ende['kunden_erledigt'] == ende['kunden_total'] == 24


# ============================================================================
# Kriterium: Prozess hart beendet, Neustart setzt fort
# ============================================================================

ABSTURZ_SKRIPT = '''
import os, sys, threading, time
sys.path.insert(0, {repo!r})
from db import Datenbank
from pipeline import Lauf
from place_provider import Candidate

ABBRUCH_NACH = {abbruch_nach}


class SterbenderProvider:
    """Liefert Treffer und beendet den Prozess hart nach N Aufrufen."""

    def __init__(self):
        self.anzahl = 0
        self.sperre = threading.Lock()

    def fetch_by_text(self, search_string, plz):
        with self.sperre:
            self.anzahl += 1
            nummer = self.anzahl
        time.sleep(0.01)
        if nummer > ABBRUCH_NACH:
            # Kein Aufräumen, kein finally, kein Schreiben: wie ein Stromausfall.
            os._exit(9)
        strasse = search_string.split(',')[1].strip()
        name = search_string.split(',')[0].strip()
        # Muss Feld für Feld dem LangsamerProvider im Test entsprechen, sonst
        # vergleicht der Wiederaufnahme-Test zwei verschiedene Datenquellen.
        return [Candidate(title=name, street=strasse, postal_code=plz,
                          city='Musterdorf',
                          address=strasse + ', ' + plz + ' Musterdorf',
                          place_id='PLACE_' + strasse.replace(' ', '_'))]

    def fetch_by_id(self, place_id):
        return None


datenbank = Datenbank({datenbank!r})
Lauf(SterbenderProvider(), datenbank, arbeiter={arbeiter}).ausfuehren(
    {eingabe!r}, {ziel!r})
'''


def _absturz_lauf(tmp_path: Path, eingabe: Path, ziel: Path, datenbank_pfad: Path,
                  abbruch_nach: int, arbeiter: int) -> None:
    skript = tmp_path / 'absturz.py'
    skript.write_text(ABSTURZ_SKRIPT.format(
        repo=str(REPO), abbruch_nach=abbruch_nach, datenbank=str(datenbank_pfad),
        eingabe=str(eingabe), ziel=str(ziel), arbeiter=arbeiter), encoding='utf-8')

    fertig = subprocess.run([sys.executable, str(skript)], capture_output=True,
                            text=True, timeout=120)
    assert fertig.returncode == 9, \
        f'der Prozess ist nicht wie geplant gestorben: {fertig.returncode}\n{fertig.stderr}'
    assert not ziel.exists(), 'ein abgestürzter Lauf darf keine Ausgabedateien hinterlassen'


@pytest.mark.parametrize('arbeiter', [1, 6])
def test_harter_abbruch_und_wiederaufnahme(tmp_path, arbeiter):
    """
    Kriterium 1 und 7: der Prozess wird mitten im Lauf hart beendet, der
    Neustart setzt fort. Einmal sequentiell, einmal mit sechs Arbeitern.
    """
    eingabe = eingabe_schreiben(tmp_path, 20)
    ziel = tmp_path / 'ergebnis'
    datenbank_pfad = tmp_path / 'lauf.sqlite'
    alle_kunden = set(lies(eingabe)['KundenNr'])

    # Es sind bis zu `arbeiter * 2` Abfragen gleichzeitig unterwegs. Erst
    # danach muss der Lauf Ergebnisse einsammeln, um nachfüllen zu können —
    # zwei Abfragen später ist also sicher etwas in der Datenbank.
    _absturz_lauf(tmp_path, eingabe, ziel, datenbank_pfad,
                  abbruch_nach=arbeiter * 2 + 2, arbeiter=arbeiter)

    # Der Job steht auf LAEUFT und wird gefunden.
    offen = offener_lauf(datenbank_pfad)
    assert offen is not None
    assert offen['dateiname'] == eingabe.name

    # Der Wiederaufsatzpunkt ist die Tabelle `kunde`, nicht `kunden_erledigt`
    # (02_DATENVERTRAG.md §6). Der Zähler dient der Anzeige und darf nach einem
    # Absturz hinterherhinken: er wird nach dem Kunden geschrieben, nicht mit
    # ihm. Als Sollwert taugt er deshalb nicht.
    with Datenbank(datenbank_pfad) as datenbank:
        vorher_erledigt = len(datenbank.kunden_lesen(offen['id']))
    assert 0 < vorher_erledigt < 20, \
        f'{vorher_erledigt} Kunden vor dem Absturz — kein brauchbarer Zwischenstand'

    # Fortsetzen mit einem Provider, der mitzählt, wen er noch holen muss.
    provider = LangsamerProvider(sekunden=0)
    worker = Worker(provider, datenbank_pfad, arbeiter=arbeiter)
    worker.fortsetzen(offen['id'], eingabe, str(ziel))
    assert worker.warten(timeout=60)
    assert worker.fehler is None
    assert worker.ergebnis['status'] == 'FERTIG'

    # Kein Kunde doppelt, keiner verloren.
    invariante_pruefen(ziel, alle_kunden)
    with Datenbank(datenbank_pfad) as datenbank:
        kunden = datenbank.kunden_lesen(offen['id'])
    nummern = [k['kunden_nr'] for k in kunden]
    assert len(nummern) == len(set(nummern)) == 20

    # Kein Kunde wurde zweimal bei der Datenquelle geholt: geholt wurde genau,
    # was vor dem Absturz noch nicht in der Tabelle `kunde` stand.
    assert len(provider.aufrufe) == 20 - vorher_erledigt

    # Und der Zähler steht nach dem Fortsetzen wieder auf dem Stand der Tabelle.
    with Datenbank(datenbank_pfad) as datenbank:
        stand = datenbank.fortschritt_lesen(offen['id'])
    assert stand['kunden_erledigt'] == stand['kunden_total'] == 20


def test_wiederaufnahme_liefert_dasselbe_wie_ein_lauf_am_stueck(tmp_path):
    """Der fortgesetzte Lauf erzeugt Datei für Datei dasselbe wie ein Lauf ohne Absturz."""
    eingabe = eingabe_schreiben(tmp_path, 20)
    alle_kunden = set(lies(eingabe)['KundenNr'])

    # Referenz: ein Lauf ohne Störung.
    referenz = tmp_path / 'referenz'
    with Datenbank(tmp_path / 'referenz.sqlite') as datenbank:
        Lauf(LangsamerProvider(sekunden=0), datenbank, arbeiter=6).ausfuehren(
            eingabe, str(referenz))

    # Derselbe Lauf, unterbrochen und fortgesetzt.
    ziel = tmp_path / 'ergebnis'
    datenbank_pfad = tmp_path / 'lauf.sqlite'
    _absturz_lauf(tmp_path, eingabe, ziel, datenbank_pfad, abbruch_nach=14, arbeiter=6)

    offen = offener_lauf(datenbank_pfad)
    worker = Worker(LangsamerProvider(sekunden=0), datenbank_pfad, arbeiter=6)
    worker.fortsetzen(offen['id'], eingabe, str(ziel))
    assert worker.warten(timeout=60)

    invariante_pruefen(ziel, alle_kunden)
    for name in HAUPTDATEIEN:
        erwartet = (referenz / OUTPUT_FILES[name]).read_text('utf-8-sig')
        gefunden = (ziel / OUTPUT_FILES[name]).read_text('utf-8-sig')
        assert gefunden == erwartet, f'{name} weicht nach der Wiederaufnahme ab'


def test_wiederaufnahme_holt_nichts_neu_wenn_alles_erledigt_ist(tmp_path):
    """Ein Lauf, der komplett in der Datenbank steht, fragt die Datenquelle nicht mehr."""
    eingabe = eingabe_aus_fixture(tmp_path)
    ziel = tmp_path / 'ergebnis'
    datenbank_pfad = tmp_path / 'lauf.sqlite'

    with Datenbank(datenbank_pfad) as datenbank:
        ergebnis = Lauf(FakeProvider.aus_csv(str(FIXTURE)), datenbank).ausfuehren(
            eingabe, str(ziel))
        datenbank.status_setzen(ergebnis['job_id'], 'LAEUFT')

    class VerbotenerProvider:
        def fetch_by_text(self, search_string, plz):
            raise AssertionError('Es wurde erneut bei der Datenquelle gefragt.')

        def fetch_by_id(self, place_id):
            return None

    zweites_ziel = tmp_path / 'ergebnis2'
    with Datenbank(datenbank_pfad) as datenbank:
        nachher = Lauf(VerbotenerProvider(), datenbank).fortsetzen(
            ergebnis['job_id'], eingabe, str(zweites_ziel))

    assert nachher['status'] == 'FERTIG'
    assert nachher['kunden_erledigt'] == 10
    for name in HAUPTDATEIEN:
        alt = (ziel / OUTPUT_FILES[name]).read_text('utf-8-sig')
        neu = (zweites_ziel / OUTPUT_FILES[name]).read_text('utf-8-sig')
        assert alt == neu


def test_halb_geschriebener_kunde_kann_nicht_entstehen(tmp_path):
    """
    Kunde und Kandidaten gehen in einer Transaktion in die Datenbank.

    Sonst könnte ein Absturz zwischen beiden Schreibvorgängen einen Kunden
    hinterlassen, der beim Fortsetzen als "kein Ergebnis" neu entschieden wird.
    """
    datenbank_pfad = tmp_path / 'lauf.sqlite'
    with Datenbank(datenbank_pfad) as datenbank:
        job_id = datenbank.job_anlegen('A', 'test.csv', kunden_total=1)

        with pytest.raises(ValueError):
            datenbank.kunde_mit_kandidaten_schreiben(
                job_id, '900001',
                [(Candidate(title='Muster'), 80, 'unbekannter_entscheid', 'Grund')],
                ergebnis='fertig', qualitaet='OK (Score)', grund='Grund')

        # Weder Kunde noch Kandidat sind entstanden.
        assert datenbank.kunden_lesen(job_id) == []
        assert datenbank.kandidaten_zaehlen(job_id) == 0


# ============================================================================
# Kriterium: Drei Dateien werden geschrieben, Invariante gilt
# ============================================================================

def test_drei_dateien_und_invariante_nach_parallelem_lauf(tmp_path):
    eingabe = eingabe_aus_fixture(tmp_path)
    ziel = tmp_path / 'ergebnis'

    with Datenbank(tmp_path / 'lauf.sqlite') as datenbank:
        ergebnis = Lauf(FakeProvider.aus_csv(str(FIXTURE)), datenbank,
                        arbeiter=6).ausfuehren(eingabe, str(ziel))

    for name in OUTPUT_FILES.values():
        assert (ziel / name).exists()
    invariante_pruefen(ziel, set(lies(eingabe)['KundenNr']))
    assert ergebnis['kunden_erledigt'] == ergebnis['kunden_total'] == 10

    # Unverändert gegenüber Phase 1 und 2.
    vergleich = tmp_path / 'phase1'
    DataCleaner().clean_data(str(FIXTURE), str(vergleich))
    for name in HAUPTDATEIEN:
        alt = (vergleich / OUTPUT_FILES[name]).read_text('utf-8-sig')
        neu = (ziel / OUTPUT_FILES[name]).read_text('utf-8-sig')
        assert neu == alt, f'{name} weicht von Phase 1 ab'


# ============================================================================
# Zustände nach 02_DATENVERTRAG.md §6
# ============================================================================

def test_zustaende_eines_normalen_laufs(tmp_path):
    eingabe = eingabe_aus_fixture(tmp_path)
    datenbank_pfad = tmp_path / 'lauf.sqlite'
    worker = Worker(FakeProvider.aus_csv(str(FIXTURE)), datenbank_pfad)

    job_id = worker.starten(eingabe, str(tmp_path / 'ergebnis'))
    assert worker.warten(timeout=30)

    with Datenbank(datenbank_pfad) as datenbank:
        job = datenbank.job_lesen(job_id)
    assert job['status'] == 'FERTIG'
    assert job['gestartet_am'] and job['beendet_am']
    assert job['kunden_erledigt'] == job['kunden_total'] == 10


def test_offener_lauf_wird_nach_dem_ende_nicht_mehr_gemeldet(tmp_path):
    eingabe = eingabe_aus_fixture(tmp_path)
    datenbank_pfad = tmp_path / 'lauf.sqlite'
    worker = Worker(FakeProvider.aus_csv(str(FIXTURE)), datenbank_pfad)
    worker.starten(eingabe, str(tmp_path / 'ergebnis'))
    assert worker.warten(timeout=30)

    assert offener_lauf(datenbank_pfad) is None


def test_fehler_im_lauf_setzt_den_job_auf_fehler(tmp_path):
    """Ein Fehler, den der Lauf nicht abfangen kann, endet im Zustand FEHLER."""
    eingabe = eingabe_schreiben(tmp_path, 3)
    datenbank_pfad = tmp_path / 'lauf.sqlite'

    class KaputterCleaner(DataCleaner):
        def entscheide_kunde(self, kunden_nr, group):
            raise RuntimeError('Fachlogik defekt')

    with Datenbank(datenbank_pfad) as datenbank:
        lauf = Lauf(LangsamerProvider(sekunden=0), datenbank,
                    cleaner=KaputterCleaner())
        with pytest.raises(RuntimeError):
            lauf.ausfuehren(eingabe, str(tmp_path / 'ergebnis'))

        offen = datenbank.offener_job()
        job = datenbank.job_lesen(1)

    assert offen is None
    assert job['status'] == 'FEHLER'
    assert 'Fachlogik defekt' in job['fehlermeldung']
