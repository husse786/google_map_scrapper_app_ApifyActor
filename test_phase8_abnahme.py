# test_phase8_abnahme.py
# One test per acceptance criterion of phase 8 (agent/01_PHASENPLAN.md).
# The review mask runs through the HTTP interface, never by calling internals.
# No network: the answers come from the invented fixture.

import html
import re
import time
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

import pruefmaske
import webapp
from data_cleaner import OUTPUT_FILES
from db import Datenbank
from fake_provider import FakeProvider
from pipeline import Lauf
from place_provider import Candidate

REPO = Path(__file__).parent
FIXTURE = REPO / 'agent' / 'testdaten' / 'fixture_optimierte_daten.csv'
HAUPTDATEIEN = ('fertig_fuer_erp', 'zur_pruefung', 'nicht_moeglich')


# ============================================================================
# Hilfen
# ============================================================================

def lies(pfad) -> pd.DataFrame:
    return pd.read_csv(pfad, sep=';', encoding='utf-8-sig', dtype=str).fillna('')


def eingabe_csv() -> bytes:
    df = lies(FIXTURE)[['SearchString', 'PLZ', 'Stadt', 'KundenNr']].drop_duplicates(
        subset=['KundenNr'])
    return df.to_csv(sep=';', index=False).encode('utf-8-sig')


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setattr(webapp, 'LAUFDATEN', tmp_path)
    monkeypatch.setattr(webapp, 'UPLOADS', tmp_path / 'uploads')
    monkeypatch.setattr(webapp, 'DATENBANK', tmp_path / 'laeufe.sqlite')
    webapp.UPLOADS.mkdir(parents=True, exist_ok=True)
    webapp.zustand['worker'] = None
    webapp.zustand['hochgeladen'] = None
    webapp.zustand['kunden'] = 0
    webapp.zustand['provider'] = FakeProvider.aus_csv(str(FIXTURE))
    yield webapp
    worker = webapp.zustand['worker']
    if worker and worker.laeuft:
        worker.abbrechen()
        worker.warten(timeout=10)


@pytest.fixture
def browser(app):
    with TestClient(app.app) as klient:
        yield klient


def lauf_durchfuehren(browser, name: str = 'InputData.csv') -> int:
    """Der Weg des Nutzers bis zur fertigen Ergebnisseite."""
    browser.get('/')
    browser.get('/datei', params={'modus': 'A'})
    browser.post('/datei', files={'datei': (name, eingabe_csv(), 'text/csv')})
    antwort = browser.post('/starten', follow_redirects=False)
    job_id = int(antwort.headers['location'].rsplit('/', 1)[1])

    frist = time.monotonic() + 30
    while time.monotonic() < frist and webapp.zustand['worker'].laeuft:
        time.sleep(0.05)
    webapp.zustand['worker'].warten(timeout=10)
    return job_id


def ordner_von(name: str = 'InputData.csv') -> Path:
    return webapp.ergebnisordner(name)


def fall_ids(browser, job_id: int) -> list:
    """Die offenen Fälle, so wie die Liste sie anbietet."""
    text = browser.get(f'/pruefung/{job_id}').text
    gefunden = re.findall(rf'/pruefung/{job_id}/fall/(\d+)', text)
    # Reihenfolge erhalten, Doppelte raus (der «Weiter prüfen»-Knopf zeigt auf
    # denselben ersten Fall wie die Tabelle).
    return list(dict.fromkeys(int(nummer) for nummer in gefunden))


def kandidaten_knoepfe(seite_text: str) -> list:
    return re.findall(r'name="kandidat_id"\s+value="(\d+)"', seite_text)


def kundennummern_je_datei(ordner: Path) -> dict:
    return {name: set(lies(ordner / OUTPUT_FILES[name])['KundenNr'])
            for name in HAUPTDATEIEN}


