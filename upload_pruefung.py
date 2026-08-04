# upload_pruefung.py
# Prüft eine hochgeladene Datei, bevor der Lauf startet (03_ENTSCHEIDUNGEN.md D).
#
# Der Zweck ist eine einzige Frage: Was wird an dieser Datei schiefgehen, und
# zwar bevor der Lauf beginnt.
#
# Zur Wirkung: Die Messung in Phase 4 hat die ursprüngliche Erwartung widerlegt.
# Auf zwei realen Batches trafen die beiden inhaltlichen Prüfungen 14 und 11
# Zeilen von je 2'513 — die Prüffälle entstehen fast alle woanders. Die
# Prüfungen bleiben trotzdem: sie kosten nichts und melden echte Eingabefehler.
#
# Zwei der drei Prüfungen aus 03_ENTSCHEIDUNGEN.md D **warnen**: der Nutzer
# entscheidet, ob er trotzdem läuft.
#
# Abgewiesen wird in zwei Fällen:
#   - eine fehlende Pflichtspalte (03_ENTSCHEIDUNGEN.md D, geändert nach
#     Phase 4). Ohne SearchString, PLZ oder KundenNr kann der Lauf nicht
#     arbeiten — eine wegklickbare Warnung führt nur in eine Sackgasse.
#   - eine Datei über der Zeilenobergrenze (03_ENTSCHEIDUNGEN.md C).

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from data_cleaner import DataCleaner

logger = logging.getLogger(__name__)

# 02_DATENVERTRAG.md §1
PFLICHTSPALTEN = ('SearchString', 'PLZ', 'KundenNr')
PFLICHTSPALTEN_JE_MODUS = {
    'A': ('SearchString', 'PLZ', 'KundenNr'),
    'B': ('placeId', 'KundenNr'),
}
KOPFZEILE_VORLAGE = 'SearchString;PLZ;Stadt;KundenNr'
KOPFZEILE_JE_MODUS = {
    'A': 'SearchString;PLZ;Stadt;KundenNr',
    'B': 'placeId;lat;lng;KundenNr',
}

# 03_ENTSCHEIDUNGEN.md C
MAX_ZEILEN = 10_000

# Erkennt eine Buchstabenfolge von mindestens vier Zeichen — auch mit Umlauten
# und französischen Akzenten. Fehlt sie im Strassenteil, steht dort keine
# Strasse (03_ENTSCHEIDUNGEN.md D).
BUCHSTABENFOLGE = re.compile(r'[A-Za-zÀ-ÿ]{4,}')
KOSTENSTELLEN_PRAEFIX = re.compile(r'^(kst|kost)', re.IGNORECASE)

# Wörter, die nur eine Kategorie benennen und keinen Betrieb.
#
# Grundlage ist die Liste aus dem Scoring (`GENERIC_FIRST_WORDS`). Sie ist rein
# deutschsprachig; für die Westschweiz und das Tessin reicht sie nicht — das
# Abnahmekriterium nennt ausdrücklich `Boucherie`. Die Scoring-Liste selbst
# bleibt unangetastet (03_ENTSCHEIDUNGEN.md B3), diese hier ist eine Obermenge
# und wird nur beim Hochladen verwendet.
#
# Alle Wörter stehen in der Schreibweise, die `_normalize_text` erzeugt:
# klein, Umlaute aufgelöst, Akzente entfernt.
ZUSAETZLICHE_KATEGORIE_WOERTER = {
    # Französisch
    'boucherie', 'boulangerie', 'patisserie', 'epicerie', 'alimentation',
    'brasserie', 'buvette', 'auberge', 'pharmacie', 'droguerie', 'magasin',
    'kiosque', 'tabac', 'coiffure', 'fromagerie', 'laiterie', 'traiteur',
    'cave', 'depot', 'station service',
    # Italienisch
    'macelleria', 'panetteria', 'pasticceria', 'alimentari', 'ristorante',
    'albergo', 'farmacia', 'osteria', 'trattoria',
    # Deutsch, in der Scoring-Liste nicht enthalten
    'lebensmittel', 'lebensmittelgeschaeft', 'imbiss', 'takeaway', 'take away',
    'dorfladen', 'quartierladen', 'getraenkemarkt', 'snack', 'tearoom',
}

KATEGORIE_WOERTER = set(DataCleaner.GENERIC_FIRST_WORDS) | ZUSAETZLICHE_KATEGORIE_WOERTER

# Schweregrade eines Befunds
HINWEIS = 'hinweis'        # warnt, blockiert nicht
ABWEISUNG = 'abweisung'    # die Datei kann so nicht laufen

_normalisierer = DataCleaner()


@dataclass
class Befund:
    """Ein Ergebnis der Prüfung, fertig zum Anzeigen."""

    art: str
    schwere: str
    anzahl: int
    meldung: str
    beispiel_zeile: str = ''
    zeilennummer: int = 0

    def als_text(self) -> str:
        text = self.meldung
        if self.beispiel_zeile:
            text += (f'\nBeispiel Zeile {zahl(self.zeilennummer)}: '
                     f'«{self.beispiel_zeile}»')
        return text


