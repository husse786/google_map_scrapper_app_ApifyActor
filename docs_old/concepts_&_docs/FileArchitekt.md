> ## ⚠ Historisches Dokument — nicht mehr gültig
>
> **Stand: 17.10.2025**, verschoben nach `docs_old/` am 03.08.2026. Zeigt den
> Dateibaum der Tkinter-Anwendung vor dem Umbau zur Webapp.
>
> **Von den elf Dateien, die dieser Baum nennt, gibt es neun nicht mehr.**
> Geblieben sind `data_cleaner.py` und `config.py`. `main.py` und
> `ui_manager.py` entfielen mit dem Umbau selbst, `apify_wrapper.py` in Phase 2;
> `clean_input_data.py`, `csv_processor.py`, `csv_postprocessor.py`,
> `logger_config.py`, `data_preprocessor.py` und `data_consolidator.py` wurden
> in der Abschlussrunde entfernt. Alle liegen in der Git-Historie.
>
> **Den heutigen Aufbau** beschreibt [`README.md`](../../README.md);
> `agent/UMBAUPLAN_WEBAPP.md` hält fest, welche Datei wohin ging, und
> `agent/02_DATENVERTRAG.md` §5 und §7 die Schnittstellen zwischen den Modulen.

---

# google-maps-scraper-app/

│
├── main.py               # Koordiniert den gesamten Ablauf und die UI
│
├── ui_manager.py         # Definiert die grafische Benutzeroberfläche
│
├── csv_processor.py      # Liest und validiert die initiale CSV-Datei
├── csv_postprocessor.py  # Filtert die Ergebnisse auf die gewünschten Spalten
├── data_cleaner.py       # Bereinigt Duplikate mit dem Scoring-Modell
│
├── apify_wrapper.py      # Kapselt die gesamte API-Kommunikation mit Apify
│
├── logger_config.py      # Konfiguriert das Logging-System
└── config.py             # Speichert Konfigurationen (API-Token, Spaltenlisten etc.)