def viele_pruefaelle(anzahl: int, pfad: Path, name: str = 'Viele.csv') -> int:
    """
    Ein fertiger Auftrag mit `anzahl` offenen Prüffällen.

    Direkt in die Datenbank geschrieben: Geprüft wird hier die Maske, nicht der
    Abgleich. Erfundene Kundennummern, wie in `agent/05_TESTDATEN.md` verlangt.
    """
    with Datenbank(pfad) as datenbank:
        job_id = datenbank.job_anlegen('A', name, kunden_total=anzahl)
        for nummer in range(1, anzahl + 1):
            datenbank.kunde_mit_kandidaten_schreiben(
                job_id, f'9{nummer:05d}',
                [(Candidate(title=f'Muster Laden {nummer}',
                            street=f'Hauptstrasse {nummer}',
                            postal_code='5620', city='Musterdorf',
                            place_id=f'PLACE_{nummer}_A'),
                  84.0, 'vorgeschlagen', f'Treffer A für Kunde {nummer}.'),
                 (Candidate(title=f'Muster Markt {nummer}',
                            street=f'Dorfstrasse {nummer}',
                            postal_code='5620', city='Musterdorf',
                            place_id=f'PLACE_{nummer}_B'),
                  81.0, 'vorgeschlagen', f'Treffer B für Kunde {nummer}.')],
                search_string=f'Muster Laden {nummer}, Hauptstrasse {nummer}, '
                              f'5620 Musterdorf',
                plz='5620', stadt='Musterdorf', ergebnis='pruefung',
                qualitaet='PRUEFUNG (mehrere hohe Treffer)',
                grund='Zwei Treffer gleich gut.')
        datenbank.fortschritt_setzen(job_id, anzahl)
        datenbank.status_setzen(job_id, 'FERTIG')
        pruefmaske.dateien_neu_schreiben(datenbank, job_id,
                                         str(ordner_von(name)))
    return job_id


# ============================================================================
# Kriterium: Alle Prüffälle eines Jobs sind aufrufbar und einzeln entscheidbar
# ============================================================================

def test_alle_pruefaelle_sind_aufrufbar(browser):
    job_id = lauf_durchfuehren(browser)

    with Datenbank(webapp.DATENBANK) as datenbank:
        erwartet = {k['id'] for k in datenbank.pruefaelle_lesen(job_id)}

    assert erwartet, 'die Fixture soll Prüffälle erzeugen, sonst prüft der Test nichts'
    assert set(fall_ids(browser, job_id)) == erwartet

    for kunde_id in erwartet:
        seite = browser.get(f'/pruefung/{job_id}/fall/{kunde_id}')
        assert seite.status_code == 200
        assert kandidaten_knoepfe(seite.text), 'ohne Treffer keine Entscheidung'


def test_jeder_fall_ist_einzeln_entscheidbar(browser):
    job_id = lauf_durchfuehren(browser)
    offen = fall_ids(browser, job_id)

    for kunde_id in offen:
        seite = browser.get(f'/pruefung/{job_id}/fall/{kunde_id}')
        erster = kandidaten_knoepfe(seite.text)[0]
        antwort = browser.post(f'/pruefung/{job_id}/fall/{kunde_id}',
                               data={'kandidat_id': erster},
                               follow_redirects=False)
        assert antwort.status_code == 303

    assert fall_ids(browser, job_id) == [], 'danach ist nichts mehr offen'


def test_kundendaten_links_treffer_rechts(browser):
    """
    Umfang: Kundendaten, Kandidaten, je mit score und grund aus `kandidat`.

    Für alle Fälle, nicht nur den ersten: Bei mehreren Arbeitern steht nicht
    fest, welcher Kunde zuerst in der Datenbank landet.
    """
    job_id = lauf_durchfuehren(browser)

    for kunde_id in fall_ids(browser, job_id):
        with Datenbank(webapp.DATENBANK) as datenbank:
            kunde = datenbank.kunde_lesen(kunde_id)
            kandidaten = datenbank.kandidaten_lesen(kunde_id)

        # Die Seite maskiert Anführungszeichen, wie sich das gehört; verglichen
        # wird deshalb der Text, den der Nutzer liest.
        text = html.unescape(browser.get(f'/pruefung/{job_id}/fall/{kunde_id}').text)

        assert kunde['kunden_nr'] in text
        assert kunde['search_string'] in text
        assert kunde['grund'] in text
        for kandidat in kandidaten:
            assert kandidat['title'] in text
            assert str(kandidat['score']) in text
            assert kandidat['grund'] in text
            assert kandidat['street'] in text


# ============================================================================
# Kriterium: Eine Entscheidung ist nach dem Neuladen der Seite noch da
# ============================================================================

def test_entscheidung_ueberlebt_das_neuladen(browser):
    job_id = lauf_durchfuehren(browser)
    kunde_id = fall_ids(browser, job_id)[0]
    seite = browser.get(f'/pruefung/{job_id}/fall/{kunde_id}')
    gewaehlt = kandidaten_knoepfe(seite.text)[0]

    browser.post(f'/pruefung/{job_id}/fall/{kunde_id}',
                 data={'kandidat_id': gewaehlt}, follow_redirects=False)

    # Neu laden: die Seite sagt, dass entschieden ist.
    erneut = browser.get(f'/pruefung/{job_id}/fall/{kunde_id}')
    assert 'bereits entschieden' in erneut.text
    assert pruefmaske.GEWAEHLT_QUALITAET in erneut.text

    # Und der Fall steht nicht mehr in der Liste der offenen.
    assert kunde_id not in fall_ids(browser, job_id)


