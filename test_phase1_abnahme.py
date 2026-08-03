# test_phase1_abnahme.py
# One test per acceptance criterion of phase 1 (agent/01_PHASENPLAN.md).
# All data comes from agent/testdaten/fixture_optimierte_daten.csv or is made up
# on the spot. No real customer data.

from pathlib import Path

import pandas as pd
import pytest

from data_cleaner import OUTPUT_COLUMNS, DataCleaner

FIXTURE = Path(__file__).parent / 'agent' / 'testdaten' / 'fixture_optimierte_daten.csv'

HAUPTDATEIEN = ('fertig_fuer_erp', 'zur_pruefung', 'nicht_moeglich')

# 05_TESTDATEN.md: where each of the ten fixture customers has to end up.
FIXTURE_ERWARTUNG = {
    '900001': ('fertig_fuer_erp', 'OK (Strasse)'),
    '900002': ('zur_pruefung', 'PRUEFUNG (keine Strassentreffer)'),
    '900003': ('fertig_fuer_erp', None),
    '900004': ('fertig_fuer_erp', None),
    '900005': ('fertig_fuer_erp', None),
    '900006': ('fertig_fuer_erp', None),
    '900007': ('zur_pruefung', 'PRUEFUNG (mehrere hohe Treffer)'),
    '900008': ('nicht_moeglich', None),
    '900009': ('zur_pruefung', None),
    '900010': ('fertig_fuer_erp', None),
}

# 03_ENTSCHEIDUNGEN.md B1: the seven measured street pairs.
STRASSENPAARE = [
    ('Dorfstrasse', 'Oberdorfstrasse', False),
    ('Rainweg', 'Rebrainweg', False),
    ('Bahnhofstrasse', 'Bahnhofplatz', False),
    ('Seetalstrasse', 'Lenzburgerstrasse', False),
    ('Hundwilerhöhe', 'Hundwillerhöche', True),
    ('St. Bernhardstrasse', 'St.Bernhardstrasse', True),
    ('Wohlerstrasse', 'Wohlerstr.', True),
]


@pytest.fixture(scope='module')
def fixture_lauf(tmp_path_factory):
    """Runs the cleaner once over the fixture; all fixture tests read this."""
    ziel = tmp_path_factory.mktemp('fixture_lauf')
    pfade = DataCleaner().clean_data(str(FIXTURE), str(ziel))
    return {key: pd.read_csv(pfad, sep=';', encoding='utf-8-sig', dtype=str).fillna('')
            for key, pfad in pfade.items()}


@pytest.fixture(scope='module')
def eingabe_kunden():
    df = pd.read_csv(FIXTURE, sep=';', encoding='utf-8-sig', dtype=str).fillna('')
    return set(df['KundenNr'])


def kunden_in(df: pd.DataFrame) -> set:
    return set(df['KundenNr']) if not df.empty else set()


# ============================================================================
# Kriterium: keine KundenNr in mehr als einer der drei Ausgabedateien
# ============================================================================

def test_keine_kundennr_in_zwei_dateien(fixture_lauf):
    mengen = {name: kunden_in(fixture_lauf[name]) for name in HAUPTDATEIEN}
    for i, erste in enumerate(HAUPTDATEIEN):
        for zweite in HAUPTDATEIEN[i + 1:]:
            gemeinsam = mengen[erste] & mengen[zweite]
            assert not gemeinsam, f'{gemeinsam} steht in {erste} und in {zweite}'


# ============================================================================
# Kriterium: Summe der Kunden über alle drei Dateien = Kunden in der Eingabe
# ============================================================================

def test_summe_der_kunden_stimmt(fixture_lauf, eingabe_kunden):
    verteilt = set()
    anzahl = 0
    for name in HAUPTDATEIEN:
        kunden = kunden_in(fixture_lauf[name])
        verteilt |= kunden
        anzahl += len(kunden)

    assert anzahl == len(eingabe_kunden)
    assert verteilt == eingabe_kunden


# ============================================================================
# Kriterium: alle sieben Beispielpaare aus 03_ENTSCHEIDUNGEN.md B1
# ============================================================================

