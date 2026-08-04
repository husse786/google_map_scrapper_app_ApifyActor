# place_provider.py
# Die Schnittstelle zwischen Datenquelle und Fachlogik (02_DATENVERTRAG.md §7).
#
# Ein Provider liefert Kandidaten, sonst nichts. Wie er sie beschafft — Apify,
# Google Place Details, eine Datei mit festen Antworten — bleibt in ihm.
# Ausserhalb eines Providers kennt kein Modul die Feldnamen einer Datenquelle.

from dataclasses import dataclass, fields
from typing import Protocol

# Candidate-Feld → Spaltenname der Ausgabedatei (02_DATENVERTRAG.md §2).
# Die Spaltennamen stehen im Datenvertrag, nicht in einer Datenquelle: beide
# Provider liefern dieselben Spalten.
CSV_FELDER = {
    'title': 'title',
    'address': 'address',
    'street': 'street',
    'postal_code': 'postalCode',
    'city': 'city',
    'opening_hours': 'openingHours',
    'phone': 'phone',
    'phone_unformatted': 'phoneUnformatted',
    'website': 'website',
    'permanently_closed': 'permanentlyClosed',
    'temporarily_closed': 'temporarilyClosed',
    'cid': 'cid',
    'place_id': 'placeId',
    'location': 'location',
}


def als_text(wert) -> str:
    """
    Macht aus einem beliebigen Wert der Datenquelle einen Text.

    Zahlen, Wahrheitswerte, Listen und Dictionaries werden so geschrieben, wie
    Pandas sie bisher in die CSV geschrieben hat — sonst wären die Ausgabedateien
    nach dem Umbau anders als vorher. Fehlende Werte werden zu einer leeren
    Zeichenkette, nie zu "None" oder "nan".
    """
    if wert is None:
        return ''
    if isinstance(wert, str):
        return wert
    return str(wert)


@dataclass
class Candidate:
    """
    Ein Treffer einer Datenquelle, normalisiert.

    Felder und Reihenfolge wie die Tabelle `kandidat` in 02_DATENVERTRAG.md §5,
    ohne `id`, `kunde_id`, `score`, `entscheid` und `grund` — die entstehen erst
    bei der Entscheidung. Alle Werte sind Text; die Datenbankspalten sind TEXT
    und die CSV kennt ohnehin nur Text.
    """

    title: str = ''
    street: str = ''
    postal_code: str = ''
    city: str = ''
    address: str = ''
    place_id: str = ''
    cid: str = ''
    location: str = ''
    phone: str = ''
    phone_unformatted: str = ''
    website: str = ''
    opening_hours: str = ''
    permanently_closed: str = ''
    temporarily_closed: str = ''

    def __post_init__(self):
        # Ein Provider darf Zahlen oder Wahrheitswerte liefern; ab hier ist alles Text.
        for feld in fields(self):
            setattr(self, feld.name, als_text(getattr(self, feld.name)))

    def als_ausgabezeile(self) -> dict:
        """Die vierzehn Kandidatenspalten der Ausgabedatei (02_DATENVERTRAG.md §2)."""
        return {spalte: getattr(self, feld) for feld, spalte in CSV_FELDER.items()}

    def ist_leer(self) -> bool:
        """Wie `DataCleaner._is_empty_result`: kein Titel, keine Adresse, keine Id."""
        return not any(str(wert).strip() for wert in
                       (self.title, self.address, self.street, self.place_id))


def leere_ausgabezeile() -> dict:
    """Die vierzehn Kandidatenspalten, alle leer — für Kunden ohne jeden Treffer."""
    return {spalte: '' for spalte in CSV_FELDER.values()}


def candidate_aus_zeile(zeile) -> Candidate:
    """
    Baut einen Candidate aus einer Zeile der Tabelle `kandidat`.

    Gebraucht bei der Wiederaufnahme: die Treffer eines bereits verarbeiteten
    Kunden stehen in der Datenbank und müssen nicht erneut geholt werden.
    """
    return Candidate(**{feld.name: zeile[feld.name] for feld in fields(Candidate)})


class QuelleNichtVerfuegbar(Exception):
    """
    Die Datenquelle kann nicht liefern — und zwar nicht nur für diesen Kunden.

    Der Unterschied zu einem leeren Ergebnis ist wichtig: ein Kunde ohne
    Treffer gehört nach ③. Ein erschöpftes Kontingent dagegen macht jeden
    weiteren Kunden ebenfalls leer — dann sähe ein Lauf aus wie ein Ergebnis,
    obwohl er keines ist. Solche Fälle beenden den Lauf mit `FEHLER`.

    `meldung` ist für den Nutzer bestimmt: deutsch, mit Handlungsanweisung.
    `endgueltig` heisst, dass Weitermachen nichts bringt (Kontingent, Token).
    Ist es False, verträgt der Lauf einige Fehlschläge hintereinander, bevor
    er aufgibt — ein kurzer Netzaussetzer soll keinen Lauf über Stunden töten.
    """

    def __init__(self, meldung: str, endgueltig: bool = True):
        super().__init__(meldung)
        self.meldung = meldung
        self.endgueltig = endgueltig


class PlaceProvider(Protocol):
    """Was eine Datenquelle können muss (02_DATENVERTRAG.md §7)."""

    def fetch_by_text(self, search_string: str, plz: str) -> list[Candidate]:
        ...

    def fetch_by_id(self, place_id: str) -> Candidate | None:
        ...
