# data_cleaner.py
# Modul zur qualitativen Bereinigung der optimierten Ergebnis-CSV.

import pandas as pd
from thefuzz import fuzz
from logger_config import logger

class DataCleaner:
    """
    Implementiert die Logik zur Bereinigung von Mehrfachtreffern
    basierend auf einem Scoring-Modell.
    """
    def _calculate_score(self, row):
        """Berechnet den Plausibilitäts-Score für eine einzelne Zeile."""
        try:
            # Kriterium A: Titel-Ähnlichkeit (max. 100 Punkte)
            search_title = str(row.get('SearchString', '')).split(',')[0].strip()
            google_title = str(row.get('title', ''))
            title_score = fuzz.ratio(search_title.lower(), google_title.lower())

            # Kriterium B: Strassen-Bonus (max. 50 Punkte)
            search_string = str(row.get('SearchString', '')).lower()
            google_street = str(row.get('street', '')).lower()
            street_bonus = 50 if google_street and google_street in search_string else 0

            return title_score + street_bonus
        except Exception:
            return 0 # Bei Fehlern gibt es 0 Punkte

    def clean_data(self, input_filepath: str, cleaned_filepath: str, rejected_filepath: str):
        """
        Liest, bewertet und trennt die Daten.
        """
        try:
            logger.info("Starte Datenbereinigungsprozess...")
            df = pd.read_csv(input_filepath, sep=';', encoding='utf-8-sig')

            final_results = []
            rejected_results = []

            # Gruppiere den DataFrame nach der KundenNr
            for kunden_nr, group in df.groupby('KundenNr'):
                if len(group) == 1:
                    # Wenn es nur ein Ergebnis gibt, ist es automatisch das beste.
                    final_results.append(group.iloc[0].to_dict())
                    continue

                # Wenn es mehrere Ergebnisse gibt, berechne Scores
                group['score'] = group.apply(self._calculate_score, axis=1)
                
                # Finde den höchsten Score in der Gruppe
                max_score = group['score'].max()
                
                # Wähle die beste(n) Zeile(n) aus
                best_matches = group[group['score'] == max_score]
                
                # Hänge die schlechteren Ergebnisse an die "rejected"-Liste an
                other_matches = group[group['score'] < max_score]

                final_results.extend(best_matches.to_dict('records'))
                rejected_results.extend(other_matches.to_dict('records'))
            
            # Schreibe die finalen, bereinigten Daten
            if final_results:
                final_df = pd.DataFrame(final_results)
                if 'score' in final_df.columns:
                     final_df = final_df.drop(columns=['score']) # Score-Spalte entfernen
                final_df.to_csv(cleaned_filepath, sep=';', index=False, encoding='utf-8-sig')
                logger.info(f"Bereinigte Datei erfolgreich gespeichert: '{cleaned_filepath}'")
            
            # Schreibe die aussortierten Daten
            if rejected_results:
                rejected_df = pd.DataFrame(rejected_results)
                if 'score' in rejected_df.columns:
                     rejected_df = rejected_df.drop(columns=['score']) # Score-Spalte entfernen
                rejected_df.to_csv(rejected_filepath, sep=';', index=False, encoding='utf-8-sig')
                logger.info(f"Aussortierte Ergebnisse gespeichert: '{rejected_filepath}'")

        except Exception as e:
            logger.error(f"Ein Fehler ist während der Datenbereinigung aufgetreten: {e}")