# data_cleaner.py
# Modul zur qualitativen Bereinigung mit integrierter Qualitätsbewertung.

import pandas as pd
from thefuzz import fuzz
import re
from logger_config import logger
import config

class DataCleaner:
    def __init__(self, title_similarity_threshold=80, dynamic_gap_threshold=config.DYNAMIC_THRESHOLD_GAP):
        self.title_similarity_threshold = title_similarity_threshold
        self.dynamic_gap_threshold = dynamic_gap_threshold

    def _normalize_text(self, text: str) -> str:
        if not isinstance(text, str): return ""
        text = text.lower().replace('ä', 'ae').replace('ö', 'oe').replace('ü', 'ue').replace('ß', 'ss')
        text = re.sub(r'\bstr\.\b', 'strasse', text)
        text = text.replace('-', ' ')
        text = re.sub(r'[^\w\s]', '', text)
        return text.strip()

    def _get_street_from_searchstring(self, search_string: str) -> str:
        parts = str(search_string).split(',')
        return parts[1].strip() if len(parts) > 1 else ""

    def _has_street_in_searchstring(self, search_string: str) -> bool:
        return bool(self._get_street_from_searchstring(search_string))

    def _get_core_search_name(self, search_string: str) -> str:
        return str(search_string).split(',')[0].strip()
    
    def _calculate_scores(self, group_df):
    #Berechnet Scores für einen DataFrame und gibt ihn mit einer 'score'-Spalte zurück."""
        scores = []
        result_df = group_df.copy()
        for index, row in result_df.iterrows():
            search_string = row['SearchString']
            google_title = str(row['title'])
            
            # Titel-Score
            search_name_full = self._get_core_search_name(search_string)
            norm_search_name = self._normalize_text(search_name_full)
            norm_google_title = self._normalize_text(google_title)
            search_core = norm_search_name.split()[0] if norm_search_name else ""
            google_core = norm_google_title.split()[0] if norm_google_title else ""
            core_name_score = fuzz.ratio(search_core, google_core)
            full_title_score = fuzz.token_set_ratio(norm_search_name, norm_google_title)
            title_score = (core_name_score * 0.7) + (full_title_score * 0.3)
            scores.append(title_score)
        
        result_df['score'] = scores
        return result_df

    def clean_data(self, input_filepath: str, cleaned_ok_filepath: str, cleaned_review_filepath: str, rejected_filepath: str):
        try:
            logger.info("Starte finalen Datenbereinigungsprozess...")
            df = pd.read_csv(input_filepath, sep=';', encoding='utf-8-sig', dtype=str).fillna('')
            logger.debug(f"Die erste 5 Zeilen der Eingabedatei:\n{df.head()}")

            final_ok_results = []
            final_review_results = []
            rejected_results = []

            for kunden_nr, original_group in df.groupby('KundenNr'):
                group = original_group.copy()
                group['SearchString'] = group['SearchString'].fillna('')
                group['title'] = group['title'].fillna('')

                if len(group) == 1:
                    group.loc[:, 'qualitaet'] = 'OK'
                    final_ok_results.extend(group.to_dict('records'))
                    continue

                search_string = group.iloc[0]['SearchString']
                
                if self._has_street_in_searchstring(search_string):
                    # SZENARIO B: Strasse hat Vorrang
                    logger.debug(f"--- Szenario B für KundenNr {kunden_nr} ---")
                    street_to_find = self._get_street_from_searchstring(search_string)
                    norm_street_to_find = self._normalize_text(street_to_find)
                    
                    street_matches_mask = group['street'].apply(
                        lambda x: fuzz.partial_ratio(norm_street_to_find, self._normalize_text(str(x))) > 90 if norm_street_to_find else False
                    )
                    street_matches = group[street_matches_mask]
                    street_mismatches = group[~street_matches_mask]
                    
                    if street_matches.empty:
                        logger.warning(f"Kein Strassen-Treffer für {kunden_nr}. Markiere alle Originale zur Prüfung.")
                        group.loc[:, 'qualitaet'] = 'ZUR_PRUEFUNG'
                        final_review_results.extend(group.to_dict('records'))
                        continue
                    
                    rejected_results.extend(street_mismatches.to_dict('records'))
                    processing_group = street_matches.copy()
                else:
                    # SZENARIO A: Keine Strasse
                    logger.debug(f"--- Szenario A für KundenNr {kunden_nr} ---")
                    processing_group = group

                scored_group = self._calculate_scores(processing_group)
                high_confidence_hits = scored_group[scored_group['score'] >= self.title_similarity_threshold]
                low_confidence_hits = scored_group[scored_group['score'] < self.title_similarity_threshold]

                if not high_confidence_hits.empty:
                    high_confidence_hits = high_confidence_hits.copy()
                    high_confidence_hits.loc[:, 'qualitaet'] = 'OK'
                    final_ok_results.extend(high_confidence_hits.to_dict('records'))
                    rejected_results.extend(low_confidence_hits.to_dict('records'))
                else:
                    sorted_low_hits = low_confidence_hits.sort_values(by='score', ascending=False)
                    if len(sorted_low_hits) < 2:
                        if not sorted_low_hits.empty:
                            sorted_low_hits = sorted_low_hits.copy()
                            sorted_low_hits.loc[:, 'qualitaet'] = 'ZUR_PRUEFUNG'
                            final_review_results.extend(sorted_low_hits.to_dict('records'))
                        continue

                    score_1 = sorted_low_hits.iloc[0]['score']
                    score_2 = sorted_low_hits.iloc[1]['score']
                    
                    if score_1 > 0 and (score_1 - score_2 >= self.dynamic_gap_threshold):
                        winner = sorted_low_hits.head(1).copy()
                        winner.loc[:, 'qualitaet'] = 'OK (Dynamischer Schwellenwert)'
                        losers = sorted_low_hits.iloc[1:].copy()
                        final_ok_results.extend(winner.to_dict('records'))
                        rejected_results.extend(losers.to_dict('records'))
                    else:
                        logger.warning(f"Auswahl unklar für KundenNr {kunden_nr} (Top Score: {score_1:.0f} vs {score_2:.0f}). Markiere relevante Gruppe zur Prüfung.")
                        sorted_low_hits = sorted_low_hits.copy()
                        sorted_low_hits.loc[:, 'qualitaet'] = 'ZUR_PRUEFUNG'
                        final_review_results.extend(sorted_low_hits.to_dict('records'))

            # Schreibe die drei finalen Dateien
            all_cols = list(df.columns) + ['qualitaet']
            for filepath, data_list, name in [
                (cleaned_ok_filepath, final_ok_results, "Eindeutige"),
                (cleaned_review_filepath, final_review_results, "Zur Prüfung"),
                (rejected_filepath, rejected_results, "Aussortierte")
            ]:
                if data_list:
                    df_to_write = pd.DataFrame(data_list)
                    # Spaltenreihenfolge erzwingen
                    cols_in_order = [col for col in all_cols if col in df_to_write.columns]
                    df_to_write[cols_in_order].to_csv(filepath, sep=';', index=False, encoding='utf-8-sig')
                    logger.info(f"{name} Ergebnisse erfolgreich gespeichert: '{filepath}'")

        except Exception as e:
            logger.error(f"Ein Fehler ist während der finalen Datenbereinigung aufgetreten: {e}", exc_info=True)