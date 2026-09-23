# test_korrekturrunde1_abnahme.py
# Correction round 1: one test (or a few) per fix. Invented data and the public
# fixture only (agent/05_TESTDATEN.md).

import io
import threading
import time
import types
import sys
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

import webapp
from apify_provider import ApifyProvider
from data_cleaner import DataCleaner
from db import Datenbank
from fake_provider import FakeProvider
from pipeline import Lauf
from place_provider import Candidate, QuelleNichtVerfuegbar
from upload_pruefung import pruefe_datei

REPO = Path(__file__).parent
FIXTURE = REPO / 'agent' / 'testdaten' / 'fixture_optimierte_daten.csv'
HAUPTDATEIEN = ('fertig_fuer_erp', 'zur_pruefung', 'nicht_moeglich')


def lies(inhalt) -> pd.DataFrame:
    quelle = io.BytesIO(inhalt) if isinstance(inhalt, bytes) else inhalt
    return pd.read_csv(quelle, sep=';', encoding='utf-8-sig', dtype=str).fillna('')


def fixture_kunden(nummern=None) -> bytes:
    df = lies(FIXTURE).drop_duplicates('KundenNr')[['SearchString', 'PLZ', 'Stadt',
                                                    'KundenNr']]
    if nummern:
        df = df[df['KundenNr'].isin(nummern)]
    return df.to_csv(sep=';', index=False).encode('utf-8-sig')


def kunden_zeilen(anzahl: int, start: int = 900600) -> bytes:
    return pd.DataFrame([{'SearchString': f'Laden {i}, Hauptstrasse {i}, 5620 Musterdorf',
                          'PLZ': '5620', 'Stadt': 'Musterdorf',
                          'KundenNr': str(start + i)} for i in range(anzahl)]
                        ).to_csv(sep=';', index=False).encode('utf-8-sig')


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setattr(webapp, 'LAUFDATEN', tmp_path)
    monkeypatch.setattr(webapp, 'UPLOADS', tmp_path / 'uploads')
    monkeypatch.setattr(webapp, 'DATENBANK', tmp_path / 'laeufe.sqlite')
    webapp.UPLOADS.mkdir(parents=True, exist_ok=True)
    webapp.zustand.update(worker=None, hochgeladen=None, kunden=0, modus='A',
                          email='', provider=FakeProvider.aus_csv(str(FIXTURE)))
    yield webapp
    worker = webapp.zustand['worker']
    if worker and worker.laeuft:
        worker.abbrechen()
        worker.warten(timeout=10)
    webapp.zustand['provider'] = None


@pytest.fixture
def browser(app):
    with TestClient(app.app) as klient:
        yield klient


def hochladen_und_starten(browser, name: str, inhalt: bytes) -> int:
    browser.get('/datei', params={'modus': 'A'})
    browser.post('/datei', data={'modus': 'A'}, files={'datei': (name, inhalt, 'text/csv')})
    antwort = browser.post('/starten', follow_redirects=False)
    assert antwort.status_code == 303, antwort.text
    webapp.zustand['worker'].warten(timeout=30)
    return int(antwort.headers['location'].rsplit('/', 1)[1])


def kundennummern(browser, job_id: int, schluessel: str) -> set:
    antwort = browser.get(f'/ergebnis/{job_id}/datei/{schluessel}')
    assert antwort.status_code == 200
    return set(lies(antwort.content)['KundenNr'])


# ============================================================================
# 1 — ein Ordner je Auftrag
# ============================================================================

def test_gleicher_dateiname_ueberschreibt_keinen_anderen_auftrag(browser):
    erster = hochladen_und_starten(
        browser, 'kunden.csv', fixture_kunden(['900001', '900002', '900003']))
    vorher = kundennummern(browser, erster, 'fertig_fuer_erp')

    zweiter = hochladen_und_starten(
        browser, 'kunden.csv', fixture_kunden(['900006', '900007', '900010']))

    assert kundennummern(browser, erster, 'fertig_fuer_erp') == vorher
    assert kundennummern(browser, zweiter, 'fertig_fuer_erp') == {'900006', '900010'}


