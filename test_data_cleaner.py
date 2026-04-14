# test_data_cleaner.py
# Test suite for data_cleaner.py algorithm
# Purpose: Validate the cleaning logic and identify edge cases / improvements

import pandas as pd
import tempfile
import os
from pathlib import Path
from data_cleaner import DataCleaner

# ============================================================================
# TEST UTILITIES
# ============================================================================

def create_test_csv(data: list, filename: str) -> str:
    """Create a test CSV file and return its path."""
    df = pd.DataFrame(data)
    temp_dir = tempfile.gettempdir()
    filepath = os.path.join(temp_dir, filename)
    df.to_csv(filepath, sep=';', index=False, encoding='utf-8-sig')
    return filepath

def cleanup_test_files(base_path: str):
    """Remove all test output files."""
    patterns = ['_eindeutig.csv', '_zur_pruefung.csv', '_aussortiert.csv', '_erneut_crawlen.csv']
    for pattern in patterns:
        filepath = f"{base_path}{pattern}"
        if os.path.exists(filepath):
            os.remove(filepath)

# ============================================================================
# TEST CASES
# ============================================================================

class TestDataCleaner:
    """Test suite for DataCleaner algorithm."""

    def __init__(self):
        self.cleaner = DataCleaner(dynamic_gap_threshold=30)

    # ========================================================================
    # TEST 1: Empty Results (should go to erneut_crawlen.csv)
    # ========================================================================
    def test_empty_results(self):
        """Test: Empty API results are detected and saved for re-crawl."""
        print("\n" + "="*70)
        print("TEST 1: Empty Results Detection")
        print("="*70)

        data = [
            {
                'SearchString': 'Denner, Hauptstrasse 5, 5620 Bremgarten',
                'PLZ': '5620',
                'Stadt': 'Bremgarten',
                'KundenNr': 'K001',
                'title': '',           # Empty!
                'address': '',         # Empty!
                'street': '',          # Empty!
                'postalCode': '',      # Empty!
                'placeId': '',         # Empty — triggers "is_empty_result"
                'city': '',
                'phone': ''
            }
        ]

        csv_path = create_test_csv(data, 'test_empty.csv')
        base_path = csv_path.rsplit('.', 1)[0]

        try:
            results = self.cleaner.clean_data(csv_path)

            # Check: Should create erneut_crawlen.csv (not unique/review/rejected)
            assert 'erneut_crawlen' in results, "Empty results should create erneut_crawlen.csv"

            recrawl_df = pd.read_csv(results['erneut_crawlen'], sep=';', encoding='utf-8-sig')
            assert len(recrawl_df) == 1, "Should have 1 row in erneut_crawlen"
            assert recrawl_df.iloc[0]['SearchString'] == 'Denner, Hauptstrasse 5, 5620 Bremgarten'

            print("✅ PASS: Empty results correctly identified and saved for re-crawl")
        finally:
            cleanup_test_files(base_path)
            os.remove(csv_path)

    # ========================================================================
    # TEST 2: Single Result (should be automatically unique)
    # ========================================================================
    def test_single_result_automatic_match(self):
        """Test: Single result per customer = automatic unique match."""
        print("\n" + "="*70)
        print("TEST 2: Single Result = Automatic Match")
        print("="*70)

        data = [
            {
                'SearchString': 'Denner, Hauptstrasse 5, 5620 Bremgarten',
                'PLZ': '5620',
                'Stadt': 'Bremgarten',
                'KundenNr': 'K001',
                'title': 'Denner Bremgarten',
                'address': 'Hauptstrasse 5, 5620 Bremgarten',
                'street': 'Hauptstrasse 5',
                'postalCode': '5620',
                'placeId': 'ChIJ123',
                'city': 'Bremgarten',
                'phone': '0564123456'
            }
        ]

        csv_path = create_test_csv(data, 'test_single.csv')
        base_path = csv_path.rsplit('.', 1)[0]

        try:
            results = self.cleaner.clean_data(csv_path)

            # Check: Should go to eindeutig.csv
            unique_df = pd.read_csv(results['eindeutig'], sep=';', encoding='utf-8-sig')
            assert len(unique_df) == 1, "Single valid result should go to eindeutig"
            assert unique_df.iloc[0]['title'] == 'Denner Bremgarten'
            assert unique_df.iloc[0]['qualitaet'] == 'OK'

            print("✅ PASS: Single result correctly marked as unique (OK)")
        finally:
            cleanup_test_files(base_path)
            os.remove(csv_path)

    # ========================================================================
    # TEST 3: PLZ Filter (wrong postal code = rejected)
    # ========================================================================
    def test_plz_filter(self):
        """Test: Results with wrong postal code are filtered out."""
        print("\n" + "="*70)
        print("TEST 3: PLZ Filter")
        print("="*70)

        data = [
            {
                'SearchString': 'Denner, Hauptstrasse 5, 5620 Bremgarten',
                'PLZ': '5620',
                'Stadt': 'Bremgarten',
                'KundenNr': 'K001',
                'title': 'Denner Bremgarten',
                'address': 'Hauptstrasse 5, 5620 Bremgarten',
                'street': 'Hauptstrasse 5',
                'postalCode': '5620',
                'placeId': 'ChIJ123',
                'city': 'Bremgarten',
                'phone': ''
            },
            {
                'SearchString': 'Denner, Hauptstrasse 5, 5620 Bremgarten',
                'PLZ': '5620',
                'Stadt': 'Bremgarten',
                'KundenNr': 'K001',
                'title': 'Denner Zurich',
                'address': 'Bahnhofstrasse 10, 8000 Zurich',
                'street': 'Bahnhofstrasse 10',
                'postalCode': '8000',  # Wrong PLZ!
                'placeId': 'ChIJ456',
                'city': 'Zurich',
                'phone': ''
            }
        ]

        csv_path = create_test_csv(data, 'test_plz_filter.csv')
        base_path = csv_path.rsplit('.', 1)[0]

        try:
            results = self.cleaner.clean_data(csv_path)

            # Check: First result (correct PLZ) goes to unique
            unique_df = pd.read_csv(results['eindeutig'], sep=';', encoding='utf-8-sig')
            assert len(unique_df) == 1, "Should have 1 unique result"

            # Check: Second result (wrong PLZ) goes to rejected
            rejected_df = pd.read_csv(results['aussortiert'], sep=';', encoding='utf-8-sig')
            assert len(rejected_df) == 1, "Should have 1 rejected result"
            assert 'PLZ' in rejected_df.iloc[0]['qualitaet'], "Should mention PLZ in rejection reason"

            print("✅ PASS: PLZ filter correctly rejects wrong postal codes")
        finally:
            cleanup_test_files(base_path)
            os.remove(csv_path)

    # ========================================================================
    # TEST 4: Street Matching (Szenario B)
    # ========================================================================
    def test_street_matching_scenario_b(self):
        """Test: Street matching when street is in SearchString."""
        print("\n" + "="*70)
        print("TEST 4: Street Matching (Szenario B)")
        print("="*70)

        data = [
            {
                'SearchString': 'Restaurant, Seetalstrasse 60, 5703 Seon',
                'PLZ': '5703',
                'Stadt': 'Seon',
                'KundenNr': 'K001',
                'title': 'Restaurant Waldegg',
                'address': 'Seetalstrasse 60, 5703 Seon',
                'street': 'Seetalstrasse 60',
                'postalCode': '5703',
                'placeId': 'ChIJ123',
                'city': 'Seon',
                'phone': ''
            },
            {
                'SearchString': 'Restaurant, Seetalstrasse 60, 5703 Seon',
                'PLZ': '5703',
                'Stadt': 'Seon',
                'KundenNr': 'K001',
                'title': 'Restaurant Alpenrose',
                'address': 'Dorfstrasse 10, 5703 Seon',
                'street': 'Dorfstrasse 10',  # Different street!
                'postalCode': '5703',
                'placeId': 'ChIJ456',
                'city': 'Seon',
                'phone': ''
            }
        ]

        csv_path = create_test_csv(data, 'test_street_matching.csv')
        base_path = csv_path.rsplit('.', 1)[0]

        try:
            results = self.cleaner.clean_data(csv_path)

            # Check: Only Seetalstrasse match goes to unique
            unique_df = pd.read_csv(results['eindeutig'], sep=';', encoding='utf-8-sig')
            assert len(unique_df) == 1, "Should have 1 unique result (street match)"
            assert 'Waldegg' in unique_df.iloc[0]['title'], "Should match Waldegg (Seetalstrasse)"

            # Check: Dorfstrasse match goes to rejected (street mismatch)
            rejected_df = pd.read_csv(results['aussortiert'], sep=';', encoding='utf-8-sig')
            assert len(rejected_df) == 1, "Should have 1 rejected result (street mismatch)"
            assert 'Strasse' in rejected_df.iloc[0]['qualitaet'], "Should mention Strasse rejection"

            print("✅ PASS: Street matching correctly filters mismatched streets")
        finally:
            cleanup_test_files(base_path)
            os.remove(csv_path)

    # ========================================================================
    # TEST 5: Title Scoring — High Confidence (≥80)
    # ========================================================================
    def test_title_scoring_high_confidence(self):
        """Test: Title score ≥80 = unique, <80 = rejected."""
        print("\n" + "="*70)
        print("TEST 5: Title Scoring — High Confidence (≥80)")
        print("="*70)

        data = [
            {
                'SearchString': 'Coop Supermarkt, , 5620 Bremgarten',
                'PLZ': '5620',
                'Stadt': 'Bremgarten',
                'KundenNr': 'K001',
                'title': 'Coop Supermarkt Bremgarten',  # High score expected
                'address': 'Hauptstrasse 5, 5620 Bremgarten',
                'street': 'Hauptstrasse 5',
                'postalCode': '5620',
                'placeId': 'ChIJ123',
                'city': 'Bremgarten',
                'phone': ''
            },
            {
                'SearchString': 'Coop Supermarkt, , 5620 Bremgarten',
                'PLZ': '5620',
                'Stadt': 'Bremgarten',
                'KundenNr': 'K001',
                'title': 'Denner Shop',  # Low score expected
                'address': 'Dorfstrasse 10, 5620 Bremgarten',
                'street': 'Dorfstrasse 10',
                'postalCode': '5620',
                'placeId': 'ChIJ456',
                'city': 'Bremgarten',
                'phone': ''
            }
        ]

        csv_path = create_test_csv(data, 'test_scoring_high.csv')
        base_path = csv_path.rsplit('.', 1)[0]

        try:
            results = self.cleaner.clean_data(csv_path)

            # Check: First result (high score) goes to unique
            unique_df = pd.read_csv(results['eindeutig'], sep=';', encoding='utf-8-sig')
            assert len(unique_df) == 1, "Should have 1 unique result (high score)"
            assert 'Coop' in unique_df.iloc[0]['title'], "Should match Coop"

            # Check: Second result (low score) goes to rejected
            rejected_df = pd.read_csv(results['aussortiert'], sep=';', encoding='utf-8-sig')
            assert len(rejected_df) == 1, "Should have 1 rejected result (low score)"

            print("✅ PASS: Title scoring correctly identifies high-confidence matches")
        finally:
            cleanup_test_files(base_path)
            os.remove(csv_path)

    # ========================================================================
    # TEST 6: Dynamic Threshold (gap ≥30 between 1st and 2nd score)
    # ========================================================================
    def test_dynamic_threshold(self):
        """Test: No score ≥80, but gap ≥30 between 1st/2nd = unique (dynamic)."""
        print("\n" + "="*70)
        print("TEST 6: Dynamic Threshold (gap ≥30)")
        print("="*70)

        data = [
            {
                'SearchString': 'Coiffeur Baumann, , 5620 Bremgarten',
                'PLZ': '5620',
                'Stadt': 'Bremgarten',
                'KundenNr': 'K001',
                'title': 'Coiffeur Baumann',  # Score: ~75
                'address': 'Hauptstrasse 5, 5620 Bremgarten',
                'street': 'Hauptstrasse 5',
                'postalCode': '5620',
                'placeId': 'ChIJ123',
                'city': 'Bremgarten',
                'phone': ''
            },
            {
                'SearchString': 'Coiffeur Baumann, , 5620 Bremgarten',
                'PLZ': '5620',
                'Stadt': 'Bremgarten',
                'KundenNr': 'K001',
                'title': 'Coiffeur Shop',  # Score: ~40 (gap = 35)
                'address': 'Dorfstrasse 10, 5620 Bremgarten',
                'street': 'Dorfstrasse 10',
                'postalCode': '5620',
                'placeId': 'ChIJ456',
                'city': 'Bremgarten',
                'phone': ''
            }
        ]

        csv_path = create_test_csv(data, 'test_dynamic.csv')
        base_path = csv_path.rsplit('.', 1)[0]

        try:
            results = self.cleaner.clean_data(csv_path)

            # Check: First result should go to unique (dynamic threshold)
            unique_df = pd.read_csv(results['eindeutig'], sep=';', encoding='utf-8-sig')
            assert len(unique_df) >= 1, "Should have at least 1 unique result (dynamic)"

            print("✅ PASS: Dynamic threshold correctly applies gap logic")
        finally:
            cleanup_test_files(base_path)
            os.remove(csv_path)

    # ========================================================================
    # TEST 7: Multiple High Scores → Review
    # ========================================================================
    def test_multiple_high_scores_requires_review(self):
        """Test: Multiple results with score ≥80 = ambiguous → review."""
        print("\n" + "="*70)
        print("TEST 7: Multiple High Scores → Manual Review")
        print("="*70)

        data = [
            {
                'SearchString': 'Spar Supermarkt, , 5620 Bremgarten',
                'PLZ': '5620',
                'Stadt': 'Bremgarten',
                'KundenNr': 'K001',
                'title': 'Spar Supermarkt Bremgarten',
                'address': 'Hauptstrasse 5, 5620 Bremgarten',
                'street': 'Hauptstrasse 5',
                'postalCode': '5620',
                'placeId': 'ChIJ123',
                'city': 'Bremgarten',
                'phone': ''
            },
            {
                'SearchString': 'Spar Supermarkt, , 5620 Bremgarten',
                'PLZ': '5620',
                'Stadt': 'Bremgarten',
                'KundenNr': 'K001',
                'title': 'Spar Markt Bremgarten',
                'address': 'Bahnhofstrasse 3, 5620 Bremgarten',
                'street': 'Bahnhofstrasse 3',
                'postalCode': '5620',
                'placeId': 'ChIJ456',
                'city': 'Bremgarten',
                'phone': ''
            }
        ]

        csv_path = create_test_csv(data, 'test_multi_high.csv')
        base_path = csv_path.rsplit('.', 1)[0]

        try:
            results = self.cleaner.clean_data(csv_path)

            # Check: Both should go to review (ambiguous)
            review_df = pd.read_csv(results['zur_pruefung'], sep=';', encoding='utf-8-sig')
            assert len(review_df) >= 2, "Multiple high scores should go to review"
            assert 'mehrere hohe Treffer' in review_df.iloc[0]['qualitaet'] or len(review_df) > 1

            print("✅ PASS: Multiple high-score matches correctly marked for manual review")
        finally:
            cleanup_test_files(base_path)
            os.remove(csv_path)

    # ========================================================================
    # TEST 8: Umlauts & Normalization
    # ========================================================================
    def test_umlaut_normalization(self):
        """Test: Umlauts (ä, ö, ü) are correctly normalized."""
        print("\n" + "="*70)
        print("TEST 8: Umlaut Normalization")
        print("="*70)

        # Input has umlaut, Google result doesn't (normalized)
        data = [
            {
                'SearchString': 'Bäckerei Müller, Strasse 10, 5620 Bremgarten',
                'PLZ': '5620',
                'Stadt': 'Bremgarten',
                'KundenNr': 'K001',
                'title': 'Baeckerei Mueller Bremgarten',  # Normalized version
                'address': 'Strasse 10, 5620 Bremgarten',
                'street': 'Strasse 10',
                'postalCode': '5620',
                'placeId': 'ChIJ123',
                'city': 'Bremgarten',
                'phone': ''
            }
        ]

        csv_path = create_test_csv(data, 'test_umlauts.csv')
        base_path = csv_path.rsplit('.', 1)[0]

        try:
            results = self.cleaner.clean_data(csv_path)

            # Check: Should be recognized as match despite umlaut difference
            unique_df = pd.read_csv(results['eindeutig'], sep=';', encoding='utf-8-sig')
            assert len(unique_df) == 1, "Umlaut normalization should match Bäckerei with Baeckerei"

            print("✅ PASS: Umlauts correctly normalized for matching")
        finally:
            cleanup_test_files(base_path)
            os.remove(csv_path)

# ============================================================================
# RUN ALL TESTS
# ============================================================================

if __name__ == '__main__':
    print("\n" + "="*70)
    print("DATA CLEANER ALGORITHM TEST SUITE")
    print("="*70)

    tester = TestDataCleaner()

    tests = [
        tester.test_empty_results,
        tester.test_single_result_automatic_match,
        tester.test_plz_filter,
        tester.test_street_matching_scenario_b,
        tester.test_title_scoring_high_confidence,
        tester.test_dynamic_threshold,
        tester.test_multiple_high_scores_requires_review,
        tester.test_umlaut_normalization,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"❌ FAIL: {e}")
            failed += 1
        except Exception as e:
            print(f"❌ ERROR: {e}")
            failed += 1

    print("\n" + "="*70)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("="*70 + "\n")
