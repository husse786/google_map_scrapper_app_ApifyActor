# apify_provider.py
# Die einzige Stelle im Projekt, die Apify-Feldnamen kennt.
#
# Nachfolger von apify_wrapper.py. Neu gegenüber dem alten Wrapper:
#   - Timeout pro Aufruf, 90 Sekunden (03_ENTSCHEIDUNGEN.md C)
#   - ein hängender oder abgebrochener Lauf wird wie ein leeres Ergebnis
#     behandelt: kein Retry, der Kunde landet in Datei ③
#   - der Lauf wird bei Zeitüberschreitung auf Apify wirklich abgebrochen,
#     damit er kein Kontingent weiterverbraucht
#   - Rückgabe sind Candidate-Objekte, keine Apify-Dictionaries

import copy
import logging

from apify_client import ApifyClient
from apify_client.errors import ApifyApiError

from place_provider import Candidate

logger = logging.getLogger(__name__)

# 03_ENTSCHEIDUNGEN.md C: Timeout pro API-Aufruf.
STANDARD_TIMEOUT_SEKUNDEN = 90

# Die Einstellungen des Actors. Sie standen bisher in config.py und wichen dort
# von config.template.py ab (Umbauplan §9). Hier sind die Werte, mit denen die
# 5'000 produktiven Kunden gelaufen sind — und nur noch an einer Stelle.
STANDARD_ACTOR_INPUT = {
    'countryCode': 'ch',
    'language': 'de',
    'maxCrawledPlacesPerSearch': 6,
    # Detailseite und Kontakte werden gebraucht: Webseite, Öffnungszeiten, Telefon.
    'scrapePlaceDetailPage': True,
    'scrapeContacts': True,
    # Einkaufszentren enthalten mehrere Betriebe; die sollen mitkommen.
    'scrapeDirectories': True,
    # Alles Übrige kostet nur Zeit und Geld.
    'includeWebResults': False,
    'maxReviews': 0,
    'maxImages': 0,
    'maxQuestions': 0,
    'scrapeReviewsPersonalData': False,
    'scrapeImageAuthors': False,
    'scrapeTableReservationProvider': False,
    'skipClosedPlaces': False,
}

# Apify-Feldname → Candidate-Feld. Diese Zuordnung ist der Grund, warum es
# dieses Modul gibt. Kein anderes Modul kennt die linke Spalte.
FELD_ZUORDNUNG = {
    'title': 'title',
    'street': 'street',
    'postalCode': 'postal_code',
    'city': 'city',
    'address': 'address',
    'placeId': 'place_id',
    'cid': 'cid',
    'location': 'location',
    'phone': 'phone',
    'phoneUnformatted': 'phone_unformatted',
    'website': 'website',
    'openingHours': 'opening_hours',
    'permanentlyClosed': 'permanently_closed',
    'temporarilyClosed': 'temporarily_closed',
}


