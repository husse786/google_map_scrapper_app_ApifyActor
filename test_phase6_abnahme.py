# test_phase6_abnahme.py
# One test per acceptance criterion of phase 6 (agent/01_PHASENPLAN.md).
# No network: the Google provider is exercised against recorded answers.
# All place ids and coordinates are made up.

from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

import modus_b
import webapp
from data_cleaner import OUTPUT_COLUMNS, OUTPUT_FILES, DataCleaner
from db import Datenbank
from fake_provider import FakeProvider
from google_provider import GoogleProvider
from pipeline import Lauf
from place_provider import Candidate
from upload_pruefung import pruefe_datei
from worker import Worker

REPO = Path(__file__).parent
FIXTURE = REPO / 'agent' / 'testdaten' / 'fixture_optimierte_daten.csv'
HAUPTDATEIEN = ('fertig_fuer_erp', 'zur_pruefung', 'nicht_moeglich')

# Erfundene Koordinaten. Musterdorf liegt bei 47.3500 / 8.2400.
MUSTERDORF = (47.3500, 8.2400)


# ============================================================================
# Hilfen
# ============================================================================

def lies(pfad) -> pd.DataFrame:
    return pd.read_csv(pfad, sep=';', encoding='utf-8-sig', dtype=str).fillna('')


def kandidat(**werte) -> Candidate:
    """Ein Treffer, wie ihn der GoogleProvider liefern würde."""
    grund = {
        'title': 'Denner Musterdorf',
        'street': 'Hauptstrasse 5',
        'postal_code': '5620',
        'city': 'Musterdorf',
        'address': 'Hauptstrasse 5, 5620 Musterdorf',
        'place_id': 'PLACE_A001',
        'location': str({'lat': MUSTERDORF[0], 'lng': MUSTERDORF[1]}),
        'phone': '044 111 22 33',
        'phone_unformatted': '+41441112233',
        'website': 'https://beispiel-a.example',
        'opening_hours': "['Montag: 08:00–19:00']",
        'permanently_closed': 'False',
        'temporarily_closed': 'False',
    }
    grund.update(werte)
    return Candidate(**grund)


def stamm(place_id: str = 'PLACE_A001', lat: str = '', lng: str = '') -> dict:
    return {'placeId': place_id, 'lat': lat, 'lng': lng, 'KundenNr': '900001'}


def eingabe_b(tmp_path: Path, zeilen: list, name: str = 'IDs.csv') -> Path:
    ziel = tmp_path / name
    pd.DataFrame(zeilen).to_csv(ziel, sep=';', index=False, encoding='utf-8-sig')
    return ziel


class IdProvider:
    """Antwortet auf Ids aus einem Nachschlagewerk. Kein Netz."""

    def __init__(self, antworten: dict):
        self.antworten = antworten
        self.aufrufe = []

    def fetch_by_id(self, place_id):
        self.aufrufe.append(place_id)
        return self.antworten.get(place_id)

    def fetch_by_text(self, search_string, plz):
        raise AssertionError('Im Modus B darf nicht gesucht werden.')


def entscheide(place_id='PLACE_A001', lat='', lng='', treffer='vorhanden', **werte):
    """Kürzel: ein Kunde durch die Entscheidung des Modus B schicken."""
    gefunden = None if treffer is None else kandidat(**werte)
    return modus_b.entscheide_kunde('900001', stamm(place_id, lat, lng), gefunden)


def datei_von(ablage: dict) -> str:
    gefuellt = [name for name in HAUPTDATEIEN if ablage[name]]
    assert len(gefuellt) == 1, f'Kunde in {len(gefuellt)} Dateien statt in einer'
    return gefuellt[0]


def zeile_von(ablage: dict) -> dict:
    return ablage[datei_von(ablage)][0]


# ============================================================================
# Kriterium: Gültige ID → ① mit OK (ID)
# ============================================================================

def test_gueltige_id_geht_nach_eins():
    ablage = entscheide()

    assert datei_von(ablage) == 'fertig_fuer_erp'
    zeile = zeile_von(ablage)
    assert zeile['qualitaet'] == 'OK (ID)'
    assert zeile['title'] == 'Denner Musterdorf'
    assert zeile['grund']
    assert zeile['score'] == 100.0


