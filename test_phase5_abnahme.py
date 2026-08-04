# test_phase5_abnahme.py
# One test per acceptance criterion of phase 5 (agent/01_PHASENPLAN.md).
# The whole flow runs through the HTTP interface, never by calling internals.
# No network: the answers come from the invented fixture.

import re
import signal
import subprocess
import sys
import time
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

import webapp
from db import Datenbank
from fake_provider import FakeProvider

REPO = Path(__file__).parent
FIXTURE = REPO / 'agent' / 'testdaten' / 'fixture_optimierte_daten.csv'
AUSGABEN = ('fertig_fuer_erp', 'zur_pruefung', 'nicht_moeglich')


# ============================================================================
# Hilfen
# ============================================================================

def eingabe_csv() -> bytes:
    """Die Fixture als Eingabedatei im Modus A."""
    df = pd.read_csv(FIXTURE, sep=';', encoding='utf-8-sig', dtype=str).fillna('')
    df = df[['SearchString', 'PLZ', 'Stadt', 'KundenNr']].drop_duplicates(
        subset=['KundenNr'])
    return df.to_csv(sep=';', index=False).encode('utf-8-sig')


@pytest.fixture
def app(tmp_path, monkeypatch):
    """Die Anwendung mit eigenen Ordnern und eigener Datenbank."""
    monkeypatch.setattr(webapp, 'LAUFDATEN', tmp_path)
    monkeypatch.setattr(webapp, 'UPLOADS', tmp_path / 'uploads')
    monkeypatch.setattr(webapp, 'DATENBANK', tmp_path / 'laeufe.sqlite')
    webapp.UPLOADS.mkdir(parents=True, exist_ok=True)
    webapp.zustand['worker'] = None
    webapp.zustand['hochgeladen'] = None
    webapp.zustand['kunden'] = 0
    webapp.zustand['provider'] = FakeProvider.aus_csv(str(FIXTURE))
    yield webapp
    worker = webapp.zustand['worker']
    if worker and worker.laeuft:
        worker.abbrechen()
        worker.warten(timeout=10)


@pytest.fixture
def browser(app):
    with TestClient(app.app) as klient:
        yield klient


def lauf_durchfuehren(browser, inhalt: bytes = None, name: str = 'InputData.csv') -> int:
    """Der Weg des Nutzers: Art wählen, Datei hochladen, starten, warten."""
    browser.get('/')
    browser.get('/datei', params={'modus': 'A'})
    browser.post('/datei', files={'datei': (name, inhalt or eingabe_csv(), 'text/csv')})
    antwort = browser.post('/starten', follow_redirects=False)
    job_id = int(antwort.headers['location'].rsplit('/', 1)[1])

    frist = time.monotonic() + 30
    while time.monotonic() < frist:
        if not webapp.zustand['worker'].laeuft:
            break
        time.sleep(0.05)
    webapp.zustand['worker'].warten(timeout=10)
    return job_id


# ============================================================================
# Kriterium: vollständiger Durchlauf, nur im Browser
# ============================================================================

def test_vollstaendiger_durchlauf_ohne_terminal(browser):
    """Vier Seiten, ein Weg: Art wählen, Datei, Lauf, Ergebnis."""
    start = browser.get('/')
    assert start.status_code == 200
    assert 'Was haben Sie zu den Kunden?' in start.text

    formular = browser.get('/datei', params={'modus': 'A'})
    assert formular.status_code == 200
    assert 'Datei hochladen' in formular.text

    hochgeladen = browser.post(
        '/datei', files={'datei': ('InputData.csv', eingabe_csv(), 'text/csv')})
    assert hochgeladen.status_code == 200
    assert '10 Kunden erkannt' in hochgeladen.text
    assert 'Lauf starten' in hochgeladen.text

    gestartet = browser.post('/starten', follow_redirects=False)
    assert gestartet.status_code == 303
    job_id = int(gestartet.headers['location'].rsplit('/', 1)[1])

    lauf = browser.get(f'/lauf/{job_id}')
    assert lauf.status_code == 200

    webapp.zustand['worker'].warten(timeout=30)

    ergebnis = browser.get(f'/ergebnis/{job_id}')
    assert ergebnis.status_code == 200
    assert 'Fertig' in ergebnis.text
    assert 'Herunterladen' in ergebnis.text

    with Datenbank(webapp.DATENBANK) as datenbank:
        job = datenbank.job_lesen(job_id)
    assert job['status'] == 'FERTIG'
    assert job['kunden_erledigt'] == job['kunden_total'] == 10


