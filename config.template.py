# config.template.py
# Zentrale Konfigurationsdatei. Sensible Daten kommen aus der Datei .env.
#
# SETUP:
# 1. Erstelle eine Datei namens '.env' im Projektordner mit folgendem Inhalt:
#    APIFY_API_TOKEN=dein_echter_token_hier
#    ACTOR_ID=deine_actor_id_hier
#    GOOGLE_API_KEY=dein_google_schluessel_hier   (nur für Modus B)
#    SMTP_SERVER=mail.firma.ch                    (nur für die Benachrichtigung)
#    SMTP_ABSENDER=anreicherung@firma.ch
# 2. Kopiere diese Datei als 'config.py'
#
# Die Einstellungen des Apify-Actors stehen NICHT hier, sondern in
# apify_provider.py (STANDARD_ACTOR_INPUT). Ausserhalb dieses einen Moduls
# kennt kein Teil des Projekts Apify-Feldnamen — sonst liesse sich die
# Datenquelle nicht austauschen.

import os
from dotenv import load_dotenv

# Lade Umgebungsvariablen aus der .env-Datei
load_dotenv()

# API-Token und Actor-ID aus Umgebungsvariablen lesen
APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN", "DEIN_APIFY_API_TOKEN")
ACTOR_ID = os.getenv("ACTOR_ID", "DEIN_ACTOR_ID")

# Schlüssel für die Google Places API — nur für Modus B (Auffrischen über die
# gespeicherte Google-Id). Für die Erstanreicherung wird er nicht gebraucht.
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "DEIN_GOOGLE_API_KEY")

# Mailversand für die Benachrichtigung am Ende eines Laufs.
# Fehlt SMTP_SERVER oder SMTP_ABSENDER, wird nicht versendet — der Lauf läuft
# trotzdem normal durch und schreibt ins Protokoll, was er verschickt hätte.
SMTP_SERVER = os.getenv("SMTP_SERVER", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "25"))
SMTP_BENUTZER = os.getenv("SMTP_BENUTZER", "")
SMTP_PASSWORT = os.getenv("SMTP_PASSWORT", "")
SMTP_ABSENDER = os.getenv("SMTP_ABSENDER", "")
SMTP_TLS = os.getenv("SMTP_TLS", "ja").lower() in ("ja", "true", "1")

# Der Mindestabstand zwischen dem besten und zweitbesten Score,
# wenn kein Ergebnis den festen Schwellenwert erreicht (03_ENTSCHEIDUNGEN.md B3).
DYNAMIC_THRESHOLD_GAP = 30
