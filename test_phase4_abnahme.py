# test_phase4_abnahme.py
# One test per acceptance criterion of phase 4 (agent/01_PHASENPLAN.md).
# The three example lines come from the phase plan itself; everything else is
# made up on the spot. No real customer data, no network.

from pathlib import Path

import pandas as pd
import pytest

import cli
from data_cleaner import DataCleaner
from upload_pruefung import (ABWEISUNG, HINWEIS, KATEGORIE_WOERTER, MAX_ZEILEN,
                             PFLICHTSPALTEN, ist_kategorietitel,
                             ist_kostenstelle, pruefe_datei, strassenteil,
                             titelteil, zahl)

# Die drei Beispiele aus dem Phasenplan, wörtlich.
BEISPIEL_KOSTENSTELLE = 'Emil Frey AG, KST 715611 0, 5745 Safenwil'
BEISPIEL_ECHTE_STRASSE = 'Denner, Hauptstrasse 5, 5620 Bremgarten'
BEISPIEL_KATEGORIE = 'Boucherie, Rue des Tilleuls 5, 1800 Vevey'


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


def zeile(search_string: str, kunden_nr: str = '900001', plz: str = '5620') -> dict:
    return {'SearchString': search_string, 'PLZ': plz,
            'Stadt': 'Musterdorf', 'KundenNr': kunden_nr}


# ============================================================================
# Kriterium: die drei Beispiele des Phasenplans
# ============================================================================

def test_kostenstelle_wird_erkannt():
    assert ist_kostenstelle(strassenteil(BEISPIEL_KOSTENSTELLE)) is True


def test_echte_strasse_wird_nicht_als_kostenstelle_erkannt():
    assert ist_kostenstelle(strassenteil(BEISPIEL_ECHTE_STRASSE)) is False


def test_kategorietitel_wird_erkannt():
    assert ist_kategorietitel(titelteil(BEISPIEL_KATEGORIE)) is True


def test_die_drei_beispiele_im_ganzen_bericht(tmp_path):
    """Dieselben drei Zeilen, aber durch die vollständige Prüfung geschickt."""
    quelle = datei_schreiben(tmp_path, [
        zeile(BEISPIEL_KOSTENSTELLE, '900001'),
        zeile(BEISPIEL_ECHTE_STRASSE, '900002'),
        zeile(BEISPIEL_KATEGORIE, '900003'),
    ])

    bericht = pruefe_datei(quelle)

    kostenstelle = bericht.befund('kostenstelle')
    kategorie = bericht.befund('kategorietitel')
    assert kostenstelle.anzahl == 1
    assert kategorie.anzahl == 1
    # Die Beispielzeile ist die Zeile aus der Datei, mit ihrer Nummer.
    assert kostenstelle.beispiel_zeile.startswith('Emil Frey AG')
    assert kostenstelle.zeilennummer == 2
    assert kategorie.beispiel_zeile.startswith('Boucherie')
    assert kategorie.zeilennummer == 4
    # Denner löst nichts aus.
    assert 'Denner' not in kostenstelle.beispiel_zeile
    assert 'Denner' not in kategorie.beispiel_zeile


# ============================================================================
# Kriterium: fehlende Pflichtspalte, deutsche Meldung, kein Stacktrace
# ============================================================================

def test_fehlende_pflichtspalte_meldet_deutsch(tmp_path):
    quelle = datei_schreiben(
        tmp_path,
        [{'SearchString': BEISPIEL_ECHTE_STRASSE, 'PLZ': '5620',
          'Stadt': 'Bremgarten'}],
        spalten=('SearchString', 'PLZ', 'Stadt'))

    bericht = pruefe_datei(quelle)

    befund = bericht.befund('pflichtspalten')
    assert befund is not None
    assert befund.schwere == HINWEIS
    assert 'KundenNr' in befund.meldung
    assert 'SearchString;PLZ;Stadt;KundenNr' in befund.meldung
    assert befund.zeilennummer == 1
    assert befund.beispiel_zeile.startswith('SearchString')
    # Deutsch, ohne ß, ohne Fachsprache.
    text = bericht.als_text()
    assert 'ß' not in text
    for englisch in ('Traceback', 'Error', 'column', 'missing'):
        assert englisch not in text


def test_fehlende_pflichtspalte_wirft_keine_ausnahme(tmp_path):
    """Auch ohne SearchString läuft die Prüfung durch — kein Stacktrace."""
    quelle = datei_schreiben(tmp_path, [{'Irgendwas': 'x'}], spalten=('Irgendwas',))

    bericht = pruefe_datei(quelle)

    befund = bericht.befund('pflichtspalten')
    assert befund is not None
    for spalte in PFLICHTSPALTEN:
        assert spalte in befund.meldung
    assert bericht.kunden == 0