def test_pruefentscheid_schreibt_nur_in_den_eigenen_auftrag(browser):
    erster = hochladen_und_starten(
        browser, 'kunden.csv', fixture_kunden(['900001', '900002', '900003']))
    zweiter = hochladen_und_starten(
        browser, 'kunden.csv', fixture_kunden(['900006', '900007', '900010']))
    zweiter_vorher = kundennummern(browser, zweiter, 'fertig_fuer_erp')

    with Datenbank(webapp.DATENBANK) as datenbank:
        fall = datenbank.pruefaelle_lesen(erster)[0]
        kandidat = datenbank.kandidaten_lesen(fall['id'])[0]
    browser.post(f'/pruefung/{erster}/fall/{fall["id"]}',
                 data={'kandidat_id': str(kandidat['id'])})

    assert kundennummern(browser, zweiter, 'fertig_fuer_erp') == zweiter_vorher
    assert fall['kunden_nr'] in kundennummern(browser, erster, 'fertig_fuer_erp')


def test_eingabe_und_ergebnis_liegen_im_ordner_des_auftrags(browser):
    job_id = hochladen_und_starten(browser, 'kunden.csv', fixture_kunden())
    ordner = webapp.UPLOADS / f'auftrag_{job_id}'
    assert (ordner / 'kunden.csv').exists()
    # Datenvertrag §2: <eingabedateiname>_ergebnis neben der Eingabedatei
    assert (ordner / 'kunden_ergebnis' / 'fertig_fuer_erp.csv').exists()


def test_alter_auftrag_ohne_eigenen_ordner_bleibt_erreichbar(browser):
    """Jobs von vor der Korrekturrunde liegen direkt im Upload-Ordner."""
    with Datenbank(webapp.DATENBANK) as datenbank:
        job_id = datenbank.job_anlegen('A', 'Alt.csv', kunden_total=1)
        datenbank.status_setzen(job_id, 'FERTIG')
    alt = webapp.UPLOADS / 'Alt_ergebnis'
    alt.mkdir()
    (alt / 'fertig_fuer_erp.csv').write_text('KundenNr\n900001\n', encoding='utf-8-sig')

    antwort = browser.get(f'/ergebnis/{job_id}/datei/fertig_fuer_erp')
    assert antwort.status_code == 200
    assert '900001' in antwort.text


def test_neuer_upload_ueberschreibt_nicht_die_eingabe_eines_offenen_auftrags(browser):
    hochladen_und_starten(browser, 'kunden.csv', fixture_kunden(['900001']))
    browser.get('/datei', params={'modus': 'A'})
    browser.post('/datei', data={'modus': 'A'},
                 files={'datei': ('kunden.csv', fixture_kunden(['900009']), 'text/csv')})

    eingabe = lies(webapp.UPLOADS / 'auftrag_1' / 'kunden.csv')
    assert list(eingabe['KundenNr']) == ['900001']


# ============================================================================
# 3 — ein Apify-Lauf, der nicht mit SUCCEEDED endet, ist kein leeres Ergebnis
# ============================================================================

class _LaufStub:
    def __init__(self, status):
        self.status = status

    def wait_for_finish(self, wait_secs=None):
        return {'status': self.status, 'defaultDatasetId': 'D1'}

    def abort(self):
        pass


class _ClientStub:
    def __init__(self, status, datensatz_fehler=False):
        self.status = status
        self.datensatz_fehler = datensatz_fehler

    def run(self, lauf_id):
        return _LaufStub(self.status)

    def dataset(self, kennung):
        klient = self

        class _Datensatz:
            def iterate_items(self):
                if klient.datensatz_fehler:
                    raise ConnectionError('Verbindung weg')
                return iter([])
        return _Datensatz()


class _ActorStub:
    def start(self, run_input=None, timeout_secs=None):
        return {'id': 'LAUF_1'}


def _apify(status, datensatz_fehler=False) -> ApifyProvider:
    provider = ApifyProvider('token', 'actor')
    provider.client = _ClientStub(status, datensatz_fehler)
    provider.actor = _ActorStub()
    return provider


@pytest.mark.parametrize('status', ['TIMED-OUT', 'FAILED', 'ABORTED', 'RUNNING'])
def test_unvollendeter_apify_lauf_ist_ein_fehlschlag(status):
    with pytest.raises(QuelleNichtVerfuegbar) as gemeldet:
        _apify(status).fetch_by_text('Laden, Hauptstrasse 1, 5620 Musterdorf', '5620')
    assert gemeldet.value.endgueltig is False
    assert 'nichts gefunden' in gemeldet.value.meldung


def test_unlesbarer_datensatz_ist_ein_fehlschlag():
    with pytest.raises(QuelleNichtVerfuegbar):
        _apify('SUCCEEDED', datensatz_fehler=True).fetch_by_text(
            'Laden, Hauptstrasse 1, 5620 Musterdorf', '5620')