def test_entscheidung_steht_in_der_datenbank(browser):
    """Nicht im Speicher: wer den Server neu startet, findet den Stand vor."""
    job_id = lauf_durchfuehren(browser)
    kunde_id = fall_ids(browser, job_id)[0]
    seite = browser.get(f'/pruefung/{job_id}/fall/{kunde_id}')
    gewaehlt = int(kandidaten_knoepfe(seite.text)[0])

    browser.post(f'/pruefung/{job_id}/fall/{kunde_id}',
                 data={'kandidat_id': str(gewaehlt)}, follow_redirects=False)

    # Eine frische Verbindung, wie nach einem Neustart.
    with Datenbank(webapp.DATENBANK) as datenbank:
        kunde = datenbank.kunde_lesen(kunde_id)
        kandidaten = {k['id']: k for k in datenbank.kandidaten_lesen(kunde_id)}

    assert kunde['ergebnis'] == 'fertig'
    assert kunde['qualitaet'] == pruefmaske.GEWAEHLT_QUALITAET
    assert kandidaten[gewaehlt]['entscheid'] == 'gewaehlt'
    for kandidat_id, kandidat in kandidaten.items():
        if kandidat_id != gewaehlt:
            assert kandidat['entscheid'] == 'abgelehnt'


# ============================================================================
# Kriterium: Entschiedene Fälle stehen in fertig_fuer_erp.csv,
#            nicht mehr in zur_pruefung.csv
# ============================================================================

def test_entschiedener_fall_wandert_in_die_erp_datei(browser):
    job_id = lauf_durchfuehren(browser)
    kunde_id = fall_ids(browser, job_id)[0]
    with Datenbank(webapp.DATENBANK) as datenbank:
        kunden_nr = datenbank.kunde_lesen(kunde_id)['kunden_nr']

    vorher = kundennummern_je_datei(ordner_von())
    assert kunden_nr in vorher['zur_pruefung']
    assert kunden_nr not in vorher['fertig_fuer_erp']

    seite = browser.get(f'/pruefung/{job_id}/fall/{kunde_id}')
    browser.post(f'/pruefung/{job_id}/fall/{kunde_id}',
                 data={'kandidat_id': kandidaten_knoepfe(seite.text)[0]},
                 follow_redirects=False)

    nachher = kundennummern_je_datei(ordner_von())
    assert kunden_nr in nachher['fertig_fuer_erp']
    assert kunden_nr not in nachher['zur_pruefung']


def test_keiner_passt_schickt_den_kunden_nach_drei(browser):
    job_id = lauf_durchfuehren(browser)
    kunde_id = fall_ids(browser, job_id)[0]
    with Datenbank(webapp.DATENBANK) as datenbank:
        kunden_nr = datenbank.kunde_lesen(kunde_id)['kunden_nr']

    browser.post(f'/pruefung/{job_id}/fall/{kunde_id}',
                 data={'kandidat_id': 'keiner'}, follow_redirects=False)

    verteilt = kundennummern_je_datei(ordner_von())
    assert kunden_nr in verteilt['nicht_moeglich']
    assert kunden_nr not in verteilt['zur_pruefung']
    assert kunden_nr not in verteilt['fertig_fuer_erp']

    zeile = lies(ordner_von() / OUTPUT_FILES['nicht_moeglich'])
    zeile = zeile[zeile['KundenNr'] == kunden_nr].iloc[0]
    assert zeile['qualitaet'] == pruefmaske.KEINER_QUALITAET
    assert 'keiner der gefundenen Treffer' in zeile['grund']


