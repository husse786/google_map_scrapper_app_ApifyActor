# test_phase2_abnahme.py
# One test per acceptance criterion of phase 2 (agent/01_PHASENPLAN.md).
# Nothing here touches the network. The only data used is the invented fixture.

import os
import socket
import sqlite3
import time
from dataclasses import fields
from pathlib import Path

import pandas as pd
import pytest

from apify_provider import (FELD_ZUORDNUNG, STANDARD_ACTOR_INPUT,
                            STANDARD_TIMEOUT_SEKUNDEN, ApifyProvider)
from data_cleaner import OUTPUT_FILES, DataCleaner
from db import ENTSCHEIDE, ERGEBNISSE, Datenbank
from fake_provider import FakeProvider
from pipeline import Lauf
from place_provider import Candidate

REPO = Path(__file__).parent
FIXTURE = REPO / 'agent' / 'testdaten' / 'fixture_optimierte_daten.csv'
HAUPTDATEIEN = ('fertig_fuer_erp', 'zur_pruefung', 'nicht_moeglich')


# ============================================================================
# Hilfen
# ============================================================================

def lies(pfad) -> pd.DataFrame:
    return pd.read_csv(pfad, sep=';', encoding='utf-8-sig', dtype=str).fillna('')


def eingabedatei_aus_fixture(tmp_path: Path) -> Path:
    """Die Fixture ohne Trefferspalten — das ist die Eingabe im Modus A."""
    df = lies(FIXTURE)[['SearchString', 'PLZ', 'Stadt', 'KundenNr']].drop_duplicates(
        subset=['KundenNr'])
    ziel = tmp_path / 'eingabe.csv'
    df.to_csv(ziel, sep=';', index=False, encoding='utf-8-sig')
    return ziel


class SchlafenderProvider:
    """Antwortet nie rechtzeitig. Für den Timeout-Nachweis."""

    def __init__(self, sekunden: float):
        self.sekunden = sekunden
        self.aufrufe = 0

    def fetch_by_text(self, search_string, plz):
        self.aufrufe += 1
        time.sleep(self.sekunden)
        return [Candidate(title='Zu spät', street='Hauptstrasse 5',
                          postal_code=plz, place_id='PLACE_SPAET')]

    def fetch_by_id(self, place_id):
        return None


# ============================================================================
# Kriterium: Kein Modul ausserhalb von ApifyProvider kennt Apify-Feldnamen
# ============================================================================

# Namen, die es nur bei Apify gibt. Spalten wie `title` oder `placeId` stehen
# dagegen im Datenvertrag §2 und gehören damit allen Providern.
APIFY_EIGENE_NAMEN = [
    'searchStringsArray', 'defaultDatasetId', 'maxCrawledPlacesPerSearch',
    'scrapePlaceDetailPage', 'scrapeContacts', 'scrapeDirectories',
    'includeWebResults', 'countryCode', 'categoryName', 'totalScore',
    'plusCode', 'reviewsCount', 'scrapedAt', 'ApifyClient', 'ApifyApiError',
    'apify_client',
]

# apify_provider.py darf sie kennen, das ist seine Aufgabe.
# config.py gehört nicht zum Repository (per .gitignore, je Rechner eigen) und
# liefert nur Token und Actor-Id.
ERLAUBT = {'apify_provider.py', 'config.py'}


def projekt_module():
    for pfad in sorted(REPO.glob('*.py')):
        if pfad.name in ERLAUBT or pfad.name.startswith('test_'):
            continue
        yield pfad


@pytest.mark.parametrize('modul', list(projekt_module()), ids=lambda p: p.name)
def test_kein_modul_kennt_apify_feldnamen(modul):
    text = modul.read_text(encoding='utf-8')
    gefunden = [name for name in APIFY_EIGENE_NAMEN if name in text]
    assert not gefunden, f'{modul.name} kennt Apify-Namen: {gefunden}'


def test_apify_provider_kennt_sie_als_einziger():
    """Gegenprobe: die Zuordnung existiert wirklich, der Test oben ist nicht leer."""
    text = (REPO / 'apify_provider.py').read_text(encoding='utf-8')
    assert 'searchStringsArray' in text
    assert 'defaultDatasetId' in text
    assert set(FELD_ZUORDNUNG.values()) == {f.name for f in fields(Candidate)}


