# main.py
# Main Part - Verbindet UI, CSV-Verarbeitung und den API-Client.

import tkinter as tk
from tkinter import filedialog
import threading
from pathlib import Path

# Importiere unsere eigenen Module
from ui_manager import AppUI
from csv_processor import CSVProcessor
from apify_wrapper import ApifyClientWrapper
import config
from logger_config import logger # Importiere den Logger

class MainApplication:
    """
    Die Hauptklasse der Anwendung, die alle Komponenten koordiniert.
    """
    def __init__(self, root):
        self.root = root
        self.processor = CSVProcessor()

        # Überprüfen, ob der API-Token gesetzt ist
        if "DEIN_APIFY_API_TOKEN" in config.APIFY_API_TOKEN:
            # Zeige eine Fehlermeldung, wenn der Token fehlt
            self.show_error_and_exit("API-Token fehlt!", "Bitte trage deinen API-Token in die config.py Datei ein.")
            return

        self.api_client = ApifyClientWrapper(config.APIFY_API_TOKEN, config.ACTOR_ID)
        self.ui = AppUI(root, upload_callback=self.start_processing_thread)
        #Leite Logs in die UI um
        log_handler = TextHandler(self.ui.log_text)
        logger.addHandler(log_handler)
        #logger.setLevel("INFO") # Setze das gewünschte Log-Level hier
        self.ui.set_status("Bereit. Bitte eine CSV-Datei zum Hochladen auswählen.")

    def show_error_and_exit(self, title, message):
        """Zeigt ein Fehlerfenster an und beendet die Anwendung."""
        tk.messagebox.showerror(title, message)
        self.root.destroy()

    def start_processing_thread(self):
        """Öffnet den Dateidialog und startet den Verarbeitungsprozess in einem neuen Thread."""
        filepath = filedialog.askopenfilename(
            title="CSV-Datei auswählen",
            filetypes=(("CSV Files", "*.csv"), ("All files", "*.*"))
        )
        if not filepath:
            self.ui.set_status("Vorgang abgebrochen.")
            return

        # Wir starten die lange dauernde Verarbeitung in einem separaten Thread,
        # um zu verhindern, dass die Benutzeroberfläche einfriert.
        processing_thread = threading.Thread(target=self.process_file, args=(filepath,))
        processing_thread.start()

    def process_file(self, filepath: str):
        """Die Hauptlogik, die in einem Hintergrund-Thread läuft."""
        try:
            # UI für die Dauer der Verarbeitung anpassen
            self.ui.upload_button.config(state=tk.DISABLED)
            self.ui.set_status(f"Verarbeite Datei: {Path(filepath).name}...")
            logger.info("--------------------------------")
            logger.info(f"Datei '{Path(filepath).name}' wird verarbeitet...")

            # 1. CSV laden und validieren
            valid_data, invalid_data = self.processor.load_and_validate(filepath)
            logger.info(f"{len(valid_data)} gültige und {len(invalid_data)} ungültige Zeilen gefunden.")

            output_dir = Path(filepath).parent

            # 2. Ungültige Daten (falls vorhanden) speichern
            if invalid_data:
                invalid_filepath = output_dir / "fehlende_daten.csv"
                self.processor.write_csv(str(invalid_filepath), invalid_data)
                logger.info(f"Ungültige Zeilen wurden in '{invalid_filepath.name}' gespeichert.")

            enriched_results = []
            total_valid = len(valid_data)

            # 3. Gültige Daten Zeile für Zeile verarbeiten
            for i, row in enumerate(valid_data):
                search_string = row.get("SearchString")
                plz = row.get("PLZ")
                self.ui.set_status(f"Verarbeite Zeile {i+1}/{total_valid}: {search_string}")

                # API-Aufruf durchführen
                api_results = self.api_client.run_scraper_and_get_results(search_string, plz)
                logger.info(f"-> Zeile {i+1}/{total_valid}: '{search_string}' - {len(api_results)} Ergebnis(se) von Apify erhalten.")

                if not api_results:
                    # Wenn Apify nichts findet, behalten wir die Originalzeile
                    enriched_results.append(row)
                else:
                    # Füge die Originaldaten zu jedem Apify-Ergebnis hinzu
                    for result in api_results:
                        new_row = row.copy() # Kopiere die originalen Spalten
                        new_row.update(result) # Füge die neuen Spalten von Apify hinzu/überschreibe sie
                        enriched_results.append(new_row)

            # 4. Angereicherte Ergebnisse speichern
            if enriched_results:
                enriched_filepath = output_dir / "angereicherte_daten.csv"
                self.processor.write_csv(str(enriched_filepath), enriched_results)
                self.ui.update_log(f"\nVerarbeitung abgeschlossen!")
                self.ui.update_log(f"Alle angereicherten Daten wurden in '{enriched_filepath.name}' gespeichert.")
            else:
                self.ui.update_log("\nVerarbeitung abgeschlossen, aber keine Daten zum Speichern vorhanden.")

        except Exception as e:
            logger.critical(f"\nEin kritischer Fehler ist aufgetreten: {e}")
            tk.messagebox.showerror("Kritischer Fehler", f"Ein unerwarteter Fehler ist aufgetreten:\n{e}")
        finally:
            # UI am Ende wieder freigeben
            self.ui.set_status("Bereit. Bitte eine CSV-Datei zum Hochladen auswählen.")
            self.ui.upload_button.config(state=tk.NORMAL)

    def run(self):
        """Startet die Haupt-Event-Loop der Anwendung."""
        self.root.mainloop()
import logging
class TextHandler:
    """
    Ein Logging-Handler, der Log-Nachrichten in ein Tkinter Text-Widget schreibt.
    """
    def __init__(self, text_widget):
        logging.Handler.__init__(self)
        self.text_widget = text_widget

    def emit(self, record):
        msg = self.format(record)
        def append():
            self.text_widget.config(state=tk.NORMAL) # Schreibzugriff erlauben
            self.text_widget.insert(tk.END, msg + "\n")
            self.text_widget.see(tk.END) # Automatisch nach unten scrollen
            self.text_widget.config(state=tk.DISABLED) # Schreibzugriff sperren
        self.text_widget.after(0, append) # Sicherstellen, dass es im Hauptthread läuft

if __name__ == "__main__":
    main_root = tk.Tk()
    app = MainApplication(main_root)
    app.run()