def test_die_erp_zeile_traegt_score_und_deutschen_grund(browser):
    """Regel 3 aus CLAUDE.md gilt auch für eine Zeile, die ein Mensch entschied."""
    job_id = lauf_durchfuehren(browser)
    kunde_id = fall_ids(browser, job_id)[0]
    seite = browser.get(f'/pruefung/{job_id}/fall/{kunde_id}')
    gewaehlt = int(kandidaten_knoepfe(seite.text)[0])

    with Datenbank(webapp.DATENBANK) as datenbank:
        kunden_nr = datenbank.kunde_lesen(kunde_id)['kunden_nr']
        kandidat = {k['id']: k for k in datenbank.kandidaten_lesen(kunde_id)}[gewaehlt]

    browser.post(f'/pruefung/{job_id}/fall/{kunde_id}',
                 data={'kandidat_id': str(gewaehlt)}, follow_redirects=False)

    fertig = lies(ordner_von() / OUTPUT_FILES['fertig_fuer_erp'])
    zeile = fertig[fertig['KundenNr'] == kunden_nr]
    assert len(zeile) == 1, 'ein Kunde, eine Zeile'
    zeile = zeile.iloc[0]

    # Der gewählte Treffer steht drin, nicht irgendeiner.
    assert zeile['title'] == kandidat['title']
    assert zeile['placeId'] == kandidat['place_id']
    # Score bleibt der gemessene Wert — er wird nie verworfen (§2).
    assert float(zeile['score']) == float(kandidat['score'])
    # Deutscher Klartext, der Werte nennt (§4).
    assert 'Von Hand geprüft' in zeile['grund']
    assert kandidat['title'] in zeile['grund']
    assert 'ß' not in zeile['grund']


# ============================================================================
# Kriterium: Die Invariante aus 02_DATENVERTRAG.md §2 gilt auch nach
#            Entscheidungen
# ============================================================================

def test_invariante_haelt_nach_jeder_entscheidung(browser):
    job_id = lauf_durchfuehren(browser)
    alle = set(lies(REPO / 'agent' / 'testdaten' /
                    'fixture_optimierte_daten.csv')['KundenNr'])

    def pruefen(wann: str):
        verteilt = kundennummern_je_datei(ordner_von())
        vereinigt = set().union(*verteilt.values())
        assert vereinigt == alle, f'{wann}: nicht jeder Kunde in einer Datei'
        for eine, andere in (('fertig_fuer_erp', 'zur_pruefung'),
                             ('fertig_fuer_erp', 'nicht_moeglich'),
                             ('zur_pruefung', 'nicht_moeglich')):
            assert not verteilt[eine] & verteilt[andere], \
                f'{wann}: Kunde in {eine} und {andere}'

    pruefen('vor der Prüfung')
    for lauf, kunde_id in enumerate(fall_ids(browser, job_id), start=1):
        seite = browser.get(f'/pruefung/{job_id}/fall/{kunde_id}')
        knoepfe = kandidaten_knoepfe(seite.text)
        # Abwechselnd einen Treffer wählen und «keiner passt».
        daten = {'kandidat_id': knoepfe[0] if lauf % 2 else 'keiner'}
        browser.post(f'/pruefung/{job_id}/fall/{kunde_id}', data=daten,
                     follow_redirects=False)
        pruefen(f'nach Entscheidung {lauf}')


def test_neu_schreiben_ohne_entscheidung_aendert_nichts(tmp_path):
    """
    Die Grundlage, auf der alles andere steht.

    Die Maske schreibt die Dateien aus der Datenbank neu. Dass diese Regel
    dasselbe ergibt wie der Lauf selbst, ist keine Annahme, sondern hier
    Zeichen für Zeichen verglichen — sonst würde die erste Entscheidung still
    alle übrigen Zeilen verändern.

    Ein Arbeiter, damit die Reihenfolge in der Datenbank der Eingabedatei
    entspricht; bei mehreren ist die Ausgabe nach Verarbeitung sortiert.
    """
    df = lies(FIXTURE)[['SearchString', 'PLZ', 'Stadt', 'KundenNr']].drop_duplicates(
        subset=['KundenNr'])
    eingabe = tmp_path / 'InputData.csv'
    df.to_csv(eingabe, sep=';', index=False, encoding='utf-8-sig')
    ziel = tmp_path / 'ergebnis'

    with Datenbank(tmp_path / 'lauf.sqlite') as datenbank:
        ergebnis = Lauf(FakeProvider.aus_csv(str(FIXTURE)), datenbank,
                        arbeiter=1).ausfuehren(eingabe, str(ziel))
        vorher = {name: (ziel / name).read_bytes()
                  for name in OUTPUT_FILES.values()}
        pruefmaske.dateien_neu_schreiben(datenbank, ergebnis['job_id'], str(ziel))

    for name in OUTPUT_FILES.values():
        assert (ziel / name).read_bytes() == vorher[name], \
            f'{name} hat sich ohne eine einzige Entscheidung verändert'


# ============================================================================
# Kriterium: Eine unentschiedene Restmenge bleibt korrekt in ②
# ============================================================================

