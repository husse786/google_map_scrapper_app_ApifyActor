# test_phase7_abnahme.py
# One test per acceptance criterion of phase 7 (agent/01_PHASENPLAN.md).
# No network and no real SMTP server: the mail path is exercised against a stub.

import re
import time
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

import mail
import webapp
from apify_provider import ENDGUELTIGE_FEHLER, NETZ_MELDUNG, _pruefen_ob_endgueltig
from data_cleaner import OUTPUT_FILES
from db import Datenbank
from fake_provider import FakeProvider
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
