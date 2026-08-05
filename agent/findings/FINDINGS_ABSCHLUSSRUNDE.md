# Findings — Abschlussrunde, Teil 1

Datum: 05.08.2026
Bearbeitete Runde: Abschlussrunde nach `ABSCHLUSSRUNDE.md`, **Teil 1**
Status: fertig

Umfang dieser Runde: **Teil 1 — die Rückentwicklung bei den unvollständigen
Suchbegriffen.** Teil 2 (toter Code) ist bewusst nicht angefasst; die Begründung
steht in Abschnitt 7.

Testlauf: `venv/bin/python -m pytest` → **362 grün, 1 übersprungen**, fünfmal
hintereinander (Abschnitt 6.1). Fassungen unverändert: `apify-client` 2.0.0,
`thefuzz` 0.22.1.

---

## 1. Abnahmekriterien

| # | Kriterium | Status | Beleg |
|---|---|---|---|
| 1 | `Denner, Hauptstrasse 5, 5620 Bremgarten` löst **nicht** aus | grün | `test_vollstaendiger_suchbegriff_loest_nicht_aus` |
| 2 | `Denner Bremgarten` löst aus | grün | `test_suchbegriff_ohne_komma_loest_aus` |
| 3 | `Denner, 5620 Bremgarten` löst aus | grün | `test_suchbegriff_ohne_strasse_loest_aus` — und hält zusätzlich fest, dass keine der bisherigen Prüfungen diese Zeile sieht |
| 4 | Leerer `SearchString` löst aus | grün | `test_leerer_suchbegriff_loest_aus` |
| 5 | Modus B ist unberührt | grün | `test_modus_b_kennt_die_pruefung_nicht`, `test_modus_b_bleibt_still_auch_mit_einer_searchstring_spalte` |
| 6 | Die Prüfung warnt und blockiert nicht | grün | `test_die_pruefung_warnt_und_blockiert_nicht` — `schwere == HINWEIS`, `start_moeglich` bleibt wahr |
| 7 | Fünf vollständige Läufe | grün | Abschnitt 6.1 |

Dazu, weil eine Prüfung ohne Weg zum Nutzer nichts nützt:
`test_die_warnung_steht_auf_der_seite_datei` schickt die Datei durch die
Weboberfläche und liest die Warnung von der Seite «Datei» ab.

---

## 2. Geänderte und neue Dateien

| Datei | neu / geändert | Was |
|---|---|---|
| `upload_pruefung.py` | geändert | `plz_ort_teil`, `ist_unvollstaendig`, `_pruefe_unvollstaendige_suchbegriffe`. Kopfkommentar: aus drei Prüfungen sind vier geworden. |
| `templates/datei.html` | geändert | Der Satz «Diese Kunden landen voraussichtlich in *Zur Prüfung*» erscheint jetzt auch beim neuen Befund. Er war auf die zwei bestehenden inhaltlichen Prüfungen eingeschränkt. |
| `README.md` | geändert | Eine Aufzählung: Die Anwendung sagt jetzt auch «unvollständige Suchbegriffe». Der Satz war nach der Änderung sonst unvollständig. |
| `test_abschlussrunde_abnahme.py` | **neu** | 29 Tests, einer je Abnahmekriterium und die Ränder. |
| `agent/findings/FINDINGS_ABSCHLUSSRUNDE.md` | **neu** | Dieses Dokument. |

**Nicht angefasst:** die sieben Dateien aus Teil 2 — darunter
`data_preprocessor.py`, die Referenz für diese Prüfung. Ebenso unberührt: die
drei bestehenden Prüfungen, `03_ENTSCHEIDUNGEN.md`, `02_DATENVERTRAG.md`.

---

## 3. Getroffene Annahmen