def test_gueltige_id_mit_passender_position_geht_nach_eins():
    ablage = entscheide(lat=str(MUSTERDORF[0]), lng=str(MUSTERDORF[1]))

    assert datei_von(ablage) == 'fertig_fuer_erp'
    assert zeile_von(ablage)['qualitaet'] == 'OK (ID)'
    assert 'Standort stimmt' in zeile_von(ablage)['grund']


# ============================================================================
# Kriterium: Unbekannte ID → ③ mit NICHT_MOEGLICH (ID ungueltig)
# ============================================================================

def test_unbekannte_id_geht_nach_drei():
    ablage = entscheide(treffer=None)

    assert datei_von(ablage) == 'nicht_moeglich'
    zeile = zeile_von(ablage)
    assert zeile['qualitaet'] == 'NICHT_MOEGLICH (ID ungueltig)'
    assert 'gelöscht' in zeile['grund'] or 'ersetzt' in zeile['grund']
    assert zeile['score'] == 0.0
    # Die gesuchte Id steht trotzdem in der Zeile, damit sie auffindbar bleibt.
    assert zeile['placeId'] == 'PLACE_A001'


def test_fehlende_id_in_der_eingabe_geht_nach_drei():
    ablage = entscheide(place_id='', treffer=None)

    assert datei_von(ablage) == 'nicht_moeglich'
    zeile = zeile_von(ablage)
    assert zeile['qualitaet'] == 'NICHT_MOEGLICH (Eingabe unbrauchbar)'
    assert 'Google-ID' in zeile['grund']


# ============================================================================
# Kriterium: permanentlyClosed → ② mit verständlichem Grund
# ============================================================================

def test_dauerhaft_geschlossen_geht_nach_zwei():
    ablage = entscheide(permanently_closed='True')

    assert datei_von(ablage) == 'zur_pruefung'
    zeile = zeile_von(ablage)
    assert zeile['qualitaet'] == 'PRUEFUNG (geschlossen)'
    assert zeile['grund'] == ('Google meldet den Betrieb als dauerhaft '
                              'geschlossen: "Denner Musterdorf".')


def test_geschlossen_schlaegt_die_entfernung():
    """Beides zugleich: die Schliessung ist die wichtigere Auskunft."""
    ablage = entscheide(lat='47.4000', lng='8.3000', permanently_closed='True')

    assert zeile_von(ablage)['qualitaet'] == 'PRUEFUNG (geschlossen)'


def test_voruebergehend_geschlossen_ist_kein_prueffall():
    """03_ENTSCHEIDUNGEN.md B4 nennt nur die dauerhafte Schliessung."""
    ablage = entscheide(temporarily_closed='True')

    assert datei_von(ablage) == 'fertig_fuer_erp'


# ============================================================================
# Kriterium: 1.4 km entfernt → ②; 150 m entfernt → ①
# ============================================================================

def verschoben(meter_noerdlich: float) -> tuple:
    """Eine Position, die um so viele Meter nach Norden verschoben ist."""
    return MUSTERDORF[0] + meter_noerdlich / 111_320, MUSTERDORF[1]


def test_position_1400_meter_entfernt_geht_nach_zwei():
    breite, laenge = verschoben(1400)
    ablage = entscheide(lat=str(breite), lng=str(laenge))

    assert datei_von(ablage) == 'zur_pruefung'
    zeile = zeile_von(ablage)
    assert zeile['qualitaet'] == 'PRUEFUNG (Standort abweichend)'
    assert '1.4 km' in zeile['grund']
    assert 'von der gespeicherten Position entfernt' in zeile['grund']


def test_position_150_meter_entfernt_geht_nach_eins():
    breite, laenge = verschoben(150)
    ablage = entscheide(lat=str(breite), lng=str(laenge))

    assert datei_von(ablage) == 'fertig_fuer_erp'
    assert zeile_von(ablage)['qualitaet'] == 'OK (ID)'
    assert '150 m' in zeile_von(ablage)['grund']


