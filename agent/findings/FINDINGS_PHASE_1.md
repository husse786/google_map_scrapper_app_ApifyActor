# Findings — Phase 1, Version 1.0

Datum: 03.08.2026
Bearbeitete Phase: 1 — Kern reparieren und aus der GUI lösen
Status: fertig

Branch: `umbau/webapp`. `main` unberührt.
Testlauf: `python -m pytest` → **48 Tests, alle grün**.

---

## 1. Abnahmekriterien

| # | Kriterium | Status | Beleg |
|---|---|---|---|
| 1 | `pytest` grün, inklusive der bestehenden Tests aus `test_data_cleaner.py` | grün | `python -m pytest` → 48 passed. `test_data_cleaner.py` enthält weiterhin alle acht ursprünglichen Szenarien, auf pytest umgestellt und auf den Datenvertrag angepasst. Zu Test 6 siehe Abschnitt 5. |
| 2 | Neuer Test: keine `KundenNr` erscheint in mehr als einer der drei Ausgabedateien | grün | `test_phase1_abnahme.py::test_keine_kundennr_in_zwei_dateien`. Zusätzlich real geprüft: batch_3 und batch_4, alle drei Schnittmengen leer (Abschnitt 6). |
| 3 | Neuer Test: Summe der Kunden über alle drei Dateien = Anzahl Kunden in der Eingabe | grün | `test_summe_der_kunden_stimmt`. Real: 1'603 + 745 + 165 = 2'513 (batch_3), 1'494 + 849 + 170 = 2'513 (batch_4). |
| 4 | Neuer Test: alle sieben Beispielpaare aus `03_ENTSCHEIDUNGEN.md` B1 werden korrekt entschieden | grün | `test_strassenvergleich_b1`, sieben parametrisierte Fälle. Zusätzlich `test_hausnummern_logik_unveraendert`. |
| 5 | Neuer Test: Einzeltreffer-Regel B2 greift, Rebranding-Fall bleibt in ① | grün | `test_einzeltreffer_namensscore_reicht`, `test_einzeltreffer_rebranding_bleibt_in_eins` (Score 11 < 60, Adresse exakt → ①), `test_einzeltreffer_unsicher_geht_zur_pruefung`, `test_einzeltreffer_ohne_hausnummer_faellt_auf_namen_zurueck`. |
| 6 | `score` und `grund` sind in allen drei Ausgabedateien befüllt, keine leeren Werte | grün | `test_score_und_grund_befuellt` (je Datei), `test_spalten_nach_datenvertrag`, `test_gruende_ohne_fachsprache`. Real nachgezählt: 0 leere Werte in `score`, `grund`, `qualitaet` über alle 4'313 bzw. 4'651 Ausgabezeilen. |
| 7 | Alle 10 Fälle der Fixture landen dort, wo `05_TESTDATEN.md` es vorgibt — insbesondere 900002 und 900009 nur noch in einer Datei, 900005 weiterhin in ① | grün | `test_fixture_faelle` (10 parametrisierte Fälle, prüft auch Abwesenheit in den beiden anderen Dateien), `test_doppelzaehlung_behoben` für 900002/900009, `test_900003_nimmt_nur_die_echte_dorfstrasse`. Vollständige Liste in Abschnitt 6. |
| 8 | Vergleichslauf dokumentiert, Fixture vollständig, reale Datei nur aggregiert, Einzelfallliste unter `Daten/` und nicht committet | grün | Abschnitt 6. Einzelfalllisten: `Daten/_vergleich_phase1/wechsler_batch_3.csv` und `wechsler_batch_4.csv`. `Daten/` ist in `.gitignore`, `git status` zeigt keine dieser Dateien. |

---

## 2. Geänderte und neue Dateien