def test_ergebnisseite_zeigt_die_drei_zahlen(browser):
    job_id = lauf_durchfuehren(browser)
    seite = browser.get(f'/ergebnis/{job_id}').text

    for titel in ('Fertig fürs ERP', 'Zur Prüfung', 'Nicht möglich'):
        assert titel in seite
    # Die Verteilung der Fixture: 6 / 3 / 1.
    zahlen = re.findall(r'<p class="zahl gross">(\d+)</p>', seite)
    assert zahlen == ['6', '3', '1']


# ============================================================================
# Kriterium: Fortschrittsanzeige aktualisiert sich ohne Neuladen
# ============================================================================

def test_statusseite_laedt_den_stand_alle_fuenf_sekunden(browser):
    job_id = lauf_durchfuehren(browser)
    seite = browser.get(f'/lauf/{job_id}').text

    assert 'htmx.min.js' in seite
    assert f'hx-get="/lauf/{job_id}/stand"' in seite or 'Fertig' in seite


def test_stand_ist_ein_ausschnitt_keine_ganze_seite(app, browser, monkeypatch):
    """Der Ausschnitt trägt die Anweisung, sich alle 5 Sekunden zu erneuern."""
    langsam = _LangsamerProvider(FakeProvider.aus_csv(str(FIXTURE)), 10)
    webapp.zustand['provider'] = langsam

    browser.get('/datei', params={'modus': 'A'})
    browser.post('/datei', files={'datei': ('InputData.csv', eingabe_csv(), 'text/csv')})
    antwort = browser.post('/starten', follow_redirects=False)
    job_id = int(antwort.headers['location'].rsplit('/', 1)[1])

    try:
        stand = browser.get(f'/lauf/{job_id}/stand')
        assert stand.status_code == 200
        assert '<!DOCTYPE html>' not in stand.text
        assert 'hx-trigger="every 5s"' in stand.text
        assert 'von 10 Kunden' in stand.text
        assert 'HX-Redirect' not in stand.headers
    finally:
        webapp.zustand['worker'].abbrechen()
        webapp.zustand['worker'].warten(timeout=10)


def test_stand_schickt_am_ende_zur_ergebnisseite(browser):
    job_id = lauf_durchfuehren(browser)
    stand = browser.get(f'/lauf/{job_id}/stand')

    assert stand.headers.get('HX-Redirect') == f'/ergebnis/{job_id}'
    assert 'hx-trigger' not in stand.text


def test_fortschritt_waechst_waehrend_des_laufs(browser):
    langsam = _LangsamerProvider(FakeProvider.aus_csv(str(FIXTURE)), 0.3)
    webapp.zustand['provider'] = langsam

    browser.get('/datei', params={'modus': 'A'})
    browser.post('/datei', files={'datei': ('InputData.csv', eingabe_csv(), 'text/csv')})
    antwort = browser.post('/starten', follow_redirects=False)
    job_id = int(antwort.headers['location'].rsplit('/', 1)[1])

    try:
        staende = []
        frist = time.monotonic() + 20
        while webapp.zustand['worker'].laeuft and time.monotonic() < frist:
            text = browser.get(f'/lauf/{job_id}/stand').text
            treffer = re.search(r'<strong>(\d+)</strong> von', text)
            if treffer:
                staende.append(int(treffer.group(1)))
            time.sleep(0.1)
        webapp.zustand['worker'].warten(timeout=10)
    finally:
        if webapp.zustand['worker'].laeuft:
            webapp.zustand['worker'].abbrechen()

    assert staende, 'kein einziger Stand abgerufen'
    assert staende == sorted(staende), 'die Zahl ist zwischendurch gesunken'
    assert max(staende) > min(staende), 'die Zahl hat sich nie bewegt'