def test_unentschiedener_rest_bleibt_in_zwei(browser):
    job_id = lauf_durchfuehren(browser)
    offen = fall_ids(browser, job_id)
    assert len(offen) >= 2, 'für diesen Test braucht es mehr als einen Fall'

    with Datenbank(webapp.DATENBANK) as datenbank:
        nummer_je_fall = {kunde_id: datenbank.kunde_lesen(kunde_id)['kunden_nr']
                          for kunde_id in offen}

    # Nur den ersten entscheiden, der Rest bleibt liegen.
    erster = offen[0]
    seite = browser.get(f'/pruefung/{job_id}/fall/{erster}')
    browser.post(f'/pruefung/{job_id}/fall/{erster}',
                 data={'kandidat_id': kandidaten_knoepfe(seite.text)[0]},
                 follow_redirects=False)

    pruefung = lies(ordner_von() / OUTPUT_FILES['zur_pruefung'])
    verblieben = set(pruefung['KundenNr'])
    assert verblieben == {nummer_je_fall[k] for k in offen[1:]}

    # Die Restmenge trägt unverändert ihre Herkunft — nicht plötzlich «geprüft».
    for _, zeile in pruefung.iterrows():
        assert zeile['qualitaet'].startswith('PRUEFUNG (')
        assert zeile['grund']
        assert float(zeile['score']) >= 0

    # Und sie sind weiterhin aufrufbar.
    assert set(fall_ids(browser, job_id)) == set(offen[1:])


def test_restmenge_behaelt_alle_ihre_treffer(browser):
    """Ein Prüffall hat mehrere Vorschläge — die bleiben alle in ②."""
    job_id = lauf_durchfuehren(browser)
    offen = fall_ids(browser, job_id)

    with Datenbank(webapp.DATENBANK) as datenbank:
        erwartet = {}
        for kunde_id in offen[1:]:
            kunde = datenbank.kunde_lesen(kunde_id)
            erwartet[kunde['kunden_nr']] = len(datenbank.kandidaten_lesen(kunde_id))

    seite = browser.get(f'/pruefung/{job_id}/fall/{offen[0]}')
    browser.post(f'/pruefung/{job_id}/fall/{offen[0]}',
                 data={'kandidat_id': kandidaten_knoepfe(seite.text)[0]},
                 follow_redirects=False)

    pruefung = lies(ordner_von() / OUTPUT_FILES['zur_pruefung'])
    for kunden_nr, anzahl in erwartet.items():
        assert len(pruefung[pruefung['KundenNr'] == kunden_nr]) == anzahl


# ============================================================================
# Kriterium: Bedienbar mit Tastatur; 50 Fälle hintereinander ohne Mausgriff
# ============================================================================

def test_fuenfzig_faelle_ohne_einen_mausgriff(browser, tmp_path):
    """
    Der Kern der Tastaturbedienung.

    Fünfzig Entscheidungen hintereinander, ohne dazwischen die Liste
    aufzurufen: Jede Antwort verweist selbst auf den nächsten offenen Fall.
    Nur deshalb reicht «Ziffer drücken, Ziffer drücken, …» — die Maske holt
    den nächsten Fall, nicht der Nutzer.
    """
    job_id = viele_pruefaelle(50, webapp.DATENBANK)

    weiter = f'/pruefung/{job_id}'
    seite = browser.get(weiter)
    ziel = re.search(rf'/pruefung/{job_id}/fall/(\d+)', seite.text)
    weiter = f'/pruefung/{job_id}/fall/{ziel.group(1)}'

    entschieden = 0
    besucht = []
    while entschieden < 50:
        fall = browser.get(weiter)
        assert fall.status_code == 200
        besucht.append(weiter)
        knoepfe = kandidaten_knoepfe(fall.text)
        assert knoepfe, 'ohne Knopf keine Entscheidung mit der Tastatur'

        antwort = browser.post(weiter, data={'kandidat_id': knoepfe[0]},
                               follow_redirects=False)
        assert antwort.status_code == 303
        weiter = antwort.headers['location']
        entschieden += 1

    assert len(set(besucht)) == 50, 'jeder Fall genau einmal'
    assert weiter == f'/pruefung/{job_id}', 'am Ende führt der Weg zur Liste'

    with Datenbank(webapp.DATENBANK) as datenbank:
        assert datenbank.pruefaelle_lesen(job_id) == []
        stand = pruefmaske.fortschritt(datenbank, job_id)
    assert stand['entschieden'] == 50
    assert stand['alle_entschieden']

    fertig = lies(ordner_von('Viele.csv') / OUTPUT_FILES['fertig_fuer_erp'])
    assert len(fertig) == 50


