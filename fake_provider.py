# fake_provider.py
# Ein Provider mit festen Antworten aus einer Datei.
#
# Damit laufen alle Phasen ab hier ohne Apify-Kosten und ohne Netz. Die
# Antwortdatei hat dasselbe Format wie eine angereicherte CSV: Suchbegriff und
# PLZ links, die Treffer rechts. Eine Zeile ohne Treffer bedeutet "nichts
# gefunden" — der Kunde landet dann in Datei ③.

import logging

import pandas as pd

from place_provider import CSV_FELDER, Candidate

logger = logging.getLogger(__name__)


class FakeProvider:
    """Liefert vorher festgelegte Treffer. Kein Netzzugriff."""

    def __init__(self, antworten: dict = None):
        # Schlüssel: (Suchbegriff, PLZ) → Liste von Candidate
        self.antworten = antworten or {}
        self._nach_id = {k.place_id: k
                         for treffer in self.antworten.values()
                         for k in treffer if k.place_id}

    # ------------------------------------------------------------------
    # Aufbau
    # ------------------------------------------------------------------

    @classmethod
    def aus_csv(cls, pfad: str) -> 'FakeProvider':
        """
        Liest eine Antwortdatei im Format einer angereicherten CSV.

        Pflichtspalten: SearchString, PLZ. Alles Weitere sind Kandidatenspalten
        nach 02_DATENVERTRAG.md §2; was fehlt, bleibt leer.
        """
        df = pd.read_csv(pfad, sep=';', encoding='utf-8-sig', dtype=str).fillna('')
        for spalte in ('SearchString', 'PLZ'):
            if spalte not in df.columns:
                raise ValueError(f'In der Antwortdatei fehlt die Spalte "{spalte}".')

        antworten = {}
        for _, zeile in df.iterrows():
            schluessel = (str(zeile['SearchString']).strip(), str(zeile['PLZ']).strip())
            antworten.setdefault(schluessel, [])
            kandidat = cls._zeile_als_candidate(zeile)
            if not kandidat.ist_leer():
                antworten[schluessel].append(kandidat)

        logger.info(f'FakeProvider: {len(antworten)} Suchbegriffe aus {pfad} geladen.')
        return cls(antworten)

    @staticmethod
    def _zeile_als_candidate(zeile) -> Candidate:
        werte = {feld: zeile.get(spalte, '') for feld, spalte in CSV_FELDER.items()}
        return Candidate(**werte)

    # ------------------------------------------------------------------
    # Schnittstelle
    # ------------------------------------------------------------------

    def fetch_by_text(self, search_string: str, plz: str) -> list[Candidate]:
        schluessel = (str(search_string).strip(), str(plz).strip())
        treffer = self.antworten.get(schluessel)
        if treffer is None:
            logger.info(f'FakeProvider kennt "{search_string}" nicht, liefert nichts.')
            return []
        return list(treffer)

    def fetch_by_id(self, place_id: str) -> Candidate | None:
        return self._nach_id.get(str(place_id).strip())