# ============================================================================
# Kriterium: Fenster schliessen und wieder öffnen
# ============================================================================

def test_fenster_schliessen_und_wieder_oeffnen(app):
    """Zwei getrennte Browsersitzungen sehen denselben Lauf."""
    langsam = _LangsamerProvider(FakeProvider.aus_csv(str(FIXTURE)), 0.3)
    webapp.zustand['provider'] = langsam

    with TestClient(app.app) as erster:
        erster.get('/datei', params={'modus': 'A'})
        erster.post('/datei',
                    files={'datei': ('InputData.csv', eingabe_csv(), 'text/csv')})
        antwort = erster.post('/starten', follow_redirects=False)
        job_id = int(antwort.headers['location'].rsplit('/', 1)[1])
    # Fenster zu.

    assert webapp.zustand['worker'].laeuft, 'der Lauf ist mit dem Fenster gestorben'

    with TestClient(app.app) as zweiter:  # Fenster wieder auf
        seite = zweiter.get(f'/lauf/{job_id}')
        assert seite.status_code == 200
        assert 'von 10 Kunden' in seite.text or 'Fertig' in seite.text

        webapp.zustand['worker'].warten(timeout=30)
        ergebnis = zweiter.get(f'/ergebnis/{job_id}')
        assert 'Herunterladen' in ergebnis.text

    with Datenbank(webapp.DATENBANK) as datenbank:
        job = datenbank.job_lesen(job_id)
    assert job['kunden_erledigt'] == 10


def test_startseite_fuehrt_zum_laufenden_auftrag(app, browser):
    """Wer während des Laufs auf die Startseite geht, landet beim Lauf."""
    langsam = _LangsamerProvider(FakeProvider.aus_csv(str(FIXTURE)), 0.3)
    webapp.zustand['provider'] = langsam

    browser.get('/datei', params={'modus': 'A'})
    browser.post('/datei', files={'datei': ('InputData.csv', eingabe_csv(), 'text/csv')})
    antwort = browser.post('/starten', follow_redirects=False)
    job_id = int(antwort.headers['location'].rsplit('/', 1)[1])

    try:
        start = browser.get('/', follow_redirects=False)
        assert start.status_code == 303
        assert start.headers['location'] == f'/lauf/{job_id}'
    finally:
        webapp.zustand['worker'].abbrechen()
        webapp.zustand['worker'].warten(timeout=10)


def test_offener_auftrag_wird_zur_fortsetzung_angeboten(app, browser):
    """Nach einem Absturz steht der Auftrag auf LAEUFT — die Startseite bietet ihn an."""
    job_id = lauf_durchfuehren(browser)
    with Datenbank(webapp.DATENBANK) as datenbank:
        datenbank.status_setzen(job_id, 'LAEUFT')
    webapp.zustand['worker'] = None

    start = browser.get('/')
    assert 'Ein Auftrag ist noch offen' in start.text
    assert 'Auftrag fortsetzen' in start.text

    weiter = browser.post('/fortsetzen', follow_redirects=False)
    assert weiter.status_code == 303
    assert weiter.headers['location'] == f'/lauf/{job_id}'
    webapp.zustand['worker'].warten(timeout=30)

    with Datenbank(webapp.DATENBANK) as datenbank:
        job = datenbank.job_lesen(job_id)
        kunden = datenbank.kunden_lesen(job_id)
    assert job['status'] == 'FERTIG'
    assert len(kunden) == len({k['kunden_nr'] for k in kunden}) == 10


# ============================================================================
# Kriterium: die drei Dateien laden korrekt herunter
# ============================================================================

