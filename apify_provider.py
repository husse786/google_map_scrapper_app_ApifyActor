# apify_provider.py
# Die einzige Stelle im Projekt, die Apify-Feldnamen kennt.
#
# Nachfolger von apify_wrapper.py. Neu gegenüber dem alten Wrapper:
#   - Timeout pro Aufruf, 180 Sekunden (03_ENTSCHEIDUNGEN.md C)
#   - ein hängender oder abgebrochener Lauf wird wie ein leeres Ergebnis
#     behandelt: kein Retry, der Kunde landet in Datei ③
#   - der Lauf wird bei Zeitüberschreitung auf Apify wirklich abgebrochen,
#     damit er kein Kontingent weiterverbraucht
#   - Rückgabe sind Candidate-Objekte, keine Apify-Dictionaries

import copy
import logging
import threading

from apify_client import ApifyClient
from apify_client.errors import ApifyApiError

from place_provider import Candidate, QuelleNichtVerfuegbar

logger = logging.getLogger(__name__)

# 03_ENTSCHEIDUNGEN.md C: Timeout pro API-Aufruf. Von 90 auf 180 Sekunden
# heraufgesetzt, nachdem gemessene Kaltstarts bei 83, 87 und 91 Sekunden lagen —
# 90 Sekunden hätten gesunde Aufrufe fälschlich nach ③ geschoben.
STANDARD_TIMEOUT_SEKUNDEN = 180

# Sekunden, die von der Frist abgezogen werden, damit dieser Provider vor dem
# Notschalter im Lauf zum Zug kommt. Der Lauf schneidet jeden Aufruf nach
# STANDARD_TIMEOUT_SEKUNDEN ab, egal welcher Provider dahintersteht. Ohne
# diesen Vorsprung wäre der Provider immer der Zweite: er käme nie dazu, den
# überzogenen Apify-Lauf abzubrechen, und der liefe auf Kosten des Kontingents
# weiter. Beobachtet am 03.08.2026 bei einem Lauf, der 91 Sekunden brauchte.
RESERVE_SEKUNDEN = 5

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

# Fehler, bei denen Weitermachen nichts bringt. Apify benennt sie in
# `error.type`; der Text daneben ist das, was der Sachbearbeiter zu lesen
# bekommt — mit einer Handlungsanweisung, nicht mit einer Fehlernummer.
ENDGUELTIGE_FEHLER = {
    'monthly-usage-hard-limit-exceeded':
        'Das monatliche Guthaben bei Apify ist aufgebraucht. Der Lauf wurde '
        'gestoppt, damit keine halben Ergebnisse entstehen. Bitte das Guthaben '
        'aufstocken oder bis zum nächsten Abrechnungsmonat warten, dann den '
        'Lauf fortsetzen.',
    'usage-limit-exceeded':
        'Das eingestellte Ausgabenlimit bei Apify ist erreicht. Der Lauf wurde '
        'gestoppt. Bitte das Limit im Apify-Konto anheben, dann den Lauf '
        'fortsetzen.',
    'insufficient-permissions':
        'Der Apify-Zugang hat nicht die nötigen Rechte. Bitte prüfen, ob der '
        'Token noch gültig ist und zum richtigen Konto gehört.',
    'token-not-provided':
        'Es ist kein Apify-Token hinterlegt. Bitte den Eintrag '
        'APIFY_API_TOKEN in der Datei .env prüfen.',
    'invalid-token':
        'Der Apify-Token wird nicht akzeptiert. Bitte den Eintrag '
        'APIFY_API_TOKEN in der Datei .env prüfen und bei Bedarf im '
        'Apify-Konto einen neuen erzeugen.',
    'actor-not-found':
        'Der eingestellte Apify-Actor ist nicht auffindbar. Bitte den Eintrag '
        'ACTOR_ID in der Datei .env prüfen.',
}

# Wortfetzen für den Fall, dass Apify keinen Typ mitschickt.
ENDGUELTIGE_WORTE = ('usage limit', 'hard limit', 'credit', 'quota',
                     'unauthorized', 'invalid token', 'not authorized')

