# config.py
# Zentrale Konfigurationsdatei zur Speicherung von API-Schlüsseln und Einstellungen.

# WICHTIG: Ersetze "DEIN_APIFY_API_TOKEN" durch deinen echten API-Token von Apify.
APIFY_API_TOKEN = "Dein Apify API Token hier"

# Die ID des Google Maps Scraper Actors. Diese findest du auf der Apify-Seite des Actors.
# Beispiel: "apify/google-maps-scraper"
ACTOR_ID = "Dein Actor ID hier"

# Standard-Input-Parameter für den Apify Actor.
# Diese werden für jeden Lauf als Basis verwendet und dann mit den
# spezifischen Daten aus der CSV-Datei (search_string, postal_code) ergänzt.
DEFAULT_ACTOR_INPUT = {
    "countryCode": "ch",
    "includeWebResults": False,
    "language": "de",
    "maxCrawledPlacesPerSearch": 4, # Diese Zahl kann später angepasst werden.
    # ---- Effizienz-Einstellungen ----
    # Wir aktivieren das Scrapen der Detailseite, da wir Daten wie Webseite und Öffnungszeiten benötigen.
    "scrapePlaceDetailPage": True,
    # Wir aktivieren das Scrapen von Kontakten, da wir die Telefonnummer wollen.
    "scrapeContacts": True,
    
    # Wir deaktivieren alles, was wir NICHT brauchen:
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