@pytest.mark.parametrize('meter, erwartet', [
    (0, 'fertig_fuer_erp'),
    (199, 'fertig_fuer_erp'),
    (200, 'fertig_fuer_erp'),   # genau die Grenze zählt noch als am selben Ort
    (201, 'zur_pruefung'),
    (5000, 'zur_pruefung'),
])
def test_die_grenze_liegt_bei_200_metern(meter, erwartet):
    breite, laenge = verschoben(meter)
    assert datei_von(entscheide(lat=str(breite), lng=str(laenge))) == erwartet


def test_haversine_rechnet_richtig():
    """Gegenprobe an einer bekannten Strecke: ein Grad Breite sind rund 111 km."""
    meter = modus_b.entfernung_meter((47.0, 8.0), (48.0, 8.0))
    assert 111_000 < meter < 111_400

    # Und die Nullstrecke ist null.
    assert modus_b.entfernung_meter(MUSTERDORF, MUSTERDORF) == pytest.approx(0)


# ============================================================================
# Kriterium: fehlende lat/lng → keine Distanzprüfung, kein Prüffall
# ============================================================================

@pytest.mark.parametrize('lat, lng', [
    ('', ''),
    ('47.35', ''),
    ('', '8.24'),
    ('keine Angabe', 'auch nicht'),
])
def test_ohne_position_keine_distanzpruefung(lat, lng):
    """Auch wenn der Betrieb weit weg liegt: ohne Vergleichspunkt kein Prüffall."""
    ablage = entscheide(lat=lat, lng=lng,
                        location=str({'lat': 46.0, 'lng': 7.0}))

    assert datei_von(ablage) == 'fertig_fuer_erp'
    assert 'keine Angabe zum Vergleichen' in zeile_von(ablage)['grund']


def test_ohne_standort_von_google_keine_distanzpruefung():
    ablage = entscheide(lat='47.35', lng='8.24', location='')

    assert datei_von(ablage) == 'fertig_fuer_erp'
    assert 'keine Angabe zum Vergleichen' in zeile_von(ablage)['grund']


# ============================================================================
# Kriterium: Namensänderung allein löst keinen Prüffall aus
# ============================================================================

def test_namensaenderung_ist_kein_prueffall():
    """Aus Volg wird Spar — derselbe Betrieb, dieselbe Id."""
    ablage = entscheide(title='Spar Musterdorf',
                        lat=str(MUSTERDORF[0]), lng=str(MUSTERDORF[1]))

    assert datei_von(ablage) == 'fertig_fuer_erp'
    zeile = zeile_von(ablage)
    assert zeile['qualitaet'] == 'OK (ID)'
    assert zeile['title'] == 'Spar Musterdorf'


def test_auch_eine_andere_adresse_am_selben_ort_ist_kein_prueffall():
    """Google schreibt die Adresse um, die Position bleibt — kein Prüffall."""
    ablage = entscheide(address='Hauptstrasse 5a, 5620 Musterdorf',
                        street='Hauptstrasse 5a',
                        lat=str(MUSTERDORF[0]), lng=str(MUSTERDORF[1]))

    assert datei_von(ablage) == 'fertig_fuer_erp'


# ============================================================================
# Kriterium: beide Modi schreiben identisch aufgebaute Ausgabedateien
# ============================================================================