def test_erfolgreicher_leerer_lauf_bleibt_nichts_gefunden():
    """Gegenprobe: SUCCEEDED mit leerem Datensatz ist weiterhin ein Ergebnis."""
    assert _apify('SUCCEEDED').fetch_by_text(
        'Laden, Hauptstrasse 1, 5620 Musterdorf', '5620') == []


def test_nach_abbruch_durch_den_nutzer_kein_fehlschlag():
    provider = _apify('ABORTED')
    provider._abgebrochen = True
    assert provider.fetch_by_text('Laden, Hauptstrasse 1, 5620 Musterdorf', '5620') == []


def test_lauf_mit_lauter_zeitueberschreitungen_endet_nicht_als_fertig(tmp_path):
    """Früher: FERTIG mit allen Kunden in ③ «lieferte keinen einzigen Treffer»."""
    eingabe = tmp_path / 'kunden.csv'
    eingabe.write_bytes(kunden_zeilen(30))
    with Datenbank(tmp_path / 'lauf.sqlite') as datenbank:
        ergebnis = Lauf(_apify('TIMED-OUT'), datenbank, arbeiter=6).ausfuehren(
            str(eingabe), str(tmp_path / 'aus'))

    assert ergebnis['status'] == 'FEHLER'
    assert not (tmp_path / 'aus').exists()


# ============================================================================
# 4 — der normale Start ist der echte Betrieb
# ============================================================================

@pytest.fixture
def ohne_server(tmp_path, monkeypatch):
    """main() ohne echten Server, ohne harten Stopp, ohne Ordner im Repo."""
    monkeypatch.setitem(webapp.zustand, 'harter_stopp', False)
    monkeypatch.setitem(webapp.zustand, 'provider', None)
    monkeypatch.setattr(webapp, 'UPLOADS', tmp_path / 'uploads')
    monkeypatch.setattr(webapp, 'logging_einrichten', lambda: None)
    monkeypatch.setattr(webapp, 'offener_lauf', lambda pfad: None)
    monkeypatch.setattr(webapp.uvicorn, 'run', lambda *a, **k: None)


def test_start_ohne_angaben_ist_echter_betrieb(ohne_server, monkeypatch):
    gewaehlt = {}
    monkeypatch.setattr(webapp, 'provider_einrichten',
                        lambda antworten, quelle: gewaehlt.update(quelle=quelle))
    assert webapp.main([]) == 0
    assert gewaehlt['quelle'] == 'echt'


def test_antwortdatei_allein_heisst_probebetrieb(ohne_server, monkeypatch):
    gewaehlt = {}
    monkeypatch.setattr(webapp, 'provider_einrichten',
                        lambda antworten, quelle: gewaehlt.update(quelle=quelle))
    assert webapp.main(['--antworten', str(FIXTURE)]) == 0
    assert gewaehlt['quelle'] == 'fake'


def test_probebetrieb_ohne_antwortdatei_startet_nicht(ohne_server, monkeypatch, capsys):
    monkeypatch.setattr(webapp.uvicorn, 'run',
                        lambda *a, **k: pytest.fail('Server darf nicht starten'))
    assert webapp.main(['--quelle', 'fake']) == 1
    assert 'Antwortdatei' in capsys.readouterr().out


def test_probebetrieb_steht_auf_jeder_seite(browser):
    assert 'Probebetrieb' in browser.get('/').text
    webapp.zustand['provider'] = None
    assert 'Probebetrieb' not in browser.get('/').text


# ============================================================================
# 6 — «Auftrag fortsetzen» zweimal startet den Auftrag nicht zweimal
# ============================================================================

class _Langsam:
    def __init__(self):
        self.aufrufe = {}
        self.sperre = threading.Lock()

    def fetch_by_text(self, s, plz):
        with self.sperre:
            self.aufrufe[s] = self.aufrufe.get(s, 0) + 1
        time.sleep(0.05)
        return [Candidate(title=s.split(',')[0], street=s.split(',')[1].strip(),
                          postal_code=plz, place_id='P')]

    def fetch_by_id(self, place_id):
        return None


