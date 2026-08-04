#!/usr/bin/env python3
# cli.py
# Schlanke Kommandozeile ohne Tkinter. Zwei Befehle:
#
#   python cli.py pruefen <eingabe.csv>
#       sagt vor dem Lauf, was an der Datei schiefgehen wird
#
#   python cli.py bereinigen <angereicherte_datei.csv>
#       wertet eine bereits angereicherte Datei aus (Phase 1)
#
#   python cli.py lauf <eingabe.csv> --antworten <datei.csv>
#       reichert an und wertet aus, mit festen Antworten statt Apify
#
#   python cli.py lauf <eingabe.csv> --quelle echt
#       dasselbe über Apify. Kostet Kontingent.
#
#   python cli.py lauf <eingabe.csv> --modus B --quelle echt
#       Auffrischen über die gespeicherte Google-Id
#
#   python cli.py fortsetzen <eingabe.csv> --quelle echt
#       nimmt einen Lauf wieder auf, der abgestürzt ist
#
# Der Lauf arbeitet im Hintergrund. Strg+C bricht ihn ab, ohne die bisher
# verarbeiteten Kunden zu verlieren — sie stehen in der Datenbank.
#
# Alle Meldungen sind deutsch. Technische Details stehen im Protokoll unter
# logs/bereinigung.log, nicht auf dem Bildschirm.

import argparse
import logging
import sys
import time
from pathlib import Path

import pandas as pd

from data_cleaner import DataCleaner
from fake_provider import FakeProvider
from pipeline import STANDARD_ARBEITER, STANDARD_TIMEOUT_SEKUNDEN
from upload_pruefung import KOPFZEILE_JE_MODUS, pruefe_datei
from worker import LaeuftBereits, Worker, offener_lauf

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

def pruefen(args) -> int:
    """Prüft eine Datei, ohne etwas zu starten."""
    if not args.eingabe.exists():
        print(f'Die Datei "{args.eingabe}" gibt es nicht. Bitte den Pfad prüfen.')
        return 1
    try:
        bericht = pruefe_datei(args.eingabe, modus=getattr(args, 'modus', 'A'))
    except Exception:
        logging.getLogger(__name__).exception('Prüfung abgebrochen')
        print(f'Die Datei "{args.eingabe.name}" konnte nicht gelesen werden.')
        print('Erwartet wird eine CSV-Datei mit Semikolon als Trennzeichen.')
        return 1

    print(bericht.als_text())
    return 0 if bericht.start_moeglich else 1


def lauf(args) -> int:
    return _lauf_oder_fortsetzen(args, fortsetzen=False)


def fortsetzen(args) -> int:
    return _lauf_oder_fortsetzen(args, fortsetzen=True)


def _lauf_oder_fortsetzen(args, fortsetzen: bool) -> int:
    eingabe: Path = args.eingabe
    pflicht = ('placeId', 'KundenNr') if args.modus == 'B' \
        else ('SearchString', 'PLZ', 'KundenNr')
    df = _eingabe_pruefen(eingabe, pflicht)
    if df is None:
        return 1

    # Vor dem langen Lauf: was wird an dieser Datei schiefgehen?
    bericht = pruefe_datei(eingabe, modus=args.modus)
    if bericht.hinweise or not bericht.start_moeglich:
        for hinweis in bericht.befunde:
            print()
            print(hinweis.als_text())
        print()
    if not bericht.start_moeglich:
        print('Der Lauf wird nicht gestartet.')
        return 1

    try:
        provider = _provider_bauen(args)
    except Exception as fehler:
        print(str(fehler))
        return 1

    worker = Worker(provider, args.datenbank, timeout_sekunden=args.timeout,
                    arbeiter=args.arbeiter, modus=args.modus)

    if fortsetzen:
        offen = offener_lauf(args.datenbank)
        if not offen:
            print('Es gibt keinen unterbrochenen Auftrag zum Fortsetzen.')
            return 1
        if offen['dateiname'] != eingabe.name:
            print(f'Der unterbrochene Auftrag gehört zur Datei '
                  f'"{offen["dateiname"]}", angegeben wurde "{eingabe.name}".')
            return 1
        print(f'Auftrag Nummer {offen["id"]} wird fortgesetzt '
              f'({_zahl(offen["kunden_erledigt"])} Kunden lagen schon vor).')
        job_id = worker.fortsetzen(offen['id'], eingabe,
                                   str(args.ausgabe) if args.ausgabe else None)
    else:
        kunden_eingabe = df['KundenNr'].nunique()
        print(f'Datei:  {eingabe.name}')
        print(f'Kunden: {_zahl(kunden_eingabe)} ({_zahl(len(df))} Zeilen)')
        print(f'Modus:  {"Auffrischen über die Google-Id" if args.modus == "B" else "Erstanreicherung"}')
        print(f'Quelle: {_quelle_in_worten(args)}')
        print(f'Es arbeiten {args.arbeiter} Abfragen gleichzeitig. '
              f'Abbrechen mit Strg+C.')
        try:
            job_id = worker.starten(eingabe,
                                    str(args.ausgabe) if args.ausgabe else None,
                                    email=args.email)
        except LaeuftBereits as hinweis:
            print(str(hinweis))
            return 1

    return _auf_lauf_warten(worker, job_id, args)


