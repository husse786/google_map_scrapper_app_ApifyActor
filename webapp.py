#!/usr/bin/env python3
# webapp.py
# Die Weboberfläche. Vier Seiten: Art wählen, Datei, Lauf, Ergebnis.
#
#   python webapp.py            → http://localhost:8000
#   python webapp.py --offen    → auch für andere Rechner im Firmennetz
#
# Ablauf, Texte und Reihenfolge folgen agent/webapp_prototyp.html. Zwei Texte
# des Prototyps fehlen bewusst:
#   - „Rund 2 Stunden für 2'500 Kunden" — die Zahl ist seit der Messung in
#     Phase 4 nicht belegt. Angezeigt wird nur der Fortschritt und eine
#     Restzeit, die aus den bereits verarbeiteten Kunden gerechnet ist.
#   - „Wir schicken eine Mail" — Mailversand kommt in Phase 7.
#
# Ein Nutzer, ein Auftrag. Zustand steht in der Datenbank, nicht im Speicher:
# Wer das Fenster schliesst und später wiederkommt, sieht denselben Stand.

import argparse
import logging
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from data_cleaner import OUTPUT_FILES
from db import Datenbank
from fake_provider import FakeProvider
from upload_pruefung import pruefe_datei, zahl
from worker import LaeuftBereits, Worker, offener_lauf

WURZEL = Path(__file__).resolve().parent
LAUFDATEN = WURZEL / 'laufdaten'
UPLOADS = LAUFDATEN / 'uploads'
DATENBANK = LAUFDATEN / 'laeufe.sqlite'
LOG_DATEI = WURZEL / 'logs' / 'webapp.log'

logger = logging.getLogger(__name__)

app = FastAPI(title='Kundendaten anreichern', docs_url=None, redoc_url=None)
app.mount('/static', StaticFiles(directory=WURZEL / 'static'), name='static')
vorlagen = Jinja2Templates(directory=WURZEL / 'templates')
vorlagen.env.globals['zahl'] = zahl

# Ein Nutzer, ein Auftrag (03_ENTSCHEIDUNGEN.md C).
zustand = {
    'worker': None,       # der laufende Worker
    'hochgeladen': None,  # Pfad der zuletzt geprüften Datei
    'kunden': 0,          # Kundenzahl aus der Prüfung, für die erste Anzeige
    'provider': None,     # wird beim Start gesetzt
    # Nur der echte Serverbetrieb beendet den Prozess hart (s. beim_beenden).
    # Im Test würde das die Testsuite mitnehmen.
    'harter_stopp': False,
}

# Beschriftungen der drei Ausgabedateien (02_DATENVERTRAG.md §2)
AUSGABEN = [
    ('fertig_fuer_erp', 'Fertig fürs ERP', 'Kann direkt importiert werden.', 'fertig'),
    ('zur_pruefung', 'Zur Prüfung',
     'Mehrere mögliche Treffer — Sie entscheiden. Der Grund steht in jeder Zeile.',
     'pruefung'),
    ('nicht_moeglich', 'Nicht möglich',
     'Nichts gefunden. Adresse im ERP prüfen, dann neu versuchen.', 'nicht_moeglich'),
]


# ==========================================================================
# Hilfen
# ==========================================================================

def seite(request: Request, vorlage: str, schritt: str, **werte) -> HTMLResponse:
    return vorlagen.TemplateResponse(request, vorlage, {'schritt': schritt, **werte})


def fehlerseite(request: Request, ueberschrift: str, erklaerung: str,
                rat: str = '', code: int = 400) -> HTMLResponse:
    antwort = seite(request, 'fehler.html', 'art', ueberschrift=ueberschrift,
                    erklaerung=erklaerung, rat=rat)
    antwort.status_code = code
    return antwort


def dauer_in_worten(sekunden: float) -> str:
    """90 → «1 Minute», 5400 → «1 Stunde 30 Minuten». Immer deutsch, immer gerundet."""
    sekunden = max(0, int(sekunden))
    if sekunden < 60:
        return 'weniger als eine Minute'
    minuten = round(sekunden / 60)
    stunden, minuten = divmod(minuten, 60)

    teile = []
    if stunden:
        teile.append('1 Stunde' if stunden == 1 else f'{zahl(stunden)} Stunden')
    if minuten:
        teile.append('1 Minute' if minuten == 1 else f'{minuten} Minuten')
    return ' '.join(teile) if teile else 'weniger als eine Minute'