| Situation | Entscheidung | Warum |
|---|---|---|
| Wann gilt ein Teil als vorhanden? | Wenn nach dem Trennen am Komma etwas übrig bleibt, das nicht nur Leerzeichen ist. | Wörtlich dieselbe Regel wie `_analyze_searchstring` in `data_preprocessor.py`: `split(',')`, jeder Teil `strip()`, leer heisst fehlend. Die Referenz stand noch da, also wurde nicht neu erfunden, sondern nachgebaut. |
| Vier oder mehr Teile | Vollständig. | `Denner, Hauptstrasse 5, 5620 Bremgarten, Zusatz` hat alle drei nötigen Teile; was danach kommt, ist Zugabe. So verhielt sich auch die alte Prüfung. |
| Nennt die Meldung, **welche** Teile fehlen? | Nein. | Der Korrekturplan sagt es ausdrücklich: «Wie viele Teile fehlen, ist für die Meldung nicht nötig; die Beispielzeile zeigt es.» |
| Reihenfolge der vier Prüfungen | Die neue zuerst. | Sie beschreibt die grundlegendste Art von Fehler — der Suchbegriff ist gar nicht erst zerlegbar. Wer den Bericht von oben liest, soll zuerst das lesen, was am ehesten die Ursache ist. |
| «1 Zeilen haben» im Singular | In der **neuen** Meldung behoben: «1 Zeile hat». | Der Satz steht in der Oberfläche. Die beiden bestehenden Meldungen tragen denselben Fehler; die habe ich nicht angefasst — siehe Abschnitt 5. |

---

## 4. Abweichungen von den Vorgaben

Keine.

Zur Einordnung: `03_ENTSCHEIDUNGEN.md D` überschreibt seine Tabelle mit «Diese
drei Prüfungen sind Pflicht». Es sind jetzt vier. Die vierte stammt nicht aus
`03 D`, sondern aus `02_DATENVERTRAG.md` §1 — die Regel stand dort von Anfang
an, sie war nur nirgends umgesetzt. `03 D` nennt ein Minimum, keine
Obergrenze, und die Abschlussrunde verlangt die vierte ausdrücklich. Ob `03 D`
den Zusatz aufnehmen soll, entscheidet der Prüfer; ich habe das Dokument nicht
angefasst.

---

## 5. Was gefunden wurde

| Fund | Datei / Stelle | Auswirkung | eingegriffen? |
|---|---|---|---|
| **Der Fall, den der Korrekturplan als zweiten nennt, war der einzige völlig unsichtbare.** `Denner, 5620 Bremgarten` hat zwei Teile; im Strassenfeld steht damit `5620 Bremgarten`. Das ist eine Buchstabenfolge, also schweigt die Kostenstellenprüfung, und ein Kategoriename ist es auch nicht. | `upload_pruefung.py` | Diese Zeilen gingen ungewarnt zu Apify. Die drei anderen Beispiele (kein Komma, leerer Mittelteil, leer) wurden immerhin schon als «Kostenstelle» gemeldet — mit einem Text, der etwas anderes behauptet. | **ja** — das ist Teil 1 |
| **Drei der vier Arten unvollständiger Zeilen werden jetzt doppelt gemeldet.** Ist der Strassenteil leer, findet die Kostenstellenprüfung dort keine Buchstabenfolge und meldet «kein Strassenname, sondern zum Beispiel eine Kostenstelle». Dieselbe Zeile erscheint als Beispiel unter zwei Befunden. | `upload_pruefung.py`, `_pruefe_kostenstellen` | Der Bericht sagt zweimal etwas über dieselbe Zeile, und die zweite Aussage ist die ungenauere: Bei `Denner Bremgarten` gibt es kein Strassenfeld, in dem etwas Falsches stünde — der Suchbegriff ist gar nicht zerlegt. Gemessen in Abschnitt 6.3. | **nein** — die Kostenstellenprüfung ist seit Phase 4 abgenommen, ihre Zeilenzahlen sind dort in Tests festgehalten, und der Umfang dieser Runde ist Teil 1. Vorschlag in Abschnitt 7 |
| **«1 Zeilen haben» — Singular fehlt in den beiden bestehenden Meldungen.** «1 Zeilen haben im Strassenfeld keinen Strassennamen». | `upload_pruefung.py`, `_pruefe_kostenstellen` und `_pruefe_kategorietitel` | Sichtbar in der Oberfläche, sobald genau eine Zeile betroffen ist — bei den gemessenen 14 und 11 Treffern je Batch nicht der Regelfall, aber möglich. In meiner neuen Meldung behoben, in den beiden alten nicht. | **teilweise** — nur die neue Meldung, siehe Abschnitt 3 |
| **Das README kennt die Prüfmaske aus Phase 8 nicht.** Schritt 4 endet mit «Ergebnis — die drei Dateien zum Herunterladen»; dass die Prüffälle im Browser entschieden werden, steht nirgends. | `README.md` | Phase 7 verlangte ein README, dem «jemand ohne Vorkenntnisse dem Ablauf folgen kann». Phase 8 hat dem Ablauf einen Schritt hinzugefügt, ohne das README nachzuziehen; abgenommen wurde es trotzdem. Der Nutzer findet die Maske nur über den Knopf auf der Ergebnisseite. | **nein** — ausserhalb von Teil 1. Vorschlag in Abschnitt 7 |