def test_die_maske_ist_ohne_javascript_bedienbar(browser):
    """
    Tab und Enter müssen reichen.

    Die Zifferntasten sind eine Abkürzung auf echte Absendeknöpfe in einem
    gewöhnlichen Formular. Bliebe das Skript aus, wäre die Maske weiterhin
    vollständig bedienbar — deshalb steht hier kein einziges `onclick`.
    """
    job_id = lauf_durchfuehren(browser)
    kunde_id = fall_ids(browser, job_id)[0]
    text = browser.get(f'/pruefung/{job_id}/fall/{kunde_id}').text

    assert 'method="post"' in text
    assert 'onclick' not in text
    assert text.count('type="submit"') >= 2, 'Treffer und «Keiner passt»'


def test_die_zifferntasten_stehen_an_den_knoepfen(browser):
    """Jeder Treffer trägt seine Ziffer, «Keiner passt» die Null."""
    job_id = lauf_durchfuehren(browser)
    kunde_id = fall_ids(browser, job_id)[0]
    seite = browser.get(f'/pruefung/{job_id}/fall/{kunde_id}')
    anzahl = len(kandidaten_knoepfe(seite.text))

    for ziffer in range(1, anzahl + 1):
        assert f'data-taste="{ziffer}"' in seite.text
    assert 'data-taste="0"' in seite.text
    assert '<kbd>' in seite.text, 'die Seite sagt, welche Tasten gehen'


# ============================================================================
# Fortschritt sichtbar, Arbeit jederzeit unterbrechbar
# ============================================================================

def test_fortschritt_ist_sichtbar_und_waechst(browser):
    job_id = lauf_durchfuehren(browser)
    offen = fall_ids(browser, job_id)
    gesamt = len(offen)

    liste = browser.get(f'/pruefung/{job_id}').text
    assert '<strong>0</strong>' in liste, 'die Seite nennt den Stand'
    assert f'von {gesamt}' in liste
    assert 'aria-valuenow="0"' in liste

    seite = browser.get(f'/pruefung/{job_id}/fall/{offen[0]}')
    browser.post(f'/pruefung/{job_id}/fall/{offen[0]}',
                 data={'kandidat_id': kandidaten_knoepfe(seite.text)[0]},
                 follow_redirects=False)

    # Der Stand auf der Seite ist mitgewachsen, nicht nur der in der Datenbank.
    danach = browser.get(f'/pruefung/{job_id}').text
    assert '<strong>1</strong>' in danach
    assert 'aria-valuenow="0"' not in danach

    with Datenbank(webapp.DATENBANK) as datenbank:
        stand = pruefmaske.fortschritt(datenbank, job_id)
    assert stand['entschieden'] == 1
    assert stand['offen'] == gesamt - 1
    assert not stand['alle_entschieden']


def test_arbeit_kann_unterbrochen_und_fortgesetzt_werden(browser):
    """Nach der Hälfte aufhören, später weitermachen — nichts geht verloren."""
    job_id = viele_pruefaelle(6, webapp.DATENBANK)
    offen = fall_ids(browser, job_id)

    for kunde_id in offen[:3]:
        seite = browser.get(f'/pruefung/{job_id}/fall/{kunde_id}')
        browser.post(f'/pruefung/{job_id}/fall/{kunde_id}',
                     data={'kandidat_id': kandidaten_knoepfe(seite.text)[0]},
                     follow_redirects=False)

    # «Später»: eine frische Sitzung auf derselben Datenbank.
    with TestClient(webapp.app) as spaeter:
        assert set(fall_ids(spaeter, job_id)) == set(offen[3:])
        liste = spaeter.get(f'/pruefung/{job_id}').text
        assert 'Weiter prüfen' in liste

        for kunde_id in offen[3:]:
            seite = spaeter.get(f'/pruefung/{job_id}/fall/{kunde_id}')
            spaeter.post(f'/pruefung/{job_id}/fall/{kunde_id}',
                         data={'kandidat_id': kandidaten_knoepfe(seite.text)[0]},
                         follow_redirects=False)

    fertig = lies(ordner_von('Viele.csv') / OUTPUT_FILES['fertig_fuer_erp'])
    assert len(fertig) == 6


# ============================================================================
# Der Weg dahin und die Ränder
# ============================================================================