def test_beide_modi_schreiben_dieselben_spalten(tmp_path):
    # Modus A über den FakeProvider.
    eingabe_a = tmp_path / 'A.csv'
    df = lies(FIXTURE)[['SearchString', 'PLZ', 'Stadt', 'KundenNr']].drop_duplicates(
        subset=['KundenNr'])
    df.to_csv(eingabe_a, sep=';', index=False, encoding='utf-8-sig')
    with Datenbank(tmp_path / 'a.sqlite') as datenbank:
        Lauf(FakeProvider.aus_csv(str(FIXTURE)), datenbank).ausfuehren(
            eingabe_a, str(tmp_path / 'aus_a'))

    # Modus B über die gespeicherten Ids.
    eingabe = eingabe_b(tmp_path, [
        {'placeId': 'PLACE_A001', 'lat': '', 'lng': '', 'KundenNr': '900001'},
        {'placeId': 'GIBT_ES_NICHT', 'lat': '', 'lng': '', 'KundenNr': '900002'},
        {'placeId': 'PLACE_ZU', 'lat': '', 'lng': '', 'KundenNr': '900003'},
    ])
    provider = IdProvider({'PLACE_A001': kandidat(),
                           'PLACE_ZU': kandidat(place_id='PLACE_ZU',
                                                permanently_closed='True')})
    with Datenbank(tmp_path / 'b.sqlite') as datenbank:
        Lauf(provider, datenbank, modus='B').ausfuehren(
            eingabe, str(tmp_path / 'aus_b'))

    for name in HAUPTDATEIEN:
        spalten_a = list(lies(tmp_path / 'aus_a' / OUTPUT_FILES[name]).columns)
        spalten_b = list(lies(tmp_path / 'aus_b' / OUTPUT_FILES[name]).columns)
        assert spalten_a == spalten_b == OUTPUT_COLUMNS

    # Und die Kunden sind richtig verteilt.
    assert set(lies(tmp_path / 'aus_b' / OUTPUT_FILES['fertig_fuer_erp'])
               ['KundenNr']) == {'900001'}
    assert set(lies(tmp_path / 'aus_b' / OUTPUT_FILES['zur_pruefung'])
               ['KundenNr']) == {'900003'}
    assert set(lies(tmp_path / 'aus_b' / OUTPUT_FILES['nicht_moeglich'])
               ['KundenNr']) == {'900002'}


def test_jede_zeile_traegt_score_und_grund(tmp_path):
    eingabe = eingabe_b(tmp_path, [
        {'placeId': 'PLACE_A001', 'lat': '', 'lng': '', 'KundenNr': '900001'},
        {'placeId': 'GIBT_ES_NICHT', 'lat': '', 'lng': '', 'KundenNr': '900002'},
        {'placeId': 'PLACE_ZU', 'lat': '', 'lng': '', 'KundenNr': '900003'},
    ])
    provider = IdProvider({'PLACE_A001': kandidat(),
                           'PLACE_ZU': kandidat(permanently_closed='True')})
    ziel = tmp_path / 'aus'
    with Datenbank(tmp_path / 'b.sqlite') as datenbank:
        Lauf(provider, datenbank, modus='B').ausfuehren(eingabe, str(ziel))

    for name in HAUPTDATEIEN:
        df = lies(ziel / OUTPUT_FILES[name])
        assert not df.empty
        assert (df['score'].str.strip() != '').all()
        assert (df['grund'].str.strip() != '').all()
        assert (df['qualitaet'].str.strip() != '').all()


# ============================================================================
# Der Lauf im Modus B
# ============================================================================

def test_lauf_im_modus_b_haelt_die_invariante(tmp_path):
    zeilen = [{'placeId': f'PLACE_{i}', 'lat': '', 'lng': '',
               'KundenNr': f'9{i:05d}'} for i in range(1, 13)]
    eingabe = eingabe_b(tmp_path, zeilen)
    # Nur jede zweite Id ist bekannt.
    provider = IdProvider({f'PLACE_{i}': kandidat(place_id=f'PLACE_{i}')
                           for i in range(1, 13, 2)})
    ziel = tmp_path / 'aus'

    with Datenbank(tmp_path / 'b.sqlite') as datenbank:
        ergebnis = Lauf(provider, datenbank, modus='B', arbeiter=6).ausfuehren(
            eingabe, str(ziel))

    assert ergebnis['status'] == 'FERTIG'
    assert ergebnis['kunden_erledigt'] == 12
    mengen = {name: set(lies(ziel / OUTPUT_FILES[name])['KundenNr'])
              for name in HAUPTDATEIEN}
    vereinigung = set().union(*mengen.values())
    assert sum(len(m) for m in mengen.values()) == len(vereinigung) == 12
    assert len(mengen['fertig_fuer_erp']) == 6
    assert len(mengen['nicht_moeglich']) == 6


