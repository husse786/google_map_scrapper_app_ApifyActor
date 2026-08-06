# Findings — Historische Dokumente kennzeichnen

Datum: 05.08.2026
Bearbeitete Runde: `FREIGABE_ABSCHLUSSRUNDE.md` Abschnitt 6 — die letzte kurze
Runde nach dem abgeschlossenen Umbau
Status: fertig

Umfang: **`WORKFLOW_AND_HANDOFF.md` und `docs_old/` als historisch
kennzeichnen.** Nicht umschreiben, je ein Kopfabsatz. Sonst nichts.

Testlauf: `venv/bin/python -m pytest` → **383 grün, 1 übersprungen**
(Abschnitt 6). Kein Code geändert.

---

## 1. Abnahmekriterien

| # | Kriterium | Status | Beleg |
|---|---|---|---|
| 1 | Je ein Kopfabsatz mit **Stand** | grün | Fünf Dokumente, jedes mit seinem eigenen Datum aus der Git-Historie — Abschnitt 6.1 |
| 2 | Je ein Kopfabsatz mit **Gültigkeit** | grün | Jeder sagt zuerst «nicht mehr gültig» und danach, was konkret nicht mehr stimmt |
| 3 | Verweis auf `README.md` bzw. `agent/` | grün | Alle sechs relativen Verweise aufgelöst und geprüft — Abschnitt 6.2 |
| 4 | Nicht umschreiben | grün | Kein Zeichen unterhalb des Kopfabsatzes verändert; der Diff besteht ausschliesslich aus eingefügten Blöcken |

---

## 2. Geänderte Dateien

| Datei | Stand des Inhalts | Kopfabsatz |
|---|---|---|
| `WORKFLOW_AND_HANDOFF.md` | 14.04.2026 | ja |
| `docs_old/ALGORITHM_EXPLAINED.md` | 14.04.2026 | ja |
| `docs_old/concepts_&_docs/FileArchitekt.md` | 17.10.2025 | ja |
| `docs_old/concepts_&_docs/DataCleansing/data_cleansing.md` | 06.11.2025 | ja |
| `docs_old/concepts_&_docs/DataCleansing/flow.md` | 25.02.2026 | ja |
| `docs_old/diagrams/datacleansing_logik.svg` | 06.11.2025 | — siehe Abschnitt 3 |
| `agent/findings/FINDINGS_DOKUMENTATION.md` | neu | dieses Dokument |

Die Daten stammen aus `git log --follow`, nicht aus dem Dateidatum: Alle
`docs_old/`-Dateien tragen als letzten Commit den 03.08.2026, weil sie damals in
den Ordner verschoben wurden. Ihr Inhalt ist älter, und das steht jetzt im Kopf.

Kein Code angefasst. Kein Text unterhalb des Kopfabsatzes geändert.

---

## 3. Getroffene Annahmen

| Situation | Entscheidung | Warum |
|---|---|---|
| Sprache der Kopfabsätze — `WORKFLOW_AND_HANDOFF.md` und `ALGORITHM_EXPLAINED.md` sind englisch | **Deutsch**, in allen fünf. | Die Dokumente, auf die verwiesen wird, sind deutsch: `README.md` und alles in `agent/`. Ein Hinweis, der den Leser weiterschickt, soll in der Sprache stehen, in der es weitergeht. Einheitlich in allen fünf, damit der Absatz beim Überfliegen als dasselbe Element erkennbar ist. |
| Wo steht der Absatz? | **Vor** dem Titel, als Blockzitat, gefolgt von einer Trennlinie. | Er soll gelesen werden, bevor der Leser im Inhalt ist — das ist der ganze Zweck. Ein Hinweis unter dem Titel wird beim Springen zum interessanten Abschnitt übersehen. Als Blockzitat hebt er sich sichtbar vom Dokument ab, das er einordnet. |
| Das SVG-Diagramm `datacleansing_logik.svg` | **Kein eigener Kopfabsatz.** Stattdessen nennt der Kopf von `data_cleansing.md` es ausdrücklich mit. | Eine Grafik hat keine Stelle, an der ein Absatz stünde, ohne die Grafik selbst zu verändern — und «nicht umschreiben» gilt. Das Diagramm ist genau einmal eingebettet, nämlich in `data_cleansing.md` Zeile 17; wer es sieht, hat den Hinweis darüber gelesen. |
| Wie viel Inhalt in den Absatz? | Über «veraltet» hinaus: **was konkret nicht mehr stimmt.** | Ein Hinweis «historisch» allein hätte die beiden Irreführungen nicht verhindert. Wer eine Zahl sucht, liest nicht die Kopfzeile, sondern die Tabelle. Deshalb nennt der Kopf von `WORKFLOW_AND_HANDOFF.md` die beiden Stellen mit Zeilennummer, und `ALGORITHM_EXPLAINED.md` die zwei geänderten Regeln. |