def _auf_lauf_warten(worker: Worker, job_id: int, args) -> int:
    """Zeigt den Fortschritt, bis der Lauf fertig ist. Strg+C bricht ab."""
    letzter_stand = -1
    try:
        while not worker.warten(timeout=1.0):
            stand = worker.fortschritt() or {}
            erledigt = stand.get('kunden_erledigt', 0)
            if erledigt != letzter_stand:
                gesamt = stand.get('kunden_total', 0)
                print(f'  {_zahl(erledigt)} von {_zahl(gesamt)} Kunden ...')
                letzter_stand = erledigt
    except KeyboardInterrupt:
        print()
        print('Abbruch angefordert, der Lauf wird gestoppt ...')
        worker.abbrechen()
        worker.warten(timeout=10)

    if worker.fehler:
        logging.getLogger(__name__).error('Lauf gescheitert', exc_info=worker.fehler)
        print()
        print('Der Lauf konnte nicht abgeschlossen werden.')
        print(f'Was genau passiert ist, steht im Protokoll: {LOG_DIR / "bereinigung.log"}')
        return 1

    ergebnis = worker.ergebnis or {}
    if ergebnis.get('status') == 'ABGEBROCHEN':
        print()
        print(f'Abgebrochen nach {_zahl(ergebnis["kunden_erledigt"])} von '
              f'{_zahl(ergebnis["kunden_total"])} Kunden.')
        print('Die bereits verarbeiteten Kunden sind gespeichert. Fortsetzen mit:')
        print(f'  python cli.py fortsetzen {args.eingabe}')
        return 1

    if ergebnis.get('doppelte_kundennummern'):
        print(f'Hinweis: {_zahl(ergebnis["doppelte_kundennummern"])} Zeilen hatten '
              f'eine Kundennummer, die schon vorkam. Es zählt die erste Zeile.')

    code = _ergebnis_zeigen(ergebnis['dateien'], ergebnis['kunden_total'])
    print(f'Lauf Nummer {job_id} in der Datenbank: {args.datenbank}')
    return code


def _quelle_in_worten(args) -> str:
    if args.quelle != 'echt':
        return 'feste Antworten'
    return 'Google Place Details' if args.modus == 'B' else 'Apify'


def _provider_bauen(args):
    if args.quelle == 'echt':
        if args.modus == 'B':
            import google_provider
            return google_provider.aus_konfiguration(timeout_sekunden=args.timeout)
        import apify_provider
        return apify_provider.aus_konfiguration(timeout_sekunden=args.timeout)

    if not args.antworten:
        raise ValueError('Für feste Antworten fehlt die Angabe --antworten '
                         '<datei.csv>. Alternativ --quelle echt verwenden.')
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

    p = befehle.add_parser('pruefen', parents=[gemeinsam],
                           help='eine Eingabedatei prüfen, ohne sie zu starten')
    p.add_argument('--modus', choices=('A', 'B'), default='A',
                   help='A = Erstanreicherung, B = Auffrischen über die Google-Id')
    p.set_defaults(funktion=pruefen)

    lauf_optionen = argparse.ArgumentParser(add_help=False)
    lauf_optionen.add_argument('--quelle', choices=('fake', 'echt'), default='fake',
                               help='woher die Treffer kommen: «echt» nutzt '
                                    'Apify beziehungsweise Google '
                                    '(Standard: feste Antworten)')
    lauf_optionen.add_argument('--modus', choices=('A', 'B'), default='A',
                               help='A = Erstanreicherung über den Suchbegriff, '
                                    'B = Auffrischen über die Google-Id')
    lauf_optionen.add_argument('--antworten', type=Path, default=None,
                               help='Antwortdatei für --quelle fake')
    lauf_optionen.add_argument('--datenbank', type=Path, default=STANDARD_DATENBANK,
                               help=f'SQLite-Datei (Standard: {STANDARD_DATENBANK.name})')
    lauf_optionen.add_argument('--timeout', type=int,
                               default=STANDARD_TIMEOUT_SEKUNDEN,
                               help=f'Sekunden pro Abfrage '
                                    f'(Standard: {STANDARD_TIMEOUT_SEKUNDEN})')
    lauf_optionen.add_argument('--arbeiter', type=int, default=STANDARD_ARBEITER,
                               help=f'gleichzeitige Abfragen '
                                    f'(Standard: {STANDARD_ARBEITER})')
    lauf_optionen.add_argument('--email', default=None,
                               help='Adresse für die Benachrichtigung (Phase 7)')

    l = befehle.add_parser('lauf', parents=[gemeinsam, lauf_optionen],
                           help='anreichern und auswerten')
    l.set_defaults(funktion=lauf)

    f = befehle.add_parser('fortsetzen', parents=[gemeinsam, lauf_optionen],
                           help='einen unterbrochenen Lauf wieder aufnehmen')
    f.set_defaults(funktion=fortsetzen)

    args = parser.parse_args(argv)
    _setup_logging(args.protokoll_anzeigen)
    return args.funktion(args)


if __name__ == '__main__':
    sys.exit(main())