@pytest.mark.parametrize('schluessel', AUSGABEN)
def test_dateien_laden_mit_semikolon_und_bom(browser, schluessel):
    job_id = lauf_durchfuehren(browser)

    antwort = browser.get(f'/ergebnis/{job_id}/datei/{schluessel}')

    assert antwort.status_code == 200
    assert antwort.content.startswith(b'\xef\xbb\xbf'), 'kein utf-8-sig'
    kopf = antwort.content.decode('utf-8-sig').splitlines()[0]
    assert kopf.startswith('KundenNr;SearchString;PLZ;Stadt;')
    assert ',' not in kopf
    assert f'filename="{schluessel}.csv"' in antwort.headers['content-disposition']


def test_umlaute_kommen_unbeschaedigt_an(browser):
    job_id = lauf_durchfuehren(browser)
    antwort = browser.get(f'/ergebnis/{job_id}/datei/fertig_fuer_erp')
    text = antwort.content.decode('utf-8-sig')

    assert 'Berggasthaus Musterhöche' in text
    assert 'ähnlich' in text


def test_datei_vor_dem_ende_gibt_eine_erklaerung(app, browser):
    langsam = _LangsamerProvider(FakeProvider.aus_csv(str(FIXTURE)), 0.3)
    webapp.zustand['provider'] = langsam

    browser.get('/datei', params={'modus': 'A'})
    browser.post('/datei', files={'datei': ('InputData.csv', eingabe_csv(), 'text/csv')})
    antwort = browser.post('/starten', follow_redirects=False)
    job_id = int(antwort.headers['location'].rsplit('/', 1)[1])

    try:
        frueh = browser.get(f'/ergebnis/{job_id}/datei/fertig_fuer_erp')
        assert frueh.status_code == 404
        assert 'liegt nicht bereit' in frueh.text
        assert 'Traceback' not in frueh.text
    finally:
        webapp.zustand['worker'].abbrechen()
        webapp.zustand['worker'].warten(timeout=10)


# ============================================================================
# Kriterium: keine englische Zeichenkette, kein Stacktrace
# ============================================================================

ENGLISCHE_WOERTER = [
    'Traceback', 'Internal Server Error', 'Not Found', 'Unprocessable',
    'Submit', 'Download', 'Cancel', 'Upload file', 'Error:', 'Exception',
    ' the ', ' and ', ' file ', 'Please ',
]


def sichtbarer_text(html: str) -> str:
    ohne_skript = re.sub(r'<(script|style)[^>]*>.*?</\1>', ' ', html, flags=re.S)
    return re.sub(r'<[^>]+>', ' ', ohne_skript)


def test_keine_englischen_woerter_in_der_oberflaeche(browser):
    job_id = lauf_durchfuehren(browser)
    seiten = ['/', '/datei?modus=A', f'/lauf/{job_id}', f'/lauf/{job_id}/stand',
              f'/ergebnis/{job_id}', '/datei?modus=B', '/lauf/99999',
              '/ergebnis/99999']

    for pfad in seiten:
        text = sichtbarer_text(browser.get(pfad).text)
        for wort in ENGLISCHE_WOERTER:
            assert wort not in text, f'«{wort.strip()}» steht auf {pfad}'
        assert 'ß' not in text, f'ß steht auf {pfad}'


def test_unbekannte_seiten_zeigen_keinen_stacktrace(browser):
    for pfad, code in [('/lauf/99999', 404), ('/ergebnis/99999', 404),
                       ('/ergebnis/1/datei/gibtsnicht', 404)]:
        antwort = browser.get(pfad)
        assert antwort.status_code == code
        assert 'Traceback' not in antwort.text
        assert 'Zurück zum Anfang' in antwort.text


def test_kaputte_datei_wird_verstaendlich_gemeldet(browser):
    browser.get('/datei', params={'modus': 'A'})
    antwort = browser.post('/datei', files={
        'datei': ('kaputt.csv', b'\xff\xfe\x00nicht lesbar', 'text/csv')})

    assert 'Traceback' not in antwort.text
    assert 'Semikolon' in antwort.text or 'Spalten' in antwort.text


