# main.py
# Main App. Verbindet UI, CSV-Verarbeitung und den API-Client.
#
# Ablauf:
#   Schritt 0: Vorverarbeitung  → prüft Vollständigkeit der Input-Daten
#   Schritt 1: Anreichern       → sendet vollständige Daten an Google Maps API
#   Schritt 2: Bereinigen       → wertet API-Ergebnisse qualitativ aus

import tkinter as tk
from tkinter import filedialog
from pathlib import Path
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import config
from ui_manager import AppUI
from csv_processor import CSVProcessor
from apify_wrapper import ApifyClientWrapper
from csv_postprocessor import CSVPostProcessor
from data_cleaner import DataCleaner
from data_preprocessor import DataPreprocessor
from data_consolidator import DataConsolidator

logger = logging.getLogger(__name__)

# Spalten, die in der optimierten Ausgabedatei behalten werden
COLUMNS_TO_KEEP = [
    'SearchString', 'PLZ', 'Stadt', 'KundenNr',
    'title', 'address', 'street', 'postalCode', 'city',
    'openingHours', 'phone', 'phoneUnformatted', 'website',
    'permanentlyClosed', 'temporarilyClosed', 'cid', 'placeId', 'location'
]


class TextHandler(logging.Handler):
    """Logging-Handler, der Nachrichten ins Tkinter-ScrolledText-Widget schreibt."""
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget

    def emit(self, record):
        msg = self.format(record)
        self.text_widget.after(0, self._append, msg)

    def _append(self, msg):
        self.text_widget.config(state='normal')
        self.text_widget.insert(tk.END, msg + '\n')
        self.text_widget.see(tk.END)
        self.text_widget.config(state='disabled')


