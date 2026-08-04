# google_provider.py
# Die zweite Datenquelle: Google Place Details (Modus B).
#
# Neben apify_provider.py ist dies die einzige Stelle, die Feldnamen einer
# Datenquelle kennt. Nach aussen liefert sie dasselbe wie jeder andere
# Provider: einen `Candidate` (02_DATENVERTRAG.md §7).
#
# Verwendet wird die Places API (New), Endpunkt "Place Details". Abgefragt
# werden nur die Felder, die im Datenvertrag stehen — jedes zusätzliche Feld
# kostet Geld, ohne dass es jemand liest.

import logging

import requests

from place_provider import Candidate

logger = logging.getLogger(__name__)

BASIS_URL = 'https://places.googleapis.com/v1/places'

# 03_ENTSCHEIDUNGEN.md C: Timeout pro Aufruf. Ein Direktabruf über die ID
# antwortet in Sekundenbruchteilen; die Frist ist eine Notbremse, kein Richtwert.
STANDARD_TIMEOUT_SEKUNDEN = 30

# Nur diese Felder werden geholt. Die Reihenfolge folgt Candidate.
FELDMASKE = ','.join([
    'id',
    'displayName',
    'formattedAddress',
    'addressComponents',
    'location',
    'nationalPhoneNumber',
    'internationalPhoneNumber',
    'websiteUri',
    'regularOpeningHours.weekdayDescriptions',
    'businessStatus',
])

# Google-Adressbestandteil → Candidate-Feld
STRASSE = 'route'
HAUSNUMMER = 'street_number'
PLZ = 'postal_code'
ORT = 'locality'


class GoogleProvider:
    """Holt einen Betrieb über seine gespeicherte Google-ID (Modus B)."""

    def __init__(self, api_key: str,
                 timeout_sekunden: float = STANDARD_TIMEOUT_SEKUNDEN,
                 sprache: str = 'de'):
        self.api_key = api_key
        self.timeout_sekunden = timeout_sekunden
        self.sprache = sprache
        self._sitzung = requests.Session()

    # ------------------------------------------------------------------
    # Schnittstelle
    # ------------------------------------------------------------------

    def fetch_by_id(self, place_id: str):
        """
        Holt die aktuellen Daten zu einer Google-ID.

        Liefert `None`, wenn die ID unbekannt ist, der Abruf scheitert oder
        Google nichts zurückgibt. Der Aufrufer behandelt alle drei Fälle
        gleich: der Kunde landet in Datei ③ (03_ENTSCHEIDUNGEN.md B4).
        """
        kennung = str(place_id).strip()
        if not kennung:
            return None

        try:
            antwort = self._sitzung.get(
                f'{BASIS_URL}/{kennung}',
                headers={'X-Goog-Api-Key': self.api_key,
                         'X-Goog-FieldMask': FELDMASKE},
                params={'languageCode': self.sprache},
                timeout=self.timeout_sekunden)
        except requests.RequestException as fehler:
            logger.error(f'Google nicht erreichbar für "{kennung}": {fehler}')
            return None

        if antwort.status_code == 404:
            logger.info(f'Google kennt die Id "{kennung}" nicht mehr.')
            return None
        if antwort.status_code != 200:
            logger.error(f'Google antwortet mit {antwort.status_code} für '
                         f'"{kennung}": {antwort.text[:200]}')
            return None

        try:
            rohdaten = antwort.json()
        except ValueError:
            logger.error(f'Antwort von Google für "{kennung}" ist kein JSON.')
            return None

        if not rohdaten:
            return None
        return self.normalisieren(rohdaten)

    def fetch_by_text(self, search_string: str, plz: str) -> list:
        """Die Textsuche läuft über Apify, nicht über diesen Provider."""
        raise NotImplementedError(
            'GoogleProvider beherrscht nur den Abruf über die gespeicherte Id. '
            'Die Textsuche gehört zum ApifyProvider.')

    # ------------------------------------------------------------------
    # Innereien
    # ------------------------------------------------------------------

    @staticmethod
    def normalisieren(rohdaten: dict) -> Candidate:
        """Aus einer Google-Antwort wird ein Candidate."""
        bestandteile = _adressbestandteile(rohdaten.get('addressComponents') or [])
        standort = rohdaten.get('location') or {}
        status = str(rohdaten.get('businessStatus') or '')

        return Candidate(
            title=(rohdaten.get('displayName') or {}).get('text', ''),
            street=_strasse(bestandteile),
            postal_code=bestandteile.get(PLZ, ''),
            city=bestandteile.get(ORT, ''),
            address=rohdaten.get('formattedAddress', ''),
            place_id=rohdaten.get('id', ''),
            cid='',  # Die Places API liefert keine cid.
            location=_standort(standort),
            phone=rohdaten.get('nationalPhoneNumber', ''),
            phone_unformatted=rohdaten.get('internationalPhoneNumber', ''),
            website=rohdaten.get('websiteUri', ''),
            opening_hours=_oeffnungszeiten(rohdaten),
            permanently_closed=str(status == 'CLOSED_PERMANENTLY'),
            temporarily_closed=str(status == 'CLOSED_TEMPORARILY'),
        )


def _adressbestandteile(bestandteile: list) -> dict:
    """Aus der Liste der Adressbestandteile wird ein Nachschlagewerk."""
    gefunden = {}
    for eintrag in bestandteile:
        for art in eintrag.get('types', []):
            gefunden.setdefault(art, eintrag.get('longText')
                                or eintrag.get('shortText') or '')
    return gefunden


def _strasse(bestandteile: dict) -> str:
    """«Bahnhofstrasse» plus «12» wird zu «Bahnhofstrasse 12» — wie bei Apify."""
    name = bestandteile.get(STRASSE, '')
    nummer = bestandteile.get(HAUSNUMMER, '')
    return f'{name} {nummer}'.strip() if name else nummer


def _standort(standort: dict) -> str:
    """
    Dieselbe Schreibweise wie bei Apify: `{'lat': 47.35, 'lng': 8.24}`.

    Beide Modi schreiben identisch aufgebaute Ausgabedateien — dazu gehört,
    dass dieselbe Spalte gleich aussieht.
    """
    breite = standort.get('latitude')
    laenge = standort.get('longitude')
    if breite is None or laenge is None:
        return ''
    return str({'lat': breite, 'lng': laenge})


def _oeffnungszeiten(rohdaten: dict) -> str:
    zeiten = (rohdaten.get('regularOpeningHours') or {}).get('weekdayDescriptions')
    return str(zeiten) if zeiten else ''


def aus_konfiguration(timeout_sekunden: float = STANDARD_TIMEOUT_SEKUNDEN):
    """
    Baut den Provider aus dem Schlüssel in der Konfiguration.

    Fehlt er, ist das ein Fehler mit einer Meldung, die sagt, was zu tun ist —
    kein Stacktrace.
    """
    import config

    schluessel = getattr(config, 'GOOGLE_API_KEY', '')
    if not schluessel or schluessel.startswith('DEIN_'):
        raise ValueError(
            'In der Datei .env fehlt der Eintrag GOOGLE_API_KEY. '
            'Ohne ihn ist das Auffrischen über die Google-ID nicht möglich.')
    return GoogleProvider(schluessel, timeout_sekunden=timeout_sekunden)