def test_ohne_datei_kein_absturz(browser):
    browser.get('/datei', params={'modus': 'A'})
    antwort = browser.post('/starten')

    assert antwort.status_code == 400
    assert 'Traceback' not in antwort.text
    assert 'hochladen' in antwort.text


def test_modus_b_sagt_dass_er_noch_fehlt(browser):
    antwort = browser.get('/datei', params={'modus': 'B'})
    assert 'noch nicht verfügbar' in antwort.text
    assert 'Traceback' not in antwort.text


# ============================================================================
# Kriterium: bedienbar mit Tastatur, Fokus sichtbar
# ============================================================================

def test_fokus_ist_sichtbar():
    stil = (REPO / 'static' / 'stil.css').read_text(encoding='utf-8')
    assert ':focus-visible' in stil
    assert 'outline' in stil


def test_jede_handlung_ist_ein_knopf_oder_ein_verweis(browser):
    """Kein `onclick` auf einem `div` — sonst kommt die Tastatur nicht hin."""
    job_id = lauf_durchfuehren(browser)
    for pfad in ['/', '/datei?modus=A', f'/lauf/{job_id}', f'/ergebnis/{job_id}']:
        html = browser.get(pfad).text
        assert 'onclick' not in html, f'{pfad} bedient sich nur mit der Maus'
        assert re.search(r'<(button|a|input)\b', html), f'{pfad} hat kein Bedienelement'


def test_jede_seite_hat_genau_eine_haupthandlung(browser):
    """Der Prototyp verlangt eine Haupthandlung je Seite."""
    job_id = lauf_durchfuehren(browser)
    for pfad in ['/datei?modus=A', f'/ergebnis/{job_id}']:
        html = browser.get(pfad).text
        assert html.count('autofocus') <= 1, f'{pfad} hat mehr als einen Startpunkt'
        assert html.count('knopf gross') == 1, f'{pfad} hat nicht genau eine Haupthandlung'


# ============================================================================
# Die Prüfung aus Phase 4 ist eingebaut
# ============================================================================

def test_hinweise_der_pruefung_stehen_auf_der_dateiseite(browser):
    zeilen = pd.DataFrame([
        {'SearchString': 'Emil Frey AG, KST 715611 0, 5745 Safenwil', 'PLZ': '5745',
         'Stadt': 'Safenwil', 'KundenNr': '900001'},
        {'SearchString': 'Boucherie, Rue des Tilleuls 5, 1800 Vevey', 'PLZ': '1800',
         'Stadt': 'Vevey', 'KundenNr': '900002'},
    ])
    browser.get('/datei', params={'modus': 'A'})
    antwort = browser.post('/datei', files={
        'datei': ('mit_fehlern.csv',
                  zeilen.to_csv(sep=';', index=False).encode('utf-8-sig'), 'text/csv')})

    assert 'Strassenfeld' in antwort.text
    assert 'Branche' in antwort.text
    assert 'Beispiel Zeile 2' in antwort.text
    assert 'Lauf starten' in antwort.text, 'Hinweise dürfen nicht blockieren'


def test_fehlende_pflichtspalte_verhindert_den_start(browser):
    zeilen = pd.DataFrame([{'SearchString': 'Denner, Hauptstrasse 5, 5620 Bremgarten',
                            'PLZ': '5620'}])
    browser.get('/datei', params={'modus': 'A'})
    antwort = browser.post('/datei', files={
        'datei': ('ohne_kundennr.csv',
                  zeilen.to_csv(sep=';', index=False).encode('utf-8-sig'), 'text/csv')})

    assert 'KundenNr' in antwort.text
    assert 'Lauf starten' not in antwort.text
    assert 'erneut hochladen' in antwort.text


# ============================================================================
# Restzeit — aus dem Lauf gerechnet, nicht aus einer Erfahrungszahl
# ============================================================================

