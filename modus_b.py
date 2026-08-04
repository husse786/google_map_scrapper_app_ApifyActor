# modus_b.py
# Auffrischen über die gespeicherte Google-ID (02_DATENVERTRAG.md §1, Modus B).
#
# Hier wird nichts gesucht und nichts bewertet. Ein Kunde, eine ID, ein
# Ergebnis. Die ID ist die Identität: was Google dazu liefert, ist per
# Definition derselbe Betrieb. Geprüft wird nur, ob dieser Betrieb noch offen
# ist und noch am selben Ort steht (03_ENTSCHEIDUNGEN.md B4).
#
# Ausdrücklich **kein** Prüffall ist eine Namensänderung: aus Volg wird Spar,
# der Betrieb bleibt derselbe. Rebranding ist normal.

import ast
import logging
import math
import re

from place_provider import leere_ausgabezeile

logger = logging.getLogger(__name__)

# 03_ENTSCHEIDUNGEN.md B4: ab dieser Entfernung ist es ein anderes Gebäude.
MAX_ABWEICHUNG_METER = 200

# Erdradius in Metern, für die Haversine-Formel.
ERDRADIUS_METER = 6_371_000

# Die ID ist die Identität — es gibt nichts zu schätzen. Der Wert steht in
# jeder Ausgabezeile, weil der Datenvertrag ihn verlangt (§2).
SCORE_MIT_ID = 100.0
SCORE_OHNE_TREFFER = 0.0

WAHR = {'true', 'wahr', 'ja', '1'}


# ==========================================================================
# Hilfen
# ==========================================================================

def ist_wahr(wert) -> bool:
    """Google und Apify schreiben Wahrheitswerte unterschiedlich."""
    return str(wert).strip().lower() in WAHR


def koordinaten(text) -> tuple:
    """
    Holt Breite und Länge aus dem gespeicherten Standort.

    Der Standort steht als Text in der Datenbank (`kandidat.location` ist TEXT),
    in der Schreibweise `{'lat': 47.35, 'lng': 8.24}`. Was sich nicht lesen
    lässt, gilt als nicht vorhanden — dann findet keine Distanzprüfung statt.
    """
    if text in (None, ''):
        return None
    if isinstance(text, dict):
        werte = text
    else:
        try:
            werte = ast.literal_eval(str(text))
        except (ValueError, SyntaxError):
            zahlen = re.findall(r'-?\d+\.?\d*', str(text))
            return (float(zahlen[0]), float(zahlen[1])) if len(zahlen) >= 2 else None
    if not isinstance(werte, dict):
        return None
    try:
        return float(werte['lat']), float(werte['lng'])
    except (KeyError, TypeError, ValueError):
        return None


def als_zahl(wert):
    """Wandelt eine Eingabespalte in eine Zahl. Leer bleibt leer."""
    text = str(wert).strip().replace(',', '.')
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def entfernung_meter(punkt_a: tuple, punkt_b: tuple) -> float:
    """Luftlinie zwischen zwei Koordinaten in Metern (Haversine)."""
    breite_a, laenge_a = math.radians(punkt_a[0]), math.radians(punkt_a[1])
    breite_b, laenge_b = math.radians(punkt_b[0]), math.radians(punkt_b[1])

    d_breite = breite_b - breite_a
    d_laenge = laenge_b - laenge_a
    a = (math.sin(d_breite / 2) ** 2
         + math.cos(breite_a) * math.cos(breite_b) * math.sin(d_laenge / 2) ** 2)
    return 2 * ERDRADIUS_METER * math.asin(min(1.0, math.sqrt(a)))


def entfernung_in_worten(meter: float) -> str:
    """850.3 → «850 m», 1432 → «1.4 km». Schreibweise wie im Datenvertrag §4."""
    if meter < 1000:
        return f'{round(meter)} m'
    return f'{meter / 1000:.1f} km'


# ==========================================================================
# Die Entscheidung
# ==========================================================================