# ============================================================================
# Kriterium: Der Lauf aus Phase 1 funktioniert unverändert über einen Provider
# ============================================================================

def test_lauf_ueber_fakeprovider_ergibt_dasselbe_wie_phase1(tmp_path):
    """
    Derselbe Fall zweimal: einmal über die Bereinigung einer angereicherten
    Datei (Phase 1), einmal über Provider und Datenbank (Phase 2). Die drei
    Ausgabedateien müssen Zeichen für Zeichen gleich sein.
    """
    phase1 = tmp_path / 'phase1'
    DataCleaner().clean_data(str(FIXTURE), str(phase1))

    phase2 = tmp_path / 'phase2'
    with Datenbank(tmp_path / 'lauf.sqlite') as datenbank:
        ergebnis = Lauf(FakeProvider.aus_csv(str(FIXTURE)), datenbank).ausfuehren(
            eingabedatei_aus_fixture(tmp_path), str(phase2))

    assert ergebnis['status'] == 'FERTIG'
    assert ergebnis['kunden_total'] == 10
    assert ergebnis['kunden_erledigt'] == 10

    for schluessel in HAUPTDATEIEN:
        dateiname = OUTPUT_FILES[schluessel]
        alt = (phase1 / dateiname).read_text(encoding='utf-8-sig')
        neu = (phase2 / dateiname).read_text(encoding='utf-8-sig')
        assert neu == alt, f'{dateiname} unterscheidet sich zwischen Phase 1 und 2'


def test_lauf_ueber_fakeprovider_ohne_netzzugriff(tmp_path, monkeypatch):
    """Derselbe Lauf, aber jeder Versuch eines Netzzugriffs wird protokolliert."""
    versuche = []

    def netz_verboten(*args, **kwargs):
        versuche.append(args)
        raise OSError('Netzzugriff im Test nicht erlaubt')

    monkeypatch.setattr(socket.socket, 'connect', netz_verboten)
    monkeypatch.setattr(socket, 'create_connection', netz_verboten)

    ziel = tmp_path / 'ergebnis'
    with Datenbank(tmp_path / 'lauf.sqlite') as datenbank:
        ergebnis = Lauf(FakeProvider.aus_csv(str(FIXTURE)), datenbank).ausfuehren(
            eingabedatei_aus_fixture(tmp_path), str(ziel))

    assert versuche == []
    assert ergebnis['kunden_erledigt'] == 10
    assert lies(ziel / OUTPUT_FILES['fertig_fuer_erp'])['KundenNr'].nunique() == 6


def test_jeder_kunde_genau_einmal(tmp_path):
    """Die Invariante aus §2 gilt auch auf dem Weg über den Provider."""
    ziel = tmp_path / 'ergebnis'
    with Datenbank(tmp_path / 'lauf.sqlite') as datenbank:
        Lauf(FakeProvider.aus_csv(str(FIXTURE)), datenbank).ausfuehren(
            eingabedatei_aus_fixture(tmp_path), str(ziel))

    mengen = {name: set(lies(ziel / OUTPUT_FILES[name])['KundenNr'])
              for name in HAUPTDATEIEN}
    vereinigung = set().union(*mengen.values())
    assert sum(len(m) for m in mengen.values()) == len(vereinigung) == 10


# ============================================================================
# Kriterium: Timeout nachweisbar
# ============================================================================

def test_timeout_standard_ist_90_sekunden():
    """03_ENTSCHEIDUNGEN.md C. Beide Ebenen tragen denselben Wert."""
    import pipeline
    assert pipeline.STANDARD_TIMEOUT_SEKUNDEN == 90
    assert STANDARD_TIMEOUT_SEKUNDEN == 90
    assert Lauf(None, None).timeout_sekunden == 90
    assert ApifyProvider('x', 'y').timeout_sekunden == 90
    # Apify bekommt etwas weniger, damit der Provider vor dem Notschalter im
    # Lauf entscheidet und den überzogenen Lauf noch abbrechen kann.
    assert ApifyProvider('x', 'y').wartezeit == 85


