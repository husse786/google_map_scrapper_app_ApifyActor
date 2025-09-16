# csv_postprocessor.py
# Dieses Modul ist für die Nachbearbeitung der angereicherten CSV-Datei zuständig.

import pandas as pd
from typing import List
from logger_config import logger

class CSVPostProcessor:
    """
    Liest eine CSV-Datei, filtert sie nach einer vordefinierten Spaltenliste
    und speichert das Ergebnis in einer neuen Datei.
    """
    def process_and_filter(self, input_filepath: str, output_filepath: str, columns_to_keep: List[str]):
        """
        Liest die Eingabe-CSV, filtert die Spalten und schreibt die Ausgabe-CSV.

        Args:
            input_filepath (str): Pfad zur angereicherten Rohdaten-CSV.
            output_filepath (str): Pfad zur finalen, optimierten CSV-Datei.
            columns_to_keep (List[str]): Eine Liste der Spaltennamen, die beibehalten werden sollen.
        """
        try:
            logger.info(f"Starte Nachbearbeitung: Lese Rohdaten aus '{input_filepath}'...")
            df = pd.read_csv(input_filepath, sep=';', encoding='utf-8-sig')

            # Finde heraus, welche der gewünschten Spalten tatsächlich in der Datei existieren
            existing_columns = [col for col in columns_to_keep if col in df.columns]
            
            if not existing_columns:
                logger.error("Keine der gewünschten Spalten wurde in der Rohdaten-Datei gefunden. Breche Nachbearbeitung ab.")
                return

            logger.info(f"Filtere auf die folgenden {len(existing_columns)} Spalten: {', '.join(existing_columns)}")
            
            # Erstelle einen neuen DataFrame nur mit den existierenden, gewünschten Spalten
            filtered_df = df[existing_columns]

            # Schreibe den gefilterten DataFrame in die neue Zieldatei
            filtered_df.to_csv(output_filepath, sep=';', index=False, encoding='utf-8-sig')
            logger.info(f"Optimierte Datei erfolgreich gespeichert unter: '{output_filepath}'")

        except FileNotFoundError:
            logger.error(f"Fehler bei der Nachbearbeitung: Eingabedatei '{input_filepath}' nicht gefunden.")
        except Exception as e:
            logger.error(f"Ein unerwarteter Fehler ist bei der Nachbearbeitung aufgetreten: {e}")