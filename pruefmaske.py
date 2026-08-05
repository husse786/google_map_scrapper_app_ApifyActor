# pruefmaske.py
# Phase 8: die Prüffälle aus Datei ② werden im Browser entschieden.
#
# Bis hierher hatte Datei ② keinen Rückweg. Der Sachbearbeiter öffnete sie in
# Excel, entschied dort, und hatte am Ende zwei Dateien für das ERP statt einer.
# Diese Phase schliesst den Weg: eine Entscheidung im Browser, und der Kunde
# steht in `fertig_fuer_erp.csv`.
#
# Neue Daten entstehen dabei nicht. Jeder Kandidat liegt seit Phase 2 mit Score
# und Grund in der Tabelle `kandidat` — 02_DATENVERTRAG.md §5 nennt das
# ausdrücklich als Grundlage für diese Maske. Entschieden wird, was schon da
# ist.

import logging
from pathlib import Path

import pandas as pd

from data_cleaner import (OUTPUT_COLUMNS, OUTPUT_FILES, ausgabeordner_fuer,
                          leere_ablage, schreibe_ausgabedateien)
from place_provider import CSV_FELDER, leere_ausgabezeile
from pipeline import ENTSCHEID_JE_DATEI, ERGEBNIS_JE_DATEI

logger = logging.getLogger(__name__)

# Was in der Spalte `qualitaet` steht, nachdem ein Mensch entschieden hat.
#
# Beide Werte stehen seit der Korrekturrunde zu Phase 8 in
# 02_DATENVERTRAG.md §3 und sind damit Vorgabe, nicht Erfindung dieses Moduls.
#
# **Ohne Umlaut, und das ist keine Geschmacksfrage.** `qualitaet` ist der
# Schlüssel, den der ERP-Import liest; ein `ü` darin ist ein
# Zeichenkodierungsrisiko, das beim Import niemand sucht. Alle siebzehn Werte
# aus §3 folgen dem — `PRUEFUNG` statt `PRÜFUNG`, `(ID ungueltig)` statt
# `(ID ungültig)`. Für `grund` gilt das nicht: dort ist freies Deutsch richtig,
# und dort stehen die Umlaute weiterhin.
GEWAEHLT_QUALITAET = 'OK (geprueft)'
KEINER_QUALITAET = 'NICHT_MOEGLICH (geprueft)'


def grund_fuer_gewaehlt(kandidat: dict) -> str:
    """
    Der Klartext für einen von Hand gewählten Treffer.

    Nennt Werte, keine Regeln (02_DATENVERTRAG.md §4) — wer die Zeile später
    liest, soll sehen, wofür entschieden wurde, ohne den Kandidaten
    nachschlagen zu müssen.
    """
    teile = [str(kandidat.get(feld) or '').strip()
             for feld in ('title', 'street', 'postal_code', 'city')]
    beschreibung = ', '.join(teil for teil in teile if teil)
    if not beschreibung:
        beschreibung = 'der ausgewählte Treffer'
    return f'Von Hand geprüft und ausgewählt: {beschreibung}.'


GRUND_KEINER = ('Von Hand geprüft: keiner der gefundenen Treffer gehört zu '
                'diesem Kunden.')


def fortschritt(datenbank, job_id: int) -> dict:
    """Wie viele Prüffälle es gab, wie viele davon noch offen sind."""
    offen = len(datenbank.pruefaelle_lesen(job_id))
    entschieden = sum(
        1 for kunde in datenbank.kunden_lesen(job_id)
        if kunde['qualitaet'] in (GEWAEHLT_QUALITAET, KEINER_QUALITAET))
    gesamt = offen + entschieden
    return {
        'offen': offen,
        'entschieden': entschieden,
        'gesamt': gesamt,
        'prozent': round(100 * entschieden / gesamt) if gesamt else 0,
        'alle_entschieden': gesamt > 0 and offen == 0,
    }


