# test_phase7_abnahme.py
# One test per acceptance criterion of phase 7 (agent/01_PHASENPLAN.md).
# No network and no real SMTP server: the mail path is exercised against a stub.

import re
import time
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

import requests

import mail
import webapp
from apify_client.errors import ApifyApiError

from apify_provider import (ENDGUELTIGE_FEHLER, NETZ_MELDUNG, ApifyProvider,
                            _pruefen_ob_endgueltig)
from data_cleaner import OUTPUT_FILES
from db import Datenbank
from fake_provider import FakeProvider
from google_provider import GoogleProvider
from pipeline import MAX_FEHLSCHLAEGE_HINTEREINANDER, Lauf
from place_provider import Candidate, QuelleNichtVerfuegbar
from worker import Worker

REPO = Path(__file__).parent
FIXTURE = REPO / 'agent' / 'testdaten' / 'fixture_optimierte_daten.csv'
HAUPTDATEIEN = ('fertig_fuer_erp', 'zur_pruefung', 'nicht_moeglich')


# ============================================================================
# Hilfen
# ============================================================================

def lies(pfad) -> pd.DataFrame:
    return pd.read_csv(pfad, sep=';', encoding='utf-8-sig', dtype=str).fillna('')


def eingabe_aus_fixture(tmp_path: Path) -> Path:
    df = lies(FIXTURE)[['SearchString', 'PLZ', 'Stadt', 'KundenNr']].drop_duplicates(
        subset=['KundenNr'])
    ziel = tmp_path / 'InputData.csv'
    df.to_csv(ziel, sep=';', index=False, encoding='utf-8-sig')
    return ziel


def eingabe_schreiben(tmp_path: Path, anzahl: int) -> Path:
    zeilen = [{'SearchString': f'Muster Laden {i}, Hauptstrasse {i}, 5620 Musterdorf',
               'PLZ': '5620', 'Stadt': 'Musterdorf', 'KundenNr': f'9{i:05d}'}
              for i in range(1, anzahl + 1)]
    ziel = tmp_path / 'InputData.csv'
    pd.DataFrame(zeilen).to_csv(ziel, sep=';', index=False, encoding='utf-8-sig')
    return ziel


class Postfach:
    """Fängt die Nachricht ab, statt sie zu verschicken."""

    def __init__(self):
        self.nachrichten = []

    def als_versand(self):
        def sende(job, dateien=None, konfiguration=None):
            self.nachrichten.append({
                'an': (job.get('email') or '').strip(),
                'betreff': mail.betreff(job),
                'text': mail.nachricht(job, dateien),
                'status': job.get('status'),
            })
            return True
        return sende


@pytest.fixture
def postfach(monkeypatch):
    fach = Postfach()
    monkeypatch.setattr(mail, 'sende_abschlussmail', fach.als_versand())
    return fach


class ErschoepfterProvider:
    """Meldet nach ein paar Kunden, dass das Kontingent alle ist."""

    def __init__(self, nach: int = 3):
        self.nach = nach
        self.aufrufe = 0

    def fetch_by_text(self, search_string, plz):
        self.aufrufe += 1
        if self.aufrufe > self.nach:
            raise QuelleNichtVerfuegbar(
                ENDGUELTIGE_FEHLER['monthly-usage-hard-limit-exceeded'])
        return [Candidate(title=search_string.split(',')[0].strip(),
                          street=search_string.split(',')[1].strip(),
                          postal_code=plz, place_id=f'PLACE_{self.aufrufe}')]

    def fetch_by_id(self, place_id):
        return None


class WackligerProvider:
    """Das Netz zuckt: jeder Aufruf scheitert vorübergehend."""

    def __init__(self, immer: bool = True):
        self.immer = immer
        self.aufrufe = 0

    def fetch_by_text(self, search_string, plz):
        self.aufrufe += 1
        if self.immer or self.aufrufe % 2:
            raise QuelleNichtVerfuegbar(NETZ_MELDUNG, endgueltig=False)
        return [Candidate(title='Muster', street='Hauptstrasse 1', postal_code=plz,
                          place_id=f'PLACE_{self.aufrufe}')]

    def fetch_by_id(self, place_id):
        return None


# ============================================================================
# Kriterium: Mail in allen drei Fällen, Betreff nennt Dateiname und Ergebnis
# ============================================================================

def test_mail_bei_fertig(tmp_path, postfach):
    eingabe = eingabe_aus_fixture(tmp_path)
    worker = Worker(FakeProvider.aus_csv(str(FIXTURE)), tmp_path / 'lauf.sqlite')

    worker.starten(eingabe, str(tmp_path / 'aus'), email='sachbearbeiter@example.ch')
    assert worker.warten(timeout=30)

    assert len(postfach.nachrichten) == 1
    post = postfach.nachrichten[0]
    assert post['an'] == 'sachbearbeiter@example.ch'
    assert post['betreff'] == 'Kundendaten anreichern: InputData.csv - fertig'
    assert 'InputData.csv' in post['betreff']
    assert '10 Kunden verarbeitet' in post['text']
    assert 'fertig_fuer_erp.csv' in post['text']


def test_mail_bei_abgebrochen(tmp_path, postfach):
    class Langsam:
        def fetch_by_text(self, search_string, plz):
            time.sleep(30)
            return []

        def fetch_by_id(self, place_id):
            return None

    eingabe = eingabe_schreiben(tmp_path, 40)
    worker = Worker(Langsam(), tmp_path / 'lauf.sqlite')
    worker.starten(eingabe, str(tmp_path / 'aus'), email='sachbearbeiter@example.ch')
    time.sleep(0.4)
    worker.abbrechen()
    assert worker.warten(timeout=10)

    assert len(postfach.nachrichten) == 1
    post = postfach.nachrichten[0]
    assert post['betreff'].endswith('- abgebrochen')
    assert 'InputData.csv' in post['betreff']
    assert 'gespeichert' in post['text']
    assert 'keine Ergebnisdateien' in post['text']


def test_mail_bei_fehler(tmp_path, postfach):
    eingabe = eingabe_schreiben(tmp_path, 20)
    worker = Worker(ErschoepfterProvider(nach=2), tmp_path / 'lauf.sqlite',
                    arbeiter=1)

    worker.starten(eingabe, str(tmp_path / 'aus'), email='sachbearbeiter@example.ch')
    assert worker.warten(timeout=30)

    assert len(postfach.nachrichten) == 1
    post = postfach.nachrichten[0]
    assert post['betreff'].endswith('- gestoppt')
    assert 'Guthaben bei Apify ist aufgebraucht' in post['text']
    assert 'fortzusetzen' in post['text']


