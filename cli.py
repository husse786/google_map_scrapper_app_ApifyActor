#!/usr/bin/env python3
# cli.py
# Schlanke Kommandozeile ohne Tkinter. Zwei Befehle:
#
#   python cli.py bereinigen <angereicherte_datei.csv>
#       wertet eine bereits angereicherte Datei aus (Phase 1)
#
#   python cli.py lauf <eingabe.csv> --antworten <datei.csv>
#       reichert an und wertet aus, mit festen Antworten statt Apify
#
#   python cli.py lauf <eingabe.csv> --quelle apify
#       dasselbe über Apify. Kostet Kontingent.
#
# Alle Meldungen sind deutsch. Technische Details stehen im Protokoll unter
# logs/bereinigung.log, nicht auf dem Bildschirm.

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd

from data_cleaner import DataCleaner
from db import Datenbank
from fake_provider import FakeProvider
from pipeline import STANDARD_TIMEOUT_SEKUNDEN, Lauf

LOG_DIR = Path(__file__).resolve().parent / 'logs'
STANDARD_DATENBANK = Path(__file__).resolve().parent / 'laeufe.sqlite'

BESCHRIFTUNG = {
    'fertig_fuer_erp': 'Fertig für das ERP',
    'zur_pruefung':    'Zur Prüfung',
    'nicht_moeglich':  'Nicht möglich',
    'aussortiert':     'Aussortiert (nur zur Nachschau)',
}


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


def _ergebnis_zeigen(dateien: dict, kunden_eingabe: int) -> int:
    print()
    summe = 0
    for schluessel in ('fertig_fuer_erp', 'zur_pruefung', 'nicht_moeglich', 'aussortiert'):
        kunden, zeilen = _kunden_und_zeilen(dateien[schluessel])
        if schluessel != 'aussortiert':
            summe += kunden
        print(f'  {BESCHRIFTUNG[schluessel]:<34} {_zahl(kunden):>7} Kunden  '
              f'({_zahl(zeilen)} Zeilen)')

    print()
    if summe == kunden_eingabe:
        print(f'Alle {_zahl(kunden_eingabe)} Kunden sind genau einer Datei zugeordnet.')
    else:
        print(f'Achtung: {_zahl(kunden_eingabe)} Kunden in der Eingabe, aber '
              f'{_zahl(summe)} in den Ausgabedateien. Bitte melden.')

    print(f'Die Dateien liegen in: {Path(dateien["fertig_fuer_erp"]).parent}')
    return 0 if summe == kunden_eingabe else 1


def _eingabe_pruefen(eingabe: Path, pflichtspalten: tuple):
    """Liest die Datei und meldet in Klartext, was fehlt. None heisst: Abbruch."""
    if not eingabe.exists():
        print(f'Die Datei "{eingabe}" gibt es nicht. Bitte den Pfad prüfen.')
        return None

    try:
        df = pd.read_csv(eingabe, sep=';', encoding='utf-8-sig', dtype=str).fillna('')
    except Exception:
        print(f'Die Datei "{eingabe.name}" konnte nicht gelesen werden.')
        print('Erwartet wird eine CSV-Datei mit Semikolon als Trennzeichen.')
        return None

    fehlend = [spalte for spalte in pflichtspalten if spalte not in df.columns]
    if fehlend:
        print(f'In der Datei "{eingabe.name}" fehlen diese Spalten: '
              f'{", ".join(fehlend)}.')
        print('Die erste Zeile muss die Spaltennamen enthalten, getrennt mit Semikolon.')
        return None

    return df


# ==========================================================================
# Befehl: bereinigen
# ==========================================================================

def bereinigen(args) -> int:
    eingabe: Path = args.eingabe
    df = _eingabe_pruefen(eingabe, ('KundenNr',))
    if df is None:
        return 1

    kunden_eingabe = df['KundenNr'].nunique()
    print(f'Datei:  {eingabe.name}')
    print(f'Kunden: {_zahl(kunden_eingabe)} ({_zahl(len(df))} Zeilen)')
    print('Bereinigung läuft ...')

    try:
        dateien = DataCleaner().clean_data(
            str(eingabe), str(args.ausgabe) if args.ausgabe else None)
    except Exception:
        logging.getLogger(__name__).exception('Bereinigung abgebrochen')
        print()
        print('Die Bereinigung konnte nicht abgeschlossen werden.')
        print(f'Was genau passiert ist, steht im Protokoll: {LOG_DIR / "bereinigung.log"}')
        return 1

    return _ergebnis_zeigen(dateien, kunden_eingabe)