def test_haengender_provider_endet_in_datei_drei(tmp_path):
    """
    Ein Provider, der nicht antwortet, darf den Lauf nicht blockieren. Der Kunde
    landet in ③, ohne Retry. Hier mit einem Bruchteil einer Sekunde statt
    neunzig, damit die Testsuite schnell bleibt; der Lauf mit den echten
    90 Sekunden steht in test_timeout_mit_echten_90_sekunden.
    """
    provider = SchlafenderProvider(sekunden=5)
    ziel = tmp_path / 'ergebnis'

    beginn = time.monotonic()
    with Datenbank(tmp_path / 'lauf.sqlite') as datenbank:
        Lauf(provider, datenbank, timeout_sekunden=0.3).ausfuehren(
            eingabedatei_aus_fixture(tmp_path), str(ziel))
    gebraucht = time.monotonic() - beginn

    nicht_moeglich = lies(ziel / OUTPUT_FILES['nicht_moeglich'])
    assert len(nicht_moeglich) == 10
    assert set(nicht_moeglich['qualitaet']) == {'NICHT_MOEGLICH (kein Ergebnis)'}
    assert lies(ziel / OUTPUT_FILES['fertig_fuer_erp']).empty

    # Kein Retry: ein Aufruf je Kunde.
    assert provider.aufrufe == 10
    # Zehn Kunden mit je 0.3 s Geduld — weit unter den 50 s, die ohne Timeout
    # nötig wären.
    assert gebraucht < 15, f'{gebraucht:.1f} s gebraucht, Timeout griff nicht'


@pytest.mark.skipif(not os.environ.get('LANGSAME_TESTS'),
                    reason='Dauert 90 Sekunden. Mit LANGSAME_TESTS=1 ausführen.')
def test_timeout_mit_echten_90_sekunden(tmp_path):
    """Derselbe Nachweis mit dem echten Wert aus 03_ENTSCHEIDUNGEN.md C."""
    quelle = tmp_path / 'eingabe.csv'
    pd.DataFrame([{'SearchString': 'Muster Laden, Hauptstrasse 1, 5620 Musterdorf',
                   'PLZ': '5620', 'Stadt': 'Musterdorf', 'KundenNr': '900601'}]
                 ).to_csv(quelle, sep=';', index=False, encoding='utf-8-sig')

    ziel = tmp_path / 'ergebnis'
    beginn = time.monotonic()
    with Datenbank(tmp_path / 'lauf.sqlite') as datenbank:
        Lauf(SchlafenderProvider(sekunden=600), datenbank).ausfuehren(quelle, str(ziel))
    gebraucht = time.monotonic() - beginn

    nicht_moeglich = lies(ziel / OUTPUT_FILES['nicht_moeglich'])
    assert len(nicht_moeglich) == 1
    assert nicht_moeglich.iloc[0]['qualitaet'] == 'NICHT_MOEGLICH (kein Ergebnis)'
    assert 88 <= gebraucht <= 100, f'nach {gebraucht:.1f} s beendet, erwartet ~90 s'


# ============================================================================
# Kriterium: Nach einem Lauf enthält die Datenbank jeden Kandidaten
#            mit score und entscheid
# ============================================================================

def test_datenbank_enthaelt_jeden_kandidaten_mit_score_und_entscheid(tmp_path):
    eingabe = eingabedatei_aus_fixture(tmp_path)
    kandidaten_in_der_fixture = len(lies(FIXTURE)[lies(FIXTURE)['placeId'] != ''])

    with Datenbank(tmp_path / 'lauf.sqlite') as datenbank:
        ergebnis = Lauf(FakeProvider.aus_csv(str(FIXTURE)), datenbank).ausfuehren(
            eingabe, str(tmp_path / 'ergebnis'))
        job_id = ergebnis['job_id']

        assert datenbank.kandidaten_zaehlen(job_id) == kandidaten_in_der_fixture

        kunden = datenbank.kunden_lesen(job_id)
        assert len(kunden) == 10

        for kunde in kunden:
            assert kunde['ergebnis'] in ERGEBNISSE
            assert kunde['qualitaet']
            assert kunde['grund']
            assert kunde['verarbeitet_am']

            for kandidat in datenbank.kandidaten_lesen(kunde['id']):
                assert kandidat['score'] is not None
                assert kandidat['entscheid'] in ENTSCHEIDE
                assert kandidat['grund']