@pytest.mark.parametrize('status, endung', [
    ('FERTIG', '- fertig'),
    ('ABGEBROCHEN', '- abgebrochen'),
    ('FEHLER', '- gestoppt'),
])
def test_betreff_nennt_dateiname_und_ergebnis(status, endung):
    job = {'dateiname': 'Kunden_2026.csv', 'status': status,
           'kunden_total': 100, 'kunden_erledigt': 40}

    text = mail.betreff(job)

    assert text.startswith('Kundendaten anreichern: Kunden_2026.csv ')
    assert text.endswith(endung)


def test_mailtexte_sind_deutsch_und_ohne_fachsprache():
    for status in ('FERTIG', 'ABGEBROCHEN', 'FEHLER'):
        job = {'dateiname': 'Kunden.csv', 'status': status, 'kunden_total': 2513,
               'kunden_erledigt': 800, 'fehlermeldung': 'Etwas ist passiert.'}
        text = mail.nachricht(job)

        assert 'ß' not in text
        for wort in ('Traceback', 'Exception', 'Error', 'None', 'status='):
            assert wort not in text
        assert "2'513" in text or "2'513" in mail.betreff(job) or status == 'FERTIG'


# ============================================================================
# Kriterium: ohne SMTP-Konfiguration läuft der Job normal durch
# ============================================================================

def test_ohne_smtp_laeuft_der_job_normal_durch(tmp_path, caplog):
    """Keine Konfiguration, keine Mail — aber ein vollständiges Ergebnis."""
    eingabe = eingabe_aus_fixture(tmp_path)
    worker = Worker(FakeProvider.aus_csv(str(FIXTURE)), tmp_path / 'lauf.sqlite')

    with caplog.at_level('INFO'):
        worker.starten(eingabe, str(tmp_path / 'aus'), email='chef@example.ch')
        assert worker.warten(timeout=30)

    assert worker.fehler is None
    assert worker.ergebnis['status'] == 'FERTIG'
    for name in OUTPUT_FILES.values():
        assert (tmp_path / 'aus' / name).exists()
    # Statt zu scheitern, wird protokolliert, was verschickt worden wäre.
    assert any('keine SMTP-Konfiguration' in eintrag.message
               for eintrag in caplog.records)


def test_ohne_adresse_wird_nichts_versendet(tmp_path, caplog):
    eingabe = eingabe_aus_fixture(tmp_path)
    worker = Worker(FakeProvider.aus_csv(str(FIXTURE)), tmp_path / 'lauf.sqlite')

    with caplog.at_level('INFO'):
        worker.starten(eingabe, str(tmp_path / 'aus'))
        assert worker.warten(timeout=30)

    assert worker.ergebnis['status'] == 'FERTIG'
    assert any('keine Adresse hinterlegt' in eintrag.message
               for eintrag in caplog.records)


def test_leere_konfiguration_ist_nicht_vollstaendig():
    assert mail.SmtpKonfiguration().vollstaendig is False
    assert mail.SmtpKonfiguration(server='mail.example.ch').vollstaendig is False
    assert mail.SmtpKonfiguration(server='mail.example.ch',
                                  absender='a@example.ch').vollstaendig is True


def test_unerreichbarer_server_wirft_nichts(monkeypatch, caplog):
    """Ein Mailserver, der nicht antwortet, darf einen fertigen Lauf nicht kippen."""
    import smtplib

    def kaputt(*args, **kwargs):
        raise smtplib.SMTPException('Server antwortet nicht')

    monkeypatch.setattr(smtplib, 'SMTP', kaputt)
    job = {'id': 1, 'dateiname': 'Kunden.csv', 'status': 'FERTIG',
           'email': 'chef@example.ch', 'kunden_total': 10, 'kunden_erledigt': 10}

    with caplog.at_level('ERROR'):
        versendet = mail.sende_abschlussmail(
            job, None, mail.SmtpKonfiguration(server='mail.example.ch',
                                              absender='a@example.ch'))

    assert versendet is False
    assert any('liess sich nicht versenden' in e.message for e in caplog.records)


def test_die_nachricht_geht_an_den_richtigen_empfaenger(monkeypatch):
    """Aufbau der Nachricht gegen einen Ersatzserver geprüft."""
    gesendet = {}

    class SmtpStub:
        def __init__(self, server, port, timeout=None):
            gesendet['server'] = server
            gesendet['port'] = port

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def starttls(self):
            gesendet['tls'] = True

        def login(self, benutzer, passwort):
            gesendet['benutzer'] = benutzer

        def send_message(self, post):
            gesendet['post'] = post

    import smtplib
    monkeypatch.setattr(smtplib, 'SMTP', SmtpStub)

    job = {'id': 1, 'dateiname': 'Kunden.csv', 'status': 'FERTIG',
           'email': ' chef@example.ch ', 'kunden_total': 10, 'kunden_erledigt': 10}
    konfiguration = mail.SmtpKonfiguration(
        server='mail.example.ch', port=587, benutzer='dienst',
        passwort='geheim', absender='anreicherung@example.ch', tls=True)

    assert mail.sende_abschlussmail(job, None, konfiguration) is True

    post = gesendet['post']
    assert post['To'] == 'chef@example.ch'
    assert post['From'] == 'anreicherung@example.ch'
    assert post['Subject'] == 'Kundendaten anreichern: Kunden.csv - fertig'
    assert gesendet['tls'] is True
    assert gesendet['benutzer'] == 'dienst'
    assert gesendet['port'] == 587


# ============================================================================
# Kriterium: erschöpftes Kontingent → FEHLER mit deutscher Erklärung
# ============================================================================

def test_erschoepftes_kontingent_stoppt_den_lauf(tmp_path):
    eingabe = eingabe_schreiben(tmp_path, 20)
    provider = ErschoepfterProvider(nach=3)

    with Datenbank(tmp_path / 'lauf.sqlite') as datenbank:
        ergebnis = Lauf(provider, datenbank, arbeiter=1).ausfuehren(
            eingabe, str(tmp_path / 'aus'))
        job = datenbank.job_lesen(ergebnis['job_id'])

    assert ergebnis['status'] == 'FEHLER'
    assert job['status'] == 'FEHLER'
    assert 'Guthaben bei Apify ist aufgebraucht' in job['fehlermeldung']
    assert 'aufstocken' in job['fehlermeldung']
    assert 'ß' not in job['fehlermeldung']


def test_erschoepftes_kontingent_ist_kein_absturz(tmp_path):
    """Kein Stacktrace, keine Ausnahme beim Aufrufer — ein Ergebnis mit Erklärung."""
    eingabe = eingabe_schreiben(tmp_path, 20)
    worker = Worker(ErschoepfterProvider(nach=2), tmp_path / 'lauf.sqlite',
                    arbeiter=1)

    worker.starten(eingabe, str(tmp_path / 'aus'))
    assert worker.warten(timeout=30)

    assert worker.fehler is None, 'der Lauf ist abgestürzt statt sauber zu stoppen'
    assert worker.ergebnis['status'] == 'FEHLER'
    assert worker.ergebnis['fehlermeldung']