def test_cli_meldet_fehlende_spalte_ohne_stacktrace(tmp_path, capsys):
    quelle = datei_schreiben(tmp_path, [{'SearchString': BEISPIEL_ECHTE_STRASSE}],
                             spalten=('SearchString',))

    code = cli.main(['pruefen', str(quelle)])
    ausgabe = capsys.readouterr().out

    assert code == 0  # ein Hinweis blockiert nicht
    assert 'PLZ' in ausgabe and 'KundenNr' in ausgabe
    assert 'Traceback' not in ausgabe


# ============================================================================
# Kriterium: Datei mit 10'001 Zeilen wird abgewiesen
# ============================================================================

def test_zehntausendeins_zeilen_werden_abgewiesen(tmp_path):
    zeilen = [zeile(f'Muster Laden {i}, Hauptstrasse {i}, 5620 Musterdorf',
                    f'9{i:05d}') for i in range(1, MAX_ZEILEN + 2)]
    quelle = datei_schreiben(tmp_path, zeilen)

    bericht = pruefe_datei(quelle)

    befund = bericht.befund('zeilenzahl')
    assert befund is not None
    assert befund.schwere == ABWEISUNG
    assert bericht.start_moeglich is False
    assert "10'001" in befund.meldung and "10'000" in befund.meldung


def test_genau_zehntausend_zeilen_sind_erlaubt(tmp_path):
    zeilen = [zeile(f'Muster Laden {i}, Hauptstrasse {i}, 5620 Musterdorf',
                    f'9{i:05d}') for i in range(1, MAX_ZEILEN + 1)]
    quelle = datei_schreiben(tmp_path, zeilen)

    bericht = pruefe_datei(quelle)

    assert bericht.befund('zeilenzahl') is None
    assert bericht.start_moeglich is True
    assert bericht.zeilen == MAX_ZEILEN


def test_zu_grosse_datei_startet_keinen_lauf(tmp_path, capsys):
    zeilen = [zeile(f'Muster Laden {i}, Hauptstrasse {i}, 5620 Musterdorf',
                    f'9{i:05d}') for i in range(1, MAX_ZEILEN + 2)]
    quelle = datei_schreiben(tmp_path, zeilen)

    code = cli.main(['lauf', str(quelle), '--datenbank', str(tmp_path / 'l.sqlite'),
                     '--antworten', str(quelle)])
    ausgabe = capsys.readouterr().out

    assert code == 1
    assert 'nicht gestartet' in ausgabe
    assert not (tmp_path / 'l.sqlite').exists()


# ============================================================================
# Die drei Prüfungen warnen, sie blockieren nicht (03_ENTSCHEIDUNGEN.md D)
# ============================================================================

@pytest.mark.parametrize('search_string, art', [
    (BEISPIEL_KOSTENSTELLE, 'kostenstelle'),
    (BEISPIEL_KATEGORIE, 'kategorietitel'),
])
def test_die_drei_pruefungen_blockieren_nicht(tmp_path, search_string, art):
    quelle = datei_schreiben(tmp_path, [zeile(search_string)])

    bericht = pruefe_datei(quelle)

    assert bericht.befund(art).schwere == HINWEIS
    assert bericht.start_moeglich is True


def test_lauf_startet_trotz_hinweisen(tmp_path, capsys):
    """Der Nutzer entscheidet: gewarnt wird, gestoppt nicht."""
    quelle = datei_schreiben(tmp_path, [
        zeile(BEISPIEL_KOSTENSTELLE, '900001'),
        zeile(BEISPIEL_KATEGORIE, '900002'),
    ])

    code = cli.main(['lauf', str(quelle), '--datenbank', str(tmp_path / 'l.sqlite'),
                     '--antworten', str(quelle), '--ausgabe', str(tmp_path / 'aus')])
    ausgabe = capsys.readouterr().out

    assert code == 0
    assert 'Strassenfeld' in ausgabe
    assert 'Branche' in ausgabe
    assert (tmp_path / 'aus' / 'nicht_moeglich.csv').exists()


# ============================================================================
# Jede Meldung nennt Anzahl, Beispielzeile und Zeilennummer
# ============================================================================