def test_gewaehlter_kandidat_ist_der_aus_datei_eins(tmp_path):
    """Der Entscheid in der Datenbank passt zu dem, was in ① steht."""
    ziel = tmp_path / 'ergebnis'
    with Datenbank(tmp_path / 'lauf.sqlite') as datenbank:
        ergebnis = Lauf(FakeProvider.aus_csv(str(FIXTURE)), datenbank).ausfuehren(
            eingabedatei_aus_fixture(tmp_path), str(ziel))

        fertig = lies(ziel / OUTPUT_FILES['fertig_fuer_erp'])
        for _, zeile in fertig.iterrows():
            kunde = next(k for k in datenbank.kunden_lesen(ergebnis['job_id'])
                         if k['kunden_nr'] == zeile['KundenNr'])
            gewaehlt = [k for k in datenbank.kandidaten_lesen(kunde['id'])
                        if k['entscheid'] == 'gewaehlt']
            assert len(gewaehlt) == 1
            assert gewaehlt[0]['place_id'] == zeile['placeId']
            assert f"{gewaehlt[0]['score']:.2f}" == f"{float(zeile['score']):.2f}"


def test_abgelehnte_kandidaten_stehen_ebenfalls_in_der_datenbank(tmp_path):
    """900001: ein Treffer gewinnt, zwei werden verworfen — alle drei bleiben."""
    with Datenbank(tmp_path / 'lauf.sqlite') as datenbank:
        ergebnis = Lauf(FakeProvider.aus_csv(str(FIXTURE)), datenbank).ausfuehren(
            eingabedatei_aus_fixture(tmp_path), str(tmp_path / 'ergebnis'))

        kunde = next(k for k in datenbank.kunden_lesen(ergebnis['job_id'])
                     if k['kunden_nr'] == '900001')
        kandidaten = datenbank.kandidaten_lesen(kunde['id'])

    assert len(kandidaten) == 3
    entscheide = sorted(k['entscheid'] for k in kandidaten)
    assert entscheide == ['abgelehnt', 'abgelehnt', 'gewaehlt']


def test_fortschritt_wird_nach_jedem_kunden_geschrieben(tmp_path):
    """§6: kunden_erledigt wächst mit, nicht erst am Ende."""

    class BeobachteterLauf(Lauf):
        """Liest vor jedem Kunden den Stand, der in der Datenbank steht."""

        staende = []

        def _einen_kunden(self, job_id, kunden_nr, stamm, kandidaten):
            self.staende.append(
                self.datenbank.fortschritt_lesen(job_id)['kunden_erledigt'])
            return super()._einen_kunden(job_id, kunden_nr, stamm, kandidaten)

    with Datenbank(tmp_path / 'lauf.sqlite') as datenbank:
        lauf = BeobachteterLauf(FakeProvider.aus_csv(str(FIXTURE)), datenbank)
        lauf.staende = []
        ergebnis = lauf.ausfuehren(eingabedatei_aus_fixture(tmp_path),
                                   str(tmp_path / 'ergebnis'))
        endstand = datenbank.fortschritt_lesen(ergebnis['job_id'])

    assert lauf.staende == list(range(10))
    assert endstand['kunden_erledigt'] == 10
    assert endstand['kunden_total'] == 10
    assert endstand['status'] == 'FERTIG'


# ============================================================================
# Kriterium: idx_kunde_nr verhindert einen doppelten Kunden pro Job
# ============================================================================

def test_idx_kunde_nr_verhindert_doppelten_kunden(tmp_path):
    with Datenbank(tmp_path / 'lauf.sqlite') as datenbank:
        job_id = datenbank.job_anlegen('A', 'test.csv', kunden_total=1)
        datenbank.kunde_schreiben(job_id, '900001', ergebnis='fertig')

        with pytest.raises(sqlite3.IntegrityError):
            datenbank.kunde_schreiben(job_id, '900001', ergebnis='pruefung')

        # Dieselbe Nummer in einem anderen Job ist erlaubt.
        zweiter_job = datenbank.job_anlegen('A', 'test2.csv', kunden_total=1)
        datenbank.kunde_schreiben(zweiter_job, '900001', ergebnis='fertig')

        assert len(datenbank.kunden_lesen(job_id)) == 1
        assert len(datenbank.kunden_lesen(zweiter_job)) == 1


