# ui_manager.py
# Definiert die grafische Benutzeroberfläche der Anwendung.

import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText

class AppUI:
    """
    Diese Klasse erstellt und verwaltet alle Elemente der Benutzeroberfläche.
    """
    def __init__(self, root, upload_callback, clean_callback):
        """
        Initialisiert die Benutzeroberfläche.
        """
        self.root = root
        self.root.title("Google Maps Scraper")
        self.root.geometry("700x550") # Etwas mehr Höhe für den neuen Text

        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- Top Sektion: Buttons ---
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Button 1: Daten anreichern
        self.upload_button = ttk.Button(button_frame, text="1. Quelldatei anreichern", command=upload_callback)
        self.upload_button.pack(side=tk.LEFT, padx=(0, 10), ipady=5)
        
        # Button 2: Daten bereinigen
        self.clean_button = ttk.Button(button_frame, text="2. Optimierte Datei bereinigen", command=clean_callback)
        self.clean_button.pack(side=tk.LEFT, padx=(0, 10), ipady=5)

        # --- Info-Text (in eigener Zeile für sauberes Layout) ---
        info_label = ttk.Label(
            main_frame,
            text="CSV muss Spalten enthalten: 'SearchString', 'PLZ', 'KundenNr' (Trennzeichen: ';')."
        )
        info_label.pack(fill=tk.X, anchor="w", pady=(5, 5))

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
        # Diese Methode ist nicht mehr notwendig, da das Logging jetzt über den TextHandler läuft,
        # kann aber für direkte UI-Nachrichten beibehalten werden.
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def set_status(self, message: str):
        """Setzt den Text in der Statusleiste."""
        self.status_bar.config(text=message)