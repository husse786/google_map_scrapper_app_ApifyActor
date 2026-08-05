# test_abschlussrunde_abnahme.py
# One test per acceptance criterion of the closing round (agent/ABSCHLUSSRUNDE.md).
#
# Part 1: the completeness check on SearchString that data_preprocessor.py used
# to perform and that silently disappeared during the rebuild. The four example
# strings come from the plan itself; everything else is made up on the spot.
# No real customer data, no network.

from pathlib import Path

import pandas as pd
import pytest

from upload_pruefung import (HINWEIS, ist_kostenstelle, ist_unvollstaendig,
                             plz_ort_teil, pruefe_datei, strassenteil,
                             titelteil, zahl)

# Die vier Beispiele aus ABSCHLUSSRUNDE.md, wörtlich.
VOLLSTAENDIG = 'Denner, Hauptstrasse 5, 5620 Bremgarten'
OHNE_KOMMA = 'Denner Bremgarten'
OHNE_STRASSE = 'Denner, 5620 Bremgarten'
LEER = ''


# ============================================================================
# Hilfen
# ============================================================================

def datei_schreiben(tmp_path: Path, zeilen: list, spalten: tuple = None,
                    name: str = 'eingabe.csv') -> Path:
    spalten = spalten or ('SearchString', 'PLZ', 'Stadt', 'KundenNr')
    ziel = tmp_path / name
    pd.DataFrame(zeilen, columns=list(spalten)).to_csv(
        ziel, sep=';', index=False, encoding='utf-8-sig')
    return ziel


def zeile(search_string: str, kunden_nr: str = '900001') -> dict:
    return {'SearchString': search_string, 'PLZ': '5620',
            'Stadt': 'Musterdorf', 'KundenNr': kunden_nr}


def zeile_b(place_id: str, kunden_nr: str = '900001') -> dict:
    return {'placeId': place_id, 'lat': '', 'lng': '', 'KundenNr': kunden_nr}


# ============================================================================
# Kriterium: die vier Beispiele aus ABSCHLUSSRUNDE.md
# ============================================================================

def test_vollstaendiger_suchbegriff_loest_nicht_aus():
    assert ist_unvollstaendig(VOLLSTAENDIG) is False


def test_suchbegriff_ohne_komma_loest_aus():
    """«Denner Bremgarten» — es fehlen Strasse und PLZ."""
    assert ist_unvollstaendig(OHNE_KOMMA) is True


def test_suchbegriff_ohne_strasse_loest_aus():
    """
    «Denner, 5620 Bremgarten» — der dritte Teil fehlt.

    Der wichtigste der vier Fälle: Diese Zeile fällt **keiner** der bisherigen
    Prüfungen auf. Im Strassenfeld steht «5620 Bremgarten», also eine
    Buchstabenfolge — die Kostenstellenprüfung schweigt. Ohne diese Prüfung
    ginge die Zeile ungewarnt zu Apify.
    """
    assert ist_unvollstaendig(OHNE_STRASSE) is True
    assert ist_kostenstelle(strassenteil(OHNE_STRASSE)) is False


def test_leerer_suchbegriff_loest_aus():
    assert ist_unvollstaendig(LEER) is True


@pytest.mark.parametrize('search_string, erwartet', [
    (VOLLSTAENDIG, False),
    (OHNE_KOMMA, True),
    (OHNE_STRASSE, True),
    (LEER, True),
    # Ein Teil da, aber leer.
    ('Denner, , 5620 Bremgarten', True),
    ('Denner, Hauptstrasse 5, ', True),
    (', Hauptstrasse 5, 5620 Bremgarten', True),
    ('  ,  ,  ', True),
    # Vier Teile: der Suchbegriff ist vollständig, der Rest ist Zugabe.
    ('Denner, Hauptstrasse 5, 5620 Bremgarten, Zusatz', False),
    # Westschweiz und Tessin — nichts daran ist unvollständig.
    ('Boucherie Meier, Rue des Tilleuls 5, 1800 Vevey', False),
    ('Osteria, Via Nassa 12, 6900 Lugano', False),
    # Eine Kostenstelle ist ein vollständiger, aber falscher Suchbegriff.
    ('Emil Frey AG, KST 715611 0, 5745 Safenwil', False),
])
def test_vollstaendigkeit_im_einzelnen(search_string, erwartet):
    assert ist_unvollstaendig(search_string) is erwartet


def test_die_drei_teile_werden_richtig_zerlegt():
    """Gegenprobe: die Zerlegung ist dieselbe wie in data_preprocessor.py."""
    assert titelteil(VOLLSTAENDIG) == 'Denner'
    assert strassenteil(VOLLSTAENDIG) == 'Hauptstrasse 5'
    assert plz_ort_teil(VOLLSTAENDIG) == '5620 Bremgarten'

    assert titelteil(OHNE_STRASSE) == 'Denner'
    assert strassenteil(OHNE_STRASSE) == '5620 Bremgarten'
    assert plz_ort_teil(OHNE_STRASSE) == ''