@dataclass
class Pruefbericht:
    """Was die Prüfung über eine Datei sagt."""

    dateiname: str
    zeilen: int = 0
    kunden: int = 0
    befunde: list = field(default_factory=list)
    modus: str = 'A'

    @property
    def start_moeglich(self) -> bool:
        """Fehlende Pflichtspalte und Zeilenobergrenze verhindern den Start."""
        return not any(b.schwere == ABWEISUNG for b in self.befunde)

    @property
    def hinweise(self) -> list:
        return [b for b in self.befunde if b.schwere == HINWEIS]

    def befund(self, art: str) -> Befund:
        """Der Befund einer Art, oder None."""
        for eintrag in self.befunde:
            if eintrag.art == art:
                return eintrag
        return None

    def als_text(self) -> str:
        zeilen = [f'Datei:  {self.dateiname}',
                  f'Kunden: {zahl(self.kunden)} ({zahl(self.zeilen)} Zeilen)']
        if not self.befunde:
            zeilen.append('')
            zeilen.append('Die Datei ist in Ordnung. Es ist nichts aufgefallen.')
            return '\n'.join(zeilen)

        for eintrag in self.befunde:
            zeilen.append('')
            zeilen.append(eintrag.als_text())

        zeilen.append('')
        if self.start_moeglich:
            zeilen.append('Der Lauf kann trotzdem gestartet werden. '
                          'Die genannten Zeilen landen voraussichtlich in der '
                          'Datei «zur Prüfung».')
        else:
            zeilen.append('Der Lauf kann so nicht gestartet werden.')
        return '\n'.join(zeilen)


def zahl(wert: int) -> str:
    """Schweizer Tausendertrennung: 2513 → 2'513."""
    return f'{wert:,}'.replace(',', "'")


# ==========================================================================
# Die einzelnen Prüfungen
# ==========================================================================

def strassenteil(search_string: str) -> str:
    """Der zweite kommagetrennte Teil: Strasse und Hausnummer."""
    teile = str(search_string).split(',')
    return teile[1].strip() if len(teile) >= 2 else ''


def titelteil(search_string: str) -> str:
    """Der erste kommagetrennte Teil: Name des Betriebs."""
    teile = str(search_string).split(',')
    return teile[0].strip() if teile else ''


def ist_kostenstelle(strasse: str) -> bool:
    """
    Steht im Strassenfeld etwas, das keine Strasse ist?

    Auslöser nach 03_ENTSCHEIDUNGEN.md D: keine Buchstabenfolge von vier
    Zeichen, oder der Text beginnt mit KST oder KOST.

        "KST 715611 0"      → ja, das ist eine Kostenstelle
        "Hauptstrasse 5"    → nein
        "Rue des Tilleuls 5" → nein
    """
    text = str(strasse).strip()
    if KOSTENSTELLEN_PRAEFIX.match(text):
        return True
    return not BUCHSTABENFOLGE.search(text)


def ist_kategorietitel(titel: str) -> bool:
    """
    Besteht der Name ausschliesslich aus Kategoriewörtern?

        "Boucherie"          → ja, das ist keine Firma, das ist eine Branche
        "Restaurant"         → ja
        "Restaurant Waldegg" → nein, "Waldegg" ist der Name
        "Denner"             → nein
    """
    normalisiert = _normalisierer._normalize_text(str(titel))
    woerter = [wort for wort in re.split(r'[^a-z0-9]+', normalisiert) if wort]
    if not woerter:
        return False
    return all(wort in KATEGORIE_WOERTER for wort in woerter)


# ==========================================================================
# Die Prüfung einer Datei
# ==========================================================================

def pruefe_datei(pfad: str, modus: str = 'A') -> Pruefbericht:
    """
    Prüft eine Eingabedatei und liefert einen Bericht in Klartext.

    Im Modus B (Auffrischen über die gespeicherte Google-Id) entfallen die
    beiden inhaltlichen Prüfungen: es gibt weder einen Suchbegriff noch ein
    Strassenfeld, an dem etwas falsch sein könnte. Geprüft werden die
    Pflichtspalten und die Zeilenobergrenze.

    Wirft keine Ausnahme wegen des Inhalts — was nicht stimmt, steht im
    Bericht. Nur eine Datei, die sich gar nicht lesen lässt, führt zu einem
    Fehler beim Aufrufer.
    """
    if modus not in PFLICHTSPALTEN_JE_MODUS:
        raise ValueError(f'Unbekannter Modus "{modus}", erlaubt sind A und B.')

    quelle = Path(pfad)
    bericht = Pruefbericht(dateiname=quelle.name, modus=modus)

    df = pd.read_csv(quelle, sep=';', encoding='utf-8-sig', dtype=str).fillna('')
    rohzeilen = _rohzeilen(quelle)

    bericht.zeilen = len(df)
    bericht.kunden = df['KundenNr'].nunique() if 'KundenNr' in df.columns else 0

    _pruefe_zeilenzahl(df, bericht)
    _pruefe_pflichtspalten(df, rohzeilen, bericht)

    if modus == 'A' and 'SearchString' in df.columns:
        _pruefe_kostenstellen(df, rohzeilen, bericht)
        _pruefe_kategorietitel(df, rohzeilen, bericht)

    logger.info(f'Prüfung {quelle.name}: {len(bericht.befunde)} Befunde, '
                f'Start möglich: {bericht.start_moeglich}')
    return bericht