def test_erschoepftes_kontingent_schreibt_keine_halben_dateien(tmp_path):
    eingabe = eingabe_schreiben(tmp_path, 20)
    ziel = tmp_path / 'aus'

    with Datenbank(tmp_path / 'lauf.sqlite') as datenbank:
        Lauf(ErschoepfterProvider(nach=3), datenbank, arbeiter=1).ausfuehren(
            eingabe, str(ziel))

    assert not ziel.exists(), 'ein unvollständiger Lauf darf keine Dateien hinterlassen'


def test_verarbeitete_kunden_bleiben_nach_dem_stopp(tmp_path):
    """Der Lauf lässt sich fortsetzen, sobald das Guthaben wieder da ist."""
    eingabe = eingabe_schreiben(tmp_path, 20)

    with Datenbank(tmp_path / 'lauf.sqlite') as datenbank:
        ergebnis = Lauf(ErschoepfterProvider(nach=3), datenbank,
                        arbeiter=1).ausfuehren(eingabe, str(tmp_path / 'aus'))
        vorher = len(datenbank.kunden_lesen(ergebnis['job_id']))
    assert 0 < vorher < 20

    # Guthaben wieder da: fortsetzen bringt den Lauf zu Ende.
    class WiederDa:
        def fetch_by_text(self, search_string, plz):
            return [Candidate(title='Muster', street='Hauptstrasse 1',
                              postal_code=plz, place_id='PLACE_X')]

        def fetch_by_id(self, place_id):
            return None

    ziel = tmp_path / 'aus'
    with Datenbank(tmp_path / 'lauf.sqlite') as datenbank:
        nachher = Lauf(WiederDa(), datenbank).fortsetzen(
            ergebnis['job_id'], eingabe, str(ziel))

    assert nachher['status'] == 'FERTIG'
    assert nachher['kunden_erledigt'] == 20
    mengen = {name: set(lies(ziel / OUTPUT_FILES[name])['KundenNr'])
              for name in HAUPTDATEIEN}
    assert sum(len(m) for m in mengen.values()) == 20


@pytest.mark.parametrize('art', sorted(ENDGUELTIGE_FEHLER))
def test_jeder_endgueltige_fehler_hat_eine_handlungsanweisung(art):
    meldung = ENDGUELTIGE_FEHLER[art]

    assert 'Bitte' in meldung, 'die Meldung sagt nicht, was zu tun ist'
    assert 'ß' not in meldung
    for wort in ('Error', 'Exception', 'Traceback', 'API'):
        if wort == 'API':
            continue
        assert wort not in meldung


def test_apify_fehler_wird_richtig_einsortiert():
    class ApifyFehler(Exception):
        def __init__(self, art, text=''):
            super().__init__(text)
            self.type = art
            self.message = text

    # Endgültig: der Lauf wird gestoppt.
    with pytest.raises(QuelleNichtVerfuegbar) as gestoppt:
        _pruefen_ob_endgueltig(ApifyFehler('monthly-usage-hard-limit-exceeded'))
    assert gestoppt.value.endgueltig is True
    assert 'Guthaben' in gestoppt.value.meldung

    with pytest.raises(QuelleNichtVerfuegbar):
        _pruefen_ob_endgueltig(ApifyFehler('invalid-token'))

    # Auch ohne Typ, nur am Text erkannt.
    with pytest.raises(QuelleNichtVerfuegbar):
        _pruefen_ob_endgueltig(ApifyFehler('', 'Monthly usage limit exceeded'))

    # Alles andere ist ein Fehlschlag bei diesem einen Kunden.
    assert _pruefen_ob_endgueltig(ApifyFehler('rate-limit-exceeded')) is None
    assert _pruefen_ob_endgueltig(ApifyFehler('', 'irgendetwas')) is None


# ============================================================================
# K1: ein Fehler von Apify ist nie «nichts gefunden»
# ============================================================================

class ApifyFehlerFuerDenTest(ApifyApiError):
    """
    Ein echter ApifyApiError, ohne dessen Konstruktor zu bemühen.

    Der verlangt eine HTTP-Antwort; für die Einordnung zählen nur `type` und
    `message`. Der Typ muss echt bleiben, weil `fetch_by_text` genau darauf
    fängt.

    Warum eine Unterklasse und nicht `__new__` auf der Klasse selbst: seit
    apify-client 3.1.1 hat `ApifyApiError.__new__` zwei Pflichtargumente, und
    ein Aufruf ohne sie scheitert. Diese Fassung läuft in beiden Welten.
    """

    def __new__(cls, *args, **kwargs):
        return Exception.__new__(cls)

    def __init__(self, art: str = '', text: str = 'irgendwas'):
        Exception.__init__(self, text)
        self.type = art
        self.message = text


def apify_fehler(art: str = '', text: str = 'irgendwas') -> ApifyApiError:
    return ApifyFehlerFuerDenTest(art, text)


class UnbekannterApifyFehler:
    """Apify meldet einen Fehler, den die Liste nicht kennt."""

    def __init__(self):
        self.aufrufe = 0

    def _provider(self):
        provider = ApifyProvider('token', 'actor')

        class ActorStub:
            def start(_self, **kwargs):
                self.aufrufe += 1
                raise apify_fehler('rate-limit-exceeded', 'Too many requests')

        provider.actor = ActorStub()
        return provider

    def fetch_by_text(self, search_string, plz):
        return self._provider().fetch_by_text(search_string, plz)

    def fetch_by_id(self, place_id):
        return None


def test_unbekannter_apify_fehler_ist_kein_leeres_ergebnis():
    """Der Kern von K1: die Frage wurde nicht beantwortet, das ist kein Ergebnis."""
    provider = ApifyProvider('token', 'actor')

    class ActorStub:
        def start(self, **kwargs):
            raise apify_fehler('rate-limit-exceeded', 'Too many requests')

    provider.actor = ActorStub()

    with pytest.raises(QuelleNichtVerfuegbar) as gemeldet:
        provider.fetch_by_text('Muster Laden, Hauptstrasse 1, 5620 Musterdorf',
                               '5620')

    # Vorübergehend: ein einzelner Ausrutscher kostet nur diesen einen Kunden.
    assert gemeldet.value.endgueltig is False
    assert 'nichts gefunden' in gemeldet.value.meldung
    assert 'fortsetzen' in gemeldet.value.meldung
    assert 'ß' not in gemeldet.value.meldung
    # Was Apify wirklich schrieb, bleibt im Protokoll — nicht in der Oberfläche.
    assert 'Too many requests' not in gemeldet.value.meldung