def test_jede_meldung_nennt_anzahl_beispiel_und_zeilennummer(tmp_path):
    zeilen = [zeile('Muster Laden, Hauptstrasse 1, 5620 Musterdorf', '900001')]
    zeilen += [zeile(BEISPIEL_KOSTENSTELLE, f'9000{i:02d}') for i in range(2, 5)]
    zeilen += [zeile('Kiosk, Dorfweg 2, 5620 Musterdorf', '900010')]
    quelle = datei_schreiben(tmp_path, zeilen)

    bericht = pruefe_datei(quelle)
    text = bericht.als_text()

    kostenstelle = bericht.befund('kostenstelle')
    assert kostenstelle.anzahl == 3
    assert kostenstelle.zeilennummer == 3  # erste betroffene Zeile
    assert 'KST 715611 0' in kostenstelle.beispiel_zeile

    kategorie = bericht.befund('kategorietitel')
    assert kategorie.anzahl == 1
    assert kategorie.zeilennummer == 6

    # Alles davon steht auch im Text, den der Nutzer sieht.
    assert '3 Zeilen' in text
    assert 'Beispiel Zeile 3' in text
    assert 'Beispiel Zeile 6' in text


def test_zeilennummer_zaehlt_wie_in_excel(tmp_path):
    """Kopfzeile ist Zeile 1, der erste Datensatz steht auf Zeile 2."""
    quelle = datei_schreiben(tmp_path, [zeile(BEISPIEL_KOSTENSTELLE)])

    bericht = pruefe_datei(quelle)

    assert bericht.befund('kostenstelle').zeilennummer == 2
    rohzeilen = quelle.read_text(encoding='utf-8-sig').splitlines()
    assert rohzeilen[1].startswith('Emil Frey AG')


def test_bericht_meldet_die_zeilenzahl_auch_ohne_befund(tmp_path):
    quelle = datei_schreiben(tmp_path, [
        zeile('Denner, Hauptstrasse 5, 5620 Bremgarten', '900001'),
        zeile('Volg, Seestrasse 8, 8700 Seedorf', '900002'),
    ])

    bericht = pruefe_datei(quelle)

    assert bericht.befunde == []
    text = bericht.als_text()
    assert 'Kunden: 2 (2 Zeilen)' in text
    assert 'in Ordnung' in text


# ============================================================================
# Die Erkennung im Einzelnen
# ============================================================================

@pytest.mark.parametrize('strasse, erwartet', [
    ('KST 715611 0', True),
    ('kst 4711', True),
    ('KOST 88', True),
    ('715611', True),
    ('', True),
    ('12 34', True),
    ('Hauptstrasse 5', False),
    ('Rue des Tilleuls 5', False),
    ('Via Motta 3', False),
    ('Im Feld 7', False),
])
def test_kostenstellen_erkennung(strasse, erwartet):
    assert ist_kostenstelle(strasse) is erwartet


@pytest.mark.parametrize('titel, erwartet', [
    ('Boucherie', True),
    ('Restaurant', True),
    ('Kiosk', True),
    ('Lebensmittelgeschäft', True),
    ('Bäckerei', True),
    ('Restaurant Pizzeria', True),
    ('Denner', False),
    ('Restaurant Waldegg', False),
    ('Boucherie Dupont', False),
    ('Emil Frey AG', False),
    ('', False),
])
def test_kategorietitel_erkennung(titel, erwartet):
    assert ist_kategorietitel(titel) is erwartet


def test_scoring_liste_bleibt_unangetastet():
    """
    03_ENTSCHEIDUNGEN.md B3: GENERIC_FIRST_WORDS wird nicht verändert.

    Die Prüfung beim Hochladen benutzt eine Obermenge davon; die Liste, an der
    das Scoring hängt, bleibt Wort für Wort dieselbe.
    """
    assert len(DataCleaner.GENERIC_FIRST_WORDS) == 38
    assert 'boucherie' not in DataCleaner.GENERIC_FIRST_WORDS
    assert set(DataCleaner.GENERIC_FIRST_WORDS) <= KATEGORIE_WOERTER
    assert 'boucherie' in KATEGORIE_WOERTER


def test_gemischte_datei_zaehlt_jede_pruefung_einzeln(tmp_path):
    zeilen = [
        zeile(BEISPIEL_KOSTENSTELLE, '900001'),
        zeile(BEISPIEL_KATEGORIE, '900002'),
        zeile('Kiosk, KST 99, 5620 Musterdorf', '900003'),   # beides
        zeile('Denner, Hauptstrasse 5, 5620 Bremgarten', '900004'),
    ]
    quelle = datei_schreiben(tmp_path, zeilen)

    bericht = pruefe_datei(quelle)

    assert bericht.befund('kostenstelle').anzahl == 2
    assert bericht.befund('kategorietitel').anzahl == 2
    assert bericht.zeilen == 4
    assert bericht.kunden == 4


def test_schweizer_tausendertrennung():
    assert zahl(1000) == "1'000"
    assert zahl(10001) == "10'001"
    assert zahl(999) == '999'
