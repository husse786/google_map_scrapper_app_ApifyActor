#!/usr/bin/env python3
# cli.py
# Schlanke Kommandozeile für die Bereinigung. Ersetzt den Tkinter-Einstieg
# aus main.py: die Fachlogik ist ohne Oberfläche aufrufbar.
#
#   python cli.py Daten/beispiel_optimierte_daten.csv
#   python cli.py Daten/beispiel_optimierte_daten.csv --ausgabe Daten/lauf_17
#
# Alle Meldungen sind deutsch. Technische Details stehen im Protokoll unter
# logs/bereinigung.log, nicht auf dem Bildschirm.

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd

from data_cleaner import DataCleaner

LOG_DIR = Path(__file__).resolve().parent / 'logs'


def _setup_logging(verbose: bool) -> None:
    """Protokoll in eine Datei; auf dem Bildschirm nur, wenn ausdrücklich gewünscht."""
    LOG_DIR.mkdir(exist_ok=True)
    handlers = [logging.FileHandler(LOG_DIR / 'bereinigung.log', encoding='utf-8')]
    if verbose:
        handlers.append(logging.StreamHandler(sys.stdout))
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=handlers,
        force=True,
    )


def _zahl(wert: int) -> str:
    """Schweizer Tausendertrennung: 2513 → 2'513."""
    return f'{wert:,}'.replace(',', "'")


def _kunden_und_zeilen(pfad: str) -> tuple:
    df = pd.read_csv(pfad, sep=';', encoding='utf-8-sig', dtype=str).fillna('')
    if df.empty or 'KundenNr' not in df.columns:
        return 0, 0
    return df['KundenNr'].nunique(), len(df)


def bereinigen(eingabe: Path, ausgabe: Path | None) -> int:
    """Führt die Bereinigung aus und meldet das Ergebnis in Klartext."""
    if not eingabe.exists():
        print(f'Die Datei "{eingabe}" gibt es nicht. Bitte den Pfad prüfen.')
        return 1

    try:
        eingabe_df = pd.read_csv(eingabe, sep=';', encoding='utf-8-sig', dtype=str).fillna('')
    except Exception:
        print(f'Die Datei "{eingabe.name}" konnte nicht gelesen werden.')
        print('Erwartet wird eine CSV-Datei mit Semikolon als Trennzeichen.')
        return 1

    if 'KundenNr' not in eingabe_df.columns:
        print(f'In der Datei "{eingabe.name}" fehlt die Spalte "KundenNr".')
        print('Ohne diese Spalte lassen sich die Ergebnisse keinem Kunden zuordnen.')
        return 1

    kunden_eingabe = eingabe_df['KundenNr'].nunique()
    print(f'Datei:  {eingabe.name}')
    print(f'Kunden: {_zahl(kunden_eingabe)} ({_zahl(len(eingabe_df))} Zeilen)')
    print('Bereinigung läuft ...')

    try:
        ergebnisse = DataCleaner().clean_data(str(eingabe),
                                              str(ausgabe) if ausgabe else None)
    except Exception:
        logging.getLogger(__name__).exception('Bereinigung abgebrochen')
        print()
        print('Die Bereinigung konnte nicht abgeschlossen werden.')
        print(f'Was genau passiert ist, steht im Protokoll: {LOG_DIR / "bereinigung.log"}')
        return 1

    beschriftung = {
        'fertig_fuer_erp': 'Fertig für das ERP',
        'zur_pruefung':    'Zur Prüfung',
        'nicht_moeglich':  'Nicht möglich',
        'aussortiert':     'Aussortiert (nur zur Nachschau)',
    }

    print()
    summe = 0
    for schluessel in ('fertig_fuer_erp', 'zur_pruefung', 'nicht_moeglich', 'aussortiert'):
        kunden, zeilen = _kunden_und_zeilen(ergebnisse[schluessel])
        if schluessel != 'aussortiert':
            summe += kunden
        print(f'  {beschriftung[schluessel]:<34} {_zahl(kunden):>7} Kunden  '
              f'({_zahl(zeilen)} Zeilen)')

    print()
    if summe == kunden_eingabe:
        print(f'Alle {_zahl(kunden_eingabe)} Kunden sind genau einer Datei zugeordnet.')
    else:
        print(f'Achtung: {_zahl(kunden_eingabe)} Kunden in der Eingabe, aber '
              f'{_zahl(summe)} in den Ausgabedateien. Bitte melden.')

    print(f'Die Dateien liegen in: {Path(ergebnisse["fertig_fuer_erp"]).parent}')
    return 0 if summe == kunden_eingabe else 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description='Bereinigt eine angereicherte Google-Maps-Datei und schreibt '
                    'die drei Ausgabedateien.',
    )
    parser.add_argument('eingabe', type=Path,
                        help='angereicherte CSV-Datei (Semikolon-getrennt)')
    parser.add_argument('--ausgabe', type=Path, default=None,
                        help='Zielordner. Fehlt er, wird ein Ordner neben der '
                             'Eingabedatei angelegt.')
    parser.add_argument('--protokoll-anzeigen', action='store_true',
                        help='technische Meldungen zusätzlich auf dem Bildschirm zeigen')
    args = parser.parse_args(argv)

    _setup_logging(args.protokoll_anzeigen)
    return bereinigen(args.eingabe, args.ausgabe)


if __name__ == '__main__':
    sys.exit(main())