def naechster_offener(datenbank, job_id: int, nach_kunde_id: int = None) -> int:
    """
    Der nächste Fall, der noch auf eine Entscheidung wartet.

    Nach einer Entscheidung springt die Maske dorthin. Das ist die Grundlage
    dafür, dass fünfzig Fälle hintereinander ohne Mausgriff gehen: entscheiden,
    und der nächste Fall steht schon da.
    """
    offen = datenbank.pruefaelle_lesen(job_id)
    if not offen:
        return None
    if nach_kunde_id is not None:
        dahinter = [k for k in offen if k['id'] > nach_kunde_id]
        if dahinter:
            return dahinter[0]['id']
    return offen[0]['id']


def entscheiden(datenbank, kunde_id: int, kandidat_id: int = None) -> dict:
    """
    Hält die Entscheidung über einen Prüffall fest.

    `kandidat_id` ist `None` für «keiner passt» — dann geht der Kunde nach ③.
    Die Dateien schreibt der Aufrufer neu; hier wird nur entschieden.
    """
    kunde = datenbank.kunde_lesen(kunde_id)
    if not kunde:
        raise ValueError(f'Einen Kunden mit der Nummer {kunde_id} gibt es nicht.')

    if kandidat_id is None:
        datenbank.kunde_entscheiden(kunde_id, 'nicht_moeglich', KEINER_QUALITAET,
                                    GRUND_KEINER)
        logger.info(f'Kunde {kunde["kunden_nr"]}: keiner der Treffer passt.')
        return {'ergebnis': 'nicht_moeglich', 'qualitaet': KEINER_QUALITAET,
                'grund': GRUND_KEINER}

    kandidaten = {k['id']: k for k in datenbank.kandidaten_lesen(kunde_id)}
    gewaehlt = kandidaten.get(kandidat_id)
    if not gewaehlt:
        raise ValueError(f'Zu diesem Kunden gibt es keinen Treffer mit der '
                         f'Nummer {kandidat_id}.')

    grund = grund_fuer_gewaehlt(gewaehlt)
    datenbank.kunde_entscheiden(kunde_id, 'fertig', GEWAEHLT_QUALITAET, grund,
                                gewaehlt_id=kandidat_id)
    logger.info(f'Kunde {kunde["kunden_nr"]}: Treffer «{gewaehlt["title"]}» '
                f'von Hand gewählt.')
    return {'ergebnis': 'fertig', 'qualitaet': GEWAEHLT_QUALITAET, 'grund': grund}


# ==========================================================================
# Die Dateien neu schreiben
# ==========================================================================

def _stammspalten(kunde: dict) -> dict:
    return {'KundenNr': kunde['kunden_nr'],
            'SearchString': kunde['search_string'] or '',
            'PLZ': kunde['plz'] or '',
            'Stadt': kunde['stadt'] or ''}


def _kandidatspalten(kandidat: dict) -> dict:
    """Die vierzehn Trefferspalten aus einer Zeile der Tabelle `kandidat`."""
    return {spalte: (kandidat[feld] if kandidat[feld] is not None else '')
            for feld, spalte in CSV_FELDER.items()}


def _aussortiert_uebernehmen(ordner: Path) -> list:
    """
    Die Diagnosedatei bleibt, wie der Lauf sie geschrieben hat.

    Sie lässt sich nicht aus der Datenbank herstellen: Ihre Zeilen tragen ein
    eigenes `qualitaet` (`AUSSORTIERT (PLZ)`, `AUSSORTIERT (Strasse)`), und die
    Tabelle `kandidat` hat keine Spalte dafür — 02_DATENVERTRAG.md §5 ist
    wörtlich verbindlich und wird nicht ergänzt. Neu zu schreiben hiesse also,
    die Begründungen des Laufs durch die des Kunden zu ersetzen und damit
    Diagnose zu verlieren.

    Sie ist keine der drei Ausgaben und unterliegt der Invariante nicht (§2).
    Was ein Mensch ablehnt, steht in der Datenbank mit `entscheid = abgelehnt`
    und in der Maske selbst.
    """
    pfad = Path(ordner) / OUTPUT_FILES['aussortiert']
    if not pfad.exists():
        return []
    vorhanden = pd.read_csv(pfad, sep=';', encoding='utf-8-sig',
                            dtype=str).fillna('')
    return vorhanden.to_dict('records')


