# Google_maps_scraper_app/csv_processor.py

#Dieses Modul ist für alle Operationen mit CSV-Dateien verantwortlich.
import pandas as pd
from typing import List, Dict, Tuple
from logger_config import logger

class CSVProcessor:
    """
    Eine Klasse zur Verarbeitung von CSV-Dateien, die Suchanfragen enthalten.
    - Lädt eine CSV-Datei.
    - Validiert die notwendigen Spalten ('SearchString', 'PLZ').
    - Teilt die Daten in gültige und ungültige Zeilen auf.
    - Schreibt Daten in eine neue CSV-Datei.
    """

    def load_and_validate(self, filepath: str) -> Tuple[List[Dict], List[Dict]]:
        """
        Lädt eine CSV-Datei, validiert sie und gibt gültige sowie ungültige Zeilen zurück.

        Args:
            filepath (str): Der Pfad zur CSV-Datei.

        Returns:
            Tuple[List[Dict], List[Dict]]: Ein Tupel, das zwei Listen enthält:
                                           - Liste der gültigen Zeilen (als Dictionaries).
                                           - Liste der ungültigen Zeilen (als Dictionaries).
        """
        required_columns = ['SearchString', 'PLZ', 'KundenNr']
        valid_rows = []
        invalid_rows = []

        try:
            # ';' als Trennzeichen, da dies in Excel oft Standard ist in DE/CH.
            # pandas zwingen, die PLZ-Spalte als Text zu lesen, um das ".0"-Problem zu vermeiden.
            df = pd.read_csv(filepath, sep=';', encoding='utf-8-sig', dtype={'PLZ': str})

            # Überprüfen, ob die notwendigen Spalten vorhanden sind
            for col in required_columns:
                if col not in df.columns:
                    # Wenn eine Spalte fehlt, sind alle Zeilen ungültig.
                    logger.error(f"Fehler: Notwendige Spalte '{col}' nicht in der CSV-Datei gefunden.")
                    return [], df.to_dict('records')

            # Jede Zeile durchgehen und auf eine gültige PLZ prüfen
            for index, row in df.iterrows():
                # pd.isna prüft, ob der Wert fehlt (NaN) oder None ist.
                # Wir konvertieren die Zeile in ein Dictionary für die weitere Verarbeitung.
                row_dict = row.to_dict()
                if 'PLZ' in row and pd.notna(row['PLZ']) and str(row['PLZ']).strip():
                    valid_rows.append(row_dict)
                else:
                    invalid_rows.append(row_dict)

            return valid_rows, invalid_rows

        except FileNotFoundError:
            logger.error(f"Fehler: Die Datei unter '{filepath}' wurde nicht gefunden.")
            return [], []
        except Exception as e:
            logger.error(f"Ein unerwarteter Fehler ist beim Lesen der CSV aufgetreten: {e}")
            return [], []

    def write_csv(self, filepath: str, data: List[Dict]):
        """
        Schreibt eine Liste von Dictionaries in eine CSV-Datei.

        Args:
            filepath (str): Der Pfad, unter dem die neue CSV-Datei gespeichert werden soll.
            data (List[Dict]): Die Daten, die geschrieben werden sollen.
        """
        if not data:
            logger.warning(f"Hinweis: Keine Daten zum Schreiben in die Datei '{filepath}' vorhanden.")
            return

        try:
            df = pd.DataFrame(data)
            # Wir verwenden wieder ';' als Trennzeichen und 'utf-8-sig' für die Kompatibilität.
            # index=False verhindert, dass Pandas eine zusätzliche Index-Spalte schreibt.
            df.to_csv(filepath, sep=';', index=False, encoding='utf-8-sig')
            logger.info(f"Datei '{filepath}' wurde erfolgreich geschrieben.")
        except Exception as e:
            logger.info(f"Ein Fehler ist beim Schreiben der CSV-Datei '{filepath}' aufgetreten: {e}")