class ApifyProvider:
    """Holt Kandidaten über den Apify-Actor (Modus A, Suche über Text)."""

    def __init__(self, api_token: str, actor_id: str, actor_input: dict = None,
                 timeout_sekunden: int = STANDARD_TIMEOUT_SEKUNDEN):
        self.actor_id = actor_id
        self.actor_input = actor_input if actor_input is not None else STANDARD_ACTOR_INPUT
        self.timeout_sekunden = timeout_sekunden
        try:
            self.client = ApifyClient(api_token)
            self.actor = self.client.actor(actor_id)
        except Exception as fehler:
            logger.error(f'Apify-Client liess sich nicht aufbauen: {fehler}')
            self.client = None
            self.actor = None

    # ------------------------------------------------------------------
    # Schnittstelle
    # ------------------------------------------------------------------

    def fetch_by_text(self, search_string: str, plz: str) -> list[Candidate]:
        """
        Sucht nach einem Text und liefert die Treffer als Candidate.

        Liefert eine leere Liste, wenn nichts gefunden wurde, der Aufruf in den
        Timeout lief oder Apify einen Fehler meldet. Der Aufrufer behandelt alle
        drei Fälle gleich: der Kunde landet in Datei ③ (03_ENTSCHEIDUNGEN.md C).
        """
        if not self.actor:
            logger.error('Apify-Client ist nicht einsatzbereit, Aufruf übersprungen.')
            return []

        run_input = copy.deepcopy(self.actor_input)
        run_input['searchStringsArray'] = [search_string]
        run_input['postalCode'] = str(plz)

        try:
            lauf = self.actor.call(
                run_input=run_input,
                timeout_secs=self.timeout_sekunden,
                wait_secs=self.timeout_sekunden,
                logger=None,
            )
        except ApifyApiError as fehler:
            logger.error(f'Apify meldet einen Fehler für "{search_string}": {fehler}')
            return []
        except Exception as fehler:
            logger.error(f'Unerwarteter Fehler bei "{search_string}": {fehler}')
            return []

        if not lauf:
            logger.error(f'Apify lieferte keinen Lauf für "{search_string}".')
            return []

        status = lauf.get('status')
        if status != 'SUCCEEDED':
            # Häufigster Fall: nach wait_secs läuft der Actor noch. Abbrechen,
            # sonst verbraucht er weiter Kontingent, obwohl niemand wartet.
            logger.warning(f'Apify-Lauf für "{search_string}" endete mit Status '
                           f'{status} statt SUCCEEDED, wird als leeres Ergebnis '
                           f'behandelt.')
            self._lauf_abbrechen(lauf)
            return []

        try:
            rohdaten = list(self.client.dataset(lauf['defaultDatasetId']).iterate_items())
        except Exception as fehler:
            logger.error(f'Ergebnisse von Apify nicht lesbar für "{search_string}": {fehler}')
            return []

        kandidaten = [self.normalisieren(eintrag) for eintrag in rohdaten]
        kandidaten = [k for k in kandidaten if not k.ist_leer()]
        logger.info(f'Apify: {len(kandidaten)} Treffer für "{search_string}".')
        return kandidaten

    def fetch_by_id(self, place_id: str) -> Candidate | None:
        """Modus B läuft über GoogleProvider (Phase 6), nicht über Apify."""
        raise NotImplementedError(
            'ApifyProvider beherrscht nur die Textsuche. Der Abruf über placeId '
            'gehört zum GoogleProvider.')

    # ------------------------------------------------------------------
    # Innereien
    # ------------------------------------------------------------------

    @staticmethod
    def normalisieren(rohdaten: dict) -> Candidate:
        """Aus einem Apify-Dictionary wird ein Candidate. Unbekannte Felder entfallen."""
        werte = {ziel: rohdaten.get(quelle) for quelle, ziel in FELD_ZUORDNUNG.items()}
        return Candidate(**werte)

    def _lauf_abbrechen(self, lauf: dict) -> None:
        lauf_id = lauf.get('id')
        if not lauf_id:
            return
        try:
            self.client.run(lauf_id).abort()
            logger.info(f'Apify-Lauf {lauf_id} abgebrochen.')
        except Exception as fehler:
            logger.warning(f'Apify-Lauf {lauf_id} liess sich nicht abbrechen: {fehler}')


def aus_konfiguration(timeout_sekunden: int = STANDARD_TIMEOUT_SEKUNDEN) -> ApifyProvider:
    """
    Baut den Provider aus Token und Actor-Id der Konfiguration.

    Die Actor-Einstellungen kommen aus diesem Modul, nicht aus config.py — sonst
    kennt die Konfiguration Apify-Feldnamen. Ohne Token ist das ein Fehler mit
    einer Meldung, die sagt, was zu tun ist.
    """
    import config

    token = getattr(config, 'APIFY_API_TOKEN', '')
    actor_id = getattr(config, 'ACTOR_ID', '')
    if not token or token.startswith('DEIN_'):
        raise ValueError('In der Datei .env fehlt der Eintrag APIFY_API_TOKEN.')
    if not actor_id or actor_id.startswith('DEIN_'):
        raise ValueError('In der Datei .env fehlt der Eintrag ACTOR_ID.')

    return ApifyProvider(token, actor_id, timeout_sekunden=timeout_sekunden)