def restzeit_schaetzen(job: dict) -> str:
    """
    Wie lange es noch dauert — gerechnet aus dem, was schon gelaufen ist.

    Keine Vorhersage aus einer Erfahrungszahl: die Laufzeit je Kunde schwankt
    stark und ist seit Phase 4 offen. Diese Schätzung stimmt dafür immer, weil
    sie nur misst, was dieser Lauf auf diesem Rechner tatsächlich braucht.
    """
    erledigt = job.get('kunden_erledigt') or 0
    total = job.get('kunden_total') or 0
    gestartet = job.get('gestartet_am')

    if erledigt < 3 or not gestartet or total <= erledigt:
        return 'Die verbleibende Zeit lässt sich noch nicht abschätzen.'

    try:
        verstrichen = (datetime.now() - datetime.fromisoformat(gestartet)).total_seconds()
    except ValueError:
        return 'Die verbleibende Zeit lässt sich noch nicht abschätzen.'
    if verstrichen <= 0:
        return 'Die verbleibende Zeit lässt sich noch nicht abschätzen.'

    je_kunde = verstrichen / erledigt
    return f'Noch ungefähr {dauer_in_worten(je_kunde * (total - erledigt))}.'


def stand_lesen(job_id: int) -> dict:
    """Alles, was die Statusanzeige braucht — frisch aus der Datenbank."""
    with Datenbank(DATENBANK) as datenbank:
        job = datenbank.job_lesen(job_id)
        if not job:
            return None
        gezaehlt = datenbank.ergebnis_zaehlen(job_id)
        zuletzt = datenbank.zuletzt_verarbeitet(job_id)

    total = job['kunden_total'] or 0
    erledigt = job['kunden_erledigt'] or 0
    laeuft = job['status'] == 'LAEUFT'

    ueberschriften = {
        'LAEUFT': 'Läuft', 'FERTIG': 'Fertig',
        'ABGEBROCHEN': 'Abgebrochen', 'FEHLER': 'Abgebrochen',
        'NEU': 'Bereit', 'VALIDIERT': 'Bereit',
    }
    abschluss = {
        'FERTIG': 'Der Lauf ist durch. Die drei Dateien liegen bereit.',
        'ABGEBROCHEN': 'Der Lauf wurde gestoppt. Die bereits verarbeiteten '
                       'Kunden sind gespeichert.',
        'FEHLER': 'Der Lauf musste abbrechen. Die bereits verarbeiteten Kunden '
                  'sind gespeichert.',
    }

    return {
        'status': job['status'],
        'fertig': not laeuft,
        'ueberschrift': ueberschriften.get(job['status'], job['status']),
        'abschlusstext': abschluss.get(job['status'], ''),
        'weiter_zu': f'/ergebnis/{job_id}',
        'erledigt': erledigt,
        'total': total,
        'prozent': round(100 * erledigt / total) if total else 0,
        'restzeit': restzeit_schaetzen(job),
        'fertig_anzahl': gezaehlt['fertig'],
        'pruefung_anzahl': gezaehlt['pruefung'],
        'nicht_moeglich_anzahl': gezaehlt['nicht_moeglich'],
        'zuletzt': (zuletzt or {}).get('search_string') or '',
    }


def provider_holen():
    """
    Die Datenquelle. Ohne Apify-Zugang die festen Antworten aus einer Datei.

    Damit lässt sich die Oberfläche vollständig bedienen, ohne Kontingent zu
    verbrauchen — und ohne Netz.
    """
    if zustand['provider'] is not None:
        return zustand['provider']
    return None


# ==========================================================================
# Seite 1 — Art wählen
# ==========================================================================

@app.get('/', response_class=HTMLResponse)
def art_waehlen(request: Request):
    worker = zustand['worker']
    if worker and worker.laeuft:
        return RedirectResponse(f'/lauf/{worker.job_id}', status_code=303)

    return seite(request, 'art_waehlen.html', 'art', offener_lauf=offener_lauf(DATENBANK))


# ==========================================================================
# Seite 2 — Datei
# ==========================================================================