@pytest.mark.parametrize('eingabe, google, erwartet', STRASSENPAARE)
def test_strassenvergleich_b1(eingabe, google, erwartet):
    assert DataCleaner()._street_matches(eingabe, google) is erwartet


def test_hausnummern_logik_unveraendert():
    """Sind beide Hausnummern da, müssen sie gleich sein; fehlt eine, genügt der Name."""
    cleaner = DataCleaner()
    assert cleaner._street_matches('Seetalstrasse 60', 'Seetalstrasse 60') is True
    assert cleaner._street_matches('Seetalstrasse 60', 'Seetalstrasse 119') is False
    assert cleaner._street_matches('Seetalstrasse 60', 'Seetalstrasse') is True
    assert cleaner._street_matches('Seetalstrasse', 'Seetalstrasse 60') is True


# ============================================================================
# Kriterium: Einzeltreffer-Regel B2 greift, Rebranding bleibt in ①
# ============================================================================

def _einzeltreffer(tmp_path, search_string, title, street):
    quelle = tmp_path / 'eingabe.csv'
    pd.DataFrame([{
        'SearchString': search_string, 'PLZ': '8700', 'Stadt': 'Seedorf',
        'KundenNr': '900101', 'title': title,
        'address': f'{street}, 8700 Seedorf', 'street': street,
        'postalCode': '8700', 'city': 'Seedorf', 'placeId': 'PLACE_X',
    }]).to_csv(quelle, sep=';', index=False, encoding='utf-8-sig')

    pfade = DataCleaner().clean_data(str(quelle), str(tmp_path / 'ergebnis'))
    return {key: pd.read_csv(p, sep=';', encoding='utf-8-sig', dtype=str).fillna('')
            for key, p in pfade.items()}


def test_einzeltreffer_namensscore_reicht(tmp_path):
    """Bedingung (1): Namensscore >= 60 → ①."""
    out = _einzeltreffer(tmp_path, 'Volg Dorfladen, Seestrasse 8, 8700 Seedorf',
                         'Volg Dorfladen Seedorf', 'Seestrasse 8')
    assert len(out['fertig_fuer_erp']) == 1
    assert out['fertig_fuer_erp'].iloc[0]['qualitaet'] == 'OK (Einzeltreffer)'
    assert float(out['fertig_fuer_erp'].iloc[0]['score']) >= 60


def test_einzeltreffer_rebranding_bleibt_in_eins(tmp_path):
    """Bedingung (2): Name fällt auf 0, Strasse und Hausnummer stimmen → ①."""
    out = _einzeltreffer(tmp_path, 'Volg Dorfladen, Seestrasse 8, 8700 Seedorf',
                         'Spar Seedorf', 'Seestrasse 8')
    assert len(out['fertig_fuer_erp']) == 1
    treffer = out['fertig_fuer_erp'].iloc[0]
    assert treffer['qualitaet'] == 'OK (Einzeltreffer)'
    assert float(treffer['score']) < 60
    assert out['zur_pruefung'].empty


def test_einzeltreffer_unsicher_geht_zur_pruefung(tmp_path):
    """Weder Name noch Adresse tragen → ②, nicht ins ERP."""
    out = _einzeltreffer(tmp_path, 'Volg Dorfladen, Seestrasse 8, 8700 Seedorf',
                         'Spar Seedorf', 'Bahnhofweg 42')
    assert out['fertig_fuer_erp'].empty
    assert len(out['zur_pruefung']) == 1
    assert out['zur_pruefung'].iloc[0]['qualitaet'] == 'PRUEFUNG (Einzeltreffer unsicher)'


def test_einzeltreffer_ohne_hausnummer_faellt_auf_namen_zurueck(tmp_path):
    """Ohne Hausnummer auf einer Seite greift Bedingung (2) nicht."""
    out = _einzeltreffer(tmp_path, 'Volg Dorfladen, Seestrasse, 8700 Seedorf',
                         'Spar Seedorf', 'Seestrasse')
    assert out['fertig_fuer_erp'].empty
    assert out['zur_pruefung'].iloc[0]['qualitaet'] == 'PRUEFUNG (Einzeltreffer unsicher)'


# ============================================================================
# Kriterium: score und grund sind in allen drei Dateien befüllt
# ============================================================================