---

## 4. Abweichungen von den Vorgaben

Keine.

---

## 5. Was gefunden wurde

| Fund | Auswirkung | eingegriffen? |
|---|---|---|
| **`ALGORITHM_EXPLAINED.md` ist das gefährlichste der fünf.** Die anderen beschreiben Dateien, die es nicht mehr gibt — wer sie liest, merkt es beim ersten Nachsehen. Dieses beschreibt `data_cleaner.py`, das weiterlebt, und das meiste darin stimmt noch. Falsch sind genau die zwei Regeln, die Phase 1 geändert hat: `partial_ratio > 90` → `ratio >= 90` und der ungeprüfte Einzeltreffer. | Ein Leser hätte keinen Anlass zu zweifeln — der Text passt zum Code, bis auf die zwei Stellen, an denen die vier falschen Adressen in batch_4 entstanden. Der Kopfabsatz nennt beide ausdrücklich. | **ja** |
| **`FileArchitekt.md` nennt elf Module, neun davon gibt es nicht mehr.** Geblieben sind `data_cleaner.py` und `config.py`. | Mein erster Entwurf schrieb «die Hälfte» und zählte acht auf — nachgezählt waren es neun von elf, und `apify_wrapper.py` fehlte in der Aufzählung. Beim Nachmessen korrigiert, bevor es im Commit landete. | **ja** |
| **Die Zeilennummern im Kopf von `WORKFLOW_AND_HANDOFF.md` verschoben sich durch den Kopf selbst.** Zitiert waren 306, 311 und 396; nach dem Einfügen von 35 Zeilen stehen die Stellen auf 341, 346 und 431. | Ein Verweis, der auf die falsche Zeile zeigt, ist schlimmer als keiner — besonders in einem Absatz, der vor falschen Zahlen warnt. Nach dem Einfügen nachgeprüft und berichtigt. | **ja** |
| **`agent/UMBAUPLAN_WEBAPP.md` §2 ist weiterhin überholt.** Er führt `csv_processor.py`, `csv_postprocessor.py`, `data_preprocessor.py` und `data_consolidator.py` als «bleibt» und `data_preprocessor.py` als «wird zur Upload-Validierung erweitert». | Anders als die fünf gekennzeichneten Dokumente liegt dieses in `agent/`, also dort, wohin die Kopfabsätze den Leser gerade schicken. Der Widerspruch ist seit den Findings zu Phase 2 und 7 gemeldet. | **nein** — `agent/` gehört dem Prüfer, und der Umfang dieser Runde sind die beiden historischen Orte. Vorschlag in Abschnitt 7 |

---

## 6. Messwerte

### 6.1 Die fünf Kopfabsätze

