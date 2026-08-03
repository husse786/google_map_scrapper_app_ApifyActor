# test_data_cleaner.py
# Test suite for data_cleaner.py algorithm.
#
# These are the eight scenarios of the original suite, kept one-to-one but
# converted to pytest and updated to the output contract of 02_DATENVERTRAG.md:
# four files with fixed names, qualitaet from the closed list, score and grund
# on every row.

import pandas as pd
import pytest

from data_cleaner import DataCleaner


# ============================================================================
# TEST UTILITIES
# ============================================================================

@pytest.fixture
def cleaner():
    return DataCleaner(dynamic_gap_threshold=30)


def run_cleaner(cleaner: DataCleaner, rows: list, tmp_path) -> dict:
    """Write rows to a CSV, run the cleaner, return the four result frames."""
    source = tmp_path / 'eingabe.csv'
    pd.DataFrame(rows).to_csv(source, sep=';', index=False, encoding='utf-8-sig')

    paths = cleaner.clean_data(str(source), str(tmp_path / 'ergebnis'))

    return {
        key: pd.read_csv(path, sep=';', encoding='utf-8-sig', dtype=str).fillna('')
        for key, path in paths.items()
    }


def kunde(**overrides) -> dict:
    """A fully populated candidate row; override what the test cares about."""
    row = {
        'SearchString': 'Denner, Hauptstrasse 5, 5620 Bremgarten',
        'PLZ': '5620',
        'Stadt': 'Bremgarten',
        'KundenNr': 'K001',
        'title': 'Denner Bremgarten',
        'address': 'Hauptstrasse 5, 5620 Bremgarten',
        'street': 'Hauptstrasse 5',
        'postalCode': '5620',
        'city': 'Bremgarten',
        'placeId': 'PLACE_1',
        'phone': '',
    }
    row.update(overrides)
    return row


# ============================================================================
# TEST 1: Empty results
# ============================================================================

def test_empty_results(cleaner, tmp_path):
    """A customer without any API result belongs in file 3, nowhere else."""
    rows = [kunde(title='', address='', street='', postalCode='', city='', placeId='')]

    out = run_cleaner(cleaner, rows, tmp_path)

    assert len(out['nicht_moeglich']) == 1
    assert out['nicht_moeglich'].iloc[0]['qualitaet'] == 'NICHT_MOEGLICH (kein Ergebnis)'
    assert out['nicht_moeglich'].iloc[0]['SearchString'] == \
        'Denner, Hauptstrasse 5, 5620 Bremgarten'
    assert out['fertig_fuer_erp'].empty
    assert out['zur_pruefung'].empty


# ============================================================================
# TEST 2: Single result
# ============================================================================

def test_single_result_automatic_match(cleaner, tmp_path):
    """One surviving candidate with a matching name goes to file 1."""
    rows = [kunde()]

    out = run_cleaner(cleaner, rows, tmp_path)

    assert len(out['fertig_fuer_erp']) == 1
    hit = out['fertig_fuer_erp'].iloc[0]
    assert hit['title'] == 'Denner Bremgarten'
    assert hit['qualitaet'] == 'OK (Einzeltreffer)'
    assert float(hit['score']) >= 60


# ============================================================================
# TEST 3: PLZ filter
# ============================================================================

def test_plz_filter(cleaner, tmp_path):
    """A candidate from the wrong postal code is dropped, not decided upon."""
    rows = [
        kunde(),
        kunde(title='Denner Zurich', address='Bahnhofstrasse 10, 8000 Zurich',
              street='Bahnhofstrasse 10', postalCode='8000', city='Zurich',
              placeId='PLACE_2'),
    ]

    out = run_cleaner(cleaner, rows, tmp_path)

    assert len(out['fertig_fuer_erp']) == 1
    assert len(out['aussortiert']) == 1
    assert out['aussortiert'].iloc[0]['qualitaet'] == 'AUSSORTIERT (PLZ)'
    assert '8000' in out['aussortiert'].iloc[0]['grund']


# ============================================================================
# TEST 4: Street matching (Szenario B)
# ============================================================================