@pytest.mark.parametrize('datei', HAUPTDATEIEN)
def test_score_und_grund_befuellt(fixture_lauf, datei):
    df = fixture_lauf[datei]
    assert not df.empty, f'{datei} ist leer, das Kriterium wäre nicht prüfbar'
    assert (df['score'].str.strip() != '').all()
    assert (df['grund'].str.strip() != '').all()
    assert (df['qualitaet'].str.strip() != '').all()


@pytest.mark.parametrize('datei', HAUPTDATEIEN)
def test_spalten_nach_datenvertrag(fixture_lauf, datei):
    assert list(fixture_lauf[datei].columns) == OUTPUT_COLUMNS


@pytest.mark.parametrize('datei', HAUPTDATEIEN)
def test_gruende_ohne_fachsprache(fixture_lauf, datei):
    """Kein Stufe-N, kein threshold, kein ß."""
    verboten = ('stage', 'threshold', 'score <', 'no match', 'siehe log', 'ß')
    for grund in fixture_lauf[datei]['grund']:
        klein = grund.lower()
        for wort in verboten:
            assert wort not in klein, f'"{wort}" steht in: {grund}'


# ============================================================================
# Kriterium: alle 10 Fälle der Fixture landen dort, wo 05_TESTDATEN.md es vorgibt
# ============================================================================

@pytest.mark.parametrize('kunden_nr, erwartung', sorted(FIXTURE_ERWARTUNG.items()))
def test_fixture_faelle(fixture_lauf, kunden_nr, erwartung):
    datei, qualitaet = erwartung

    for name in HAUPTDATEIEN:
        treffer = kunden_in(fixture_lauf[name])
        if name == datei:
            assert kunden_nr in treffer, f'{kunden_nr} fehlt in {name}'
        else:
            assert kunden_nr not in treffer, f'{kunden_nr} steht zusätzlich in {name}'

    if qualitaet:
        df = fixture_lauf[datei]
        gefunden = set(df[df['KundenNr'] == kunden_nr]['qualitaet'])
        assert gefunden == {qualitaet}


@pytest.mark.parametrize('kunden_nr', ['900002', '900009'])
def test_doppelzaehlung_behoben(fixture_lauf, kunden_nr):
    """B1: bei null Strassentreffern nicht zusätzlich in aussortiert."""
    assert kunden_nr not in kunden_in(fixture_lauf['aussortiert'])


def test_900003_nimmt_nur_die_echte_dorfstrasse(fixture_lauf):
    """Oberdorfstrasse darf nicht mehr als Dorfstrasse durchgehen."""
    zeile = fixture_lauf['fertig_fuer_erp']
    treffer = zeile[zeile['KundenNr'] == '900003'].iloc[0]
    assert treffer['street'] == 'Dorfstrasse 5'
    assert treffer['qualitaet'] == 'OK (Strasse)'


# ============================================================================
# Weitere Zustände des Datenvertrags
# ============================================================================

def test_keine_plz_treffer_geht_nur_zur_pruefung(tmp_path):
    """Kein Kandidat mit passender PLZ → ②, nicht zusätzlich aussortiert."""
    quelle = tmp_path / 'eingabe.csv'
    pd.DataFrame([
        {'SearchString': 'Muster Laden, Hauptstrasse 1, 5620 Musterdorf', 'PLZ': '5620',
         'Stadt': 'Musterdorf', 'KundenNr': '900201', 'title': 'Muster Laden',
         'address': 'Hauptstrasse 1, 8000 Anderswo', 'street': 'Hauptstrasse 1',
         'postalCode': '8000', 'city': 'Anderswo', 'placeId': 'PLACE_Y'},
        {'SearchString': 'Muster Laden, Hauptstrasse 1, 5620 Musterdorf', 'PLZ': '5620',
         'Stadt': 'Musterdorf', 'KundenNr': '900201', 'title': 'Muster Laden Zwei',
         'address': 'Hauptstrasse 1, 9000 Weitweg', 'street': 'Hauptstrasse 1',
         'postalCode': '9000', 'city': 'Weitweg', 'placeId': 'PLACE_Z'},
    ]).to_csv(quelle, sep=';', index=False, encoding='utf-8-sig')

    pfade = DataCleaner().clean_data(str(quelle), str(tmp_path / 'ergebnis'))
    out = {k: pd.read_csv(p, sep=';', encoding='utf-8-sig', dtype=str).fillna('')
           for k, p in pfade.items()}

    assert len(out['zur_pruefung']) == 2
    assert set(out['zur_pruefung']['qualitaet']) == {'PRUEFUNG (keine PLZ-Treffer)'}
    assert out['aussortiert'].empty
    assert out['fertig_fuer_erp'].empty