@app.get('/datei', response_class=HTMLResponse)
def datei_formular(request: Request, modus: str = 'A'):
    if modus != 'A':
        return fehlerseite(
            request, 'Diese Art ist noch nicht verfügbar',
            'Das Auffrischen über die gespeicherte Google-ID wird gerade gebaut.',
            'Bitte die Erstanreicherung verwenden.')
    zustand['hochgeladen'] = None
    return seite(request, 'datei.html', 'datei', bericht=None)


@app.post('/datei', response_class=HTMLResponse)
async def datei_hochladen(request: Request, datei: UploadFile = None):
    if not datei or not datei.filename:
        return fehlerseite(request, 'Es wurde keine Datei ausgewählt',
                           'Bitte eine CSV-Datei auswählen und erneut hochladen.')

    UPLOADS.mkdir(parents=True, exist_ok=True)
    ziel = UPLOADS / Path(datei.filename).name
    try:
        with ziel.open('wb') as ausgabe:
            shutil.copyfileobj(datei.file, ausgabe)
    finally:
        await datei.close()

    try:
        bericht = pruefe_datei(ziel)
    except Exception:
        logger.exception('Datei nicht lesbar')
        return fehlerseite(
            request, 'Die Datei konnte nicht gelesen werden',
            f'«{ziel.name}» liess sich nicht als CSV-Datei öffnen.',
            'Erwartet wird eine CSV-Datei mit Semikolon als Trennzeichen. '
            'In Excel: Speichern unter → CSV.')

    zustand['hochgeladen'] = ziel if bericht.start_moeglich else None
    zustand['kunden'] = bericht.kunden
    return seite(request, 'datei.html', 'datei', bericht=bericht)


# ==========================================================================
# Lauf starten und fortsetzen
# ==========================================================================

@app.post('/starten')
def lauf_starten(request: Request):
    quelle = zustand['hochgeladen']
    if not quelle or not Path(quelle).exists():
        return fehlerseite(request, 'Die Datei ist nicht mehr da',
                           'Bitte die Datei noch einmal hochladen.')

    worker = Worker(provider_holen(), DATENBANK)
    try:
        job_id = worker.starten(quelle, email=None,
                                kunden_total=zustand['kunden'])
    except LaeuftBereits as hinweis:
        return fehlerseite(request, 'Es läuft bereits ein Auftrag', str(hinweis),
                           'Bitte den laufenden Auftrag abwarten oder abbrechen.',
                           code=409)

    zustand['worker'] = worker
    return RedirectResponse(f'/lauf/{job_id}', status_code=303)


@app.post('/fortsetzen')
def lauf_fortsetzen(request: Request):
    offen = offener_lauf(DATENBANK)
    if not offen:
        return RedirectResponse('/', status_code=303)

    quelle = UPLOADS / offen['dateiname']
    if not quelle.exists():
        return fehlerseite(
            request, 'Die Datei zum Auftrag fehlt',
            f'Der offene Auftrag gehört zur Datei «{offen["dateiname"]}». '
            f'Sie liegt nicht mehr im Ordner der hochgeladenen Dateien.',
            'Bitte dieselbe Datei erneut hochladen und einen neuen Lauf starten.')

    worker = Worker(provider_holen(), DATENBANK)
    try:
        worker.fortsetzen(offen['id'], quelle)
    except LaeuftBereits as hinweis:
        return fehlerseite(request, 'Es läuft bereits ein Auftrag', str(hinweis),
                           'Bitte den laufenden Auftrag abwarten oder abbrechen.',
                           code=409)

    zustand['worker'] = worker
    return RedirectResponse(f'/lauf/{offen["id"]}', status_code=303)


# ==========================================================================
# Seite 3 — Lauf
# ==========================================================================

@app.get('/lauf/{job_id}', response_class=HTMLResponse)
def lauf_zeigen(request: Request, job_id: int):
    stand = stand_lesen(job_id)
    if not stand:
        return fehlerseite(request, 'Diesen Auftrag gibt es nicht',
                           f'Ein Auftrag mit der Nummer {job_id} ist nicht '
                           f'gespeichert.', code=404)
    return seite(request, 'lauf.html', 'lauf', job_id=job_id, stand=stand)