def test_modus_b_sucht_nicht(tmp_path):
    """Kein Scoring, keine Textsuche — der IdProvider würde sonst schreien."""
    eingabe = eingabe_b(tmp_path, [
        {'placeId': 'PLACE_A001', 'lat': '', 'lng': '', 'KundenNr': '900001'}])
    provider = IdProvider({'PLACE_A001': kandidat()})

    with Datenbank(tmp_path / 'b.sqlite') as datenbank:
        Lauf(provider, datenbank, modus='B').ausfuehren(eingabe, str(tmp_path / 'aus'))

    assert provider.aufrufe == ['PLACE_A001']


def test_modus_b_speichert_id_und_position(tmp_path):
    """§5: kunde.place_id, lat und lng sind für Modus B da — sie werden gefüllt."""
    eingabe = eingabe_b(tmp_path, [
        {'placeId': 'PLACE_A001', 'lat': '47.35', 'lng': '8.24',
         'KundenNr': '900001'}])
    provider = IdProvider({'PLACE_A001': kandidat()})

    with Datenbank(tmp_path / 'b.sqlite') as datenbank:
        ergebnis = Lauf(provider, datenbank, modus='B').ausfuehren(
            eingabe, str(tmp_path / 'aus'))
        kunde = datenbank.kunden_lesen(ergebnis['job_id'])[0]
        kandidaten = datenbank.kandidaten_lesen(kunde['id'])
        job = datenbank.job_lesen(ergebnis['job_id'])

    assert job['modus'] == 'B'
    assert kunde['place_id'] == 'PLACE_A001'
    assert kunde['lat'] == '47.35' and kunde['lng'] == '8.24'
    assert kunde['ergebnis'] == 'fertig'
    assert len(kandidaten) == 1
    assert kandidaten[0]['entscheid'] == 'gewaehlt'
    assert kandidaten[0]['score'] == 100.0


def test_wiederaufnahme_im_modus_b_fragt_nicht_erneut(tmp_path):
    eingabe = eingabe_b(tmp_path, [
        {'placeId': 'PLACE_A001', 'lat': '47.35', 'lng': '8.24',
         'KundenNr': '900001'},
        {'placeId': 'PLACE_A002', 'lat': '', 'lng': '', 'KundenNr': '900002'}])
    antworten = {'PLACE_A001': kandidat(),
                 'PLACE_A002': kandidat(place_id='PLACE_A002')}
    ziel = tmp_path / 'aus'

    with Datenbank(tmp_path / 'b.sqlite') as datenbank:
        ergebnis = Lauf(IdProvider(antworten), datenbank, modus='B').ausfuehren(
            eingabe, str(ziel))
        datenbank.status_setzen(ergebnis['job_id'], 'LAEUFT')

    class VerbotenerProvider:
        def fetch_by_id(self, place_id):
            raise AssertionError('Es wurde erneut bei Google gefragt.')

        def fetch_by_text(self, search_string, plz):
            raise AssertionError('Es wurde gesucht.')

    zweites_ziel = tmp_path / 'aus2'
    with Datenbank(tmp_path / 'b.sqlite') as datenbank:
        nachher = Lauf(VerbotenerProvider(), datenbank, modus='B').fortsetzen(
            ergebnis['job_id'], eingabe, str(zweites_ziel))

    assert nachher['status'] == 'FERTIG'
    for name in HAUPTDATEIEN:
        assert (ziel / OUTPUT_FILES[name]).read_text('utf-8-sig') == \
            (zweites_ziel / OUTPUT_FILES[name]).read_text('utf-8-sig')


def test_fortsetzen_uebernimmt_den_modus_aus_dem_job(tmp_path):
    """Ein Lauf arbeitet weiter, wie er begonnen hat — auch wenn der Aufrufer irrt."""
    eingabe = eingabe_b(tmp_path, [
        {'placeId': 'PLACE_A001', 'lat': '', 'lng': '', 'KundenNr': '900001'}])

    with Datenbank(tmp_path / 'b.sqlite') as datenbank:
        ergebnis = Lauf(IdProvider({'PLACE_A001': kandidat()}), datenbank,
                        modus='B').ausfuehren(eingabe, str(tmp_path / 'aus'))
        datenbank.status_setzen(ergebnis['job_id'], 'LAEUFT')

        lauf = Lauf(IdProvider({}), datenbank, modus='A')  # falscher Modus
        lauf.fortsetzen(ergebnis['job_id'], eingabe, str(tmp_path / 'aus2'))
        assert lauf.modus == 'B'