def test_doppelklick_auf_fortsetzen_fragt_niemanden_doppelt_ab(browser):
    provider = _Langsam()
    webapp.zustand['provider'] = provider
    (webapp.UPLOADS / 'kunden.csv').write_bytes(kunden_zeilen(40))
    with Datenbank(webapp.DATENBANK) as datenbank:    # Stand nach einem Absturz
        job_id = datenbank.job_anlegen('A', 'kunden.csv', kunden_total=40)
        datenbank.status_setzen(job_id, 'LAEUFT')

    erster = browser.post('/fortsetzen', follow_redirects=False)
    zweiter = browser.post('/fortsetzen', follow_redirects=False)
    webapp.zustand['worker'].warten(timeout=30)

    assert erster.headers['location'] == zweiter.headers['location'] == f'/lauf/{job_id}'
    assert sum(provider.aufrufe.values()) == 40
    assert max(provider.aufrufe.values()) == 1
    with Datenbank(webapp.DATENBANK) as datenbank:
        assert datenbank.job_lesen(job_id)['status'] == 'FERTIG'


def test_worker_weist_zweites_fortsetzen_desselben_auftrags_ab(tmp_path):
    from worker import LaeuftBereits, Worker

    eingabe = tmp_path / 'kunden.csv'
    eingabe.write_bytes(kunden_zeilen(20))
    datenbank_pfad = tmp_path / 'lauf.sqlite'
    with Datenbank(datenbank_pfad) as datenbank:
        job_id = datenbank.job_anlegen('A', 'kunden.csv', kunden_total=20)
        datenbank.status_setzen(job_id, 'LAEUFT')

    erster = Worker(_Langsam(), datenbank_pfad, arbeiter=1)
    erster.fortsetzen(job_id, str(eingabe))
    try:
        with pytest.raises(LaeuftBereits):
            Worker(_Langsam(), datenbank_pfad).fortsetzen(job_id, str(eingabe))
    finally:
        erster.abbrechen()
        erster.warten(timeout=10)


def test_doppelklick_auf_starten_zeigt_den_laufenden_auftrag(browser):
    webapp.zustand['provider'] = _Langsam()
    browser.get('/datei', params={'modus': 'A'})
    browser.post('/datei', data={'modus': 'A'},
                 files={'datei': ('kunden.csv', kunden_zeilen(40), 'text/csv')})
    erster = browser.post('/starten', follow_redirects=False)
    zweiter = browser.post('/starten', follow_redirects=False)
    webapp.zustand['worker'].warten(timeout=30)

    assert zweiter.status_code == 303
    assert zweiter.headers['location'] == erster.headers['location']


# ============================================================================
# Kleinere Punkte
# ============================================================================

def test_upload_warnt_vor_doppelten_und_leeren_kundennummern(tmp_path):
    pfad = tmp_path / 'dopp.csv'
    pd.DataFrame([
        {'SearchString': 'Laden A, Hauptstrasse 1, 5620 Musterdorf', 'PLZ': '5620', 'KundenNr': '900301'},
        {'SearchString': 'Laden B, Bahnhofstrasse 9, 5620 Musterdorf', 'PLZ': '5620', 'KundenNr': '900301'},
        {'SearchString': 'Laden C, Seeweg 2, 5620 Musterdorf', 'PLZ': '5620', 'KundenNr': ''},
        {'SearchString': 'Laden D, Seeweg 4, 5620 Musterdorf', 'PLZ': '5620', 'KundenNr': ''},
    ]).to_csv(pfad, sep=';', index=False, encoding='utf-8-sig')

    bericht = pruefe_datei(pfad)

    assert bericht.start_moeglich, 'die Prüfung warnt nur, sie blockiert nicht'
    doppelt = bericht.befund('kundennr_doppelt')
    leer = bericht.befund('kundennr_leer')
    assert doppelt.anzahl == 1 and doppelt.zeilennummer == 3
    assert leer.anzahl == 2 and leer.zeilennummer == 4
    assert 'ß' not in doppelt.meldung + leer.meldung


def test_eine_leere_kundennummer_spricht_nicht_von_den_uebrigen(tmp_path):
    pfad = tmp_path / 'eine.csv'
    pd.DataFrame([
        {'SearchString': 'Laden A, Hauptstrasse 1, 5620 Musterdorf', 'PLZ': '5620', 'KundenNr': '900301'},
        {'SearchString': 'Laden C, Seeweg 2, 5620 Musterdorf', 'PLZ': '5620', 'KundenNr': ''},
    ]).to_csv(pfad, sep=';', index=False, encoding='utf-8-sig')
    meldung = pruefe_datei(pfad).befund('kundennr_leer').meldung
    assert meldung.startswith('1 Zeile hat keine Kundennummer')
    assert 'übrigen' not in meldung