@app.get('/lauf/{job_id}/stand', response_class=HTMLResponse)
def lauf_stand(request: Request, job_id: int):
    """Wird alle 5 Sekunden nachgeladen — nur dieser Ausschnitt, nicht die Seite."""
    stand = stand_lesen(job_id)
    if not stand:
        return Response(status_code=404)

    antwort = vorlagen.TemplateResponse(request, 'lauf_stand.html',
                                        {'job_id': job_id, 'stand': stand})
    if stand['fertig']:
        # Der Lauf ist zu Ende: der Browser wechselt auf die Ergebnisseite.
        antwort.headers['HX-Redirect'] = stand['weiter_zu']
    return antwort


@app.post('/lauf/{job_id}/abbrechen')
def lauf_abbrechen(job_id: int):
    worker = zustand['worker']
    if worker and worker.job_id == job_id:
        worker.abbrechen()
        worker.warten(timeout=10)
    return RedirectResponse(f'/ergebnis/{job_id}', status_code=303)


# ==========================================================================
# Seite 4 — Ergebnis
# ==========================================================================

@app.get('/ergebnis/{job_id}', response_class=HTMLResponse)
def ergebnis_zeigen(request: Request, job_id: int):
    with Datenbank(DATENBANK) as datenbank:
        job = datenbank.job_lesen(job_id)
        gezaehlt = datenbank.ergebnis_zaehlen(job_id) if job else {}
    if not job:
        return fehlerseite(request, 'Diesen Auftrag gibt es nicht',
                           f'Ein Auftrag mit der Nummer {job_id} ist nicht '
                           f'gespeichert.', code=404)

    ordner = ergebnisordner(job['dateiname'])
    vollstaendig = job['status'] == 'FERTIG' and ordner.exists()

    if vollstaendig:
        ueberschrift = 'Fertig'
        zusammenfassung = (f'{zahl(job["kunden_total"])} Kunden in '
                           f'{gelaufene_zeit(job)}. Drei Dateien liegen bereit.')
    elif job['status'] == 'ABGEBROCHEN':
        ueberschrift = 'Abgebrochen'
        zusammenfassung = (
            f'Der Lauf wurde nach {zahl(job["kunden_erledigt"])} von '
            f'{zahl(job["kunden_total"])} Kunden gestoppt. Das Ergebnis ist '
            f'unvollständig, deshalb gibt es keine Dateien zum Herunterladen. '
            f'Die verarbeiteten Kunden sind gespeichert.')
    elif job['status'] == 'FEHLER':
        ueberschrift = 'Abgebrochen'
        zusammenfassung = ('Der Lauf musste abbrechen. Es gibt keine Dateien '
                           'zum Herunterladen.')
    else:
        return RedirectResponse(f'/lauf/{job_id}', status_code=303)

    dateien = [{
        'schluessel': schluessel, 'titel': titel, 'text': text,
        'kunden': gezaehlt.get(ergebnis, 0),
    } for schluessel, titel, text, ergebnis in AUSGABEN] if vollstaendig else []

    return seite(request, 'ergebnis.html', 'ergebnis', job_id=job_id,
                 ueberschrift=ueberschrift, zusammenfassung=zusammenfassung,
                 dateien=dateien)


@app.get('/ergebnis/{job_id}/datei/{schluessel}')
def datei_herunterladen(request: Request, job_id: int, schluessel: str):
    if schluessel not in OUTPUT_FILES:
        return fehlerseite(request, 'Diese Datei gibt es nicht',
                           'Der Verweis führt ins Leere.', code=404)

    with Datenbank(DATENBANK) as datenbank:
        job = datenbank.job_lesen(job_id)
    if not job:
        return fehlerseite(request, 'Diesen Auftrag gibt es nicht',
                           f'Ein Auftrag mit der Nummer {job_id} ist nicht '
                           f'gespeichert.', code=404)

    pfad = ergebnisordner(job['dateiname']) / OUTPUT_FILES[schluessel]
    if not pfad.exists():
        return fehlerseite(request, 'Die Datei liegt nicht bereit',
                           'Zu diesem Auftrag wurde noch keine Ergebnisdatei '
                           'geschrieben.',
                           'Das ist normal, solange der Lauf nicht fertig ist.',
                           code=404)

    return FileResponse(pfad, media_type='text/csv; charset=utf-8',
                        filename=OUTPUT_FILES[schluessel])