# ============================================================================
# Kriterium: Die Prüfung warnt und blockiert nicht
# ============================================================================

def test_die_pruefung_warnt_und_blockiert_nicht(tmp_path):
    quelle = datei_schreiben(tmp_path, [
        zeile(OHNE_KOMMA, '900001'),
        zeile(OHNE_STRASSE, '900002'),
        zeile(VOLLSTAENDIG, '900003'),
    ])

    bericht = pruefe_datei(quelle)
    befund = bericht.befund('unvollstaendig')

    assert befund is not None
    assert befund.schwere == HINWEIS
    assert bericht.start_moeglich, 'der Nutzer entscheidet, nicht die Prüfung'
    assert befund in bericht.hinweise


def test_die_meldung_nennt_anzahl_zeile_und_beispiel(tmp_path):
    """
    Anzahl, Zeilennummer und Beispielzeile im Original — wie die anderen
    beiden inhaltlichen Prüfungen.
    """
    quelle = datei_schreiben(tmp_path, [
        zeile(VOLLSTAENDIG, '900001'),
        zeile(OHNE_KOMMA, '900002'),
        zeile(OHNE_STRASSE, '900003'),
    ])

    befund = pruefe_datei(quelle).befund('unvollstaendig')

    assert befund.anzahl == 2
    # Zeile 1 ist die Kopfzeile, der erste Treffer steht also auf Zeile 3.
    assert befund.zeilennummer == 3
    assert befund.beispiel_zeile.startswith(OHNE_KOMMA)

    text = befund.als_text()
    assert '2 Zeilen' in text
    assert 'keinen vollständigen Suchbegriff' in text
    assert 'Name, Strasse mit Hausnummer, PLZ mit Ort' in text
    assert 'Beispiel Zeile 3' in text
    assert OHNE_KOMMA in text
    assert 'ß' not in text


def test_der_bericht_sagt_wohin_die_zeilen_laufen(tmp_path):
    """«Diese Kunden landen voraussichtlich in Zur Prüfung» — im Berichtstext."""
    quelle = datei_schreiben(tmp_path, [zeile(OHNE_KOMMA)])

    text = pruefe_datei(quelle).als_text()

    assert 'keinen vollständigen Suchbegriff' in text
    assert 'zur Prüfung' in text
    assert 'kann trotzdem gestartet werden' in text


def test_bei_einer_einzigen_zeile_stimmt_die_grammatik(tmp_path):
    """«1 Zeile hat», nicht «1 Zeilen haben» — der Satz steht in der Oberfläche."""
    quelle = datei_schreiben(tmp_path, [
        zeile(VOLLSTAENDIG, '900001'),
        zeile(OHNE_STRASSE, '900002'),
    ])

    befund = pruefe_datei(quelle).befund('unvollstaendig')

    assert befund.anzahl == 1
    assert '1 Zeile hat keinen vollständigen Suchbegriff' in befund.meldung
    assert 'Zeilen haben' not in befund.meldung


def test_eine_saubere_datei_loest_nicht_aus(tmp_path):
    quelle = datei_schreiben(tmp_path, [
        zeile(VOLLSTAENDIG, '900001'),
        zeile('Volg, Dorfstrasse 12, 8006 Musterheim', '900002'),
    ])

    bericht = pruefe_datei(quelle)

    assert bericht.befund('unvollstaendig') is None
    assert bericht.start_moeglich


def test_die_zahl_traegt_den_apostroph(tmp_path):
    """Schweizer Tausendertrennung, wie überall sonst."""
    quelle = datei_schreiben(
        tmp_path, [zeile(OHNE_KOMMA, f'9{i:05d}') for i in range(1, 1235)])

    befund = pruefe_datei(quelle).befund('unvollstaendig')

    assert befund.anzahl == 1234
    assert zahl(1234) == "1'234"
    assert "1'234 Zeilen" in befund.als_text()


# ============================================================================
# Kriterium: Modus B ist unberührt
# ============================================================================

def test_modus_b_kennt_die_pruefung_nicht(tmp_path):
    """Dort gibt es keinen SearchString, an dem etwas fehlen könnte."""
    quelle = datei_schreiben(
        tmp_path, [zeile_b('PLACE_A001'), zeile_b('PLACE_A002', '900002')],
        spalten=('placeId', 'lat', 'lng', 'KundenNr'))

    bericht = pruefe_datei(quelle, modus='B')

    assert bericht.befund('unvollstaendig') is None
    assert bericht.start_moeglich


