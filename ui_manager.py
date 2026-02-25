# ui_manager.py
# Definiert die grafische Benutzeroberfläche der Anwendung.

import tkinter as tk
from tkinter import scrolledtext

class AppUI:
    """Erstellt und verwaltet die Tkinter-Benutzeroberfläche."""

    def __init__(self, root):
        root.title("Google Maps Scraper - Zweifel")
        root.geometry("800x600")

        # --- Oberer Bereich: Buttons ---
        button_frame = tk.Frame(root)
        button_frame.pack(pady=10, padx=10, fill=tk.X)

        # Schritt 0: Vorverarbeitung — prüft Vollständigkeit der Input-Daten
        self.preprocess_button = tk.Button(
            button_frame,
            text="0. Vorverarbeitung",
            width=20,
            bg="#9C27B0",    # Lila — optisch abgesetzt als Vorschritt
            fg="white"
        )
        self.preprocess_button.pack(side=tk.LEFT, padx=5)

        # Schritt 1: Anreichern — sendet Daten an Google Maps API
        self.upload_button = tk.Button(
            button_frame,
            text="1. Anreichern",
            width=20,
            bg="#2196F3",    # Blau
            fg="white"
        )
        self.upload_button.pack(side=tk.LEFT, padx=5)

        # Schritt 2: Bereinigen — wertet die API-Ergebnisse qualitativ aus
        self.clean_button = tk.Button(
            button_frame,
            text="2. Bereinigen",
            width=20,
            bg="#4CAF50",    # Grün
            fg="white"
        )
        self.clean_button.pack(side=tk.LEFT, padx=5)

        # --- Mittlerer Bereich: Log-Ausgabe ---
        self.log_display = scrolledtext.ScrolledText(
            root,
            state='disabled',   # Nur lesen, kein Benutzer-Input
            height=25,
            font=("Courier", 10)
        )
        self.log_display.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)

        # --- Unterer Bereich: Status-Leiste ---
        self.status_var = tk.StringVar(value="Bereit.")
        self.status_bar = tk.Label(
            root,
            textvariable=self.status_var,
            bd=1,
            relief=tk.SUNKEN,
            anchor=tk.W
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def set_status(self, text: str):
        """Aktualisiert die Status-Leiste am unteren Rand."""
        self.status_var.set(text)

    def log(self, message: str):
        """Fügt eine Nachricht zum Log-Fenster hinzu."""
        self.log_display.config(state='normal')
        self.log_display.insert(tk.END, message + '\n')
        self.log_display.see(tk.END)        # Auto-Scroll nach unten
        self.log_display.config(state='disabled')