def test_doppelte_kundennummer_in_der_eingabe_bricht_den_lauf_nicht(tmp_path):
    """Zwei Zeilen mit derselben KundenNr: die erste zählt, der Lauf läuft weiter."""
    quelle = tmp_path / 'eingabe.csv'
    pd.DataFrame([
        {'SearchString': 'Denner, Hauptstrasse 5, 5620 Musterdorf', 'PLZ': '5620',
         'Stadt': 'Musterdorf', 'KundenNr': '900001'},
        {'SearchString': 'Denner, Nebenstrasse 9, 5620 Musterdorf', 'PLZ': '5620',
         'Stadt': 'Musterdorf', 'KundenNr': '900001'},
    ]).to_csv(quelle, sep=';', index=False, encoding='utf-8-sig')

    with Datenbank(tmp_path / 'lauf.sqlite') as datenbank:
        ergebnis = Lauf(FakeProvider.aus_csv(str(FIXTURE)), datenbank).ausfuehren(
            quelle, str(tmp_path / 'ergebnis'))
        assert len(datenbank.kunden_lesen(ergebnis['job_id'])) == 1

    assert ergebnis['kunden_total'] == 1
    assert ergebnis['doppelte_kundennummern'] == 1


# ============================================================================
# Datenbankschema nach 02_DATENVERTRAG.md §5
# ============================================================================