def test_die_ergebnisseite_fuehrt_zur_pruefung(browser):
    """Ein ERP-Import statt zwei — die Seite sagt, wo das passiert."""
    job_id = lauf_durchfuehren(browser)
    text = browser.get(f'/ergebnis/{job_id}').text

    assert f'/pruefung/{job_id}' in text
    assert 'eine Datei statt zwei' in text
    # Der alte Weg — Datei ② herunterladen, in Excel entscheiden, wieder
    # hochladen — wird nicht mehr angeboten.
    assert 'hochladen' not in text


def test_pruefung_erst_wenn_der_lauf_durch_ist(browser):
    """Vorher steht nicht fest, welche Kunden zur Prüfung gehen."""
    with Datenbank(webapp.DATENBANK) as datenbank:
        job_id = datenbank.job_anlegen('A', 'Offen.csv', kunden_total=5)
        datenbank.status_setzen(job_id, 'LAEUFT')

    antwort = browser.get(f'/pruefung/{job_id}')
    assert antwort.status_code == 400
    assert 'noch nicht durch' in antwort.text


def test_unbekannter_auftrag_und_fremder_fall(browser):
    job_id = lauf_durchfuehren(browser)

    assert browser.get('/pruefung/9999').status_code == 404

    with Datenbank(webapp.DATENBANK) as datenbank:
        fremd = datenbank.job_anlegen('A', 'Fremd.csv')
        fremder_kunde = datenbank.kunde_schreiben(fremd, '900999',
                                                  ergebnis='pruefung')
        datenbank.status_setzen(fremd, 'FERTIG')

    antwort = browser.get(f'/pruefung/{job_id}/fall/{fremder_kunde}')
    assert antwort.status_code == 404


def test_erfundene_kandidatennummer_wird_abgewiesen(browser):
    """Kein Treffer eines anderen Kunden, keine ausgedachte Nummer."""
    job_id = lauf_durchfuehren(browser)
    offen = fall_ids(browser, job_id)
    erster, zweiter = offen[0], offen[1]

    with Datenbank(webapp.DATENBANK) as datenbank:
        fremder = datenbank.kandidaten_lesen(zweiter)[0]['id']

    antwort = browser.post(f'/pruefung/{job_id}/fall/{erster}',
                           data={'kandidat_id': str(fremder)})
    assert antwort.status_code == 400

    antwort = browser.post(f'/pruefung/{job_id}/fall/{erster}',
                           data={'kandidat_id': 'ganz sicher nicht'})
    assert antwort.status_code == 400

    # Nach beiden Fehlversuchen ist der Fall unverändert offen.
    assert erster in fall_ids(browser, job_id)


def test_eine_entscheidung_laesst_sich_aendern(browser):
    """Wer sich vertippt, wählt neu — die alte Auswahl wird ersetzt."""
    job_id = lauf_durchfuehren(browser)
    kunde_id = fall_ids(browser, job_id)[0]
    seite = browser.get(f'/pruefung/{job_id}/fall/{kunde_id}')
    knoepfe = kandidaten_knoepfe(seite.text)
    assert len(knoepfe) >= 2, 'für diesen Test braucht es zwei Treffer'

    browser.post(f'/pruefung/{job_id}/fall/{kunde_id}',
                 data={'kandidat_id': knoepfe[0]}, follow_redirects=False)
    browser.post(f'/pruefung/{job_id}/fall/{kunde_id}',
                 data={'kandidat_id': knoepfe[1]}, follow_redirects=False)

    with Datenbank(webapp.DATENBANK) as datenbank:
        kunden_nr = datenbank.kunde_lesen(kunde_id)['kunden_nr']
        entscheide = {k['id']: k['entscheid']
                      for k in datenbank.kandidaten_lesen(kunde_id)}

    assert entscheide[int(knoepfe[1])] == 'gewaehlt'
    assert entscheide[int(knoepfe[0])] == 'abgelehnt'

    fertig = lies(ordner_von() / OUTPUT_FILES['fertig_fuer_erp'])
    assert len(fertig[fertig['KundenNr'] == kunden_nr]) == 1, 'nur eine Zeile'


def test_ein_auftrag_ohne_pruefaelle_sagt_das(browser):
    with Datenbank(webapp.DATENBANK) as datenbank:
        job_id = datenbank.job_anlegen('A', 'Sauber.csv', kunden_total=1)
        datenbank.kunde_schreiben(job_id, '900001', ergebnis='fertig',
                                  qualitaet='OK (Strasse)', grund='Passt.')
        datenbank.status_setzen(job_id, 'FERTIG')

    text = browser.get(f'/pruefung/{job_id}').text
    assert 'keine Fälle zur Prüfung' in text