def test_keine_gesamtdauer_wird_versprochen(browser):
    """Solange die Laufzeitfrage offen ist, nennt die Oberfläche keine Dauer."""
    job_id = lauf_durchfuehren(browser)
    for pfad in ['/', '/datei?modus=A', f'/lauf/{job_id}']:
        text = sichtbarer_text(browser.get(pfad).text)
        assert 'Rund 2 Stunden' not in text
        assert '2 Stunden für' not in text
        assert '10 Minuten für' not in text


def test_restzeit_erst_ab_drei_kunden():
    assert 'noch nicht abschätzen' in webapp.restzeit_schaetzen(
        {'kunden_erledigt': 0, 'kunden_total': 10, 'gestartet_am': None})
    assert 'noch nicht abschätzen' in webapp.restzeit_schaetzen(
        {'kunden_erledigt': 2, 'kunden_total': 10,
         'gestartet_am': '2026-08-03T10:00:00'})


def test_restzeit_rechnet_aus_dem_bisherigen_lauf(monkeypatch):
    """Fünf Kunden in fünf Minuten, fünf offen → noch ungefähr fünf Minuten."""
    from datetime import datetime, timedelta

    jetzt = datetime(2026, 8, 3, 12, 0, 0)

    class FesteUhr(datetime):
        @classmethod
        def now(cls, tz=None):
            return jetzt

    monkeypatch.setattr(webapp, 'datetime', FesteUhr)
    text = webapp.restzeit_schaetzen({
        'kunden_erledigt': 5, 'kunden_total': 10,
        'gestartet_am': (jetzt - timedelta(minutes=5)).isoformat()})

    assert text == 'Noch ungefähr 5 Minuten.'


@pytest.mark.parametrize('sekunden, erwartet', [
    (10, 'weniger als eine Minute'),
    (60, '1 Minute'),
    (300, '5 Minuten'),
    (3600, '1 Stunde'),
    (5400, '1 Stunde 30 Minuten'),
    (43200, '12 Stunden'),
])
def test_dauer_in_worten(sekunden, erwartet):
    assert webapp.dauer_in_worten(sekunden) == erwartet


# ============================================================================
# Abbruch über die Oberfläche
# ============================================================================

def test_abbruch_ueber_die_oberflaeche(app, browser):
    langsam = _LangsamerProvider(FakeProvider.aus_csv(str(FIXTURE)), 30)
    webapp.zustand['provider'] = langsam

    browser.get('/datei', params={'modus': 'A'})
    browser.post('/datei', files={'datei': ('InputData.csv', eingabe_csv(), 'text/csv')})
    antwort = browser.post('/starten', follow_redirects=False)
    job_id = int(antwort.headers['location'].rsplit('/', 1)[1])

    frist = time.monotonic() + 5
    while not langsam.aufrufe and time.monotonic() < frist:
        time.sleep(0.05)

    beginn = time.monotonic()
    abbruch = browser.post(f'/lauf/{job_id}/abbrechen', follow_redirects=False)
    gebraucht = time.monotonic() - beginn

    assert abbruch.status_code == 303
    assert gebraucht < 5, f'{gebraucht:.1f} s bis zur Antwort'

    with Datenbank(webapp.DATENBANK) as datenbank:
        job = datenbank.job_lesen(job_id)
    assert job['status'] == 'ABGEBROCHEN'

    seite = browser.get(f'/ergebnis/{job_id}')
    assert 'Abgebrochen' in seite.text
    # Kein Verweis auf eine Ergebnisdatei — ein abgebrochener Lauf hat keine.
    assert f'/ergebnis/{job_id}/datei/' not in seite.text
    assert 'unvollständig' in seite.text


# ============================================================================
# Kriterium: Server in unter 10 Sekunden beendbar, Auftrag bleibt LAEUFT
# ============================================================================

