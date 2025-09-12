# ui_manager.py
# Definiert die grafische Benutzeroberfläche der Anwendung.

import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText

class AppUI:
    """
    Diese Klasse erstellt und verwaltet alle Elemente der Benutzeroberfläche.
    """
    def __init__(self, root, upload_callback):
        """
        Initialisiert die Benutzeroberfläche.

        Args:
            root: Das Hauptfenster der Tkinter-Anwendung.
            upload_callback: Die Funktion, die aufgerufen wird, wenn der Upload-Button geklickt wird.
        """
        self.root = root
        self.root.title("Google Maps Scraper")
        self.root.geometry("700x500") # Startgröße des Fensters

        # Haupt-Frame mit Padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- Top Sektion: Button und Info-Text ---
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill=tk.X, pady=(0, 10))

        self.upload_button = ttk.Button(top_frame, text="CSV Hochladen", command=upload_callback)
        self.upload_button.pack(side=tk.LEFT, padx=(0, 10))

        info_label = ttk.Label(
            top_frame,
            text="CSV-Datei muss Spalten enthalten: 'SearchString', 'PLZ' , 'KundenNr' (Trennzeichen: ';')."
        )
        info_label.pack(side=tk.LEFT, anchor="w")

        # --- Log-Anzeige ---
        log_label = ttk.Label(main_frame, text="Logs:")
        log_label.pack(anchor="w")

        self.log_text = ScrolledText(main_frame, height=20, wrap=tk.WORD, state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # --- Statusleiste am unteren Rand ---
        self.status_bar = ttk.Label(main_frame, text="Bereit.", relief=tk.SUNKEN, anchor="w")
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))

    def update_log(self, message: str):
        """Fügt eine neue Nachricht zur Log-Anzeige hinzu."""
        self.log_text.config(state=tk.NORMAL) # Schreibzugriff erlauben
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END) # Automatisch nach unten scrollen
        self.log_text.config(state=tk.DISABLED) # Schreibzugriff sperren

    def set_status(self, message: str):
        """Setzt den Text in der Statusleiste."""
        self.status_bar.config(text=message)