---

## 6. Messwerte

### 6.1 Fünf vollständige Testläufe

| Lauf | Ergebnis | Dauer |
|---|---|---|
| 1 | 362 grün, 1 übersprungen | 35.87 s |
| 2 | 362 grün, 1 übersprungen | 24.14 s |
| 3 | 362 grün, 1 übersprungen | 24.11 s |
| 4 | 362 grün, 1 übersprungen | 24.31 s |
| 5 | 362 grün, 1 übersprungen | 24.06 s |
| 6 | 362 grün, 1 übersprungen | 23.81 s |

Der erste Lauf war langsamer, weil auf diesem Rechner noch Reste eines
abgebrochenen Laufs liefen; am Ergebnis ändert das nichts. Der sechste Lauf kam
dazu, weil während des ersten noch ein Satz im README geändert wurde — kein
Test hängt daran, aber so sind fünf Läufe belegt, die den unveränderten
Endstand gesehen haben.

333 vor dieser Runde, plus 29 neue — 362. Der eine übersprungene ist weiterhin
der 180-Sekunden-Langläufer aus Phase 2.

### 6.2 Was die Prüfung erkennt

| Suchbegriff | unvollständig |
|---|---|
| `Denner, Hauptstrasse 5, 5620 Bremgarten` | nein |
| `Denner Bremgarten` | **ja** |
| `Denner, 5620 Bremgarten` | **ja** |
| `` (leer) | **ja** |
| `Denner, , 5620 Bremgarten` | **ja** |
| `Denner, Hauptstrasse 5, ` | **ja** |
| `, Hauptstrasse 5, 5620 Bremgarten` | **ja** |
| `Denner, Hauptstrasse 5, 5620 Bremgarten, Zusatz` | nein |
| `Boucherie Meier, Rue des Tilleuls 5, 1800 Vevey` | nein |
| `Osteria, Via Nassa 12, 6900 Lugano` | nein |
| `Emil Frey AG, KST 715611 0, 5745 Safenwil` | nein — vollständig, aber inhaltlich falsch |

Die letzte Zeile ist der Grund, warum die Prüfung neben der Kostenstellenprüfung
steht und sie nicht ersetzt: Eine Kostenstelle ist ein **vollständiger**
Suchbegriff mit falschem Inhalt.

### 6.3 Die Überschneidung mit der Kostenstellenprüfung

| Art der Zeile | neue Prüfung | Kostenstellenprüfung | doppelt gemeldet |
|---|---|---|---|
| kein Komma (`Denner Bremgarten`) | ja | ja | **ja** |
| zwei Teile (`Denner, 5620 Bremgarten`) | ja | nein | nein — **nur die neue sieht sie** |
| leerer Mittelteil | ja | ja | **ja** |
| leerer Suchbegriff | ja | ja | **ja** |
| Kostenstelle | nein | ja | nein |

Drei von vier Arten erscheinen unter zwei Befunden. Der Bericht sieht dann so
aus:

```
2 Zeilen haben keinen vollständigen Suchbegriff. Erwartet werden drei durch
Komma getrennte Teile: Name, Strasse mit Hausnummer, PLZ mit Ort.
Beispiel Zeile 2: «Denner Bremgarten;5620;Bremgarten;900001»

1 Zeilen haben im Strassenfeld keinen Strassennamen, sondern zum Beispiel eine
Kostenstelle. Ohne Strasse findet die Suche die Adresse nicht.
Beispiel Zeile 2: «Denner Bremgarten;5620;Bremgarten;900001»
```