def ergebnisordner(dateiname: str) -> Path:
    """<eingabedateiname>_ergebnis neben der hochgeladenen Datei (§2)."""
    return UPLOADS / f'{Path(dateiname).stem}_ergebnis'


def gelaufene_zeit(job: dict) -> str:
    try:
        beginn = datetime.fromisoformat(job['gestartet_am'])
        ende = datetime.fromisoformat(job['beendet_am'])
    except (TypeError, ValueError):
        return 'unbekannter Zeit'
    return dauer_in_worten((ende - beginn).total_seconds())


# ==========================================================================
# Fehler, die trotzdem passieren
# ==========================================================================

@app.exception_handler(500)
@app.exception_handler(Exception)
def unerwarteter_fehler(request: Request, fehler: Exception):
    logger.exception('Unerwarteter Fehler')
    return fehlerseite(
        request, 'Da ist etwas schiefgegangen',
        'Die Seite konnte nicht angezeigt werden. Ihr laufender Auftrag ist '
        'davon nicht betroffen — er arbeitet weiter und der Stand ist '
        'gespeichert.', code=500)


# ==========================================================================
# Starten und beenden
# ==========================================================================

@app.on_event('shutdown')
def beim_beenden():
    """
    Beim Beenden nicht auf hängende Abfragen warten.

    Python wartet am Ende des Programms auf jeden noch laufenden Arbeitsthread.
    Eine Apify-Abfrage kann bis zu 175 Sekunden brauchen — so lange darf sich
    das Fenster nicht weigern zuzugehen, das sieht wie ein Absturz aus.

    Der laufende Auftrag bleibt bewusst auf LAEUFT stehen. Nach jedem Kunden
    ist der Stand geschrieben; beim nächsten Start bietet die Oberfläche die
    Fortsetzung an (02_DATENVERTRAG.md §6). Genau dafür wurde die
    Wiederaufnahme in Phase 3 gebaut.
    """
    worker = zustand['worker']
    if worker and worker.laeuft:
        logger.info(f'Server wird beendet, Auftrag {worker.job_id} bleibt offen '
                    f'und kann fortgesetzt werden.')
    if not zustand['harter_stopp']:
        return
    logging.shutdown()
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(0)


def logging_einrichten() -> None:
    LOG_DATEI.parent.mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[logging.FileHandler(LOG_DATEI, encoding='utf-8')],
        force=True)


def provider_einrichten(antworten: str = None, quelle: str = 'fake'):
    """Legt fest, woher die Treffer kommen. Ohne Angabe: feste Antworten."""
    if quelle == 'apify':
        import apify_provider
        zustand['provider'] = apify_provider.aus_konfiguration()
        return
    if antworten:
        zustand['provider'] = FakeProvider.aus_csv(str(antworten))
    else:
        zustand['provider'] = FakeProvider()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description='Startet die Weboberfläche für die Anreicherung.')
    parser.add_argument('--quelle', choices=('fake', 'apify'), default='fake',
                        help='woher die Treffer kommen (Standard: feste Antworten)')
    parser.add_argument('--antworten', default=None,
                        help='Antwortdatei für --quelle fake')
    parser.add_argument('--offen', action='store_true',
                        help='auch für andere Rechner im Firmennetz erreichbar')
    parser.add_argument('--port', type=int, default=8000)
    args = parser.parse_args(argv)

    logging_einrichten()
    provider_einrichten(args.antworten, args.quelle)
    # Ab hier ist das ein Server: beim Beenden wird nicht auf hängende
    # Abfragen gewartet (s. beim_beenden).
    zustand['harter_stopp'] = True
    UPLOADS.mkdir(parents=True, exist_ok=True)

    adresse = '0.0.0.0' if args.offen else '127.0.0.1'
    print('Kundendaten anreichern')
    print(f'  Im Browser öffnen: http://localhost:{args.port}')
    if args.offen:
        print(f'  Für Kolleginnen und Kollegen im Firmennetz: '
              f'http://<name-dieses-rechners>:{args.port}')
    print('  Beenden mit Strg+C')

    offen = offener_lauf(DATENBANK)
    if offen:
        print(f'  Hinweis: Auftrag {offen["id"]} ist noch offen und kann '
              f'fortgesetzt werden.')

    uvicorn.run(app, host=adresse, port=args.port, log_config=None,
                access_log=False)
    return 0


if __name__ == '__main__':
    sys.exit(main())