def test_leere_zeile_neben_treffer_erzeugt_keinen_zweiten_eintrag(tmp_path):
    """Ein Kunde mit einer leeren und einer gefüllten Zeile bleibt in einer Datei."""
    quelle = tmp_path / 'eingabe.csv'
    pd.DataFrame([
        {'SearchString': 'Muster Laden, Hauptstrasse 1, 5620 Musterdorf', 'PLZ': '5620',
         'Stadt': 'Musterdorf', 'KundenNr': '900301', 'title': '', 'address': '',
         'street': '', 'postalCode': '', 'city': '', 'placeId': ''},
        {'SearchString': 'Muster Laden, Hauptstrasse 1, 5620 Musterdorf', 'PLZ': '5620',
         'Stadt': 'Musterdorf', 'KundenNr': '900301', 'title': 'Muster Laden',
         'address': 'Hauptstrasse 1, 5620 Musterdorf', 'street': 'Hauptstrasse 1',
         'postalCode': '5620', 'city': 'Musterdorf', 'placeId': 'PLACE_Q'},
    ]).to_csv(quelle, sep=';', index=False, encoding='utf-8-sig')

    pfade = DataCleaner().clean_data(str(quelle), str(tmp_path / 'ergebnis'))
    out = {k: pd.read_csv(p, sep=';', encoding='utf-8-sig', dtype=str).fillna('')
           for k, p in pfade.items()}

    treffer = [name for name in HAUPTDATEIEN if '900301' in kunden_in(out[name])]
    assert treffer == ['fertig_fuer_erp']


def test_leerer_suchbegriff_geht_nach_drei(tmp_path):
    quelle = tmp_path / 'eingabe.csv'
    pd.DataFrame([
        {'SearchString': '', 'PLZ': '5620', 'Stadt': 'Musterdorf', 'KundenNr': '900401',
         'title': 'Irgendein Laden', 'address': 'Hauptstrasse 1, 5620 Musterdorf',
         'street': 'Hauptstrasse 1', 'postalCode': '5620', 'city': 'Musterdorf',
         'placeId': 'PLACE_R'},
    ]).to_csv(quelle, sep=';', index=False, encoding='utf-8-sig')

    pfade = DataCleaner().clean_data(str(quelle), str(tmp_path / 'ergebnis'))
    df = pd.read_csv(pfade['nicht_moeglich'], sep=';', encoding='utf-8-sig',
                     dtype=str).fillna('')

    assert len(df) == 1
    assert df.iloc[0]['qualitaet'] == 'NICHT_MOEGLICH (Eingabe unbrauchbar)'
    assert df.iloc[0]['grund'].strip() != ''


def test_dateien_werden_immer_geschrieben(tmp_path):
    """Auch ohne Inhalt existiert jede der vier Dateien mit Kopfzeile."""
    quelle = tmp_path / 'eingabe.csv'
    pd.DataFrame([{
        'SearchString': 'Muster Laden, Hauptstrasse 1, 5620 Musterdorf', 'PLZ': '5620',
        'Stadt': 'Musterdorf', 'KundenNr': '900501', 'title': 'Muster Laden',
        'address': 'Hauptstrasse 1, 5620 Musterdorf', 'street': 'Hauptstrasse 1',
        'postalCode': '5620', 'city': 'Musterdorf', 'placeId': 'PLACE_S',
    }]).to_csv(quelle, sep=';', index=False, encoding='utf-8-sig')

    pfade = DataCleaner().clean_data(str(quelle), str(tmp_path / 'ergebnis'))

    for pfad in pfade.values():
        assert Path(pfad).exists()
        kopf = pd.read_csv(pfad, sep=';', encoding='utf-8-sig', dtype=str)
        assert list(kopf.columns) == OUTPUT_COLUMNS
