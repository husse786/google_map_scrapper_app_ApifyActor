# main.py
# Main App. Verbindet UI, CSV-Verarbeitung und den API-Client.

import tkinter as tk
from tkinter import filedialog, messagebox
import threading
from pathlib import Path
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

# Importiere unsere eigenen Module
from ui_manager import AppUI # UI-Manager-Klasse
from csv_processor import CSVProcessor # CSV-Verarbeitungs-Klasse
from apify_wrapper import ApifyClientWrapper # API-Client-Wrapper
from csv_postprocessor import CSVPostProcessor # Importiere die neue Post-Processing-Klasse
from data_cleaner import DataCleaner # Importiere die DataCleaner-Klasse
import config
from logger_config import logger # Importiere den Logger

# HILFSKLASSE für die UI-Log-Umleitung
# --- DIE KORREKTUR IST HIER: class TextHandler(logging.Handler): ---
class TextHandler(logging.Handler):
    """
    Ein Logging-Handler, der Log-Nachrichten in ein Tkinter Text-Widget schreibt.
    Erbt von logging.Handler, um alle notwendigen Methoden zu erhalten.
    """
    def __init__(self, text_widget):
        # Rufe den Konstruktor der Elternklasse auf
        super().__init__()
        self.text_widget = text_widget

    def emit(self, record):
        """Sendet einen Log-Eintrag an das Text-Widget."""
        msg = self.format(record)
        # after() wird verwendet, um den UI-Aufruf im Hauptthread sicherzustellen
        self.text_widget.after(0, self.append_message, msg)

    def append_message(self, msg):
        """Fügt die Nachricht an das Text-Widget an."""
        self.text_widget.config(state=tk.NORMAL)
        self.text_widget.insert(tk.END, msg + '\n')
        self.text_widget.see(tk.END)
        self.text_widget.config(state=tk.DISABLED)