def test_schema_hat_die_drei_tabellen_und_beide_indizes(tmp_path):
    with Datenbank(tmp_path / 'lauf.sqlite') as datenbank:
        tabellen = {z['name'] for z in datenbank.verbindung.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        indizes = {z['name'] for z in datenbank.verbindung.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'")}

    assert {'job', 'kunde', 'kandidat'} <= tabellen
    assert indizes == {'idx_kunde_job', 'idx_kunde_nr', 'idx_kandidat_kunde'}


@pytest.mark.parametrize('tabelle, erwartete_spalten', [
    ('job', ['id', 'modus', 'dateiname', 'status', 'email', 'kunden_total',
             'kunden_erledigt', 'fehlermeldung', 'erstellt_am', 'gestartet_am',
             'beendet_am']),
    ('kunde', ['id', 'job_id', 'kunden_nr', 'search_string', 'plz', 'stadt',
               'place_id', 'lat', 'lng', 'ergebnis', 'qualitaet', 'grund',
               'verarbeitet_am']),
    ('kandidat', ['id', 'kunde_id', 'title', 'street', 'postal_code', 'city',
                  'address', 'place_id', 'cid', 'location', 'phone',
                  'phone_unformatted', 'website', 'opening_hours',
                  'permanently_closed', 'temporarily_closed', 'score',
                  'entscheid', 'grund']),
])
def test_spalten_der_tabellen(tmp_path, tabelle, erwartete_spalten):
    with Datenbank(tmp_path / 'lauf.sqlite') as datenbank:
        spalten = [z['name'] for z in
                   datenbank.verbindung.execute(f'PRAGMA table_info({tabelle})')]
    assert spalten == erwartete_spalten


def test_zustaende_und_entscheide_werden_geprueft(tmp_path):
    with Datenbank(tmp_path / 'lauf.sqlite') as datenbank:
        job_id = datenbank.job_anlegen('A', 'test.csv')
        with pytest.raises(ValueError):
            datenbank.status_setzen(job_id, 'IRGENDWAS')
        with pytest.raises(ValueError):
            datenbank.job_anlegen('C', 'test.csv')
        kunde_id = datenbank.kunde_schreiben(job_id, '900001', ergebnis='fertig')
        with pytest.raises(ValueError):
            datenbank.kandidaten_schreiben(
                kunde_id, [(Candidate(title='X'), 50, 'vielleicht', 'Grund')])


def test_job_durchlaeuft_die_zustaende(tmp_path):
    with Datenbank(tmp_path / 'lauf.sqlite') as datenbank:
        job_id = datenbank.job_anlegen('A', 'test.csv', kunden_total=3,
                                       email='sachbearbeiter@example.ch')
        assert datenbank.job_lesen(job_id)['status'] == 'NEU'
        assert datenbank.job_lesen(job_id)['gestartet_am'] is None

        datenbank.status_setzen(job_id, 'LAEUFT')
        assert datenbank.job_lesen(job_id)['gestartet_am']

        datenbank.status_setzen(job_id, 'FERTIG')
        job = datenbank.job_lesen(job_id)

    assert job['status'] == 'FERTIG'
    assert job['beendet_am']
    assert job['email'] == 'sachbearbeiter@example.ch'


# ============================================================================
# Candidate und die beiden Provider
# ============================================================================

def test_candidate_felder_entsprechen_der_tabelle_kandidat(tmp_path):
    """§7: dieselben Felder wie kandidat, ohne id, kunde_id, score, entscheid, grund."""
    with Datenbank(tmp_path / 'lauf.sqlite') as datenbank:
        spalten = [z['name'] for z in
                   datenbank.verbindung.execute('PRAGMA table_info(kandidat)')]

    ohne = {'id', 'kunde_id', 'score', 'entscheid', 'grund'}
    assert [f.name for f in fields(Candidate)] == [s for s in spalten if s not in ohne]


def test_candidate_macht_aus_allem_text():
    kandidat = Candidate(title='Muster', location={'lat': 47.35, 'lng': 8.24},
                         permanently_closed=False, cid=111000001,
                         opening_hours=[{'day': 'Montag', 'hours': '08-19'}],
                         website=None)

    assert kandidat.location == "{'lat': 47.35, 'lng': 8.24}"
    assert kandidat.permanently_closed == 'False'
    assert kandidat.cid == '111000001'
    assert kandidat.opening_hours == "[{'day': 'Montag', 'hours': '08-19'}]"
    assert kandidat.website == ''


def test_apify_normalisierung_uebersetzt_die_feldnamen():
    roh = {
        'title': 'Denner Musterdorf',
        'street': 'Hauptstrasse 5',
        'postalCode': '5620',
        'city': 'Musterdorf',
        'address': 'Hauptstrasse 5, 5620 Musterdorf',
        'placeId': 'PLACE_A001',
        'cid': '111000001',
        'location': {'lat': 47.35, 'lng': 8.24},
        'phone': '044 111 22 33',
        'phoneUnformatted': '+41441112233',
        'website': 'https://beispiel-a.example',
        'openingHours': [{'day': 'Montag', 'hours': '08:00 bis 19:00'}],
        'permanentlyClosed': False,
        'temporarilyClosed': False,
        # Felder, die es nur bei Apify gibt und die niemanden interessieren:
        'categoryName': 'Supermarkt', 'totalScore': 4.2, 'reviewsCount': 88,
    }

    kandidat = ApifyProvider.normalisieren(roh)

    assert kandidat.title == 'Denner Musterdorf'
    assert kandidat.postal_code == '5620'
    assert kandidat.place_id == 'PLACE_A001'
    assert kandidat.phone_unformatted == '+41441112233'
    assert kandidat.location == "{'lat': 47.35, 'lng': 8.24}"
    assert not kandidat.ist_leer()


def test_apify_normalisierung_haelt_luecken_aus():
    kandidat = ApifyProvider.normalisieren({'title': 'Nur ein Titel'})
    assert kandidat.title == 'Nur ein Titel'
    assert kandidat.street == ''
    assert kandidat.location == ''


def test_apify_leerer_treffer_wird_nicht_geliefert():
    assert ApifyProvider.normalisieren({}).ist_leer()


def test_apify_actor_input_enthaelt_die_produktiven_werte():
    """Die Werte, mit denen die 5'000 Kunden gelaufen sind (Umbauplan §9)."""
    assert STANDARD_ACTOR_INPUT['maxCrawledPlacesPerSearch'] == 6
    assert STANDARD_ACTOR_INPUT['scrapeDirectories'] is True
    assert STANDARD_ACTOR_INPUT['countryCode'] == 'ch'


def test_apify_ohne_erfolgreichen_lauf_liefert_nichts_und_bricht_ab():
    """Läuft der Actor nach dem Timeout noch, wird er abgebrochen statt bezahlt."""
    abgebrochen = []

    class LaufStub:
        def wait_for_finish(self, wait_secs=None):
            # 90 minus die Reserve, damit der Provider vor dem Lauf entscheidet
            assert wait_secs == 85
            return {'id': 'LAUF_1', 'status': 'RUNNING'}

        def abort(self):
            abgebrochen.append(True)

    class ActorStub:
        def start(self, **kwargs):
            assert kwargs['timeout_secs'] == 85
            return {'id': 'LAUF_1', 'status': 'RUNNING'}

    class ClientStub:
        def run(self, lauf_id):
            assert lauf_id == 'LAUF_1'
            return LaufStub()

    provider = ApifyProvider('token', 'actor')
    provider.actor = ActorStub()
    provider.client = ClientStub()

    assert provider.fetch_by_text('Muster Laden, Hauptstrasse 1, 5620 Musterdorf',
                                  '5620') == []
    assert abgebrochen == [True]


def test_apify_beherrscht_keine_id_suche():
    with pytest.raises(NotImplementedError):
        ApifyProvider('token', 'actor').fetch_by_id('PLACE_A001')


def test_fakeprovider_liest_die_antwortdatei():
    provider = FakeProvider.aus_csv(str(FIXTURE))

    treffer = provider.fetch_by_text('Denner, Hauptstrasse 5, 5620 Musterdorf', '5620')
    assert [k.title for k in treffer] == ['Denner Musterdorf', 'Denner Satellit',
                                          'Spar Beispielstadt']

    # 900008 steht mit einer leeren Zeile in der Datei: bekannt, aber ohne Treffer.
    assert provider.fetch_by_text(
        'Restaurant Musterkrone, Kirchgasse 7, 7000 Talheim', '7000') == []

    # Unbekannter Suchbegriff: ebenfalls nichts, kein Fehler.
    assert provider.fetch_by_text('Gibt es nicht, Nirgendweg 1, 9999 Nirgendwo',
                                  '9999') == []


def test_fakeprovider_findet_ueber_place_id():
    provider = FakeProvider.aus_csv(str(FIXTURE))
    assert provider.fetch_by_id('PLACE_A001').title == 'Denner Musterdorf'
    assert provider.fetch_by_id('GIBT_ES_NICHT') is None


def test_fakeprovider_braucht_pflichtspalten(tmp_path):
    quelle = tmp_path / 'antworten.csv'
    pd.DataFrame([{'title': 'Ohne Suchbegriff'}]).to_csv(
        quelle, sep=';', index=False, encoding='utf-8-sig')

    with pytest.raises(ValueError, match='SearchString'):
        FakeProvider.aus_csv(str(quelle))


# ============================================================================
# Der Lauf selbst
# ============================================================================

def test_lauf_meldet_fehlende_pflichtspalten(tmp_path):
    quelle = tmp_path / 'eingabe.csv'
    pd.DataFrame([{'SearchString': 'Muster', 'PLZ': '5620'}]).to_csv(
        quelle, sep=';', index=False, encoding='utf-8-sig')

    with Datenbank(tmp_path / 'lauf.sqlite') as datenbank:
        with pytest.raises(ValueError, match='KundenNr'):
            Lauf(FakeProvider(), datenbank).ausfuehren(quelle, str(tmp_path / 'aus'))


def test_lauf_legt_den_ordner_neben_der_eingabedatei_an(tmp_path):
    """§2: <eingabedateiname>_ergebnis/ ohne ausdrückliche Angabe."""
    eingabe = eingabedatei_aus_fixture(tmp_path)

    with Datenbank(tmp_path / 'lauf.sqlite') as datenbank:
        ergebnis = Lauf(FakeProvider.aus_csv(str(FIXTURE)), datenbank).ausfuehren(eingabe)

    ordner = Path(ergebnis['dateien']['fertig_fuer_erp']).parent
    assert ordner == tmp_path / 'eingabe_ergebnis'
    for dateiname in OUTPUT_FILES.values():
        assert (ordner / dateiname).exists()


def test_fehler_im_provider_setzt_den_job_nicht_auf_fertig(tmp_path):
    """Ein Provider, der zusammenbricht, führt zu ③ — nicht zu einem Abbruch."""

    class KaputterProvider:
        def fetch_by_text(self, search_string, plz):
            raise RuntimeError('Datenquelle nicht erreichbar')

        def fetch_by_id(self, place_id):
            return None

    ziel = tmp_path / 'ergebnis'
    with Datenbank(tmp_path / 'lauf.sqlite') as datenbank:
        ergebnis = Lauf(KaputterProvider(), datenbank).ausfuehren(
            eingabedatei_aus_fixture(tmp_path), str(ziel))

    assert ergebnis['status'] == 'FERTIG'
    assert len(lies(ziel / OUTPUT_FILES['nicht_moeglich'])) == 10