def test_street_matching_scenario_b(cleaner, tmp_path):
    """With a street in the search string, only candidates on it survive."""
    rows = [
        kunde(SearchString='Restaurant, Seetalstrasse 60, 5703 Seon', PLZ='5703',
              Stadt='Seon', title='Restaurant Waldegg',
              address='Seetalstrasse 60, 5703 Seon', street='Seetalstrasse 60',
              postalCode='5703', city='Seon'),
        kunde(SearchString='Restaurant, Seetalstrasse 60, 5703 Seon', PLZ='5703',
              Stadt='Seon', title='Restaurant Alpenrose',
              address='Dorfstrasse 10, 5703 Seon', street='Dorfstrasse 10',
              postalCode='5703', city='Seon', placeId='PLACE_2'),
    ]

    out = run_cleaner(cleaner, rows, tmp_path)

    assert len(out['fertig_fuer_erp']) == 1
    assert out['fertig_fuer_erp'].iloc[0]['title'] == 'Restaurant Waldegg'
    assert out['fertig_fuer_erp'].iloc[0]['qualitaet'] == 'OK (Strasse)'
    assert len(out['aussortiert']) == 1
    assert out['aussortiert'].iloc[0]['qualitaet'] == 'AUSSORTIERT (Strasse)'


# ============================================================================
# TEST 5: Title scoring, exactly one hit above 80
# ============================================================================

def test_title_scoring_high_confidence(cleaner, tmp_path):
    """Without a street, one hit above 80 and one below is decided by score."""
    rows = [
        kunde(SearchString='Coop Supermarkt, , 5620 Bremgarten',
              title='Coop Supermarkt Bremgarten'),
        kunde(SearchString='Coop Supermarkt, , 5620 Bremgarten', title='Denner Shop',
              address='Dorfstrasse 10, 5620 Bremgarten', street='Dorfstrasse 10',
              placeId='PLACE_2'),
    ]

    out = run_cleaner(cleaner, rows, tmp_path)

    assert len(out['fertig_fuer_erp']) == 1
    hit = out['fertig_fuer_erp'].iloc[0]
    assert 'Coop' in hit['title']
    assert hit['qualitaet'] == 'OK (Score)'
    assert float(hit['score']) >= 80

    assert len(out['aussortiert']) == 1
    assert out['aussortiert'].iloc[0]['qualitaet'] == 'AUSSORTIERT (Score)'


# ============================================================================
# TEST 6: Dynamic threshold, gap of 30 between first and second
# ============================================================================

def test_dynamic_threshold(cleaner, tmp_path):
    """No hit reaches 80, but the leader is 30 points ahead: file 1.

    The original data of this test ("Coiffeur Baumann" / "Coiffeur Shop")
    scored 100 and 83 and therefore never reached the dynamic branch. The
    titles below score 80 and 26.
    """
    rows = [
        kunde(SearchString='Kiosk Alpenblick, , 5620 Bremgarten', title='Kiosk Alpenrose'),
        kunde(SearchString='Kiosk Alpenblick, , 5620 Bremgarten', title='Blumen Ecke',
              address='Dorfstrasse 10, 5620 Bremgarten', street='Dorfstrasse 10',
              placeId='PLACE_2'),
    ]

    out = run_cleaner(cleaner, rows, tmp_path)

    assert len(out['fertig_fuer_erp']) == 1
    hit = out['fertig_fuer_erp'].iloc[0]
    assert hit['title'] == 'Kiosk Alpenrose'
    assert hit['qualitaet'] == 'OK (Dynamisch)'
    assert float(hit['score']) < 80

    assert len(out['aussortiert']) == 1
    assert out['aussortiert'].iloc[0]['qualitaet'] == 'AUSSORTIERT (Dynamisch)'


# ============================================================================
# TEST 7: Several hits above 80
# ============================================================================

def test_multiple_high_scores_requires_review(cleaner, tmp_path):
    """Two equally good hits cannot be decided automatically."""
    rows = [
        kunde(SearchString='Spar Supermarkt, , 5620 Bremgarten',
              title='Spar Supermarkt Bremgarten'),
        kunde(SearchString='Spar Supermarkt, , 5620 Bremgarten',
              title='Spar Markt Bremgarten', address='Bahnhofstrasse 3, 5620 Bremgarten',
              street='Bahnhofstrasse 3', placeId='PLACE_2'),
    ]

    out = run_cleaner(cleaner, rows, tmp_path)

    assert len(out['zur_pruefung']) == 2
    assert set(out['zur_pruefung']['qualitaet']) == {'PRUEFUNG (mehrere hohe Treffer)'}
    assert out['fertig_fuer_erp'].empty


# ============================================================================
# TEST 8: Umlauts and normalisation
# ============================================================================

def test_umlaut_normalization(cleaner, tmp_path):
    """Baeckerei and Bäckerei are the same name."""
    rows = [
        kunde(SearchString='Bäckerei Müller, Strasse 10, 5620 Bremgarten',
              title='Baeckerei Mueller Bremgarten',
              address='Strasse 10, 5620 Bremgarten', street='Strasse 10'),
    ]

    out = run_cleaner(cleaner, rows, tmp_path)

    assert len(out['fertig_fuer_erp']) == 1
    assert float(out['fertig_fuer_erp'].iloc[0]['score']) >= 60
