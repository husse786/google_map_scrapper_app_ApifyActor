# config.template.py
# Zentrale Konfigurationsdatei zur Speicherung von Einstellungen.
# Sensible Daten (API-Token etc.) werden aus der .env Datei geladen.
#
# SETUP:
# 1. Erstelle eine Datei namens '.env' im Projektordner mit folgendem Inhalt:
#    APIFY_API_TOKEN=dein_echter_token_hier
#    ACTOR_ID=deine_actor_id_hier
# 2. Kopiere diese Datei als 'config.py'

import os
from dotenv import load_dotenv

# Lade Umgebungsvariablen aus der .env-Datei
load_dotenv()

# API-Token und Actor-ID aus Umgebungsvariablen lesen
APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN", "DEIN_APIFY_API_TOKEN")
ACTOR_ID = os.getenv("ACTOR_ID", "DEIN_ACTOR_ID")

# Standard-Input-Parameter für den Apify Actor.
# Diese werden für jeden Lauf als Basis verwendet und dann mit den
# spezifischen Daten aus der CSV-Datei (search_string, postal_code) ergänzt.
DEFAULT_ACTOR_INPUT = {
    "countryCode": "ch",
    "includeWebResults": False,
    "language": "de",
    "maxCrawledPlacesPerSearch": 4, # Diese Zahl kann später angepasst werden.
    
    # ---- Effizienz-Einstellungen ----
    # aktivieren das Scrapen der Detailseite, da Daten wie Webseite und Öffnungszeiten benötigen werden.
    "scrapePlaceDetailPage": True,
    # Aktivieren das Scrapen von Kontakten, wenn Telefonnummer nötig ist.
    "scrapeContacts": True,
    
    # Deaktivieren alles, was NICHT benötigt wird:
    "maxReviews": 0,
    "maxImages": 0,
    "maxQuestions": 0,
    "scrapeReviewsPersonalData": False,
    "scrapeImageAuthors": False,
    "includeWebResults": False,
    "scrapeDirectories": False,
    "scrapeTableReservationProvider": False,
    "skipClosedPlaces": False, # Geschlossene Orte überspringen wir vorerst nicht
}

# Definiert die finalen Spalten, die in der optimierten CSV-Datei enthalten sein sollen.
# Die Reihenfolge der Spalten wird ebenfalls hier festgelegt.
FINAL_COLUMNS = [
    'SearchString',
    'PLZ',
    'Stadt',
    'KundenNr',
    'title',
    'address',
    'street',
    'postalCode',
    'city',
    'openingHours',
    'phone',
    'phoneUnformatted',
    'website',
    'permanentlyClosed',
    'temporarilyClosed',
    'cid',
    'placeId',
    'location'
]