| Dokument | Stand | Was der Absatz konkret nennt |
|---|---|---|
| `WORKFLOW_AND_HANDOFF.md` | 14.04.2026 | vier Dateien, die es nicht mehr gibt; die «~2 hours» (Zeile 431) und die «4,288 rows» (Zeilen 341 und 346), mit den nachgemessenen Werten 14 und 11 |
| `ALGORITHM_EXPLAINED.md` | 14.04.2026 | die zwei in Phase 1 geänderten Regeln, mit `Dorfstrasse`/`Oberdorfstrasse` als Beispiel |
| `FileArchitekt.md` | 17.10.2025 | neun von elf Modulen entfallen, welche zwei geblieben sind, und wann welches ging |
| `data_cleansing.md` | 06.11.2025 | das entfallene Zwischenformat, und dass der Vorbehalt auch für das eingebettete Diagramm gilt |
| `flow.md` | 25.02.2026 | die entfallenen Zwischendateien, und dass die Prüfung dahinter in der Abschlussrunde nachgebaut wurde |

Jeder Absatz nennt zuerst den Stand, dann die Gültigkeit, dann den Verweis.

### 6.2 Die Verweise

Alle relativen Pfade aufgelöst und gegen das Dateisystem geprüft:

```
OK   WORKFLOW_AND_HANDOFF.md                    -> README.md
OK   WORKFLOW_AND_HANDOFF.md                    -> agent/
OK   docs_old/ALGORITHM_EXPLAINED.md            -> ../README.md
OK   .../FileArchitekt.md                       -> ../../README.md
OK   .../DataCleansing/data_cleansing.md        -> ../../../README.md
OK   .../DataCleansing/flow.md                  -> ../../../README.md
```

Die im Fliesstext genannten Dokumente `agent/01_PHASENPLAN.md`,
`agent/02_DATENVERTRAG.md`, `agent/03_ENTSCHEIDUNGEN.md`,
`agent/UMBAUPLAN_WEBAPP.md` und `agent/findings/` bestehen alle.

### 6.3 Umfang der Änderung

```
5 Dokumente, je ein eingefügter Kopfabsatz
0 Zeilen unterhalb des Kopfabsatzes geändert
0 Zeilen Code geändert
```

Testlauf unverändert: **383 grün, 1 übersprungen** — dieselbe Zahl wie nach der
Abschlussrunde. Kein Test rührt an diese Dokumente; gelaufen als Gegenprobe,
dass nichts anderes mitgegangen ist.

---

## 7. Für den Auftraggeber und den Prüfer

- **`agent/UMBAUPLAN_WEBAPP.md` §2** (Abschnitt 5, letzter Fund) trägt
  weiterhin die Zuordnung von vor dem Umbau. Er liegt in `agent/`, also genau
  dort, wohin die neuen Kopfabsätze verweisen — von den drei überholten Orten
  im Repository ist er nach dieser Runde der einzige verbliebene. Eine Zeile je
  Datei genügt, oder derselbe Kopfabsatz wie hier.
- **Damit ist alles erledigt, was am Bau lag.** Offen sind nur noch die Punkte
  beim Auftraggeber: SMTP-Freigabe durch die ICT und ein echter Versand über das
  Firmen-Relais; Google Places aufschalten samt Kreditkarte und einem Live-Abruf
  (`03 B4`, die Produktivsperre für Modus B); die Zulässigkeit eines privaten
  Gmail-Kontos für Firmendaten; der Merge `umbau/webapp` → `main`; Batch 5.
- **Modus A ist ohne Vorbehalt einsatzbereit.**

---

## 8. Zeit

| Arbeitspaket | grober Aufwand |
|---|---|
| Freigabe lesen, die sechs Dokumente sichten | 0.25 h |
| Herkunftsdaten aus der Git-Historie holen | 0.25 h |
| Fünf Kopfabsätze schreiben | 0.5 h |
| Angaben nachprüfen: Verweise, Zeilennummern, Modulzahlen | 0.25 h |
| Findings | 0.25 h |
| **gesamt** | **≈ 1.5 h** |

Der Aufwand lag nicht im Schreiben, sondern im Nachprüfen. Drei Angaben, die
ich zuerst hingeschrieben hatte, waren falsch: die Zahl der entfallenen Module,
und zwei Zeilenverweise, die sich durch den eingefügten Absatz selbst
verschoben hatten. In einem Text, der davor warnt, Zahlen ungeprüft zu
übernehmen, wäre das die falsche Stelle für einen ungeprüften Wert gewesen.