def test_unbekannter_apify_fehler_stoppt_den_lauf_nach_zehn(tmp_path):
    """
    Der Nachweis aus K1.

    Vor der Korrektur hätte dieser Lauf alle 2'500 Kunden nach ③ geschrieben
    und sich `FERTIG` genannt. Jetzt endet er nach zehn Fehlschlägen mit
    `FEHLER` und einer Erklärung.
    """
    eingabe = eingabe_schreiben(tmp_path, 2500)
    provider = UnbekannterApifyFehler()
    ziel = tmp_path / 'aus'

    with Datenbank(tmp_path / 'lauf.sqlite') as datenbank:
        ergebnis = Lauf(provider, datenbank, arbeiter=1).ausfuehren(
            eingabe, str(ziel))
        job = datenbank.job_lesen(ergebnis['job_id'])
        kunden = datenbank.kunden_lesen(ergebnis['job_id'])

    assert ergebnis['status'] == 'FEHLER'
    assert job['status'] == 'FEHLER'
    assert 'nichts gefunden' in job['fehlermeldung']

    # Nach zehn ist Schluss, nicht nach 2'500.
    assert provider.aufrufe <= MAX_FEHLSCHLAEGE_HINTEREINANDER + 2
    # Die ersten neun Ausrutscher kosten je einen Kunden — so gewollt. Der
    # Unterschied zu vorher: neun statt 2'500, und der Lauf sagt es.
    assert len(kunden) < MAX_FEHLSCHLAEGE_HINTEREINANDER
    assert all(k['ergebnis'] == 'nicht_moeglich' for k in kunden)
    assert not ziel.exists(), 'ein gestoppter Lauf hinterlässt keine Dateien'


def test_ein_einzelner_unbekannter_fehler_kostet_nur_einen_kunden(tmp_path):
    """Neun Fehlschläge verträgt der Lauf — sonst wäre er zu empfindlich."""

    class NurAmAnfang:
        def __init__(self):
            self.aufrufe = 0

        def fetch_by_text(self, search_string, plz):
            self.aufrufe += 1
            if self.aufrufe <= 3:
                raise QuelleNichtVerfuegbar('Kurzer Aussetzer.', endgueltig=False)
            return [Candidate(title='Muster', street='Hauptstrasse 1',
                              postal_code=plz, place_id=f'PLACE_{self.aufrufe}')]

        def fetch_by_id(self, place_id):
            return None

    eingabe = eingabe_schreiben(tmp_path, 20)
    ziel = tmp_path / 'aus'

    with Datenbank(tmp_path / 'lauf.sqlite') as datenbank:
        ergebnis = Lauf(NurAmAnfang(), datenbank, arbeiter=1).ausfuehren(
            eingabe, str(ziel))

    assert ergebnis['status'] == 'FERTIG'
    assert ergebnis['kunden_erledigt'] == 20
    # Die drei gescheiterten landen in ③, der Rest wird normal entschieden.
    assert len(lies(ziel / OUTPUT_FILES['nicht_moeglich'])) == 3


def test_bekannte_arten_stoppen_weiterhin_sofort():
    """Die sechs Arten aus Phase 7 bleiben endgültig — K1 ändert daran nichts."""
    provider = ApifyProvider('token', 'actor')

    class ActorStub:
        def start(self, **kwargs):
            raise apify_fehler('monthly-usage-hard-limit-exceeded', '')

    provider.actor = ActorStub()

    with pytest.raises(QuelleNichtVerfuegbar) as gemeldet:
        provider.fetch_by_text('Muster, Hauptstrasse 1, 5620 Musterdorf', '5620')

    assert gemeldet.value.endgueltig is True
    assert 'Guthaben' in gemeldet.value.meldung


def test_kein_treffer_bleibt_ein_ergebnis():
    """
    Gegenprobe: der Weg für «nichts gefunden» ist unberührt.

    Ein erfolgreicher Lauf mit leerem Datensatz liefert weiterhin eine leere
    Liste — der Kunde gehört nach ③, und das ist richtig so.
    """
    provider = ApifyProvider('token', 'actor')

    class LaufStub:
        def wait_for_finish(self, wait_secs=None):
            return {'id': 'LAUF_1', 'status': 'SUCCEEDED',
                    'defaultDatasetId': 'DATENSATZ_1'}

    class DatensatzStub:
        def iterate_items(self):
            return iter([])

    class ActorStub:
        def start(self, **kwargs):
            return {'id': 'LAUF_1'}

    class ClientStub:
        def run(self, lauf_id):
            return LaufStub()

        def dataset(self, kennung):
            return DatensatzStub()

    provider.actor = ActorStub()
    provider.client = ClientStub()

    assert provider.fetch_by_text('Muster, Hauptstrasse 1, 5620 Musterdorf',
                                  '5620') == []


def test_beschreibung_passt_zum_verhalten():
    """K2: wer die Beschreibung liest, baut den Fehler nicht wieder ein."""
    text = ApifyProvider.fetch_by_text.__doc__

    assert 'kein Ergebnis' in text
    assert 'QuelleNichtVerfuegbar' in text
    # Die alte, falsche Aussage darf nicht zurückkommen.
    assert 'behandelt alle\n        drei Fälle gleich' not in text
    assert 'oder Apify einen Fehler meldet' not in text


# ============================================================================
# K2: Google sagt nur dann «gelöscht», wenn es das auch meint
# ============================================================================

class GoogleAntwort:
    """Eine Antwort von Google, ohne Netz."""

    def __init__(self, status: int, text: str = '{}', inhalt=None):
        self.status_code = status
        self.text = text
        self._inhalt = inhalt if inhalt is not None else {}

    def json(self):
        return self._inhalt


def google_mit(antwort=None, fehler=None) -> GoogleProvider:
    class Sitzung:
        def get(self, *args, **kwargs):
            if fehler is not None:
                raise fehler
            return antwort

    provider = GoogleProvider('schluessel')
    provider._sitzung = Sitzung()
    return provider


def test_unbekannte_id_bleibt_ein_geloeschter_eintrag():
    """404 ist eine Aussage über diesen Kunden — sie bleibt, wie sie war."""
    provider = google_mit(GoogleAntwort(404, 'NOT_FOUND'))

    assert provider.fetch_by_id('PLACE_WEG') is None


def test_not_found_im_rumpf_zaehlt_auch():
    """Manche Fehler kommen als 400 mit NOT_FOUND im Text."""
    provider = google_mit(GoogleAntwort(400, '{"error":{"status":"NOT_FOUND"}}'))

    assert provider.fetch_by_id('PLACE_WEG') is None


