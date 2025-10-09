# data_cleaner.py
# Modul zur qualitativen Bereinigung der optimierten Ergebnis-CSV.

import pandas as pd
from thefuzz import fuzz
import re
from logger_config import logger

class DataCleaner:
    def __init__(self, title_similarity_threshold=80): # Angepasster Schwellenwert
        self.title_similarity_threshold = title_similarity_threshold

    def _normalize_text(self, text: str) -> str:
        if not isinstance(text, str): return ""
        text = text.lower()
        text = text.replace('ä', 'ae').replace('ö', 'oe').replace('ü', 'ue').replace('ß', 'ss')
        text = re.sub(r'\bstr\.\b', 'strasse', text)
        text = re.sub(r'\bpl\.\b', 'platz', text)
        text = text.replace('-', ' ')
        text = re.sub(r'[^\w\s]', '', text)
        return text.strip()

    def _get_street_from_searchstring(self, search_string: str) -> str:
        parts = search_string.split(',')
        if len(parts) > 1: return parts[1].strip()
        return ""

    def _has_street_in_searchstring(self, search_string: str) -> bool:
        return bool(self._get_street_from_searchstring(search_string))

    def _get_core_search_name(self, search_string: str) -> str:
        return search_string.split(',')[0].strip()

    def _calculate_score(self, row):
        try:
            full_search_string = row.get('SearchString', '')
            search_name_full = self._get_core_search_name(full_search_string)
            google_title_full = str(row.get('title', ''))

            norm_search_name_full = self._normalize_text(search_name_full)
            norm_google_title_full = self._normalize_text(google_title_full)

            search_core = norm_search_name_full.split()[0] if norm_search_name_full else ""
            google_core = norm_google_title_full.split()[0] if norm_google_title_full else ""

            core_name_score = fuzz.ratio(search_core, google_core)
            full_title_score = fuzz.token_set_ratio(norm_search_name_full, norm_google_title_full)
            title_score = (core_name_score * 0.7) + (full_title_score * 0.3)

            street_bonus = 0
            if self._has_street_in_searchstring(full_search_string):
                street_to_find = self._get_street_from_searchstring(full_search_string)
                norm_street_to_find = self._normalize_text(street_to_find)
                google_street = str(row.get('street', ''))
                norm_google_street = self._normalize_text(google_street)
                if norm_street_to_find and fuzz.partial_ratio(norm_street_to_find, norm_google_street) > 90:
                    street_bonus = 50

            total_score = title_score + street_bonus
            logger.debug(f"  -> Scoring für '{google_title_full}': TitleScore({title_score:.0f}) + StreetBonus({street_bonus}) -> TOTAL: {total_score:.0f}")
            return total_score
        except Exception: return 0

    def _run_scenario_a(self, group):
        logger.debug(f"--- Szenario A (Keine Strasse) für KundenNr {group.iloc[0]['KundenNr']} ---")
        plausible_rows = []
        rejected_rows = []
        for index, row in group.iterrows():
            score = self._calculate_score(row)
            if score >= self.title_similarity_threshold:
                plausible_rows.append(row.to_dict())
            else:
                rejected_rows.append(row.to_dict())
        
        if not plausible_rows:
            logger.warning(f"Für KundenNr {group.iloc[0]['KundenNr']} wurden keine plausiblen Titel gefunden. Behalte alle {len(group)} Ergebnisse.")
            return group.to_dict('records'), []
        else:
            return plausible_rows, rejected_rows

    def _run_scenario_b(self, group):
        logger.debug(f"--- Szenario B (Mit Strasse) für KundenNr {group.iloc[0]['KundenNr']} ---")
        search_string = group.iloc[0]['SearchString']
        street_to_find = self._get_street_from_searchstring(search_string)
        normalized_street_to_find = self._normalize_text(street_to_find)
        logger.debug(f"Filtere zuerst nach Strasse: '{street_to_find}'")

        street_matches = []
        street_mismatches = []
        for index, row in group.iterrows():
            google_street = str(row.get('street', ''))
            normalized_google_street = self._normalize_text(google_street)
            if normalized_street_to_find and fuzz.partial_ratio(normalized_street_to_find, normalized_google_street) > 90:
                street_matches.append(row)
            else:
                street_mismatches.append(row.to_dict())
        
        logger.debug(f"{len(street_matches)} Treffer nach Strassen-Filter gefunden.")

        if not street_matches:
            logger.warning(f"Kein Strassen-Treffer gefunden. Fallback: Behalte alle Originale.")
            return group.to_dict('records'), []

        street_matches_df = pd.DataFrame(street_matches)
        
        if len(street_matches_df) == 1:
            logger.debug("Nur ein Strassen-Treffer gefunden. Übernehme diesen.")
            return street_matches_df.to_dict('records'), street_mismatches

        logger.debug("Mehrere Strassen-Treffer gefunden. Führe Titel-Filter als Tie-Breaker aus.")
        plausible_results, rejected_from_title_filter = self._run_scenario_a(street_matches_df)

        if plausible_results:
            all_rejected = street_mismatches + rejected_from_title_filter
            return plausible_results, all_rejected
        else: # Fallback
            logger.warning(f"Kein Titel passte nach Strassen-Filter. Fallback: Behalte alle Strassen-Treffer.")
            return street_matches_df.to_dict('records'), street_mismatches

    def clean_data(self, input_filepath: str, cleaned_filepath: str, rejected_filepath: str):
        try:
            logger.info("Starte finalen Datenbereinigungsprozess...")
            df = pd.read_csv(input_filepath, sep=';', encoding='utf-8-sig', dtype={'KundenNr': 'string'})

            final_results = []
            rejected_results = []

            for kunden_nr, group in df.groupby('KundenNr'):
                group = group.copy()
                group['SearchString'] = group['SearchString'].fillna('')
                group['title'] = group['title'].fillna('')

                if len(group) == 1:
                    final_results.extend(group.to_dict('records'))
                    continue

                search_string = group.iloc[0]['SearchString']
                if self._has_street_in_searchstring(search_string):
                    good_rows, bad_rows = self._run_scenario_b(group)
                else:
                    good_rows, bad_rows = self._run_scenario_a(group)
                
                final_results.extend(good_rows)
                rejected_results.extend(bad_rows)

            if final_results:
                final_df = pd.DataFrame(final_results).drop_duplicates()
                if 'score' in final_df.columns: final_df = final_df.drop(columns=['score'])
                final_df.to_csv(cleaned_filepath, sep=';', index=False, encoding='utf-8-sig')
                logger.info(f"Finale bereinigte Datei erfolgreich gespeichert: '{cleaned_filepath}'")
            
            if rejected_results:
                rejected_df = pd.DataFrame(rejected_results).drop_duplicates()
                if 'score' in rejected_df.columns: rejected_df = rejected_df.drop(columns=['score'])
                rejected_df.to_csv(rejected_filepath, sep=';', index=False, encoding='utf-8-sig')
                logger.info(f"Aussortierte Ergebnisse gespeichert: '{rejected_filepath}'")

        except Exception as e:
            logger.error(f"Ein Fehler ist während der finalen Datenbereinigung aufgetreten: {e}", exc_info=True)