| Datei | neu / geändert / entfernt | Was |
|---|---|---|
| `data_cleaner.py` | geändert | B1 bis B4. Ausgabe nach `02_DATENVERTRAG.md` §2/§3/§4: vier Dateien mit festen Namen, 21 Spalten in fester Reihenfolge, `qualitaet` aus der geschlossenen Liste, `score` und `grund` in jeder Zeile. Entscheid pro Kunde in `_process_customer`, Einzeltreffer in `_decide_single_hit`, Score-Stufen in `_decide_by_score`. Scoring, Gewichtungen, Schwellen 80/30 und `thefuzz` unverändert. |
| `cli.py` | neu | Schlanke Kommandozeile ohne Tkinter: `python cli.py <datei> [--ausgabe <ordner>]`. Deutsche Meldungen, keine Stacktraces, technische Details in `logs/bereinigung.log`. |
| `test_data_cleaner.py` | geändert | Die acht bestehenden Szenarien, auf pytest umgestellt und an den Datenvertrag angepasst. |
| `test_phase1_abnahme.py` | neu | Ein Test je Abnahmekriterium plus weitere Zustände des Datenvertrags (keine PLZ-Treffer, leere Zeile neben Treffer, leerer Suchbegriff, Dateien immer mit Kopfzeile). |
| `main.py` | entfernt | Tkinter-Einstieg, ersetzt durch `cli.py`. |
| `ui_manager.py` | entfernt | Tkinter-Oberfläche. |
| `requirements.txt` | geändert | `pytest` ergänzt. |
| `README.md` | geändert | Zwei Stellen korrigiert, die auf `main.py` zeigten. Vollständige Überarbeitung ist Phase 7. |

Nicht angefasst: `apify_wrapper.py`, `csv_processor.py`, `csv_postprocessor.py`,
`data_preprocessor.py`, `data_consolidator.py`, `config*.py`, `logger_config.py`.

---

## 3. Getroffene Annahmen

| Situation | Entscheidung | Warum |
|---|---|---|
| Der Datenvertrag nennt feste Dateinamen (`fertig_fuer_erp.csv` …), zwei Läufe im selben Ordner würden sich überschreiben | Die vier Dateien landen in einem Ordner. Ohne `--ausgabe` ist das `<eingabename>_ergebnis` neben der Eingabedatei. | Dateinamen bleiben exakt wie vorgegeben; ab Phase 3 bekommt jeder Job ohnehin seinen eigenen Ordner. |
| `aussortiert.csv` ist keine der drei Dateien, der Vertrag sagt nichts zu ihren Spalten | Sie bekommt dieselben 21 Spalten und ebenfalls `score` und `grund`. | Ein Format statt zwei; für die Fehlersuche ist der Grund dort genauso nützlich. |
| Ein Kunde hat eine leere und eine gefüllte Ergebniszeile | Die leere Zeile geht nach `aussortiert`, der Kunde wird über die gefüllten Zeilen entschieden. | Sonst stünde er in ③ **und** in ① oder ②. Trat real einmal auf (batch_4). |
| `NICHT_MOEGLICH (Eingabe unbrauchbar)` — welches Pflichtfeld löst aus? | Nur ein leerer `SearchString`. Eine fehlende PLZ löst nichts aus. | Ohne Suchbegriff ist keine Entscheidung möglich; eine fehlende PLZ schaltet nur den PLZ-Filter ab. Die Pflichtfeldprüfung beim Upload ist Phase 4. |
| Score für Zeilen ohne Kandidat (③) | `0` | Der Vertrag verlangt einen befüllten Wert, nicht einen sinnvollen Ähnlichkeitswert. |
| Wann wird der Score berechnet? | Einmal für alle gefüllten Zeilen eines Kunden, direkt nach der Leerprüfung. | Der Score hängt nur von `SearchString` und `title` ab, nicht von den übrigen Zeilen. Die Werte sind identisch mit der bisherigen Berechnung, aber jede Ausgabezeile trägt ihn. |
| B2 Bedingung (2): was heisst „exakt"? | Nach der Normalisierung zeichengleicher Strassenname **und** auf beiden Seiten eine Hausnummer, die gleich ist. | Strenger als der Fuzzy-Vergleich. Fehlt eine Hausnummer, entscheidet allein der Namensscore — im Zweifel ②. |
| Was gehört in die CLI? | Nur die Bereinigung. | Die Anreicherung braucht den Provider aus Phase 2; ein Platzhalter dafür wäre Vorbau. |
| `main.py` und `ui_manager.py` | gelöscht | B5 und `CLAUDE.md`. Wiederherstellbar über `git show main:main.py`. Was daraus in Phase 2/3 gebraucht wird, steht in Abschnitt 7. |
| Reihenfolge der Kunden in der Ausgabe | `groupby(sort=False)`, also Reihenfolge der Eingabedatei statt alphabetisch nach `KundenNr`. | Für den Sachbearbeiter ist die Reihenfolge seiner eigenen Datei nachvollziehbarer. |
| Testdaten von Test 6 (`test_dynamic_threshold`) | ersetzt | Die alten Werte erreichten 100 und 83 Punkte und liefen deshalb nie in den dynamischen Zweig. Details in Abschnitt 5. |
| Welche reale Datei für den Vergleich? | `Daten/V2/Prod/batch_3/…_optimierte_daten.csv` und `batch_4/…` (von Husey benannt) | 2× 2'513 Kunden, neuester Produktivstand. |
| `pytest` fehlte in `requirements.txt` | ergänzt | `03_ENTSCHEIDUNGEN.md` A nennt pytest als Testwerkzeug. |