def ablage_aus_datenbank(datenbank, job_id: int, ordner=None) -> dict:
    """
    Baut die vier Ausgabelisten aus dem, was in der Datenbank steht.

    Die Regel ist dieselbe, nach der der Lauf sie geschrieben hat: Der Kunde
    gehört in die Datei, die sein `ergebnis` nennt, und dort steht je ein
    Kandidat, dessen `entscheid` zu dieser Datei gehört (`gewaehlt` für ①,
    `vorgeschlagen` für ② und ③, `abgelehnt` für die Diagnosedatei). Hat ein
    Kunde dort keinen Kandidaten, steht er mit leeren Trefferfeldern da —
    genau wie bei einem Lauf ohne Ergebnis.

    Dass diese Regel dasselbe ergibt wie der Lauf selbst, ist kein Argument,
    sondern geprüft: `test_neu_schreiben_ohne_entscheidung_aendert_nichts`
    vergleicht die vier Dateien Zeichen für Zeichen.

    Reihenfolge: nach `kunde.id`, also so, wie die Kunden verarbeitet wurden.
    Bei einem Lauf mit mehreren Arbeitern ist das nicht die Reihenfolge der
    Eingabedatei — die Ausgabe ist danach nach Verarbeitung sortiert. Für den
    ERP-Import spielt die Reihenfolge keine Rolle; die Invariante aus §2 hängt
    nicht daran.
    """
    ablage = leere_ablage()
    entscheid_je_datei = dict(ENTSCHEID_JE_DATEI)
    datei_je_ergebnis = {ergebnis: datei
                         for datei, ergebnis in ERGEBNIS_JE_DATEI.items()}

    for kunde in datenbank.kunden_lesen(job_id):
        ziel = datei_je_ergebnis.get(kunde['ergebnis'])
        if ziel is None:
            logger.warning(f'Kunde {kunde["kunden_nr"]} hat kein Ergebnis und '
                           f'wird beim Schreiben übergangen.')
            continue

        stamm = _stammspalten(kunde)
        kopf = {'qualitaet': kunde['qualitaet'] or '',
                'grund': kunde['grund'] or ''}
        kandidaten = datenbank.kandidaten_lesen(kunde['id'])

        eigene = [k for k in kandidaten
                  if k['entscheid'] == entscheid_je_datei[ziel]]
        if eigene:
            for kandidat in eigene:
                ablage[ziel].append({
                    **stamm, **_kandidatspalten(kandidat),
                    'qualitaet': kunde['qualitaet'] or '',
                    'score': round(float(kandidat['score'] or 0), 2),
                    'grund': kandidat['grund'] or '',
                })
        else:
            # Kein Treffer in dieser Datei: eine Zeile aus Stammdaten allein.
            ablage[ziel].append({**stamm, **leere_ausgabezeile(), **kopf,
                                 'score': 0.0})

    if ordner is not None:
        ablage['aussortiert'] = _aussortiert_uebernehmen(ordner)
    return ablage


def dateien_neu_schreiben(datenbank, job_id: int, ordner: str = None) -> dict:
    """
    Schreibt die vier Ausgabedateien aus dem Stand der Datenbank.

    Wird nach jeder einzelnen Entscheidung aufgerufen. Das klingt nach viel,
    ist aber der Preis dafür, dass die Dateien in jedem Augenblick stimmen —
    und dass niemand am Ende einen Knopf «jetzt wirklich speichern» vergessen
    kann. Was der Sachbearbeiter entschieden hat, steht danach in der Datei.
    """
    job = datenbank.job_lesen(job_id)
    if not job:
        raise ValueError(f'Einen Auftrag mit der Nummer {job_id} gibt es nicht.')

    ziel = ordner or ausgabeordner_fuer(job['dateiname'])
    ablage = ablage_aus_datenbank(datenbank, job_id, ordner=ziel)
    return schreibe_ausgabedateien(ablage, str(ziel))