# ============================================================================
# K1 (v1.1): `qualitaet` bleibt umlautfrei
#
# `qualitaet` ist der Schlüssel, den der ERP-Import liest. Ein Umlaut darin ist
# ein Zeichenkodierungsrisiko, das beim Import niemand sucht. `grund` ist freier
# Text und trägt seine Umlaute weiterhin.
# ============================================================================

UMLAUTE = 'äöüÄÖÜß'
VERTRAG = REPO / 'agent' / '02_DATENVERTRAG.md'


def erlaubte_qualitaet_werte() -> list:
    """Die Werte aus der Tabelle in 02_DATENVERTRAG.md §3."""
    text = VERTRAG.read_text(encoding='utf-8')
    abschnitt = text.split('## 3. `qualitaet`')[1].split('\n## 4.')[0]
    return re.findall(r'^\|\s*`([^`]+)`\s*\|', abschnitt, flags=re.MULTILINE)


def test_der_vertrag_fuehrt_die_beiden_werte_der_pruefmaske():
    """Sie sind Vorgabe, nicht Erfindung dieses Moduls."""
    erlaubt = erlaubte_qualitaet_werte()

    assert pruefmaske.GEWAEHLT_QUALITAET in erlaubt
    assert pruefmaske.KEINER_QUALITAET in erlaubt


def test_kein_qualitaet_wert_im_vertrag_traegt_einen_umlaut():
    """Alle siebzehn Werte aus §3, nicht nur die zwei neuen."""
    for wert in erlaubte_qualitaet_werte():
        gefunden = [zeichen for zeichen in wert if zeichen in UMLAUTE]
        assert not gefunden, f'«{wert}» trägt {gefunden}'


def test_kein_geschriebener_qualitaet_wert_traegt_einen_umlaut(browser):
    """
    Die Gegenprobe am laufenden Betrieb.

    Nicht die Liste im Vertrag, sondern das, was tatsächlich in Datenbank und
    Ausgabedateien landet — nach einem vollständigen Lauf und nach beiden Arten
    von Entscheidung.
    """
    job_id = lauf_durchfuehren(browser)
    offen = fall_ids(browser, job_id)

    for lauf, kunde_id in enumerate(offen, start=1):
        seite = browser.get(f'/pruefung/{job_id}/fall/{kunde_id}')
        knoepfe = kandidaten_knoepfe(seite.text)
        browser.post(f'/pruefung/{job_id}/fall/{kunde_id}',
                     data={'kandidat_id': knoepfe[0] if lauf % 2 else 'keiner'},
                     follow_redirects=False)

    erlaubt = set(erlaubte_qualitaet_werte())
    gesehen = set()

    with Datenbank(webapp.DATENBANK) as datenbank:
        for kunde in datenbank.kunden_lesen(job_id):
            gesehen.add(kunde['qualitaet'])
    for name in HAUPTDATEIEN:
        gesehen.update(lies(ordner_von() / OUTPUT_FILES[name])['qualitaet'])
    gesehen.discard('')

    assert pruefmaske.GEWAEHLT_QUALITAET in gesehen, 'beide Arten kamen vor'
    assert pruefmaske.KEINER_QUALITAET in gesehen
    for wert in gesehen:
        assert not [z for z in wert if z in UMLAUTE], f'«{wert}» trägt einen Umlaut'
        assert wert in erlaubt, f'«{wert}» steht nicht in 02_DATENVERTRAG.md §3'


def test_der_grund_traegt_seine_umlaute_weiterhin(browser):
    """
    Die Regel gilt für `qualitaet`, nicht für den Klartext.

    Sonst wäre aus einer Kodierungsvorsicht eine verstümmelte Sprache geworden.
    """
    job_id = lauf_durchfuehren(browser)
    kunde_id = fall_ids(browser, job_id)[0]
    seite = browser.get(f'/pruefung/{job_id}/fall/{kunde_id}')

    browser.post(f'/pruefung/{job_id}/fall/{kunde_id}',
                 data={'kandidat_id': kandidaten_knoepfe(seite.text)[0]},
                 follow_redirects=False)

    fertig = lies(ordner_von() / OUTPUT_FILES['fertig_fuer_erp'])
    gruende = [g for g in fertig['grund'] if 'Von Hand' in g]
    assert gruende, 'der von Hand entschiedene Kunde steht in der ERP-Datei'
    assert 'geprüft' in gruende[0], 'im Grund bleibt der Umlaut'
    assert 'ß' not in gruende[0]