# ============================================================================
# Die Prüfung beim Hochladen kennt den Modus
# ============================================================================

def test_pruefung_modus_b_verlangt_placeid(tmp_path):
    quelle = eingabe_b(tmp_path, [{'lat': '47.35', 'lng': '8.24',
                                   'KundenNr': '900001'}])

    bericht = pruefe_datei(quelle, modus='B')

    befund = bericht.befund('pflichtspalten')
    assert befund is not None
    assert 'placeId' in befund.meldung
    assert 'placeId;lat;lng;KundenNr' in befund.meldung
    assert bericht.start_moeglich is False


def test_pruefung_modus_b_prueft_keine_strassen(tmp_path):
    """Im Modus B gibt es kein Strassenfeld — die beiden Prüfungen entfallen."""
    quelle = eingabe_b(tmp_path, [
        {'placeId': 'PLACE_A001', 'lat': '', 'lng': '', 'KundenNr': '900001'}])

    bericht = pruefe_datei(quelle, modus='B')

    assert bericht.befunde == []
    assert bericht.start_moeglich is True
    assert bericht.kunden == 1


def test_pruefung_modus_b_zaehlt_zeilen(tmp_path):
    zeilen = [{'placeId': f'PLACE_{i}', 'lat': '', 'lng': '',
               'KundenNr': f'9{i:05d}'} for i in range(1, 10_002)]
    quelle = eingabe_b(tmp_path, zeilen)

    bericht = pruefe_datei(quelle, modus='B')

    assert bericht.befund('zeilenzahl') is not None
    assert bericht.start_moeglich is False


# ============================================================================
# GoogleProvider — gegen aufgezeichnete Antworten, ohne Netz
# ============================================================================

GOOGLE_ANTWORT = {
    'id': 'PLACE_A001',
    'displayName': {'text': 'Denner Musterdorf', 'languageCode': 'de'},
    'formattedAddress': 'Hauptstrasse 5, 5620 Musterdorf, Schweiz',
    'addressComponents': [
        {'longText': '5', 'shortText': '5', 'types': ['street_number']},
        {'longText': 'Hauptstrasse', 'shortText': 'Hauptstrasse', 'types': ['route']},
        {'longText': 'Musterdorf', 'shortText': 'Musterdorf', 'types': ['locality']},
        {'longText': '5620', 'shortText': '5620', 'types': ['postal_code']},
    ],
    'location': {'latitude': 47.35, 'longitude': 8.24},
    'nationalPhoneNumber': '044 111 22 33',
    'internationalPhoneNumber': '+41 44 111 22 33',
    'websiteUri': 'https://beispiel-a.example',
    'regularOpeningHours': {'weekdayDescriptions': ['Montag: 08:00–19:00']},
    'businessStatus': 'OPERATIONAL',
}


def test_google_antwort_wird_zu_einem_candidate():
    treffer = GoogleProvider.normalisieren(GOOGLE_ANTWORT)

    assert treffer.title == 'Denner Musterdorf'
    assert treffer.street == 'Hauptstrasse 5'
    assert treffer.postal_code == '5620'
    assert treffer.city == 'Musterdorf'
    assert treffer.place_id == 'PLACE_A001'
    assert treffer.phone == '044 111 22 33'
    assert treffer.phone_unformatted == '+41 44 111 22 33'
    assert treffer.website == 'https://beispiel-a.example'
    assert treffer.permanently_closed == 'False'
    assert treffer.temporarily_closed == 'False'
    # Dieselbe Schreibweise wie bei Apify, damit die Spalte gleich aussieht.
    assert treffer.location == "{'lat': 47.35, 'lng': 8.24}"
    assert modus_b.koordinaten(treffer.location) == (47.35, 8.24)