NETZ_MELDUNG = (
    'Apify ist nicht erreichbar. Meistens liegt es an der Internetverbindung '
    'dieses Rechners. Bitte die Verbindung prüfen und den Lauf danach '
    'fortsetzen — die bereits verarbeiteten Kunden bleiben erhalten.')

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
        # Die Frist, die Apify tatsächlich bekommt: etwas kürzer als die des
        # Laufs, damit dieser Provider selbst entscheidet und aufräumt.
        self.wartezeit = max(5, int(timeout_sekunden) - RESERVE_SEKUNDEN)
        # Läufe, die gerade bei Apify rechnen. Der Abbruch-Knopf muss sie
        # erreichen, sonst laufen sie auf Kosten des Kontingents weiter.
        self._laufende = set()
        self._sperre = threading.Lock()
        self._abgebrochen = False
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
        if self._abgebrochen:
            return []

        run_input = copy.deepcopy(self.actor_input)
        run_input['searchStringsArray'] = [search_string]
        run_input['postalCode'] = str(plz)

        # Erst starten, dann warten — nicht in einem Rutsch. Nur so ist die
        # Lauf-Nummer bekannt, solange der Lauf noch rechnet, und nur so kann
        # der Abbruch-Knopf ihn erreichen.
        lauf_id = None
        try:
            lauf = self.actor.start(run_input=run_input,
                                    timeout_secs=self.wartezeit)
            lauf_id = lauf.get('id') if lauf else None
            if not lauf_id:
                logger.error(f'Apify lieferte keine Lauf-Nummer für "{search_string}".')
                return []

            with self._sperre:
                if self._abgebrochen:
                    self.client.run(lauf_id).abort()
                    return []
                self._laufende.add(lauf_id)

            fertig = self.client.run(lauf_id).wait_for_finish(wait_secs=self.wartezeit)
        except ApifyApiError as fehler:
            logger.error(f'Apify meldet einen Fehler für "{search_string}": {fehler}')
            _pruefen_ob_endgueltig(fehler)
            return []
        except QuelleNichtVerfuegbar:
            raise
        except Exception as fehler:
            logger.error(f'Unerwarteter Fehler bei "{search_string}": {fehler}')
            raise QuelleNichtVerfuegbar(NETZ_MELDUNG, endgueltig=False) from fehler
        finally:
            with self._sperre:
                self._laufende.discard(lauf_id)

        status = (fertig or {}).get('status')
        if status != 'SUCCEEDED':
            # Häufigster Fall: nach wait_secs rechnet der Actor noch. Abbrechen,
            # sonst verbraucht er weiter Kontingent, obwohl niemand wartet.
            logger.warning(f'Apify-Lauf für "{search_string}" endete mit Status '
                           f'{status} statt SUCCEEDED, wird als leeres Ergebnis '
                           f'behandelt.')
            self._lauf_abbrechen(lauf_id)
            return []

        try:
            rohdaten = list(
                self.client.dataset(fertig['defaultDatasetId']).iterate_items())
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

    def abbrechen(self) -> int:
        """
        Beendet alle Läufe, die gerade bei Apify rechnen.

        Wird vom Abbruch-Knopf gerufen. Ohne das rechnet Apify weiter und
        stellt in Rechnung, was niemand mehr abholt. Weitere Aufrufe dieses
        Providers liefern sofort nichts mehr zurück.
        """
        with self._sperre:
            self._abgebrochen = True
            offene = list(self._laufende)
            self._laufende.clear()

        for lauf_id in offene:
            self._lauf_abbrechen(lauf_id)
        return len(offene)

    def _lauf_abbrechen(self, lauf_id: str) -> None:
        if not lauf_id:
            return
        try:
            self.client.run(lauf_id).abort()
            logger.info(f'Apify-Lauf {lauf_id} abgebrochen.')
        except Exception as fehler:
            logger.warning(f'Apify-Lauf {lauf_id} liess sich nicht abbrechen: {fehler}')


def _pruefen_ob_endgueltig(fehler: ApifyApiError) -> None:
    """
    Ist das ein Fehler, nach dem Weitermachen sinnlos ist?

    Dann wird er weitergereicht und beendet den Lauf mit einer Erklärung.
    Alles andere gilt als Fehlschlag bei diesem einen Kunden — er landet in ③.
    """
    art = str(getattr(fehler, 'type', '') or '')
    if art in ENDGUELTIGE_FEHLER:
        raise QuelleNichtVerfuegbar(ENDGUELTIGE_FEHLER[art])

    text = str(getattr(fehler, 'message', '') or fehler).lower()
    if any(wort in text for wort in ENDGUELTIGE_WORTE):
        raise QuelleNichtVerfuegbar(ENDGUELTIGE_FEHLER['usage-limit-exceeded'])


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