---

## 4. Abweichungen von den Vorgaben

Keine. Schwellen (80, 30, 90, 60), Gewichtungen, `GENERIC_FIRST_WORDS`,
`LEGAL_SUFFIXES`, PLZ-Vergleich, `token_set_ratio` und `thefuzz` sind unverändert.
Spaltennamen, Dateinamen und die `qualitaet`-Werte stammen wörtlich aus
`02_DATENVERTRAG.md`; auf realen Daten traten ausschliesslich Werte aus der
geschlossenen Liste auf.

---

## 5. Was im Bestandscode gefunden wurde

| Fund | Datei / Stelle | Auswirkung | eingegriffen? |
|---|---|---|---|
| Doppelzählung bei null Strassentreffern (Fehler B1) | `data_cleaner.py`, Stufe 4 | Kunde stand in `zur_pruefung` und `aussortiert`. Alle bisherigen Statistiken über „aussortiert" sind dadurch zu hoch: real 995 statt 552 (batch_3) und 1'169 statt 662 (batch_4) Kunden. | ja |
| Dieselbe Doppelzählung bei null PLZ-Treffern | `data_cleaner.py`, Stufe 2 | Gleiche Wirkung, im Phasenplan nicht benannt. Auf den beiden realen Batches trat der Fall nie ein, in der Fixture ebenfalls nicht. | ja |
| Leere Ergebniszeilen wurden **immer** nach `erneut_crawlen` geschrieben, auch wenn der Kunde daneben echte Treffer hatte | `data_cleaner.py`, Schritt 1 | Dritte Form derselben Doppelzählung. Real einmal aufgetreten (batch_4: ein Kunde in ① und ③). | ja |
| `_street_matches` nutzte `partial_ratio > 90` (Fehler B2 des Umbauplans) | `data_cleaner.py` | Falsche Strasse konnte ins ERP. Messbar: in batch_4 wurde bei vier Kunden, die vorher und nachher in ① stehen, ein **anderer** Treffer gewählt — vier falsche Adressen im ERP-Import, die niemand bemerkt hätte. | ja |
| Einzeltreffer wurde ungeprüft akzeptiert | `data_cleaner.py`, Stufe 3 | Real 157 Kunden je Batch, die jetzt zur Prüfung gehen statt ungeprüft ins ERP. | ja |
| `score` wurde vor dem Schreiben verworfen | `data_cleaner.py`, Ausgabe | Keine Nachvollziehbarkeit. | ja |
| `qualitaet`-Wert `'OK'` und Präfix `ZUR_PRUEFUNG` | `data_cleaner.py` | Stehen nicht in der Liste aus `02_DATENVERTRAG.md` §3. | ja, auf die Vertragswerte umgestellt |
| Toter Pfad `ZUR_PRUEFUNG (niedriger Score)` | `data_cleaner.py`, Stufe 5 | Über die Weiche nicht erreichbar (Gruppen mit einer Zeile werden vorher abgefangen). | ja, als abgesicherter Zweig mit vertragskonformem Wert erhalten |
| Leere Ausgabelisten wurden ohne Kopfzeile geschrieben | `data_cleaner.py`, Ausgabe | `pd.read_csv` auf einer leeren Datei wirft `EmptyDataError` — jeder Folgeschritt wäre abgestürzt. | ja, alle vier Dateien haben immer die volle Kopfzeile |
| `test_data_cleaner.py` war keine pytest-Suite | Testdatei | Die Klasse hat einen `__init__`, pytest sammelt sie nicht ein. Die Tests liefen nur über `python test_data_cleaner.py`. „pytest grün" war vorher inhaltsleer. | ja, konvertiert |
| Test 6 prüfte nicht, was sein Name sagt | `test_data_cleaner.py` | „Coiffeur Baumann" (100) und „Coiffeur Shop" (83) liegen beide über 80, der dynamische Abstand kam nie zum Zug. Der Test wäre ausserdem an der leeren Ausgabedatei gescheitert. | ja, Testdaten ersetzt (jetzt 80 gegen 26) |
| `logger_config.py` konfiguriert den Logger `AppLogger`, alle Module nutzen `logging.getLogger(__name__)` | `logger_config.py` | Die Modul-Logs erreichten die Logdatei nie. | nein — `cli.py` konfiguriert den Root-Logger selbst |
| `_normalize_text` ersetzt `g.` durch `gasse` und `pl.` durch `platz` an beliebiger Stelle | `data_cleaner.py` | Bei abgekürzten Vornamen entsteht Unsinn: „Rue G. Muller" wird zu „rue gasse muller". Betrifft beide Vergleichsseiten gleich, verzerrt aber den Score. | nein — Änderung würde Schwellenwerte entwerten (`03` B3) |
| `data_cleaner.py.bak` liegt im Repository | Projektwurzel | Alte Fassung, wird von nichts importiert. | nein — ausserhalb des Umfangs |
| Das mitgelieferte `venv/` ist unbrauchbar | `venv/bin/*` | Die Shebangs zeigen auf einen Pfad, den es nicht mehr gibt. `venv/bin/pip` startet nicht, `venv/bin/python -m pip` schon. | nein |
| `clean_input_data.py` (laut Umbauplan „weg") | Projektwurzel | Einmalskript mit festem Pfad. | nein — nicht Umfang von Phase 1 |

---

## 6. Messwerte

### 6.1 Fixture — vollständig, alle zehn Fälle

Erfundene Daten, deshalb hier vollständig zitierbar.

| KundenNr | vorher | vorher `qualitaet` | nachher | nachher `qualitaet` | Soll nach `05_TESTDATEN.md` |
|---|---|---|---|---|---|
| 900001 | ① | `OK (Strasse)` | ① | `OK (Strasse)` | ① `OK (Strasse)` ✔ |
| 900002 | ② **+ aussortiert** | `ZUR_PRUEFUNG (keine Strassentreffer)` | ② | `PRUEFUNG (keine Strassentreffer)` | ② und nicht zusätzlich aussortiert ✔ |
| 900003 | ② | `ZUR_PRUEFUNG (mehrere hohe Treffer)` | ① | `OK (Strasse)` | ① ✔ |
| 900004 | ① | `OK` | ① | `OK (Einzeltreffer)` | ① ✔ |
| 900005 | ① | `OK` | ① | `OK (Einzeltreffer)` | ① ✔ |
| 900006 | ① | `OK` | ① | `OK (Einzeltreffer)` | ① ✔ |
| 900007 | ② | `ZUR_PRUEFUNG (mehrere hohe Treffer)` | ② | `PRUEFUNG (mehrere hohe Treffer)` | ② ✔ |
| 900008 | ③ | — | ③ | `NICHT_MOEGLICH (kein Ergebnis)` | ③ ✔ |
| 900009 | ② **+ aussortiert** | `ZUR_PRUEFUNG (keine Strassentreffer)` | ② | `PRUEFUNG (keine Strassentreffer)` | ② und nicht zusätzlich aussortiert ✔ |
| 900010 | ① | `OK` | ① | `OK (Einzeltreffer)` | ① ✔ |

| | vorher | nachher |
|---|---|---|
| ① `fertig_fuer_erp` | 5 | 6 |
| ② `zur_pruefung` | 4 | 3 |
| ③ `nicht_moeglich` | 1 | 1 |
| Kunden zusätzlich in `aussortiert` | 3 | 2 |

Ein Wechsler: **900003 von ② nach ①**. Vorher wurden „Oberdorfstrasse 5" und
„Dorfstrasse 5" beide als Treffer der gesuchten Dorfstrasse gewertet, zwei hohe
Scores ergaben einen Prüffall. Mit `fuzz.ratio` (85 < 90) fällt die
Oberdorfstrasse weg, es bleibt genau ein Strassentreffer.

Die verbliebenen zwei `aussortiert`-Einträge sind korrekt: 900001 (eine falsche
PLZ, eine falsche Strasse) und 900003 (die Oberdorfstrasse), beide Kunden sind
über eine andere Zeile in ① entschieden.

Beispiele für die neuen Gründe (aus Fixture und Tests, alle Daten erfunden;
die letzte Zeile stammt aus `test_keine_plz_treffer_geht_nur_zur_pruefung`,
weil die Fixture diesen Zustand nicht enthält):

```
Nur ein Treffer liegt an der gesuchten Adresse Hauptstrasse 5: "Denner Musterdorf",
Hauptstrasse 5. Namensähnlichkeit 100 von 100.
Gesucht Wohlerstrasse 23, gefunden Wohlerstrasse 18 und Wohlerstrasse 55.
Mehrere Treffer gleich gut: "Spar Musterheim" (88) und "Spar Musterheim Nord" (87).
Ein einziger Treffer übrig: "Spar Seedorf" an der gesuchten Adresse Seestrasse 8.
Der Name weicht ab (Ähnlichkeit 11 von 100), Strasse und Hausnummer stimmen exakt.
Gesucht Postleitzahl 5620, gefunden 8000 und 9000.
```

### 6.2 Reale Daten — nur aggregiert

Zwei Dateien unter `Daten/V2/Prod/`, je 2'513 Kunden.
Einzelfalllisten mit Kundennummern: `Daten/_vergleich_phase1/wechsler_batch_3.csv`
und `wechsler_batch_4.csv`. Beide liegen unter `Daten/` und sind nicht committet.

**Verteilung**

| | batch_3 vorher | batch_3 nachher | batch_4 vorher | batch_4 nachher |
|---|---|---|---|---|
| ① `fertig_fuer_erp` | 1'776 | 1'603 (−173) | 1'646 | 1'494 (−152) |
| ② `zur_pruefung` | 572 | 745 (+173) | 697 | 849 (+152) |
| ③ `nicht_moeglich` | 165 | 165 (±0) | 171 | 170 (−1) |
| Kunden in **mehr als einer** der drei Dateien | 0 | 0 | 1 | 0 |
| Kunden zusätzlich in `aussortiert` | 995 | 552 | 1'169 | 662 |
| Zeilen gesamt | 5'980 | | 6'651 | |

Die Anteile ①/②/③ liegen nachher bei 64 % / 30 % / 7 % (batch_3) und
59 % / 34 % / 7 % (batch_4).

**Wechsler je Richtung**

| Richtung | batch_3 | batch_4 | Begründungsmuster nachher |
|---|---|---|---|
| ① → ② | 201 | 189 | `PRUEFUNG (Einzeltreffer unsicher)` 157 / 156 · `PRUEFUNG (keine Strassentreffer)` 42 / 33 · `PRUEFUNG (kein klarer Treffer)` 2 / 0 |
| ② → ① | 28 | 38 | `OK (Strasse)` 18 / 34 · `OK (Score)` 7 / 4 · `OK (Dynamisch)` 3 / 0 |
| ①+③ → ② | 0 | 1 | `PRUEFUNG (Einzeltreffer unsicher)` — der Kunde, der vorher in zwei Dateien stand |
| **gesamt** | **229** | **228** | |

**Stiller Fehler, den B2 behebt:** Bei den Kunden, die vorher **und** nachher in ①
stehen, wurde in batch_4 bei **vier** Kunden ein anderer Treffer gewählt, alle
jetzt mit `OK (Strasse)`. Das sind vier Adressen, die mit `partial_ratio` falsch
ins ERP gewandert wären, ohne in irgendeiner Statistik aufzufallen. In batch_3:
null Fälle.

**Verteilung der Begründungen nachher (Kunden)**

| `qualitaet` | batch_3 | batch_4 |
|---|---|---|
| `OK (Einzeltreffer)` | 1'141 | 961 |
| `OK (Strasse)` | 288 | 354 |
| `OK (Score)` | 158 | 158 |
| `OK (Dynamisch)` | 16 | 21 |
| `PRUEFUNG (keine Strassentreffer)` | 448 | 512 |
| `PRUEFUNG (Einzeltreffer unsicher)` | 157 | 157 |
| `PRUEFUNG (kein klarer Treffer)` | 104 | 151 |
| `PRUEFUNG (mehrere hohe Treffer)` | 36 | 29 |
| `NICHT_MOEGLICH (kein Ergebnis)` | 165 | 170 |
| `PRUEFUNG (keine PLZ-Treffer)` | 0 | 0 |

**Einordnung.** Die Korrekturen verschieben rund 7 % der Kunden von ① nach ②.
Das ist die gewollte Richtung: ungeprüfte Einzeltreffer und Treffer an
Nachbarstrassen gehen nicht mehr automatisch ins ERP. Umgekehrt gewinnt der
korrekte Strassenvergleich 28 bzw. 38 Kunden zurück, die vorher unnötig zur
Prüfung gingen. Der grösste Prüfblock bleibt `keine Strassentreffer` mit 448 und
512 Kunden — genau der Block, den die Kostenstellen-Erkennung in Phase 4 angreift.

---

## 7. Für die nächste Phase

- **Schnittstelle für Phase 2/3.** `data_cleaner.py` ist heute dateibasiert:
  CSV rein, CSV raus. Der Entscheid pro Kunde liegt bereits isoliert in
  `_process_customer(kunden_nr, group, …)`. Wenn Phase 2 `Candidate`-Objekte
  liefert, ist das die Stelle, an der das DataFrame durch eine Kandidatenliste
  ersetzt wird. Vorbereitet wurde dafür nichts.
- **Was mit `main.py` verloren geht.** Die Orchestrierung der Anreicherung —
  sechs parallele Worker über `ThreadPoolExecutor`, das Zusammenführen von
  Eingabezeile und API-Ergebnis, die Liste `COLUMNS_TO_KEEP` mit den 18
  Eingangsspalten — stand in `process_enrichment()`. Nachlesbar über
  `git show main:main.py`. Phase 2/3 baut das neu, nicht ich in Phase 1.
- **Zeilenzahl der Ausgabe.** ② hat mehrere Zeilen pro Kunde (real 2'545 bzw.
  2'987 Zeilen für 745 bzw. 849 Kunden), ① und ③ genau eine. Für die
  Fortschrittsanzeige in Phase 3 zählen Kunden, nicht Zeilen.
- **`PRUEFUNG (keine PLZ-Treffer)` kam real kein einziges Mal vor.** Der Zustand
  existiert und ist getestet, aber die Praxis erreicht ihn nicht — der
  PLZ-Vergleich lässt fehlende Werte durch.
- **Stellschraube, falls ② zu gross wird:** die Schwelle 60 aus `03` B2 erzeugt
  157 Prüffälle je Batch. Änderung nur per Korrekturplan.
- **Umgebung.** Das mitgelieferte `venv/` ist kaputt (Abschnitt 5). Bis es neu
  angelegt ist: `venv/bin/python -m pip install -r requirements.txt`.
- **Vor Phase 4 relevant:** die 448 bzw. 512 Kunden mit `keine Strassentreffer`
  sind die Messgrundlage für die Wirkung der Kostenstellen-Prüfung. Die
  Einzelfalllisten liegen bereits unter `Daten/_vergleich_phase1/`.

---

## 8. Zeit

| Arbeitspaket | grober Aufwand |
|---|---|
| Dokumente lesen, Bestandscode verstehen | 0.5 h |
| Vorher-Lauf aufsetzen und sichern | 0.5 h |
| B1 bis B4 plus Ausgabevertrag in `data_cleaner.py` | 2.5 h |
| `cli.py` | 0.5 h |
| Tests (8 bestehende umgestellt, 40 neu) | 1.5 h |
| Vergleichslauf und Auswertung | 1.0 h |
| Findings | 0.75 h |
| **gesamt** | **≈ 7.25 h** |

Die Fehlerbehebung selbst war der kleinere Teil. Der Aufwand steckte im
Ausgabevertrag: 21 Spalten, geschlossene Wertelisten und ein Klartextgrund
für jeden der neun Zustände.