Dieselbe Zeile, zwei Aussagen, davon eine ungenau. Vorschlag in Abschnitt 7.

### 6.4 Was der Nutzer liest

Bei genau einer betroffenen Zeile, mit der neuen Meldung:

> 1 Zeile hat keinen vollständigen Suchbegriff. Erwartet werden drei durch
> Komma getrennte Teile: Name, Strasse mit Hausnummer, PLZ mit Ort.
> Beispiel Zeile 2: «Denner, 5620 Bremgarten;5620;B;900001»
>
> Der Lauf kann trotzdem gestartet werden. Die genannten Zeilen landen
> voraussichtlich in der Datei «zur Prüfung».

Deutsch, Schweizer Schreibweise, Anzahl und Beispielzeile im Original, und der
Nutzer entscheidet.

### 6.5 Dass die Tests beissen

Die Prüfung aus der Reihe genommen, sonst nichts geändert:

```
mit der Prüfung:   29 passed
ohne die Prüfung:  5 failed, 24 passed
```

Umgefallen sind die fünf, die das Verhalten am ganzen Bericht prüfen — die
Warnung, die Meldung, der Berichtstext, die Tausendertrennung und das
Zusammenspiel der vier Prüfungen.

---

## 7. Für die nächste Runde

- **Teil 2 steht noch aus** und ist bewusst nicht angefasst: `ABSCHLUSSRUNDE.md`
  verlangt Teil 1 zuerst und abgenommen, weil `data_preprocessor.py` die
  Referenz für die nachgebaute Prüfung ist. Alle sieben Dateien stehen
  unverändert da.
- **Die Doppelmeldung** (Abschnitt 5 und 6.3). Der Eingriff wäre klein: Die
  Kostenstellenprüfung überspringt Zeilen, die schon als unvollständig gemeldet
  sind. Dann sagt der Bericht über jede Zeile genau einmal etwas, und zwar das
  Genauere. Ich habe es nicht getan, weil die Kostenstellenprüfung seit Phase 4
  abgenommen ist und ihre Zeilenzahlen dort in Tests festhalten — das ist eine
  Entscheidung des Prüfers, kein Bugfix.
- **«1 Zeilen haben»** in den beiden bestehenden Meldungen. Zwei Zeilen Code,
  aber dieselbe Überlegung wie oben.
- **Das README kennt die Prüfmaske nicht.** Schritt 4 des Ablaufs endet beim
  Herunterladen. Gehört in dieselbe Runde wie die zwei Punkte darüber.
- **`data_consolidator.py`** wartet weiterhin auf die Antwort des Auftraggebers:
  Batches zu 2'513 oder eine Datei in einem Auftrag? Bis dahin bleibt die Datei
  stehen, wie in `ABSCHLUSSRUNDE.md` festgelegt.
- **Unverändert beim Auftraggeber:** SMTP-Freigabe durch die ICT und ein echter
  Versand über das Firmen-Relais; Google Places aufschalten und ein Live-Abruf
  für Modus B; die Zulässigkeit eines privaten Gmail-Kontos für Firmendaten;
  Batch 5.

---

## 8. Zeit

| Arbeitspaket | grober Aufwand |
|---|---|
| Abschlussrunde und `data_preprocessor.py` lesen | 0.25 h |
| Die Prüfung nachbauen | 0.5 h |
| 29 Tests, Gegenprobe | 0.75 h |
| Überschneidung messen, Bericht von Hand lesen | 0.5 h |
| Fünf Testläufe | 0.25 h |
| Findings | 0.5 h |
| **gesamt** | **≈ 2.75 h** |

Der Befund selbst war in zehn Minuten nachgebaut — die Referenz stand ja noch
da, und das war der Sinn der Reihenfolge. Der Aufwand lag im Danebenliegenden:
dass drei der vier Fälle schon gemeldet wurden, aber unter dem falschen Titel,
und dass ausgerechnet der vierte, den der Korrekturplan als Beispiel nennt,
bisher durch jede Prüfung fiel.
