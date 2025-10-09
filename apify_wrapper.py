# apify_wrapper.py
# Dieses Modul kapselt die gesamte Kommunikation mit der Apify API.

import copy
from typing import List, Dict
from apify_client import ApifyClient
from apify_client.errors import ApifyApiError
from logger_config import logger

# Wir importieren unsere Konfiguration, um Zugriff auf Token, ID und Standard-Input zu haben
import config

class ApifyClientWrapper:
    """
    Eine Wrapper-Klasse für den ApifyClient, um die Actor-Aufrufe zu vereinfachen.
    """
    def __init__(self, api_token: str, actor_id: str):
        """
        Initialisiert den Apify Client.
        """
        try:
            self.client = ApifyClient(api_token)  # Initialisiere den Apify Client
            self.actor = self.client.actor(actor_id) # Greife auf den spezifischen Actor zu
            logger.info("Apify Client erfolgreich initialisiert.")
        except Exception as e:
            logger.error(f"Fehler bei der Initialisierung des Apify Clients: {e}")
            self.client = None
            self.actor = None

    def run_scraper_and_get_results(self, search_string: str, postal_code: str) -> List[Dict]:  # Starte den Scraper und hole die Ergebnisse
        """
        Startet einen Actor-Run, wartet auf dessen Abschluss und holt die Ergebnisse.
        """
        if not self.actor:
            logger.error("Apify Client wurde nicht korrekt initialisiert. Breche Lauf ab.")
            return []

        logger.info(f"\nStarte Scraper für: '{search_string}' in PLZ '{postal_code}'...")
        
        try:
            run_input = copy.deepcopy(config.DEFAULT_ACTOR_INPUT) # Kopiere den Standard-Input
            run_input["searchStringsArray"] = [search_string] # Setze den Suchstring
            run_input["postalCode"] = str(postal_code) # Setze die PLZ

            run = self.actor.call(run_input=run_input)
            
            logger.info(f"Lauf für '{search_string}' beendet. Lade Ergebnisse...")

            results = list(self.client.dataset(run["defaultDatasetId"]).iterate_items())
            logger.info(f"{len(results)} Ergebnisse gefunden.")
            return results

        except ApifyApiError as e:
            logger.error(f"Ein API-Fehler ist aufgetreten bei '{search_string}': {e}")
            return []
        except Exception as e:
            logger.error(f"Ein unerwarteter Fehler ist aufgetreten bei '{search_string}': {e}")
            return []