# Google Maps Scraper GUI

Dieses Projekt ist eine Desktop-Anwendung mit einer grafischen Benutzeroberfläche (GUI), um den Prozess des Extrahierens und Bereinigens von Unternehmensdaten aus Google Maps zu automatisieren. Die Anwendung nutzt die Apify-Plattform im Hintergrund, um gezielte und genaue Suchanfragen parallel auszuführen.

## Überblick

Das System ist in zwei Haupt-Workflows unterteilt:

1. **Anreicherung:** Lädt eine CSV-Datei, liest die Suchanfragen und ruft parallel Daten von der Apify API ab.
2. **Bereinigung:** Wendet ein intelligentes, regelbasiertes Scoring-Modell an, um Duplikate und unplausible Ergebnisse aus den angereicherten Daten zu filtern.

## Features

* **Parallele Verarbeitung:** Nutzt einen Thread-Pool (4 Worker), um mehrere API-Aufrufe gleichzeitig durchzuführen und den Anreicherungsprozess drastisch zu beschleunigen.
* **Zweistufiger Workflow:** Klare Trennung der Benutzeroberfläche in "1. Anreichern" und "2. Bereinigen".
* **Intelligente Datenbereinigung:** Ein fortschrittliches `DataCleaner`-Modul mit einem gewichteten Scoring-Modell, das zwischen Suchen mit und ohne Strassenangabe unterscheidet.
* **Sichere Ergebnis-Filterung:** Stellt sicher, dass keine Kunden verloren gehen, indem unklare Fälle in eine separate Datei (`_zur_pruefung.csv`) zur manuellen Kontrolle verschoben werden.
* **Dynamische Dateinamen:** Verhindert das Überschreiben von Ergebnissen, indem die Namen der Ausgabedateien auf dem Namen der Eingabedatei basieren.
* **Asynchrone UI:** Die Benutzeroberfläche bleibt dank Threading während der gesamten Verarbeitungszeit reaktionsfähig und friert nicht ein.
* **Detailliertes Logging:** Alle Aktionen werden in Echtzeit in die UI und parallel in eine Datei (`logs/app.log`) geschrieben.

## Architektur-Überblick

Die Anwendung folgt einem modularen Design, bei dem jede Datei eine klare Verantwortung hat:

google-maps-scraper-app/
│
├── main.py               \# Koordiniert den gesamten Ablauf und die UI
│
├── ui\_manager.py         \# Definiert die grafische Benutzeroberfläche
│
├── csv\_processor.py      \# Liest und validiert die initiale CSV-Datei
├── csv\_postprocessor.py  \# Filtert die Ergebnisse auf die gewünschten Spalten
├── data\_cleaner.py       \# Bereinigt Duplikate mit dem Scoring-Modell
│
├── apify\_wrapper.py      \# Kapselt die gesamte API-Kommunikation mit Apify
│
├── logger\_config.py      \# Konfiguriert das Logging-System
└── config.py             \# Speichert Konfigurationen (API-Token, Spaltenlisten etc.)

## Setup & Installation

Diese Anleitung beschreibt, wie das Projekt von Grund auf eingerichtet wird.

### Voraussetzungen

* **Python 3.10+** ist auf dem System installiert.
  * **Hinweis für macOS:** Es wird dringend empfohlen, Python von der offiziellen Webseite [python.org](https://www.python.org/downloads/macos/) zu installieren, um Kompatibilitätsprobleme mit der `Tkinter`-Bibliothek zu vermeiden.
* Ein **Apify-Account** und der dazugehörige **API-Token**.

### Schritt-für-Schritt-Einrichtung

1. **Projekt klonen:** Klone dieses Repository auf deinen lokalen Computer:

    ```bash
    git clone [https://github.com/husse786/google_map_scrapper_app_ApifyActor.git](https://github.com/husse786/google_map_scrapper_app_ApifyActor.git)
    cd google_map_scrapper_app_ApifyActor
    ```

2. **Projekt in VS Code öffnen:**
    Öffne den soeben geklonten Projektordner in VS Code.

3. **Virtuelle Umgebung erstellen und aktivieren:**
    Eine "virtuelle Umgebung" isoliert die Projekt-Abhängigkeiten. Führe die folgenden Befehle im integrierten Terminal von VS Code aus.

    * **Erstellen:**

        ```bash
        python3 -m venv venv
        ```

    * **Aktivieren (macOS/Linux):**

        ```bash
        source venv/bin/activate
        ```

    * **Aktivieren (Windows):**

        ```bash
        .\venv\Scripts\activate
        ```

4. **Notwendige Pakete installieren:**
    Die Datei `requirements.txt` listet alle externen Python-Bibliotheken auf.

    ```bash
    pip install -r requirements.txt
    ```

5. **Persönliche Konfiguration eintragen:**
    Das Projekt benötigt deinen Apify API-Token und die Konfiguration der Bereinigungsregeln.
    * Erstelle eine Kopie der Vorlagedatei `config.template.py` und nenne sie `config.py`.
    * Öffne die neue `config.py` und trage deinen echten **`APIFY_API_TOKEN`** ein.
    * Überprüfe die Listen (`FINAL_COLUMNS`) und Schwellenwerte (`DYNAMIC_THRESHOLD_GAP`) und passe sie bei Bedarf an.

## Benutzung

Stelle sicher, dass deine virtuelle Umgebung (`venv`) aktiv ist.

### Schritt 1: Daten anreichern

1. Starte die Anwendung über das Terminal:

    ```bash
    python main.py
    ```

2. Klicke auf den Button **"1. Quelldatei anreichern"**.
3. Wähle deine CSV-Quelldatei aus.
    * **Anforderung an die CSV:** Die Datei muss durch Semikolon (`;`) getrennt sein und die Spalten `SearchString`, `PLZ` und `KundenNr` enthalten.
4. Der Prozess startet und verarbeitet die Anfragen parallel. Verfolge den Fortschritt im Log-Fenster.
5. Nach Abschluss findest du im selben Ordner die Ergebnisdateien, u.a. `DEINEDATEI_optimierte_daten.csv`.

### Schritt 2: Daten bereinigen

1. Klicke auf den Button **"2. Optimierte Datei bereinigen"**.
2. Wähle die in Schritt 1 erstellte `..._optimierte_daten.csv`-Datei aus.
3. Der Bereinigungsprozess startet und wendet die intelligente Scoring-Logik an.
4. Nach Abschluss findest du drei neue Dateien in deinem Ordner:
    * **`..._eindeutig.csv`:** Enthält alle als sicher eingestuften Treffer.
    * **`..._zur_pruefung.csv`:** Enthält alle unklaren oder mehrdeutigen Fälle zur manuellen Kontrolle.
    * **`..._aussortiert.csv`:** Enthält alle eindeutig falschen Treffer.

## Anhang: Detaillierte Logik des Datenbereinigungs-Moduls

Weitere Informationen zur Funktionsweise des `DataCleaner`-Moduls und der angewendeten Logik findest du in der [Data-Cleansing Dokumentation](docs/concepts_&_docs/DataCleansing/data_cleansing.md).