def _rohzeilen(quelle: Path) -> list:
    """
    Die Datei so, wie sie geschrieben wurde — für die Beispielzeile im Bericht.

    Der Nutzer sucht die Zeile in Excel; er soll dort genau das sehen, was im
    Bericht steht. Passt die Zeilenzahl nicht zur Tabelle (mehrzeilige Felder),
    wird die Beispielzeile aus der Tabelle zusammengesetzt.
    """
    try:
        return quelle.read_text(encoding='utf-8-sig').splitlines()
    except Exception as fehler:
        logger.warning(f'Rohzeilen von {quelle.name} nicht lesbar: {fehler}')
        return []


def _beispiel(df: pd.DataFrame, rohzeilen: list, index: int) -> tuple:
    """
    Beispielzeile und ihre Nummer in der Datei.

    Zeile 1 ist die Kopfzeile, der erste Datensatz steht also auf Zeile 2 —
    dieselbe Zählung wie in Excel.
    """
    zeilennummer = index + 2
    passend = len(rohzeilen) == len(df) + 1
    if passend and 0 <= zeilennummer - 1 < len(rohzeilen):
        return rohzeilen[zeilennummer - 1].strip(), zeilennummer
    return ';'.join(str(wert) for wert in df.iloc[index].tolist()), zeilennummer


def _pruefe_zeilenzahl(df: pd.DataFrame, bericht: Pruefbericht) -> None:
    if len(df) <= MAX_ZEILEN:
        return
    bericht.befunde.append(Befund(
        art='zeilenzahl', schwere=ABWEISUNG, anzahl=len(df),
        meldung=(f'Die Datei hat {zahl(len(df))} Zeilen. Erlaubt sind höchstens '
                 f'{zahl(MAX_ZEILEN)}. Bitte die Datei aufteilen und die Teile '
                 f'nacheinander laufen lassen.')))


def _pruefe_pflichtspalten(df: pd.DataFrame, rohzeilen: list,
                           bericht: Pruefbericht) -> None:
    fehlend = [spalte for spalte in PFLICHTSPALTEN_JE_MODUS[bericht.modus]
               if spalte not in df.columns]
    if not fehlend:
        return

    welche = ', '.join(f'«{spalte}»' for spalte in fehlend)
    kopfzeile = rohzeilen[0].strip() if rohzeilen else ''
    bericht.befunde.append(Befund(
        art='pflichtspalten', schwere=ABWEISUNG, anzahl=len(df),
        meldung=(f'In der Datei fehlt die Spalte {welche}. '
                 f'Die erste Zeile muss so aussehen: '
                 f'{KOPFZEILE_JE_MODUS[bericht.modus]}'),
        beispiel_zeile=kopfzeile, zeilennummer=1))


def _pruefe_kostenstellen(df: pd.DataFrame, rohzeilen: list,
                          bericht: Pruefbericht) -> None:
    treffer = [i for i, wert in enumerate(df['SearchString'])
               if ist_kostenstelle(strassenteil(wert))]
    if not treffer:
        return

    beispiel, nummer = _beispiel(df, rohzeilen, treffer[0])
    bericht.befunde.append(Befund(
        art='kostenstelle', schwere=HINWEIS, anzahl=len(treffer),
        meldung=(f'{zahl(len(treffer))} Zeilen haben im Strassenfeld keinen '
                 f'Strassennamen, sondern zum Beispiel eine Kostenstelle. '
                 f'Ohne Strasse findet die Suche die Adresse nicht.'),
        beispiel_zeile=beispiel, zeilennummer=nummer))


def _pruefe_kategorietitel(df: pd.DataFrame, rohzeilen: list,
                           bericht: Pruefbericht) -> None:
    treffer = [i for i, wert in enumerate(df['SearchString'])
               if ist_kategorietitel(titelteil(wert))]
    if not treffer:
        return

    beispiel, nummer = _beispiel(df, rohzeilen, treffer[0])
    bericht.befunde.append(Befund(
        art='kategorietitel', schwere=HINWEIS, anzahl=len(treffer),
        meldung=(f'{zahl(len(treffer))} Zeilen tragen als Namen nur eine '
                 f'Branche statt eines Firmennamens. Die Suche findet dann '
                 f'viele gleich gute Treffer und kann nicht entscheiden.'),
        beispiel_zeile=beispiel, zeilennummer=nummer))
