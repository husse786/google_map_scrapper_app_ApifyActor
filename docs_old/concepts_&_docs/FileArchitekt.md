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