def test_google_meldet_dauerhaft_geschlossen():
    roh = dict(GOOGLE_ANTWORT, businessStatus='CLOSED_PERMANENTLY')
    treffer = GoogleProvider.normalisieren(roh)

    assert treffer.permanently_closed == 'True'
    assert modus_b.ist_wahr(treffer.permanently_closed)


def test_google_meldet_voruebergehend_geschlossen():
    roh = dict(GOOGLE_ANTWORT, businessStatus='CLOSED_TEMPORARILY')
    treffer = GoogleProvider.normalisieren(roh)

    assert treffer.temporarily_closed == 'True'
    assert treffer.permanently_closed == 'False'


def test_google_antwort_mit_luecken():
    treffer = GoogleProvider.normalisieren({'id': 'PLACE_X'})

    assert treffer.place_id == 'PLACE_X'
    assert treffer.title == ''
    assert treffer.location == ''
    assert not treffer.ist_leer()  # die Id allein macht ihn noch brauchbar


def test_google_holt_nur_die_vertraglichen_felder():
    from google_provider import FELDMASKE
    for feld in ('id', 'displayName', 'formattedAddress', 'location',
                 'businessStatus'):
        assert feld in FELDMASKE
    # Nichts, was Geld kostet und niemand liest.
    for feld in ('reviews', 'photos', 'priceLevel', 'rating'):
        assert feld not in FELDMASKE


def test_google_unbekannte_id_liefert_nichts():
    class AntwortStub:
        status_code = 404
        text = 'NOT_FOUND'

    provider = GoogleProvider('schluessel')
    provider._sitzung = type('S', (), {'get': lambda self, *a, **k: AntwortStub()})()

    assert provider.fetch_by_id('GIBT_ES_NICHT') is None


def test_google_fehler_liefert_nichts_statt_absturz():
    import requests

    class KaputteSitzung:
        def get(self, *args, **kwargs):
            raise requests.RequestException('Netz weg')

    provider = GoogleProvider('schluessel')
    provider._sitzung = KaputteSitzung()

    assert provider.fetch_by_id('PLACE_A001') is None


def test_google_leere_id_fragt_gar_nicht_erst():
    class VerboteneSitzung:
        def get(self, *args, **kwargs):
            raise AssertionError('Es wurde ohne Id gefragt.')

    provider = GoogleProvider('schluessel')
    provider._sitzung = VerboteneSitzung()

    assert provider.fetch_by_id('') is None


def test_google_beherrscht_keine_textsuche():
    with pytest.raises(NotImplementedError):
        GoogleProvider('schluessel').fetch_by_text('Denner', '5620')


def test_google_schickt_schluessel_und_feldmaske():
    gesehen = {}

    class Sitzung:
        def get(self, url, headers=None, params=None, timeout=None):
            gesehen.update(url=url, headers=headers, params=params,
                           timeout=timeout)
            return type('A', (), {'status_code': 200,
                                  'json': lambda self: GOOGLE_ANTWORT})()

    provider = GoogleProvider('geheim', timeout_sekunden=30)
    provider._sitzung = Sitzung()
    treffer = provider.fetch_by_id('PLACE_A001')

    assert treffer.title == 'Denner Musterdorf'
    assert gesehen['url'].endswith('/places/PLACE_A001')
    assert gesehen['headers']['X-Goog-Api-Key'] == 'geheim'
    assert 'displayName' in gesehen['headers']['X-Goog-FieldMask']
    assert gesehen['params']['languageCode'] == 'de'
    assert gesehen['timeout'] == 30


def test_google_ohne_schluessel_meldet_deutsch(monkeypatch):
    import google_provider

    class OhneSchluessel:
        GOOGLE_API_KEY = ''

    monkeypatch.setitem(__import__('sys').modules, 'config', OhneSchluessel)
    with pytest.raises(ValueError) as fehler:
        google_provider.aus_konfiguration()

    text = str(fehler.value)
    assert 'GOOGLE_API_KEY' in text and '.env' in text
    assert 'ß' not in text


# ============================================================================
# Der zweite Einstieg in der Oberfläche
# ============================================================================