class GoogleMapsScraper:
    """Hauptklasse: Verbindet UI mit der Geschäftslogik."""

    def __init__(self, root):
        self.ui = AppUI(root)

        # Logging ins UI-Fenster umleiten
        text_handler = TextHandler(self.ui.log_display)
        text_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s',
                                                     datefmt='%Y-%m-%d %H:%M:%S'))
        logging.getLogger().addHandler(text_handler)
        logging.getLogger().setLevel(logging.INFO)

        # Module initialisieren
        self.csv_processor = CSVProcessor()
        self.api_client = ApifyClientWrapper(config.APIFY_API_TOKEN, config.ACTOR_ID)
        self.post_processor = CSVPostProcessor()
        self.cleaner = DataCleaner()
        self.preprocessor = DataPreprocessor()
        self.consolidator = DataConsolidator()

        # Buttons mit Funktionen verknüpfen
        self.ui.preprocess_button.config(command=self.start_preprocessing)
        self.ui.upload_button.config(command=self.start_enrichment)
        self.ui.clean_button.config(command=self.start_cleaning)
        self.ui.consolidate_button.config(command=self.start_consolidation)

    # ==========================================================================
    # Buttons deaktivieren/aktivieren
    # ==========================================================================

    def _disable_all_buttons(self):
        self.ui.preprocess_button.config(state=tk.DISABLED)
        self.ui.upload_button.config(state=tk.DISABLED)
        self.ui.clean_button.config(state=tk.DISABLED)
        self.ui.consolidate_button.config(state=tk.DISABLED)

    def _enable_all_buttons(self):
        self.ui.preprocess_button.config(state=tk.NORMAL)
        self.ui.upload_button.config(state=tk.NORMAL)
        self.ui.clean_button.config(state=tk.NORMAL)
        self.ui.consolidate_button.config(state=tk.NORMAL)

    # ==========================================================================
    # SCHRITT 0: Vorverarbeitung
    # ==========================================================================

    def start_preprocessing(self):
        filepath = filedialog.askopenfilename(
            title="Input-Datei für Vorverarbeitung auswählen",
            filetypes=[("CSV Dateien", "*.csv")],
            initialdir="./Daten"
        )
        if filepath:
            thread = threading.Thread(target=self.process_preprocessing, args=(filepath,))
            thread.daemon = True
            thread.start()

    def process_preprocessing(self, filepath: str):
        try:
            self._disable_all_buttons()
            self.ui.set_status(f"Vorverarbeitung: {Path(filepath).name}...")

            logger.info("================================")
            logger.info(f"Starte Vorverarbeitung für: {Path(filepath).name}")

            results = self.preprocessor.preprocess(str(filepath))

            stats = results['stats']
            logger.info("================================")
            logger.info("Vorverarbeitung abgeschlossen!")
            logger.info(f"  Total:          {stats['total']} Kunden")
            logger.info(f"  Vollständig:    {stats['complete']} → {Path(results['vollstaendig']).name}")
            logger.info(f"  Unvollständig:  {stats['incomplete']} → {Path(results['unvollstaendig']).name}")
            logger.info("================================")

            if stats['incomplete'] > 0:
                logger.info(f"⚠️  {stats['incomplete']} Kunden haben unvollständige Daten.")
                logger.info("   Bitte die Datei '_unvollstaendig.csv' manuell korrigieren.")
            logger.info("Nächster Schritt: Die '_vollstaendig.csv' Datei in Schritt 1 (Anreichern) verwenden.")

        except Exception as e:
            logger.critical(f"Fehler bei der Vorverarbeitung: {e}")
        finally:
            self.ui.set_status("Bereit.")
            self._enable_all_buttons()

    # ==========================================================================
    # SCHRITT 1: Anreichern (Google Maps API)
    # ==========================================================================

    def start_enrichment(self):
        filepath = filedialog.askopenfilename(
            title="CSV-Datei zum Anreichern auswählen",
            filetypes=[("CSV Dateien", "*.csv")],
            initialdir="./Daten"
        )
        if filepath:
            thread = threading.Thread(target=self.process_enrichment, args=(filepath,))
            thread.daemon = True
            thread.start()

    def process_enrichment(self, filepath: str):
        """
        Führt die Anreicherung über die Google Maps API im Hintergrund aus.

        Ablauf:
        1. CSV laden und validieren              → CSVProcessor.load_and_validate()
        2. Pro gültige Zeile die API abfragen    → ApifyClientWrapper.run_scraper_and_get_results()
        3. Input + API-Ergebnisse kombinieren und als Rohdaten speichern → CSVProcessor.write_csv()
        4. Spalten filtern → optimierte Datei    → CSVPostProcessor.process_and_filter()
        """
        try:
            self._disable_all_buttons()
            self.ui.set_status(f"Anreichern: {Path(filepath).name}...")

            logger.info("================================")
            logger.info(f"Starte Anreicherung für: {Path(filepath).name}")

            # Schritt 1: CSV laden und validieren
            valid_rows, invalid_rows = self.csv_processor.load_and_validate(str(filepath))

            if invalid_rows:
                logger.warning(f"{len(invalid_rows)} ungültige Zeilen übersprungen.")
            if not valid_rows:
                logger.error("Keine gültigen Zeilen gefunden. Abbruch.")
                return

            logger.info(f"{len(valid_rows)} gültige Suchbegriffe gefunden.")

            # Schritt 2: Pro Zeile die API abfragen (parallel mit 2 Workern)
            all_combined_rows = []
            total = len(valid_rows)

            def process_row(index_row):
                """Worker-Funktion: Verarbeitet eine einzelne Zeile."""
                i, row = index_row
                search_string = row.get('SearchString', '')
                postal_code = row.get('PLZ', '')

                logger.info(f"  [{i}/{total}] Suche: {search_string}")

                try:
                    api_results = self.api_client.run_scraper_and_get_results(
                        search_string, postal_code
                    )
                    logger.info(f"  [{i}/{total}] → {len(api_results)} Ergebnisse erhalten")

                    combined_results = []
                    if api_results:
                        # Jedes API-Ergebnis mit den Input-Daten kombinieren
                        for result in api_results:
                            combined = {
                                'SearchString': row.get('SearchString', ''),
                                'PLZ': row.get('PLZ', ''),
                                'Stadt': row.get('Stadt', ''),
                                'KundenNr': row.get('KundenNr', '')
                            }
                            combined.update(result)
                            combined_results.append(combined)
                    else:
                        # Keine Ergebnisse → leere Zeile mit Input-Daten
                        combined_results.append({
                            'SearchString': row.get('SearchString', ''),
                            'PLZ': row.get('PLZ', ''),
                            'Stadt': row.get('Stadt', ''),
                            'KundenNr': row.get('KundenNr', '')
                        })

                    return combined_results

                except Exception as e:
                    logger.error(f"  [{i}/{total}] Fehler bei API-Abfrage: {e}")
                    return [{
                        'SearchString': row.get('SearchString', ''),
                        'PLZ': row.get('PLZ', ''),
                        'Stadt': row.get('Stadt', ''),
                        'KundenNr': row.get('KundenNr', '')
                    }]

            # Parallele Verarbeitung mit 6 Workern
            logger.info("Starte parallele Verarbeitung mit 6 Workern...")
            with ThreadPoolExecutor(max_workers=6) as executor:
                # Submit alle Tasks
                futures = {
                    executor.submit(process_row, (i, row)): i
                    for i, row in enumerate(valid_rows, 1)
                }

                # Collect results as they complete
                for future in as_completed(futures):
                    try:
                        results = future.result()
                        all_combined_rows.extend(results)
                    except Exception as e:
                        logger.error(f"Worker-Fehler: {e}")

            # Schritt 3: Rohdaten speichern
            base_path = str(filepath).rsplit('.', 1)[0]
            raw_filepath = f"{base_path}_angereicherte_daten.csv"
            optimized_filepath = f"{base_path}_optimierte_daten.csv"

            self.csv_processor.write_csv(raw_filepath, all_combined_rows)

            # Schritt 4: Spalten filtern → optimierte Datei
            self.post_processor.process_and_filter(
                raw_filepath, optimized_filepath, COLUMNS_TO_KEEP
            )

            logger.info("================================")
            logger.info("Anreicherung abgeschlossen!")
            logger.info(f"  Rohdaten:    {Path(raw_filepath).name}")
            logger.info(f"  Optimiert:   {Path(optimized_filepath).name}")
            logger.info("Nächster Schritt: Die optimierte Datei in Schritt 2 (Bereinigen) verwenden.")
            logger.info("================================")

        except Exception as e:
            logger.critical(f"Fehler bei der Anreicherung: {e}")
        finally:
            self.ui.set_status("Bereit.")
            self._enable_all_buttons()

    # ==========================================================================
    # SCHRITT 2: Bereinigen
    # ==========================================================================

    def start_cleaning(self):
        filepath = filedialog.askopenfilename(
            title="Angereicherte Datei zum Bereinigen auswählen",
            filetypes=[("CSV Dateien", "*.csv")],
            initialdir="./Daten"
        )
        if filepath:
            thread = threading.Thread(target=self.process_cleaning, args=(filepath,))
            thread.daemon = True
            thread.start()

    def process_cleaning(self, filepath: str):
        try:
            self._disable_all_buttons()
            self.ui.set_status(f"Bereinige Datei: {Path(filepath).name}...")

            logger.info("================================")
            logger.info(f"Starte Bereinigung für: {Path(filepath).name}")

            results = self.cleaner.clean_data(str(filepath))

            logger.info("================================")
            logger.info("Bereinigung abgeschlossen!")
            logger.info(f"  Eindeutig:      {Path(results.get('eindeutig', 'N/A')).name}")
            logger.info(f"  Zur Prüfung:    {Path(results.get('zur_pruefung', 'N/A')).name}")
            logger.info(f"  Aussortiert:     {Path(results.get('aussortiert', 'N/A')).name}")
            if 'erneut_crawlen' in results:
                logger.info(f"  Erneut Crawlen: {Path(results['erneut_crawlen']).name}")
                logger.info("  → Diese Datei kann direkt in Schritt 1 (Anreichern) verwendet werden.")
            logger.info("================================")

        except Exception as e:
            logger.critical(f"Fehler bei der Bereinigung: {e}")
        finally:
            self.ui.set_status("Bereit.")
            self._enable_all_buttons()


    # ==========================================================================
    # SCHRITT 3: Zusammenführen (Konsolidierung aller Batches)
    # ==========================================================================

    def start_consolidation(self):
        dirpath = filedialog.askdirectory(
            title="Prod-Ordner mit batch_*-Unterordnern auswählen",
            initialdir="./Daten"
        )
        if dirpath:
            thread = threading.Thread(target=self.process_consolidation, args=(dirpath,))
            thread.daemon = True
            thread.start()

    def process_consolidation(self, dirpath: str):
        try:
            self._disable_all_buttons()
            self.ui.set_status("Zusammenführen läuft...")

            logger.info("================================")
            logger.info(f"Starte Zusammenführung in: {Path(dirpath).name}")

            results = self.consolidator.consolidate(dirpath)

            stats = results['stats']
            logger.info("================================")
            logger.info("Zusammenführung abgeschlossen!")
            logger.info(f"  Batches:              {results['batches_found']}")
            logger.info(f"  Ausgabeordner:        {Path(results['output_dir']).name}")
            logger.info(f"  Eindeutig:            {stats['eindeutig_rows']} Zeilen "
                        f"({stats['eindeutig_unique_customers']} Kunden) → {Path(results['eindeutig']).name}")
            logger.info(f"  Zur Prüfung:          {stats['zur_pruefung_rows']} Zeilen "
                        f"({stats['zur_pruefung_unique_customers']} Kunden) → {Path(results['zur_pruefung']).name}")
            logger.info("================================")

        except Exception as e:
            logger.critical(f"Fehler bei der Zusammenführung: {e}")
        finally:
            self.ui.set_status("Bereit.")
            self._enable_all_buttons()


# ==========================================================================
# APP STARTEN
# ==========================================================================
if __name__ == "__main__":
    root = tk.Tk()
    app = GoogleMapsScraper(root)
    root.mainloop()
