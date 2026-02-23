# data_cleaner.py
# Modul zur qualitativen Bereinigung mit integrierter Qualitätsbewertung.

import pandas as pd
from thefuzz import fuzz
import logging
import re

logger = logging.getLogger(__name__)

class DataCleaner:
    """Bereinigt und dedupliziert die angereicherten Google Maps Daten."""

    # --- FIX A: Generic category words that carry no brand info ---
    GENERIC_FIRST_WORDS = {
        'restaurant', 'metzgerei', 'kiosk', 'hotel', 'cafe', 'bäckerei', 'baeckerei',
        'gasthof', 'gasthaus', 'berggasthaus', 'pension', 'bar', 'bistro', 'pizzeria',
        'garage', 'apotheke', 'drogerie', 'coiffeur', 'salon', 'praxis', 'laden',
        'shop', 'markt', 'zentrum', 'haus', 'stiftung', 'verein', 'genossenschaft',
        'tankstelle', 'station', 'post', 'filiale', 'freibad', 'badi', 'hallenbad',
        'schwimmbad', 'camping', 'sportanlage', 'turnhalle'
    }
    # REMOVED from generic: 'volg', 'landi' — these are Swiss retail BRANDS

    # --- FIX C: Legal suffixes to strip before scoring ---
    LEGAL_SUFFIXES = r'\b(ag|gmbh|kg|sa|sarl|sàrl|inc|ltd|co|ohg|eg|se|mbh|lkg)\b'
    # ADDED: 'lkg' (Lebensmittel-Konsumgenossenschaft)

    def __init__(self, dynamic_gap_threshold=30):
        self.dynamic_gap_threshold = dynamic_gap_threshold

    def _normalize_text(self, text: str) -> str:
        """Normalisiert Text für den Vergleich (Kleinschreibung, Umlaute, etc.)."""
        if not text:
            return ''
        text = str(text).lower().strip()
        # Umlaute ersetzen
        text = text.replace('ä', 'ae').replace('ö', 'oe').replace('ü', 'ue')
        text = text.replace('é', 'e').replace('è', 'e').replace('ê', 'e')
        text = text.replace('à', 'a').replace('â', 'a')
        # Abkürzungen normalisieren
        text = text.replace('str.', 'strasse').replace('str ', 'strasse ')
        text = text.replace('g.', 'gasse')  # NEW: handle "g." abbreviation
        # Bindestriche und Sonderzeichen
        text = text.replace('-', ' ').replace('/', ' ')
        # Mehrfache Leerzeichen entfernen
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def _strip_legal_suffixes(self, text: str) -> str:
        """FIX C: Entfernt Rechtsform-Suffixe (AG, GmbH, KG, etc.) aus dem Text."""
        cleaned = re.sub(self.LEGAL_SUFFIXES, '', text)
        return re.sub(r'\s+', ' ', cleaned).strip()

    def _get_scoring_weights(self, first_word: str) -> tuple:
        """FIX A: Returns (first_word_weight, full_title_weight) based on whether 
        the first word is a generic category."""
        if first_word in self.GENERIC_FIRST_WORDS:
            # Generic word = flip the weights, rely on full title instead
            return (0.30, 0.70)
        else:
            # Brand name first = original weights
            return (0.70, 0.30)

    def _calculate_scores(self, group: pd.DataFrame) -> pd.DataFrame:
        """Berechnet den gewichteten Ähnlichkeitsscore für jede Zeile in der Gruppe."""
        if group.empty:
            return group

        search_name = group.iloc[0].get('SearchString', '')
        # Extract the name part (before the first comma)
        search_name_part = search_name.split(',')[0].strip() if search_name else ''
        norm_search_name = self._normalize_text(search_name_part)

        # FIX C: Strip legal suffixes from search name
        norm_search_name = self._strip_legal_suffixes(norm_search_name)

        # FIX A: Determine weights based on whether first word is generic
        search_words = norm_search_name.split()
        search_first_word = search_words[0] if search_words else ''
        first_word_weight, full_title_weight = self._get_scoring_weights(search_first_word)

        logger.debug(f"Scoring '{search_name_part}' | first_word='{search_first_word}' | "
                     f"weights=({first_word_weight:.0%}/{full_title_weight:.0%}) | "
                     f"generic={'YES' if first_word_weight == 0.30 else 'NO'}")

        scores = []
        for _, row in group.iterrows():
            google_title = str(row.get('title', ''))
            norm_google_title = self._normalize_text(google_title)

            # FIX C: Strip legal suffixes from google title too
            norm_google_title = self._strip_legal_suffixes(norm_google_title)

            google_words = norm_google_title.split()
            google_first_word = google_words[0] if google_words else ''

            # Core comparison: first word vs first word
            if search_first_word and google_first_word:
                core_score = fuzz.ratio(search_first_word, google_first_word)
            else:
                core_score = 0

            # Full title comparison
            full_score = fuzz.token_set_ratio(norm_search_name, norm_google_title)

            # FIX A: Apply dynamic weights
            weighted_score = (first_word_weight * core_score) + (full_title_weight * full_score)

            logger.debug(f"  vs '{google_title}' | core={core_score} full={full_score} "
                         f"weighted={weighted_score:.1f}")

            scores.append(round(weighted_score, 2))

        group = group.copy()
        group['score'] = scores
        return group

    def _has_street_in_searchstring(self, search_string: str) -> str:
        """Prüft, ob im SearchString eine Straße enthalten ist (2. Komma-Teil)."""
        parts = search_string.split(',')
        if len(parts) >= 2:
            street_part = parts[1].strip()
            # Check it's not just a number or empty
            if street_part and not street_part.isdigit():
                return street_part
        return ''

    def _plz_matches(self, row: pd.Series, input_plz: str) -> bool:
        """FIX B: Prüft ob die PLZ aus dem Google-Ergebnis mit der Input-PLZ übereinstimmt."""
        google_plz = str(row.get('postalCode', '')).strip()
        input_plz_clean = str(input_plz).strip()
        if not google_plz or not input_plz_clean:
            return True  # If either is missing, don't filter out
        return google_plz == input_plz_clean

    def clean_data(self, input_filepath: str) -> dict:
        """
        Hauptmethode zur Bereinigung der Daten.
        Gibt ein Dict mit den Dateipfaden der Ergebnisdateien zurück.
        """
        logger.info(f"Starte Bereinigung der Datei: {input_filepath}")
        df = pd.read_csv(input_filepath, sep=';', encoding='utf-8-sig', dtype=str).fillna('')

        if 'KundenNr' not in df.columns:
            raise ValueError("Die Spalte 'KundenNr' wurde nicht gefunden.")

        unique_results = []    # -> _eindeutig.csv
        review_results = []    # -> _zur_pruefung.csv
        rejected_results = []  # -> _aussortiert.csv

        grouped = df.groupby('KundenNr')
        total_groups = len(grouped)
        logger.info(f"Verarbeite {total_groups} Kundengruppen...")

        for kunden_nr, group in grouped:
            search_string = group.iloc[0].get('SearchString', '')
            input_plz = str(group.iloc[0].get('PLZ', '')).strip()

            # --- FIX B: PLZ pre-filter ---
            plz_mask = group.apply(lambda row: self._plz_matches(row, input_plz), axis=1)
            plz_matches = group[plz_mask]
            plz_mismatches = group[~plz_mask]

            if not plz_mismatches.empty:
                logger.debug(f"KundenNr {kunden_nr}: {len(plz_mismatches)} Ergebnisse "
                             f"mit falscher PLZ aussortiert")
                for _, row in plz_mismatches.iterrows():
                    row_dict = row.to_dict()
                    row_dict['qualitaet'] = 'AUSSORTIERT (PLZ)'
                    rejected_results.append(row_dict)

            # If PLZ filter removed everything, send all to review
            if plz_matches.empty:
                logger.info(f"KundenNr {kunden_nr}: Keine PLZ-Treffer, zur Prüfung.")
                for _, row in group.iterrows():
                    row_dict = row.to_dict()
                    row_dict['qualitaet'] = 'ZUR_PRUEFUNG (keine PLZ-Treffer)'
                    review_results.append(row_dict)
                continue

            group = plz_matches  # Continue with PLZ-filtered results

            # --- Nur 1 Ergebnis → Eindeutig ---
            if len(group) == 1:
                row_dict = group.iloc[0].to_dict()
                row_dict['qualitaet'] = 'OK'
                unique_results.append(row_dict)
                continue

            # --- Die "Weiche": Hat der SearchString eine Strasse? ---
            street_to_find = self._has_street_in_searchstring(search_string)

            processing_group = group  # Default: alle Ergebnisse werden gescored

            if street_to_find:
                # ---- SZENARIO B: Strasse vorhanden ----
                norm_street_to_find = self._normalize_text(street_to_find)
                logger.debug(f"KundenNr {kunden_nr}: Szenario B (Strasse: '{street_to_find}')")

                street_matches_mask = group['street'].apply(
                    lambda x: fuzz.partial_ratio(
                        norm_street_to_find, self._normalize_text(str(x))
                    ) > 90 if norm_street_to_find else False
                )
                street_matches = group[street_matches_mask]
                street_mismatches = group[~street_matches_mask]

                # Strassen-Fehlschläge aussortieren
                if not street_mismatches.empty:
                    for _, row in street_mismatches.iterrows():
                        row_dict = row.to_dict()
                        row_dict['qualitaet'] = 'AUSSORTIERT (Strasse)'
                        rejected_results.append(row_dict)

                if len(street_matches) == 0:
                    # Keine Strassentreffer → alle zur Prüfung
                    logger.info(f"KundenNr {kunden_nr}: Keine Strassentreffer, zur Prüfung.")
                    for _, row in group.iterrows():
                        row_dict = row.to_dict()
                        row_dict['qualitaet'] = 'ZUR_PRUEFUNG (keine Strassentreffer)'
                        review_results.append(row_dict)
                    continue
                elif len(street_matches) == 1:
                    row_dict = street_matches.iloc[0].to_dict()
                    row_dict['qualitaet'] = 'OK (Strasse)'
                    unique_results.append(row_dict)
                    continue
                else:
                    processing_group = street_matches
            else:
                logger.debug(f"KundenNr {kunden_nr}: Szenario A (keine Strasse)")

            # --- TITLE SCORING (both scenarios end up here) ---
            scored_group = self._calculate_scores(processing_group)

            # --- Fester Schwellenwert: Score >= 80 ---
            high_confidence_hits = scored_group[scored_group['score'] >= 80]
            low_confidence_hits = scored_group[scored_group['score'] < 80]

            if not high_confidence_hits.empty:
                for _, row in high_confidence_hits.iterrows():
                    row_dict = row.to_dict()
                    row_dict['qualitaet'] = 'OK (Score)'
                    unique_results.append(row_dict)
                for _, row in low_confidence_hits.iterrows():
                    row_dict = row.to_dict()
                    row_dict['qualitaet'] = 'AUSSORTIERT (Score)'
                    rejected_results.append(row_dict)
            else:
                # --- Dynamischer Schwellenwert ---
                sorted_low_hits = low_confidence_hits.sort_values('score', ascending=False)

                if len(sorted_low_hits) >= 2:
                    score_1 = sorted_low_hits.iloc[0]['score']
                    score_2 = sorted_low_hits.iloc[1]['score']

                    if float(score_1) - float(score_2) >= self.dynamic_gap_threshold:
                        best_hit = sorted_low_hits.iloc[0].to_dict()
                        best_hit['qualitaet'] = 'OK (Dynamisch)'
                        unique_results.append(best_hit)

                        for _, row in sorted_low_hits.iloc[1:].iterrows():
                            row_dict = row.to_dict()
                            row_dict['qualitaet'] = 'AUSSORTIERT (Dynamisch)'
                            rejected_results.append(row_dict)

                        logger.info(f"KundenNr {kunden_nr}: Dynamischer Treffer "
                                    f"(Score {score_1:.0f} vs {score_2:.0f})")
                    else:
                        # Gap zu klein → alle zur Prüfung
                        for _, row in sorted_low_hits.iterrows():
                            row_dict = row.to_dict()
                            row_dict['qualitaet'] = 'ZUR_PRUEFUNG (kein klarer Treffer)'
                            review_results.append(row_dict)
                else:
                    # Nur 1 Ergebnis mit niedrigem Score → zur Prüfung
                    for _, row in sorted_low_hits.iterrows():
                        row_dict = row.to_dict()
                        row_dict['qualitaet'] = 'ZUR_PRUEFUNG (niedriger Score)'
                        review_results.append(row_dict)

        # --- Ergebnisse speichern ---
        base_path = input_filepath.rsplit('.', 1)[0]

        results = {}
        for name, data in [('eindeutig', unique_results),
                           ('zur_pruefung', review_results),
                           ('aussortiert', rejected_results)]:
            filepath = f"{base_path}_{name}.csv"
            out_df = pd.DataFrame(data)

            # Drop internal score column from final output
            if 'score' in out_df.columns:
                out_df = out_df.drop(columns=['score'])

            out_df.to_csv(filepath, sep=';', index=False, encoding='utf-8-sig')
            results[name] = filepath
            logger.info(f"{name}: {len(data)} Einträge → {filepath}")

        return results