SERVER_SKRIPT = '''
import sys, threading, time
sys.path.insert(0, {repo!r})
from pathlib import Path
import uvicorn
import webapp
from place_provider import Candidate

webapp.LAUFDATEN = Path({laufdaten!r})
webapp.UPLOADS = Path({laufdaten!r}) / 'uploads'
webapp.DATENBANK = Path({laufdaten!r}) / 'laeufe.sqlite'
webapp.UPLOADS.mkdir(parents=True, exist_ok=True)


class ZaeherProvider:
    """Antwortet erst nach zwei Minuten — wie ein hängender Apify-Aufruf."""

    def fetch_by_text(self, search_string, plz):
        time.sleep(120)
        return [Candidate(title='zu spaet', street='Hauptstrasse 1', postal_code=plz)]

    def fetch_by_id(self, place_id):
        return None


webapp.zustand['provider'] = ZaeherProvider()
webapp.zustand['harter_stopp'] = True
webapp.logging_einrichten()
uvicorn.run(webapp.app, host='127.0.0.1', port={port}, log_config=None,
            access_log=False)
'''


@pytest.mark.skipif(sys.platform == 'win32', reason='braucht SIGINT')
def test_server_beendet_sich_unter_zehn_sekunden(tmp_path):
    """
    Der Server wird mitten im Lauf gestoppt.

    Verlangt sind drei Dinge: er ist in unter zehn Sekunden weg, der Auftrag
    steht danach als LAEUFT in der Datenbank, und der nächste Start bietet ihn
    zur Fortsetzung an.
    """
    import httpx

    port = 8753
    skript = tmp_path / 'server.py'
    skript.write_text(SERVER_SKRIPT.format(
        repo=str(REPO), laufdaten=str(tmp_path), port=port), encoding='utf-8')

    server = subprocess.Popen([sys.executable, str(skript)],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        basis = f'http://127.0.0.1:{port}'
        frist = time.monotonic() + 30
        while time.monotonic() < frist:
            try:
                if httpx.get(f'{basis}/', timeout=2).status_code == 200:
                    break
            except Exception:
                time.sleep(0.2)
        else:
            raise AssertionError('der Server ist nicht hochgekommen')

        with httpx.Client(base_url=basis, timeout=10) as klient:
            klient.get('/datei', params={'modus': 'A'})
            klient.post('/datei',
                        files={'datei': ('InputData.csv', eingabe_csv(), 'text/csv')})
            antwort = klient.post('/starten', follow_redirects=False)
            job_id = int(antwort.headers['location'].rsplit('/', 1)[1])
        time.sleep(1.0)  # der Lauf ist unterwegs und wartet auf die Datenquelle

        beginn = time.monotonic()
        server.send_signal(signal.SIGINT)
        rueckgabe = server.wait(timeout=30)
        gebraucht = time.monotonic() - beginn
    finally:
        if server.poll() is None:
            server.kill()
            server.wait(timeout=10)

    assert gebraucht < 10, f'der Server brauchte {gebraucht:.1f} s zum Beenden'
    assert rueckgabe == 0

    with Datenbank(tmp_path / 'laeufe.sqlite') as datenbank:
        job = datenbank.job_lesen(job_id)
    assert job['status'] == 'LAEUFT', 'der Auftrag muss offen bleiben'

    # Und der nächste Start bietet ihn an.
    from worker import offener_lauf
    offen = offener_lauf(tmp_path / 'laeufe.sqlite')
    assert offen is not None and offen['id'] == job_id


# ============================================================================

class _LangsamerProvider:
    """Legt sich um den FakeProvider und bremst ihn — für die Statusanzeige."""

    def __init__(self, echt, sekunden):
        self.echt = echt
        self.sekunden = sekunden
        self.aufrufe = []

    def fetch_by_text(self, search_string, plz):
        self.aufrufe.append(search_string)
        time.sleep(self.sekunden)
        return self.echt.fetch_by_text(search_string, plz)

    def fetch_by_id(self, place_id):
        return self.echt.fetch_by_id(place_id)
