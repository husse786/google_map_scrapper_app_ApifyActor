# google_map_scrapper_app_ApifyActor
scrapping Business Data like opening hours and telenumber to enrich Customer databank. Using Apify Actor API call and Input data


Google Maps Scraper GUI

Dieses Projekt ist eine Desktop-Anwendung mit einer grafischen Benutzeroberfläche (GUI), um das Extrahieren von Unternehmensdaten aus Google Maps zu automatisieren. Die Anwendung nutzt die Apify-Plattform im Hintergrund, um gezielte und genaue Suchanfragen durchzuführen.

Ein Benutzer kann eine CSV-Datei mit Suchbegriffen und Postleitzahlen hochladen. Die Anwendung verarbeitet diese Datei, ruft für jeden validen Eintrag angereicherte Daten ab und stellt am Ende eine vollständige Ergebnis-Datei sowie eine Fehler-Datei bereit.

Architektur-Überblick

Die Anwendung folgt einem modularen Design, bei dem jede Datei eine klare Verantwortung hat:

main.py: Das Gehirn der Anwendung. Initialisiert alle Komponenten und steuert den gesamten Workflow von der Dateiauswahl bis zum Speichern der Ergebnisse.

ui_manager.py: Verantwortlich für das Gesicht der Anwendung. Baut und verwaltet alle grafischen Elemente mit Tkinter.

csv_processor.py: Der Daten-Experte. Liest, validiert und schreibt CSV-Dateien mit der pandas-Bibliothek.

Wichtig: Stellt sicher, dass die PLZ-Spalte als Text (string) behandelt wird, um Formatierungsfehler (z.B. 8001.0) zu vermeiden.

apify_wrapper.py: Die Brücke zur Außenwelt. Kapselt die gesamte Kommunikation mit der Apify API über die apify-client-Bibliothek.

logger_config.py: Richtet das zentrale Logging-System ein, das Nachrichten gleichzeitig an die Konsole, die UI und in eine rotierende Log-Datei (logs/app.log) schreibt.

config.py (lokal): Speichert sensible Daten wie den API-Token. Wird durch .gitignore von der Versionskontrolle ausgeschlossen.

config.template.py: Eine Vorlage für die config.py, die sich im Repository befindet.

Features

Einfache Bedienung: Intuitive grafische Oberfläche zum Hochladen von CSV-Dateien.

Intelligente Datenvalidierung: Prüft hochgeladene Dateien automatisch auf das korrekte Format und trennt ungültige Einträge (z.B. ohne PLZ) ab.

Präzise Suchen: Nutzt die Kombination aus Suchbegriff und Postleitzahl für genaue Abfragen an die Apify API.

Asynchrone Verarbeitung: Die Benutzeroberfläche bleibt dank Threading während der gesamten Verarbeitungszeit reaktionsfähig und friert nicht ein.

Echtzeit-Feedback: Ein integriertes Log-Fenster zeigt dem Benutzer jederzeit den aktuellen Status des Prozesses.

Robustes Logging: Alle Aktionen werden parallel in eine app.log-Datei geschrieben, um eine einfache Fehlersuche zu ermöglichen.

Strukturierte Ergebnisse: Erzeugt am Ende zwei saubere CSV-Dateien: angereicherte_daten.csv und fehlende_daten.csv.

Setup & Installation

Diese Anleitung beschreibt, wie ein Entwickler das Projekt von Grund auf einrichtet.

Voraussetzungen

Python 3.10+ ist auf dem System installiert.

Hinweis für macOS: Es wird dringend empfohlen, Python von der offiziellen Webseite python.org zu installieren, um Kompatibilitätsprobleme mit der Tkinter-Bibliothek zu vermeiden, die bei Installationen über Homebrew auftreten können.

Der Code-Editor Visual Studio Code wird empfohlen.

Ein Apify-Account und der dazugehörige API-Token.

Schritt-für-Schritt-Einrichtung

1. Projekt klonen
Klone dieses Repository auf deinen lokalen Computer:

git clone [https://github.com/husse786/google_map_scrapper_app_ApifyActor.git](https://github.com/husse786/google_map_scrapper_app_ApifyActor.git)
cd google_map_scrapper_app_ApifyActor

2. Projekt in VS Code öffnen
Öffne den soeben geklonten Projektordner in VS Code.

3. Virtuelle Umgebung erstellen und aktivieren
Eine "virtuelle Umgebung" isoliert die Projekt-Abhängigkeiten. Führe die folgenden Befehle im integrierten Terminal von VS Code aus.

Erstellen:

python3 -m venv venv

Aktivieren:

Für macOS/Linux: source venv/bin/activate

Für Windows: .\venv\Scripts\activate

Du erkennst die aktive Umgebung am (venv)-Präfix in deiner Terminal-Zeile.

4. Notwendige Pakete installieren
Die Datei requirements.txt listet alle externen Python-Bibliotheken auf. Installiere sie mit pip:

pip install -r requirements.txt

5. Persönliche Konfiguration eintragens
Das Projekt benötigt deinen Apify API-Token.

Erstelle eine Kopie der Vorlagedatei config.template.py und nenne sie config.py.

Öffne die neue config.py.

Ersetze den Platzhalter "DEIN_APIFY_API_TOKEN_HIER_EINFÜGEN" durch deinen echten API-Token aus deinem Apify-Account (Settings → Integrations).

Abschluss: Die Entwicklungsumgebung ist jetzt vollständig konfiguriert.

Benutzung
Stelle sicher, dass deine virtuelle Umgebung (venv) aktiv ist.

Starte die Anwendung über das Terminal:

python main.py

Klicke auf den "CSV Hochladen"-Button und wähle deine CSV-Quelldatei aus.

Anforderung an die CSV: Die Datei muss durch Semikolon (;) getrennt sein und die Spalten SearchString und PLZ enthalten.

Der Prozess startet automatisch. Verfolge den Fortschritt im Log-Fenster.

Nach Abschluss findest du im selben Ordner wie deine Quelldatei die Ergebnisdateien.