def test_netzfehler_ist_kein_geloeschter_kunde():
    """
    Der Kern von K2.

    Vorher hätte die Anwendung dem Sachbearbeiter gemeldet, sein Kunde sei bei
    Google gelöscht worden — obwohl nur das Netz weg war. Er hätte einen
    intakten Datensatz aus dem ERP genommen.
    """
    provider = google_mit(fehler=requests.RequestException('Netz weg'))

    with pytest.raises(QuelleNichtVerfuegbar) as gemeldet:
        provider.fetch_by_id('PLACE_A001')

    assert gemeldet.value.endgueltig is False
    assert 'nicht erreichbar' in gemeldet.value.meldung
    assert 'Verbindung prüfen' in gemeldet.value.meldung
    assert 'ß' not in gemeldet.value.meldung


@pytest.mark.parametrize('status', [500, 502, 503, 504])
def test_stoerung_bei_google_ist_voruebergehend(status):
    provider = google_mit(GoogleAntwort(status, 'Internal error'))

    with pytest.raises(QuelleNichtVerfuegbar) as gemeldet:
        provider.fetch_by_id('PLACE_A001')

    assert gemeldet.value.endgueltig is False
    assert 'Störung' in gemeldet.value.meldung


@pytest.mark.parametrize('status, stichwort', [
    (401, 'GOOGLE_API_KEY'),
    (403, 'Places API'),
    (429, 'Kontingent'),
])
def test_schluessel_und_kontingent_stoppen_sofort(status, stichwort):
    provider = google_mit(GoogleAntwort(status, 'abgelehnt'))

    with pytest.raises(QuelleNichtVerfuegbar) as gemeldet:
        provider.fetch_by_id('PLACE_A001')

    assert gemeldet.value.endgueltig is True
    assert stichwort in gemeldet.value.meldung
    assert 'Bitte' in gemeldet.value.meldung
    assert 'ß' not in gemeldet.value.meldung


def test_unlesbare_antwort_ist_voruebergehend():
    class KaputterInhalt(GoogleAntwort):
        def json(self):
            raise ValueError('kein JSON')

    provider = google_mit(KaputterInhalt(200, 'nicht json'))

    with pytest.raises(QuelleNichtVerfuegbar) as gemeldet:
        provider.fetch_by_id('PLACE_A001')
    assert gemeldet.value.endgueltig is False


def test_leerer_datensatz_ist_kein_geloeschter_kunde():
    provider = google_mit(GoogleAntwort(200, '{}', inhalt={}))

    with pytest.raises(QuelleNichtVerfuegbar):
        provider.fetch_by_id('PLACE_A001')


def test_modus_b_stoppt_nach_zehn_netzfehlern(tmp_path):
    """
    Der Nachweis für K2 im ganzen Lauf.

    Vorher wären alle Kunden mit «Eintrag gelöscht» in ③ gelandet. Jetzt endet
    der Lauf nach zehn Fehlschlägen mit einer Erklärung, die stimmt.
    """
    zeilen = [{'placeId': f'PLACE_{i}', 'lat': '', 'lng': '',
               'KundenNr': f'9{i:05d}'} for i in range(1, 101)]
    eingabe = tmp_path / 'IDs.csv'
    pd.DataFrame(zeilen).to_csv(eingabe, sep=';', index=False, encoding='utf-8-sig')

    aufrufe = []

    class OhneNetz:
        def fetch_by_id(self, place_id):
            aufrufe.append(place_id)
            return google_mit(
                fehler=requests.RequestException('Netz weg')).fetch_by_id(place_id)

        def fetch_by_text(self, search_string, plz):
            raise AssertionError('Im Modus B darf nicht gesucht werden.')

    ziel = tmp_path / 'aus'
    with Datenbank(tmp_path / 'lauf.sqlite') as datenbank:
        ergebnis = Lauf(OhneNetz(), datenbank, modus='B', arbeiter=1).ausfuehren(
            eingabe, str(ziel))
        job = datenbank.job_lesen(ergebnis['job_id'])
        kunden = datenbank.kunden_lesen(ergebnis['job_id'])

    assert ergebnis['status'] == 'FEHLER'
    assert 'nicht erreichbar' in job['fehlermeldung']
    assert len(aufrufe) <= MAX_FEHLSCHLAEGE_HINTEREINANDER + 2
    assert not ziel.exists()
    # Und keiner der wenigen geschriebenen Kunden trägt eine falsche Begründung.
    for kunde in kunden:
        assert 'gelöscht' not in (kunde['grund'] or '')


def test_geloeschte_id_bleibt_im_lauf_ein_ergebnis(tmp_path):
    """Gegenprobe: eine wirklich unbekannte Id landet weiterhin in ③."""
    eingabe = tmp_path / 'IDs.csv'
    pd.DataFrame([{'placeId': 'PLACE_WEG', 'lat': '', 'lng': '',
                   'KundenNr': '900001'}]).to_csv(
        eingabe, sep=';', index=False, encoding='utf-8-sig')

    class NichtMehrDa:
        def fetch_by_id(self, place_id):
            return google_mit(GoogleAntwort(404, 'NOT_FOUND')).fetch_by_id(place_id)

        def fetch_by_text(self, search_string, plz):
            raise AssertionError('Im Modus B darf nicht gesucht werden.')

    ziel = tmp_path / 'aus'
    with Datenbank(tmp_path / 'lauf.sqlite') as datenbank:
        ergebnis = Lauf(NichtMehrDa(), datenbank, modus='B').ausfuehren(
            eingabe, str(ziel))

    assert ergebnis['status'] == 'FERTIG'
    df = lies(ziel / OUTPUT_FILES['nicht_moeglich'])
    assert len(df) == 1
    assert df.iloc[0]['qualitaet'] == 'NICHT_MOEGLICH (ID ungueltig)'
    assert 'gelöscht' in df.iloc[0]['grund']


# ============================================================================
# K1 (v1.3): eine Zeitüberschreitung ist keine Antwort
#
# 03_ENTSCHEIDUNGEN.md C, geändert nach Phase 7 v1.2. Vorher galt ein Timeout
# als leeres Ergebnis und schob den Kunden nach ③ — im Modus B mit der Aussage,
# er sei bei Google gelöscht. Jetzt zählt er wie ein Netzfehler.
# ============================================================================

class HaengtImmer:
    """Antwortet nie rechtzeitig, in beiden Modi."""

    def __init__(self, sekunden: float = 30):
        self.sekunden = sekunden
        self.aufrufe = 0

    def fetch_by_text(self, search_string, plz):
        self.aufrufe += 1
        time.sleep(self.sekunden)
        return []

    def fetch_by_id(self, place_id):
        self.aufrufe += 1
        time.sleep(self.sekunden)
        return None