def test_saubere_kundennummern_erzeugen_keinen_hinweis(tmp_path):
    pfad = tmp_path / 'sauber.csv'
    pfad.write_bytes(fixture_kunden())
    bericht = pruefe_datei(pfad)
    assert bericht.befund('kundennr_doppelt') is None
    assert bericht.befund('kundennr_leer') is None


@pytest.mark.parametrize('fall', ['config.py fehlt', 'Token-Platzhalter'])
def test_fehlende_zugangsdaten_sagen_was_fehlt(app, fall, monkeypatch):
    webapp.zustand['provider'] = None                    # echter Betrieb
    monkeypatch.delitem(sys.modules, 'config', raising=False)
    if fall == 'Token-Platzhalter':
        monkeypatch.setitem(sys.modules, 'config', types.SimpleNamespace(
            APIFY_API_TOKEN='DEIN_APIFY_API_TOKEN', ACTOR_ID='DEIN_ACTOR_ID'))
    else:
        import builtins
        echter_import = builtins.__import__

        def ohne_config(name, *args, **kwargs):
            if name == 'config':
                raise ModuleNotFoundError("No module named 'config'", name='config')
            return echter_import(name, *args, **kwargs)
        monkeypatch.setattr(builtins, '__import__', ohne_config)

    with TestClient(app.app, raise_server_exceptions=False) as browser:
        browser.get('/datei', params={'modus': 'A'})
        browser.post('/datei', data={'modus': 'A'},
                     files={'datei': ('kunden.csv', fixture_kunden(), 'text/csv')})
        antwort = browser.post('/starten', follow_redirects=False)

    assert 'Die Zugangsdaten fehlen' in antwort.text
    assert 'arbeitet weiter' not in antwort.text
    assert ('config.py' in antwort.text) or ('APIFY_API_TOKEN' in antwort.text)
    with Datenbank(webapp.DATENBANK) as datenbank:
        assert datenbank.offener_job() is None


def test_pruefmaske_ignoriert_gehaltene_tasten():
    vorlage = (REPO / 'templates' / 'pruefung_fall.html').read_text(encoding='utf-8')
    assert 'ereignis.repeat' in vorlage


def test_upload_fehler_nennt_csv_utf8(browser):
    antwort = browser.post('/datei', data={'modus': 'A'}, files={
        'datei': ('kaputt.csv', 'Name;PLZ\nMüller;5620\n'.encode('cp1252'), 'text/csv')})
    assert 'CSV UTF-8' in antwort.text


def test_cli_gestoppter_lauf_ohne_stacktrace(tmp_path, monkeypatch, capsys):
    import cli
    from apify_provider import ENDGUELTIGE_FEHLER

    class Erschoepft:
        def fetch_by_text(self, s, plz):
            raise QuelleNichtVerfuegbar(
                ENDGUELTIGE_FEHLER['monthly-usage-hard-limit-exceeded'])

        def fetch_by_id(self, place_id):
            return None

    eingabe = tmp_path / 'kunden.csv'
    eingabe.write_bytes(kunden_zeilen(5))
    monkeypatch.setattr(cli, '_provider_bauen', lambda args: Erschoepft())
    monkeypatch.setattr(cli, '_setup_logging', lambda verbose: None)

    code = cli.main(['lauf', str(eingabe), '--datenbank', str(tmp_path / 'db.sqlite')])

    ausgabe = capsys.readouterr().out
    assert code == 1
    assert 'Guthaben bei Apify ist aufgebraucht' in ausgabe
    assert 'Traceback' not in ausgabe


def test_algorithmus_unveraendert_auf_der_fixture(tmp_path):
    """
    Wächter für diese Runde: die Fachlogik ist nicht angefasst worden.
    Die zehn Fixture-Kunden landen genau dort, wo 05_TESTDATEN.md es vorgibt.
    """
    DataCleaner().clean_data(str(FIXTURE), str(tmp_path))
    erwartet = {
        'fertig_fuer_erp': {'900001', '900003', '900004', '900005', '900006', '900010'},
        'zur_pruefung': {'900002', '900007', '900009'},
        'nicht_moeglich': {'900008'},
    }
    for datei, nummern in erwartet.items():
        assert set(lies(tmp_path / f'{datei}.csv')['KundenNr']) == nummern