class MainApplication:
    """
    Die Hauptklasse der Anwendung, die alle Komponenten koordiniert.
    """
    def __init__(self, root):
        self.root = root
        self.processor = CSVProcessor()
        self.post_processor = CSVPostProcessor()  # Initialisiere die Post-Processing-Klasse
        self.cleaner = DataCleaner()  # Initialisiere die DataCleaner-Klasse

        if "DEIN_APIFY_API_TOKEN" in config.APIFY_API_TOKEN:
            self.show_error_and_exit("API-Token fehlt!", "Bitte trage deinen API-Token in die config.py Datei ein.")
            return

        self.api_client = ApifyClientWrapper(config.APIFY_API_TOKEN, config.ACTOR_ID)
        
        self.ui = AppUI(root, 
                upload_callback=self.start_processing_thread,
                clean_callback=self.start_cleaning_thread)
        
        # Leite Logs in die UI um
        log_handler = TextHandler(self.ui.log_text)
        # Setze ein Format für den UI-Handler, damit keine Zeitstempel in der UI erscheinen
        log_handler.setFormatter(logging.Formatter('%(message)s'))
        logger.addHandler(log_handler)
        
        self.ui.set_status("Bereit. Bitte eine CSV-Datei zum Hochladen auswählen.")

    def show_error_and_exit(self, title, message):
        """Zeigt ein Fehlerfenster an und beendet die Anwendung."""
        messagebox.showerror(title, message)
        self.root.destroy()

    def start_processing_thread(self):
        """Öffnet den Dateidialog und startet den Verarbeitungsprozess in einem neuen Thread."""
        filepath = filedialog.askopenfilename(
            title="CSV Queldatei für Anreicherung auswählen",
            filetypes=(("CSV Files", "*.csv"), ("All files", "*.*"))
        )
        if not filepath:
            self.ui.set_status("Vorgang abgebrochen.")
            return
        # Starte Anreichernungsprozess in einem Thread.
        processing_thread = threading.Thread(target=self.process_file, args=(filepath,))
        processing_thread.start()
    

    def start_cleaning_thread(self):
        """Öffnet den Dateidialog und startet den Bereinigungsprozess in einem neuen Thread."""
        filepath = filedialog.askopenfilename(
            title="2. Optimierte Datei zur Bereinigung auswählen", 
            filetypes=(("CSV Files", "*.csv"),)
        )
        if not filepath:
            self.ui.set_status("Bereinigung abgebrochen.")
            return
        threading.Thread(target=self.process_cleaning, args=(filepath,)).start()

    def process_cleaning(self, filepath: str):
        """Führt den Bereinigungsprozess im Hintergrund aus."""
        try:
            self.ui.upload_button.config(state=tk.DISABLED)
            self.ui.clean_button.config(state=tk.DISABLED)
            self.ui.set_status(f"Bereinige Datei: {Path(filepath).name}...")
            logger.info("--------------------------------")
            logger.info(f"Starte Bereinigung für: {Path(filepath).name}")
            # Dateipfade für die Ausgabe generieren
            
            input_filename_base = Path(filepath).stem.replace("_optimierte_daten", "")
            output_dir = Path(filepath).parent

            cleaned_ok_filepath = output_dir / f"{input_filename_base}_eindeutig.csv"
            cleaned_review_filepath = output_dir / f"{input_filename_base}_zur_pruefung.csv"
            rejected_filepath = output_dir / f"{input_filename_base}_aussortiert.csv"

            # Alle vier Argumente korrekt übergeben ---
            self.cleaner.clean_data(
                str(filepath), 
                str(cleaned_ok_filepath), 
                str(cleaned_review_filepath), 
                str(rejected_filepath)
            )
            logger.info("Bereinigung abgeschlossen.")

        except Exception as e:
            logger.critical(f"Ein kritischer Fehler ist bei der Bereinigung aufgetreten: {e}")
        finally:
            self.ui.set_status("Bereit.")
            self.ui.upload_button.config(state=tk.NORMAL)
            self.ui.clean_button.config(state=tk.NORMAL)
    def _enrich_worker(self, i, total_valid, row):
        """Führt die API-Anreicherung für eine einzelne Zeile aus (wird von einem Thread aufgerufen)."""
        search_string = str(row.get("SearchString", ""))
        plz = str(row.get("PLZ", ""))
        
        # UI-Update muss sicher über das Hauptfenster laufen
        self.root.after(0, self.ui.set_status, f"Verarbeite Zeile {i+1}/{total_valid}: {search_string}")
        
        api_results = self.api_client.run_scraper_and_get_results(search_string, plz)
        
        logger.info(f"-> Zeile {i+1}/{total_valid}: '{search_string}' - {len(api_results)} Ergebnis(se) von Apify erhalten.")
        
        # Gib die Original-Zeile UND das API-Ergebnis zurück
        return row, api_results

    def process_file(self, filepath: str):
            """Die Hauptlogik, die den Anreicherungsprozess parallel steuert."""
            try:
                self.ui.upload_button.config(state=tk.DISABLED)
                self.ui.clean_button.config(state=tk.DISABLED)
                self.ui.set_status(f"Verarbeite Datei: {Path(filepath).name}...")
                logger.info("--------------------------------")
                logger.info(f"Datei '{Path(filepath).name}' wird verarbeitet...")

                valid_data, invalid_data = self.processor.load_and_validate(filepath)
                logger.info(f"{len(valid_data)} gültige und {len(invalid_data)} ungültige Zeilen gefunden.")

                output_dir = Path(filepath).parent
                input_filename_base = Path(filepath).stem

                if invalid_data:
                    invalid_filepath = output_dir / f"{input_filename_base}_fehlende_daten.csv"
                    self.processor.write_csv(str(invalid_filepath), invalid_data)
                    logger.info(f"Ungültige Zeilen wurden in '{invalid_filepath.name}' gespeichert.")

                enriched_results = []
                
                # --- START DER PARALLELEN VERARBEITUNG ---
                # Wir erstellen einen Pool mit 4 Worker-Threads.
                with ThreadPoolExecutor(max_workers=4) as executor:
                    # Wir übergeben alle Aufgaben an den Pool.
                    # Jede Aufgabe ist ein Aufruf unserer _enrich_worker-Funktion.
                    futures = [executor.submit(self._enrich_worker, i, len(valid_data), row) 
                            for i, row in enumerate(valid_data)]

                    # Wir warten auf die Ergebnisse, sobald sie eintreffen.
                    for future in as_completed(futures):
                        original_row, api_results = future.result()
                        
                        # Logik zum Zusammenführen der Ergebnisse (wie vorher)
                        if not api_results:
                            enriched_results.append(original_row)
                        else:
                            for result in api_results:
                                new_row = original_row.copy()
                                new_row.update(result)
                                enriched_results.append(new_row)
                # --- ENDE DER PARALLELEN VERARBEITUNG ---

                if enriched_results:
                    enriched_filepath = output_dir / f"{input_filename_base}_angereicherte_daten.csv"
                    self.processor.write_csv(str(enriched_filepath), enriched_results)
                    logger.info("\nRohdaten-Anreicherung abgeschlossen!")
                    logger.info(f"Alle angereicherten Rohdaten wurden in '{enriched_filepath.name}' gespeichert.")
                    
                    optimierte_filepath = output_dir / f"{input_filename_base}_optimierte_daten.csv"
                    self.post_processor.process_and_filter(
                        input_filepath=str(enriched_filepath),
                        output_filepath=str(optimierte_filepath),
                        columns_to_keep=config.FINAL_COLUMNS
                    )
                else:
                    logger.info("\nVerarbeitung abgeschlossen, aber keine Daten zum Speichern vorhanden.")

            except Exception as e:
                logger.critical(f"\nEin kritischer Fehler ist aufgetreten: {e}")
                messagebox.showerror("Kritischer Fehler", f"Ein unerwarteter Fehler ist aufgetreten:\n{e}")
            finally:
                self.ui.set_status("Bereit. Bitte eine Datei auswählen.")
                self.ui.upload_button.config(state=tk.NORMAL)
                self.ui.clean_button.config(state=tk.NORMAL)
    def run(self):
        """Startet die Haupt-Event-Loop der Anwendung."""
        self.root.mainloop()

if __name__ == "__main__":
    main_root = tk.Tk()
    app = MainApplication(main_root)
    app.run()