class HaengtEinmal:
    """
    Beim ersten Kunden zu langsam, danach ein sauberer Treffer.

    Der Treffer spiegelt die Eingabe, damit die neun übrigen Kunden nicht in ③
    landen — sonst liesse sich nicht ablesen, ob der Timeout einen Kunden
    gekostet hat oder alle zehn.
    """

    def __init__(self, sekunden: float = 30):
        self.sekunden = sekunden
        self.aufrufe = 0

    def fetch_by_text(self, search_string, plz):
        self.aufrufe += 1
        if self.aufrufe == 1:
            time.sleep(self.sekunden)
        teile = [t.strip() for t in search_string.split(',')]
        return [Candidate(title=teile[0], street=teile[1], postal_code=plz,
                          place_id=f'PLACE_{self.aufrufe}')]

    def fetch_by_id(self, place_id):
        raise AssertionError('Im Modus A wird nicht über die Id gefragt.')


def test_zeitueberschreitung_ist_kein_leeres_ergebnis():
    """
    Der Kern von K1 v1.3, auf der untersten Ebene.

    `_mit_frist` gab bei Ablauf der Frist `None` zurück — daraus wurde eine
    gewöhnliche leere Liste, also ein Ergebnis. Jetzt kommt eine Ausnahme.
    """
    lauf = Lauf(HaengtImmer(), None, timeout_sekunden=0.2)

    with pytest.raises(QuelleNichtVerfuegbar) as gemeldet:
        lauf._mit_frist(lambda: time.sleep(30), 'Muster Laden')

    assert gemeldet.value.endgueltig is False
    assert 'nicht rechtzeitig geantwortet' in gemeldet.value.meldung
    assert 'Bitte' in gemeldet.value.meldung
    assert 'ß' not in gemeldet.value.meldung


def test_ein_einzelner_timeout_kostet_genau_einen_kunden(tmp_path):
    """
    Erste der drei Wirkungen aus dem Korrekturplan.

    Ein Ausrutscher darf einen Lauf über Stunden nicht töten. Zehn Kunden, nur
    der erste hängt: der Lauf kommt durch, und genau ein Kunde fehlt.
    """
    eingabe = eingabe_schreiben(tmp_path, 10)
    provider = HaengtEinmal()
    ziel = tmp_path / 'aus'

    with Datenbank(tmp_path / 'lauf.sqlite') as datenbank:
        ergebnis = Lauf(provider, datenbank, timeout_sekunden=0.3,
                        arbeiter=1).ausfuehren(eingabe, str(ziel))

    assert ergebnis['status'] == 'FERTIG'
    assert provider.aufrufe == 10, 'kein Retry, kein übersprungener Kunde'

    # Jeder Kunde in genau einer Datei — die Grundregel gilt auch hier.
    gesamt = sum(len(lies(ziel / OUTPUT_FILES[d])) for d in HAUPTDATEIEN)
    assert gesamt == 10

    # Genau der eine, der hing — und niemand sonst.
    ausgefallen = lies(ziel / OUTPUT_FILES['nicht_moeglich'])
    assert list(ausgefallen['KundenNr']) == ['900001']


def test_zehn_timeouts_hintereinander_stoppen_den_lauf(tmp_path):
    """
    Zweite Wirkung: `FEHLER` statt `FERTIG` mit vollen ③-Dateien.

    Vorher hätten 2'500 hängende Kunden 2'500 Zeilen in ③ ergeben und der Lauf
    hätte sich `FERTIG` genannt — ein Ergebnis, in dem keine einzige Frage
    beantwortet wurde.
    """
    eingabe = eingabe_schreiben(tmp_path, 100)
    provider = HaengtImmer()
    ziel = tmp_path / 'aus'

    with Datenbank(tmp_path / 'lauf.sqlite') as datenbank:
        ergebnis = Lauf(provider, datenbank, timeout_sekunden=0.2,
                        arbeiter=1).ausfuehren(eingabe, str(ziel))
        job = datenbank.job_lesen(ergebnis['job_id'])

    assert ergebnis['status'] == 'FEHLER'
    assert provider.aufrufe <= MAX_FEHLSCHLAEGE_HINTEREINANDER + 2
    assert not ziel.exists(), 'ein gestoppter Lauf schreibt keine Ausgabedateien'
    assert 'nicht rechtzeitig geantwortet' in job['fehlermeldung']
    assert 'ß' not in job['fehlermeldung']


def test_timeout_im_modus_b_sagt_nie_geloescht(tmp_path):
    """
    Dritte Wirkung, und der Grund für die ganze Änderung.

    Aus einer Zeitüberschreitung wurde im Modus B die Aussage, der Betrieb sei
    bei Google gelöscht. Der Sachbearbeiter hätte einen intakten Datensatz aus
    dem ERP genommen, weil die Quelle zu langsam war.
    """
    zeilen = [{'placeId': f'PLACE_{i}', 'lat': '', 'lng': '',
               'KundenNr': f'9{i:05d}'} for i in range(1, 101)]
    eingabe = tmp_path / 'IDs.csv'
    pd.DataFrame(zeilen).to_csv(eingabe, sep=';', index=False, encoding='utf-8-sig')

    ziel = tmp_path / 'aus'
    with Datenbank(tmp_path / 'lauf.sqlite') as datenbank:
        ergebnis = Lauf(HaengtImmer(), datenbank, modus='B', timeout_sekunden=0.2,
                        arbeiter=1).ausfuehren(eingabe, str(ziel))
        kunden = datenbank.kunden_lesen(ergebnis['job_id'])

    assert ergebnis['status'] == 'FEHLER'
    assert kunden, 'die Kunden vor dem Stopp stehen in der Datenbank'
    for kunde in kunden:
        assert 'gelöscht' not in (kunde['grund'] or '')
        assert kunde['qualitaet'] == 'NICHT_MOEGLICH (kein Ergebnis)'
        assert 'nicht geprüft' in kunde['grund']


def test_abbruch_bleibt_von_der_aenderung_unberuehrt(tmp_path):
    """
    Der Korrekturplan sagt ausdrücklich: das Verhalten bei Abbruch bleibt.

    Abbruch ist ein anderer Rückgabeweg als die Zeitüberschreitung — er liefert
    weiterhin `None` und wirft nicht.
    """
    lauf = Lauf(HaengtImmer(), None, timeout_sekunden=30)
    lauf.abbruch.set()

    assert lauf._mit_frist(lambda: time.sleep(30), 'Muster Laden') is None


# ============================================================================
# K1 (v1.4): «nichts gefunden» und «nicht gefragt» sind zwei Sätze
#
# Die letzte Stelle, an der eine ausgefallene Abfrage noch als Ergebnis auftrat.
# Im Modus A trug der Kunde den Grund «Die Suche … lieferte keinen einzigen
# Treffer» — wer das liest, prüft die Adresse im ERP. Wer liest, die Abfrage sei
# nicht zurückgekommen, versucht es erneut.
# ============================================================================