def test_modus_b_bleibt_still_auch_mit_einer_searchstring_spalte(tmp_path):
    """
    Eine Datei mit beiden Spalten: im Modus B wird der Suchbegriff nicht
    angesehen, auch wenn einer dasteht.
    """
    quelle = datei_schreiben(tmp_path, [
        {'placeId': 'PLACE_A001', 'lat': '', 'lng': '', 'KundenNr': '900001',
         'SearchString': OHNE_KOMMA},
    ], spalten=('placeId', 'lat', 'lng', 'KundenNr', 'SearchString'))

    bericht = pruefe_datei(quelle, modus='B')

    assert bericht.befund('unvollstaendig') is None


# ============================================================================
# Die Prüfung im Zusammenspiel mit den drei bestehenden
# ============================================================================

def test_die_vier_pruefungen_stehen_nebeneinander(tmp_path):
    """Jede meldet ihren eigenen Befund; keine verdrängt eine andere."""
    quelle = datei_schreiben(tmp_path, [
        zeile(VOLLSTAENDIG, '900001'),
        zeile(OHNE_STRASSE, '900002'),
        zeile('Emil Frey AG, KST 715611 0, 5745 Safenwil', '900003'),
        zeile('Boucherie, Rue des Tilleuls 5, 1800 Vevey', '900004'),
    ])

    bericht = pruefe_datei(quelle)
    arten = {b.art for b in bericht.befunde}

    assert arten == {'unvollstaendig', 'kostenstelle', 'kategorietitel'}
    assert bericht.befund('unvollstaendig').anzahl == 1
    assert bericht.befund('kostenstelle').anzahl == 1
    assert bericht.befund('kategorietitel').anzahl == 1
    assert bericht.start_moeglich


def test_eine_kostenstelle_gilt_nicht_als_unvollstaendig():
    """
    Die beiden Prüfungen sagen Verschiedenes.

    «KST 715611 0» ist ein vollständiger Suchbegriff mit falschem Inhalt.
    Wären beide dasselbe, wäre eine von ihnen überflüssig.
    """
    kostenstelle = 'Emil Frey AG, KST 715611 0, 5745 Safenwil'

    assert ist_unvollstaendig(kostenstelle) is False
    assert ist_kostenstelle(strassenteil(kostenstelle)) is True


# ============================================================================
# Der Weg zum Nutzer: die Warnung steht auf der Seite «Datei»
# ============================================================================

@pytest.fixture
def browser(tmp_path, monkeypatch):
    import webapp
    from fake_provider import FakeProvider

    monkeypatch.setattr(webapp, 'LAUFDATEN', tmp_path)
    monkeypatch.setattr(webapp, 'UPLOADS', tmp_path / 'uploads')
    monkeypatch.setattr(webapp, 'DATENBANK', tmp_path / 'laeufe.sqlite')
    webapp.UPLOADS.mkdir(parents=True, exist_ok=True)
    webapp.zustand['worker'] = None
    webapp.zustand['hochgeladen'] = None
    webapp.zustand['provider'] = FakeProvider()

    from fastapi.testclient import TestClient
    with TestClient(webapp.app) as klient:
        yield klient


def test_die_warnung_steht_auf_der_seite_datei(browser):
    """
    Der Nutzer sieht sie vor dem Start — sonst nützt die Prüfung nichts.

    Und er kann trotzdem starten: der Knopf ist da.
    """
    inhalt = pd.DataFrame([
        zeile(OHNE_KOMMA, '900001'),
        zeile(OHNE_STRASSE, '900002'),
        zeile(VOLLSTAENDIG, '900003'),
    ]).to_csv(sep=';', index=False).encode('utf-8-sig')

    browser.get('/datei', params={'modus': 'A'})
    antwort = browser.post('/datei',
                           files={'datei': ('InputData.csv', inhalt, 'text/csv')})

    assert antwort.status_code == 200
    assert 'keinen vollständigen Suchbegriff' in antwort.text
    assert 'Name, Strasse mit Hausnummer, PLZ mit Ort' in antwort.text
    assert OHNE_KOMMA in antwort.text
    # Der Satz, den der Korrekturplan verlangt.
    assert 'Diese Kunden landen voraussichtlich in' in antwort.text
    # Warnung, keine Abweisung: der Start bleibt möglich.
    assert 'action="/starten"' in antwort.text


def test_der_datenvertrag_beschreibt_diese_regel():
    """
    §1 sagt sie seit Anfang an; umgesetzt war sie nicht.

    Der Test hält die Verbindung fest, damit die Regel nicht ein zweites Mal
    still verschwindet.
    """
    vertrag = (Path(__file__).parent / 'agent' / '02_DATENVERTRAG.md').read_text(
        encoding='utf-8')

    assert 'drei kommagetrennte Teile' in vertrag
    assert 'ist die Zeile unvollständig' in vertrag