# ==========================================================================
# Befehl: lauf
# ==========================================================================

def lauf(args) -> int:
    eingabe: Path = args.eingabe
    df = _eingabe_pruefen(eingabe, ('SearchString', 'PLZ', 'KundenNr'))
    if df is None:
        return 1

    try:
        provider = _provider_bauen(args)
    except Exception as fehler:
        print(str(fehler))
        return 1

    kunden_eingabe = df['KundenNr'].nunique()
    print(f'Datei:  {eingabe.name}')
    print(f'Kunden: {_zahl(kunden_eingabe)} ({_zahl(len(df))} Zeilen)')
    print(f'Quelle: {"Apify" if args.quelle == "apify" else "feste Antworten"}')
    print('Lauf läuft ...')

    datenbank = Datenbank(args.datenbank)
    try:
        ergebnis = Lauf(provider, datenbank,
                        timeout_sekunden=args.timeout).ausfuehren(
            eingabe, str(args.ausgabe) if args.ausgabe else None)
    except Exception:
        logging.getLogger(__name__).exception('Lauf abgebrochen')
        print()
        print('Der Lauf konnte nicht abgeschlossen werden.')
        print(f'Was genau passiert ist, steht im Protokoll: {LOG_DIR / "bereinigung.log"}')
        return 1
    finally:
        datenbank.schliessen()

    if ergebnis['doppelte_kundennummern']:
        print(f'Hinweis: {_zahl(ergebnis["doppelte_kundennummern"])} Zeilen hatten '
              f'eine Kundennummer, die schon vorkam. Es zählt die erste Zeile.')

    code = _ergebnis_zeigen(ergebnis['dateien'], ergebnis['kunden_total'])
    print(f'Lauf Nummer {ergebnis["job_id"]} in der Datenbank: {args.datenbank}')
    return code


def _provider_bauen(args):
    if args.quelle == 'apify':
        import apify_provider
        return apify_provider.aus_konfiguration(timeout_sekunden=args.timeout)

    if not args.antworten:
        raise ValueError('Für feste Antworten fehlt die Angabe --antworten '
                         '<datei.csv>. Alternativ --quelle apify verwenden.')
    if not Path(args.antworten).exists():
        raise ValueError(f'Die Antwortdatei "{args.antworten}" gibt es nicht.')
    return FakeProvider.aus_csv(str(args.antworten))


# ==========================================================================

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description='Reichert ERP-Kundendaten mit Google-Maps-Daten an und '
                    'schreibt die drei Ausgabedateien.')
    befehle = parser.add_subparsers(dest='befehl', required=True)

    gemeinsam = argparse.ArgumentParser(add_help=False)
    gemeinsam.add_argument('eingabe', type=Path, help='CSV-Datei (Semikolon-getrennt)')
    gemeinsam.add_argument('--ausgabe', type=Path, default=None,
                           help='Zielordner. Fehlt er, wird ein Ordner neben der '
                                'Eingabedatei angelegt.')
    gemeinsam.add_argument('--protokoll-anzeigen', action='store_true',
                           help='technische Meldungen zusätzlich auf dem Bildschirm')

    b = befehle.add_parser('bereinigen', parents=[gemeinsam],
                           help='eine bereits angereicherte Datei auswerten')
    b.set_defaults(funktion=bereinigen)

    l = befehle.add_parser('lauf', parents=[gemeinsam],
                           help='anreichern und auswerten')
    l.add_argument('--quelle', choices=('fake', 'apify'), default='fake',
                   help='woher die Treffer kommen (Standard: feste Antworten)')
    l.add_argument('--antworten', type=Path, default=None,
                   help='Antwortdatei für --quelle fake')
    l.add_argument('--datenbank', type=Path, default=STANDARD_DATENBANK,
                   help=f'SQLite-Datei (Standard: {STANDARD_DATENBANK.name})')
    l.add_argument('--timeout', type=int, default=STANDARD_TIMEOUT_SEKUNDEN,
                   help=f'Sekunden pro Abfrage (Standard: {STANDARD_TIMEOUT_SEKUNDEN})')
    l.set_defaults(funktion=lauf)

    args = parser.parse_args(argv)
    _setup_logging(args.protokoll_anzeigen)
    return args.funktion(args)


if __name__ == '__main__':
    sys.exit(main())