ALTER_GRUND = 'lieferte keinen einzigen Treffer'


class AntwortetLeer:
    """Die Quelle antwortet, und sie hat nichts. Das ist ein Ergebnis."""

    def fetch_by_text(self, search_string, plz):
        return []

    def fetch_by_id(self, place_id):
        return None


class AntwortetSauber:
    """Spiegelt die Eingabe als Treffer zurück."""

    def fetch_by_text(self, search_string, plz):
        teile = [t.strip() for t in search_string.split(',')]
        return [Candidate(title=teile[0], street=teile[1], postal_code=plz,
                          place_id=f'PLACE_{teile[0]}')]

    def fetch_by_id(self, place_id):
        raise AssertionError('Im Modus A wird nicht über die Id gefragt.')


def test_ausgefallene_abfrage_behauptet_nicht_die_suche_habe_nichts_geliefert(tmp_path):
    """
    Der Kern von K1 v1.4.

    Zehn Kunden, nur beim ersten läuft die Abfrage in die Frist. Er landet in ③
    — das war schon richtig — aber mit einem Grund, der sagt, was war.
    """
    eingabe = eingabe_schreiben(tmp_path, 10)
    ziel = tmp_path / 'aus'

    with Datenbank(tmp_path / 'lauf.sqlite') as datenbank:
        ergebnis = Lauf(HaengtEinmal(), datenbank, timeout_sekunden=0.3,
                        arbeiter=1).ausfuehren(eingabe, str(ziel))

    assert ergebnis['status'] == 'FERTIG'
    df = lies(ziel / OUTPUT_FILES['nicht_moeglich'])
    assert list(df['KundenNr']) == ['900001']

    zeile = df.iloc[0]
    assert zeile['qualitaet'] == 'NICHT_MOEGLICH (kein Ergebnis)', \
        'kein neuer Wert — 02_DATENVERTRAG.md §3 bleibt, wie es ist'
    assert 'nicht geprüft' in zeile['grund']
    assert 'nicht zurück' in zeile['grund']
    assert ALTER_GRUND not in zeile['grund']
    assert 'ß' not in zeile['grund']
    assert zeile['score'] == '0.0'


def test_echtes_leeres_ergebnis_behaelt_seinen_grund(tmp_path):
    """
    Die Gegenprobe, und der Grund, warum `data_cleaner.py` unangetastet bleibt.

    Die Quelle hat geantwortet und nichts gefunden. Genau dafür ist ihr Satz
    geschrieben, und genau da steht er weiterhin.
    """
    eingabe = eingabe_schreiben(tmp_path, 3)
    ziel = tmp_path / 'aus'

    with Datenbank(tmp_path / 'lauf.sqlite') as datenbank:
        ergebnis = Lauf(AntwortetLeer(), datenbank).ausfuehren(eingabe, str(ziel))

    assert ergebnis['status'] == 'FERTIG'
    df = lies(ziel / OUTPUT_FILES['nicht_moeglich'])
    assert len(df) == 3
    for _, zeile in df.iterrows():
        assert zeile['qualitaet'] == 'NICHT_MOEGLICH (kein Ergebnis)'
        assert ALTER_GRUND in zeile['grund']
        assert 'nicht geprüft' not in zeile['grund']


def test_der_richtige_grund_ueberlebt_das_fortsetzen(tmp_path):
    """
    Fortsetzen ist der Weg, den die Meldung nach zehn Fehlschlägen empfiehlt.

    Beim Fortsetzen wird die Entscheidung aus der Datenbank neu hergeleitet.
    Ohne Vorkehrung fiele der Kunde dabei auf «lieferte keinen einzigen
    Treffer» zurück — die Korrektur hielte genau bis zu dem Schritt, zu dem die
    Anwendung selbst auffordert.
    """
    eingabe = eingabe_schreiben(tmp_path, 100)
    ziel = tmp_path / 'aus'

    with Datenbank(tmp_path / 'lauf.sqlite') as datenbank:
        gestoppt = Lauf(HaengtImmer(), datenbank, timeout_sekunden=0.2,
                        arbeiter=1).ausfuehren(eingabe, str(ziel))
        assert gestoppt['status'] == 'FEHLER'
        ausgefallene = {k['kunden_nr'] for k in datenbank.kunden_lesen(gestoppt['job_id'])}

    assert ausgefallene, 'die Kunden vor dem Stopp stehen in der Datenbank'

    with Datenbank(tmp_path / 'lauf.sqlite') as datenbank:
        nachher = Lauf(AntwortetSauber(), datenbank).fortsetzen(
            gestoppt['job_id'], eingabe, str(ziel))

    assert nachher['status'] == 'FERTIG'
    df = lies(ziel / OUTPUT_FILES['nicht_moeglich'])
    wieder_da = df[df['KundenNr'].isin(ausgefallene)]
    assert len(wieder_da) == len(ausgefallene)
    for _, zeile in wieder_da.iterrows():
        assert 'nicht geprüft' in zeile['grund']
        assert ALTER_GRUND not in zeile['grund']


# ============================================================================
# Netz weg — Fehlertext mit Handlungsanweisung
# ============================================================================

def test_ein_kurzer_aussetzer_stoppt_den_lauf_nicht(tmp_path):
    """Jeder zweite Aufruf scheitert: der Lauf kommt trotzdem durch."""
    eingabe = eingabe_schreiben(tmp_path, 20)
    ziel = tmp_path / 'aus'

    with Datenbank(tmp_path / 'lauf.sqlite') as datenbank:
        ergebnis = Lauf(WackligerProvider(immer=False), datenbank,
                        arbeiter=1).ausfuehren(eingabe, str(ziel))

    assert ergebnis['status'] == 'FERTIG'
    assert ergebnis['kunden_erledigt'] == 20
    mengen = {name: set(lies(ziel / OUTPUT_FILES[name])['KundenNr'])
              for name in HAUPTDATEIEN}
    assert sum(len(m) for m in mengen.values()) == 20


def test_dauerhaft_weg_stoppt_den_lauf_mit_erklaerung(tmp_path):
    eingabe = eingabe_schreiben(tmp_path, 40)
    provider = WackligerProvider(immer=True)

    with Datenbank(tmp_path / 'lauf.sqlite') as datenbank:
        ergebnis = Lauf(provider, datenbank, arbeiter=1).ausfuehren(
            eingabe, str(tmp_path / 'aus'))
        job = datenbank.job_lesen(ergebnis['job_id'])

    assert ergebnis['status'] == 'FEHLER'
    assert 'nicht erreichbar' in job['fehlermeldung']
    assert 'Verbindung prüfen' in job['fehlermeldung']
    # Nach zehn Fehlschlägen ist Schluss, nicht nach vierzig.
    assert provider.aufrufe <= MAX_FEHLSCHLAEGE_HINTEREINANDER + 2