def entscheide_kunde(kunden_nr: str, stamm: dict, kandidat) -> dict:
    """
    Entscheidet einen Kunden im Modus B.

    Reihenfolge nach 03_ENTSCHEIDUNGEN.md B4:
        keine ID in der Eingabe  → ③ NICHT_MOEGLICH (Eingabe unbrauchbar)
        ID liefert nichts        → ③ NICHT_MOEGLICH (ID ungueltig)
        dauerhaft geschlossen    → ② PRUEFUNG (geschlossen)
        weiter als 200 m weg     → ② PRUEFUNG (Standort abweichend)
        sonst                    → ① OK (ID)

    Returns dasselbe wie `DataCleaner.entscheide_kunde`: vier Listen, von denen
    genau eine der ersten drei gefüllt ist.
    """
    place_id = str(stamm.get('placeId', '')).strip()
    ablage = {'fertig_fuer_erp': [], 'zur_pruefung': [],
              'nicht_moeglich': [], 'aussortiert': []}

    if not place_id:
        ablage['nicht_moeglich'].append(_zeile(
            kunden_nr, stamm, None, 'NICHT_MOEGLICH (Eingabe unbrauchbar)',
            SCORE_OHNE_TREFFER,
            'In dieser Zeile fehlt die Google-ID. Ohne sie ist kein Abruf möglich.'))
        return ablage

    if kandidat is None:
        ablage['nicht_moeglich'].append(_zeile(
            kunden_nr, stamm, None, 'NICHT_MOEGLICH (ID ungueltig)',
            SCORE_OHNE_TREFFER,
            'Zur gespeicherten Google-ID gibt es keinen Eintrag mehr. '
            'Der Betrieb wurde bei Google gelöscht oder durch einen neuen '
            'Eintrag ersetzt.'))
        return ablage

    titel = kandidat.title or 'ohne Namen'

    if ist_wahr(kandidat.permanently_closed):
        ablage['zur_pruefung'].append(_zeile(
            kunden_nr, stamm, kandidat, 'PRUEFUNG (geschlossen)', SCORE_MIT_ID,
            f'Google meldet den Betrieb als dauerhaft geschlossen: "{titel}".'))
        return ablage

    abweichung = _abweichung(stamm, kandidat)

    if abweichung is not None and abweichung > MAX_ABWEICHUNG_METER:
        ablage['zur_pruefung'].append(_zeile(
            kunden_nr, stamm, kandidat, 'PRUEFUNG (Standort abweichend)',
            SCORE_MIT_ID,
            f'Standort liegt {entfernung_in_worten(abweichung)} von der '
            f'gespeicherten Position entfernt: "{titel}", '
            f'{kandidat.address or "ohne Adresse"}.'))
        return ablage

    # Ein anderer Name ist ausdrücklich kein Prüffall (03_ENTSCHEIDUNGEN.md B4).
    grund = (f'Über die gespeicherte Google-ID geholt: "{titel}", '
             f'{kandidat.address or "ohne Adresse"}.')
    if abweichung is not None:
        grund += (f' Der Standort stimmt, Abweichung '
                  f'{entfernung_in_worten(abweichung)}.')
    else:
        grund += ' Zur gespeicherten Position gibt es keine Angabe zum Vergleichen.'

    ablage['fertig_fuer_erp'].append(_zeile(
        kunden_nr, stamm, kandidat, 'OK (ID)', SCORE_MIT_ID, grund))
    return ablage


def _abweichung(stamm: dict, kandidat):
    """
    Wie weit ist der gefundene Betrieb von der gespeicherten Position entfernt?

    None heisst: nicht vergleichbar. Fehlen `lat`/`lng` in der Eingabe, findet
    keine Distanzprüfung statt und es entsteht kein Prüffall (03 B4). Dasselbe
    gilt, wenn Google keinen Standort liefert.
    """
    breite = als_zahl(stamm.get('lat', ''))
    laenge = als_zahl(stamm.get('lng', ''))
    if breite is None or laenge is None:
        return None

    gefunden = koordinaten(kandidat.location)
    if gefunden is None:
        return None

    return entfernung_meter((breite, laenge), gefunden)


def _zeile(kunden_nr: str, stamm: dict, kandidat, qualitaet: str, score: float,
           grund: str) -> dict:
    """
    Eine Ausgabezeile, gleich aufgebaut wie im Modus A.

    Die Spalten `SearchString`, `PLZ` und `Stadt` gibt es in der Eingabe des
    Modus B nicht; sie bleiben leer. Der Aufbau der Datei ist derselbe, damit
    beide Modi denselben Import füttern (02_DATENVERTRAG.md §2).
    """
    zeile = {
        'KundenNr': kunden_nr,
        'SearchString': '',
        'PLZ': '',
        'Stadt': '',
    }
    zeile.update(kandidat.als_ausgabezeile() if kandidat else leere_ausgabezeile())
    if not zeile.get('placeId'):
        zeile['placeId'] = str(stamm.get('placeId', '')).strip()
    zeile['qualitaet'] = qualitaet
    zeile['score'] = round(float(score), 2)
    zeile['grund'] = grund
    return zeile