@pytest.fixture
def browser(tmp_path, monkeypatch):
    monkeypatch.setattr(webapp, 'LAUFDATEN', tmp_path)
    monkeypatch.setattr(webapp, 'UPLOADS', tmp_path / 'uploads')
    monkeypatch.setattr(webapp, 'DATENBANK', tmp_path / 'laeufe.sqlite')
    webapp.UPLOADS.mkdir(parents=True, exist_ok=True)
    webapp.zustand.update(worker=None, hochgeladen=None, kunden=0, modus='A',
                          provider=IdProvider({'PLACE_A001': kandidat()}))
    with TestClient(webapp.app) as klient:
        yield klient
    worker = webapp.zustand['worker']
    if worker and worker.laeuft:
        worker.abbrechen()
        worker.warten(timeout=10)


def test_startseite_bietet_beide_arten_an(browser):
    seite = browser.get('/').text

    assert 'Erstanreicherung' in seite
    assert 'Auffrischen' in seite
    assert 'noch nicht verfügbar' not in seite
    assert 'value="A"' in seite and 'value="B"' in seite


def test_durchlauf_im_modus_b_ueber_den_browser(browser, tmp_path):
    inhalt = pd.DataFrame([
        {'placeId': 'PLACE_A001', 'lat': '47.35', 'lng': '8.24',
         'KundenNr': '900001'},
    ]).to_csv(sep=';', index=False).encode('utf-8-sig')

    formular = browser.get('/datei', params={'modus': 'B'})
    assert 'placeId' in formular.text

    hochgeladen = browser.post('/datei', data={'modus': 'B'},
                               files={'datei': ('IDs.csv', inhalt, 'text/csv')})
    assert hochgeladen.status_code == 200
    assert '1 Kunden erkannt' in hochgeladen.text
    assert 'Lauf starten' in hochgeladen.text

    gestartet = browser.post('/starten', follow_redirects=False)
    job_id = int(gestartet.headers['location'].rsplit('/', 1)[1])
    webapp.zustand['worker'].warten(timeout=30)

    ergebnis = browser.get(f'/ergebnis/{job_id}')
    assert 'Fertig' in ergebnis.text
    # Die Kacheln erklären den Modus B, nicht den Modus A.
    assert 'Über die gespeicherte Google-ID aufgefrischt' in ergebnis.text
    assert 'Mehrere mögliche Treffer' not in ergebnis.text

    with Datenbank(webapp.DATENBANK) as datenbank:
        job = datenbank.job_lesen(job_id)
    assert job['modus'] == 'B'
    assert job['status'] == 'FERTIG'

    datei = browser.get(f'/ergebnis/{job_id}/datei/fertig_fuer_erp')
    assert datei.content.startswith(b'\xef\xbb\xbf')
    text = datei.content.decode('utf-8-sig')
    assert 'OK (ID)' in text
    assert text.splitlines()[0].startswith('KundenNr;SearchString;PLZ;Stadt;')


def test_modus_b_ohne_placeid_startet_nicht(browser):
    inhalt = pd.DataFrame([{'lat': '47.35', 'lng': '8.24', 'KundenNr': '900001'}]
                          ).to_csv(sep=';', index=False).encode('utf-8-sig')

    browser.get('/datei', params={'modus': 'B'})
    antwort = browser.post('/datei', data={'modus': 'B'},
                           files={'datei': ('IDs.csv', inhalt, 'text/csv')})

    assert 'placeId' in antwort.text
    assert 'Lauf starten' not in antwort.text
    assert 'Traceback' not in antwort.text


def test_worker_gibt_den_modus_weiter(tmp_path):
    eingabe = eingabe_b(tmp_path, [
        {'placeId': 'PLACE_A001', 'lat': '', 'lng': '', 'KundenNr': '900001'}])
    worker = Worker(IdProvider({'PLACE_A001': kandidat()}),
                    tmp_path / 'b.sqlite', modus='B')

    job_id = worker.starten(eingabe, str(tmp_path / 'aus'))
    assert worker.warten(timeout=30)

    with Datenbank(tmp_path / 'b.sqlite') as datenbank:
        assert datenbank.job_lesen(job_id)['modus'] == 'B'