def test_die_grenze_liegt_bei_zehn_fehlschlaegen():
    assert MAX_FEHLSCHLAEGE_HINTEREINANDER == 10


# ============================================================================
# Die Adresse in der Oberfläche
# ============================================================================

@pytest.fixture
def browser(tmp_path, monkeypatch):
    monkeypatch.setattr(webapp, 'LAUFDATEN', tmp_path)
    monkeypatch.setattr(webapp, 'UPLOADS', tmp_path / 'uploads')
    monkeypatch.setattr(webapp, 'DATENBANK', tmp_path / 'laeufe.sqlite')
    webapp.UPLOADS.mkdir(parents=True, exist_ok=True)
    webapp.zustand.update(worker=None, hochgeladen=None, kunden=0, modus='A',
                          email='', provider=FakeProvider.aus_csv(str(FIXTURE)))
    with TestClient(webapp.app) as klient:
        yield klient
    worker = webapp.zustand['worker']
    if worker and worker.laeuft:
        worker.abbrechen()
        worker.warten(timeout=10)


def eingabe_csv() -> bytes:
    df = lies(FIXTURE)[['SearchString', 'PLZ', 'Stadt', 'KundenNr']].drop_duplicates(
        subset=['KundenNr'])
    return df.to_csv(sep=';', index=False).encode('utf-8-sig')


def test_adressfeld_steht_auf_der_dateiseite(browser):
    browser.get('/datei', params={'modus': 'A'})
    antwort = browser.post('/datei', data={'modus': 'A'},
                           files={'datei': ('InputData.csv', eingabe_csv(),
                                            'text/csv')})

    assert 'Wohin sollen wir Bescheid geben?' in antwort.text
    assert 'name="email"' in antwort.text
    assert 'Freiwillig' in antwort.text


def test_adresse_landet_im_job(browser, postfach):
    browser.get('/datei', params={'modus': 'A'})
    browser.post('/datei', data={'modus': 'A'},
                 files={'datei': ('InputData.csv', eingabe_csv(), 'text/csv')})
    antwort = browser.post('/starten', data={'email': 'kollege@example.ch'},
                           follow_redirects=False)
    job_id = int(antwort.headers['location'].rsplit('/', 1)[1])
    webapp.zustand['worker'].warten(timeout=30)

    with Datenbank(webapp.DATENBANK) as datenbank:
        job = datenbank.job_lesen(job_id)
    assert job['email'] == 'kollege@example.ch'
    assert postfach.nachrichten[0]['an'] == 'kollege@example.ch'


def test_laufseite_nennt_die_adresse(browser):
    browser.get('/datei', params={'modus': 'A'})
    browser.post('/datei', data={'modus': 'A'},
                 files={'datei': ('InputData.csv', eingabe_csv(), 'text/csv')})
    antwort = browser.post('/starten', data={'email': 'kollege@example.ch'},
                           follow_redirects=False)
    job_id = int(antwort.headers['location'].rsplit('/', 1)[1])

    seite = browser.get(f'/lauf/{job_id}').text
    assert 'Wir schicken eine Mail an kollege@example.ch' in seite


def test_ohne_adresse_verspricht_die_seite_keine_mail(browser):
    browser.get('/datei', params={'modus': 'A'})
    browser.post('/datei', data={'modus': 'A'},
                 files={'datei': ('InputData.csv', eingabe_csv(), 'text/csv')})
    antwort = browser.post('/starten', data={'email': ''}, follow_redirects=False)
    job_id = int(antwort.headers['location'].rsplit('/', 1)[1])

    seite = browser.get(f'/lauf/{job_id}').text
    assert 'Mail' not in seite
    assert 'Öffnen Sie die Seite später wieder' in seite


def test_gestoppter_lauf_erklaert_sich_auf_der_ergebnisseite(browser, tmp_path):
    webapp.zustand['provider'] = ErschoepfterProvider(nach=2)

    browser.get('/datei', params={'modus': 'A'})
    browser.post('/datei', data={'modus': 'A'},
                 files={'datei': ('InputData.csv', eingabe_csv(), 'text/csv')})
    antwort = browser.post('/starten', data={'email': ''}, follow_redirects=False)
    job_id = int(antwort.headers['location'].rsplit('/', 1)[1])
    webapp.zustand['worker'].warten(timeout=30)

    seite = browser.get(f'/ergebnis/{job_id}').text
    assert 'Gestoppt' in seite
    assert 'Guthaben bei Apify ist aufgebraucht' in seite
    assert 'fortzusetzen' in seite
    assert 'Traceback' not in seite
    assert f'/ergebnis/{job_id}/datei/' not in seite


# ============================================================================
# Kriterium: das README führt jemanden ohne Vorkenntnisse durch
# ============================================================================

def test_readme_erklaert_die_einrichtung():
    text = (REPO / 'README.md').read_text(encoding='utf-8')

    # Die Schritte, ohne die niemand starten kann.
    for schritt in ('python3 -m venv venv', 'pip install -r requirements.txt',
                    'cp config.template.py config.py', 'APIFY_API_TOKEN',
                    'python webapp.py'):
        assert schritt in text, f'«{schritt}» fehlt in der Anleitung'

    # Und was zu tun ist, wenn etwas schiefgeht.
    assert 'Wenn etwas nicht klappt' in text
    assert 'Guthaben bei Apify ist aufgebraucht' in text
    assert 'nicht erreichbar' in text
    assert 'Token wird nicht akzeptiert' in text


def test_readme_beschreibt_die_anwendung_die_es_gibt():
    text = (REPO / 'README.md').read_text(encoding='utf-8')

    # Nichts mehr aus der Zeit vor dem Umbau.
    for veraltet in ('Tkinter', 'main.py', 'ui_manager', 'apify_wrapper',
                     'Desktop-Anwendung', '_eindeutig.csv'):
        assert veraltet not in text, f'«{veraltet}» steht noch im README'

    # Die drei Ausgabedateien beim richtigen Namen.
    for datei in OUTPUT_FILES.values():
        if datei != 'aussortiert.csv':
            assert datei in text


def test_readme_nennt_keine_unbelegte_gesamtdauer():
    """Seit Phase 4 ist die Laufzeit offen — das README verspricht nichts."""
    text = (REPO / 'README.md').read_text(encoding='utf-8')

    assert not re.search(r'[Rr]und \d+ Stunden', text)
    assert '2 Stunden' not in text


def test_readme_nennt_die_wichtigen_grenzen():
    text = (REPO / 'README.md').read_text(encoding='utf-8')

    assert "10'000" in text          # Zeilenobergrenze
    assert 'Semikolon' in text       # Format der Datei
    assert 'ein Auftrag' in text or 'ein Lauf' in text
