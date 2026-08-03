# Findings — Phase 3, Version 1.1

Datum: 03.08.2026
Bearbeitete Phase: 3 — Worker, Korrekturrunde nach `KORREKTURPLAN_PHASE_3.md`
Status: fertig

Umfang dieser Runde: **K1, K2, K3**. Sonst nichts — keine Refaktorierung, kein
Vorgriff auf Phase 4.

Testlauf: `python -m pytest` → **114 grün, 1 übersprungen**, fünfmal
hintereinander (Abschnitt 6.1).

---

## 1. Abnahmekriterien

### Die drei Punkte des Korrekturplans

| # | Punkt | Status | Beleg |
|---|---|---|---|
| K1 | Sollzahl aus der Tabelle `kunde` statt aus `kunden_erledigt`; fünf vollständige Testläufe grün | grün | `test_phase3_abnahme.py:465`. Fünf Läufe in Abschnitt 6.1. Einschränkung zur Reproduktion in Abschnitt 5. |
| K2 | Timeout von 90 auf 180 Sekunden nachziehen, Abstand von fünf Sekunden bleibt | grün | `pipeline.STANDARD_TIMEOUT_SEKUNDEN = 180`, `apify_provider.STANDARD_TIMEOUT_SEKUNDEN = 180`, Apify bekommt 175. `test_timeout_standard_ist_180_sekunden`, gemessener Lauf in Abschnitt 6.2. |
| K3 | Ein erfolgreicher echter Apify-Abruf über den neuen Aufrufweg | grün | Abschnitt 6.3: 80 Sekunden, 6 Treffer, 14 von 14 Feldern befüllt, Datenbank vollständig, kein verwaister Lauf. |

### Die acht Kriterien der Phase, erneut geprüft

Unverändert grün. Die Belege stehen in `FINDINGS_PHASE_3.md` Abschnitt 1; an der
Fachlogik und am Ausführungsmodell wurde in dieser Runde nichts geändert. Neu
ist allein: die Zahlen stammen jetzt aus fünf vollständigen Läufen statt aus
einem, und der Timeout-Wert lautet 180 statt 90 Sekunden.

---

## 2. Geänderte Dateien

| Datei | Was | Punkt |
|---|---|---|
| `test_phase3_abnahme.py` | `vorher_erledigt` kommt aus `kunden_lesen()` statt aus `kunden_erledigt`, mit Begründung im Kommentar. Zusätzliche Prüfung, dass der Zähler nach dem Fortsetzen wieder auf dem Stand der Tabelle steht. Ein `timeout_sekunden=90` im Abbruchtest auf 180 gezogen. | K1, K2 |
| `pipeline.py` | `STANDARD_TIMEOUT_SEKUNDEN` 90 → 180, Kopfkommentar nachgezogen. | K2 |
| `apify_provider.py` | `STANDARD_TIMEOUT_SEKUNDEN` 90 → 180 mit Begründung, Kopfkommentar nachgezogen. `RESERVE_SEKUNDEN = 5` unverändert, Apify bekommt damit 175 Sekunden. | K2 |
| `test_phase2_abnahme.py` | `test_timeout_standard_ist_90_sekunden` → `..._180_sekunden`, Stub-Werte 85 → 175, langsamer Test umbenannt und auf 178–195 Sekunden geprüft. Die Wartezeit des künstlichen Providers dabei von 600 auf 200 Sekunden gekürzt, siehe Abschnitt 5. | K2 |

Nicht angefasst: `worker.py`, `db.py`, `place_provider.py`, `fake_provider.py`,
`data_cleaner.py`, `cli.py`, `README.md`.

---

## 3. Getroffene Annahmen

| Situation | Entscheidung | Warum |
|---|---|---|
| Der Abstand zwischen Aussenschutz und Provider-Frist bei 180 Sekunden | Bleibt bei fünf Sekunden absolut, nicht anteilig. Apify bekommt 175. | Der Korrekturplan sagt „bleibt wie gebaut". Die fünf Sekunden decken das Starten des Laufs und das Abbrechen ab; beides hängt nicht an der Länge der Frist. |
| Der langsame Timeout-Test dauert jetzt 180 statt 90 Sekunden | Bleibt hinter `LANGSAME_TESTS=1`, einmal ausgeführt und in Abschnitt 6.2 belegt. | Drei Minuten Stillstand in jedem Testlauf würden dazu führen, dass niemand mehr die Suite ausführt. Ein übersprungener Test ist sichtbar. |
| Weitere Tests, die `kunden_erledigt` lesen | Belassen. Sie prüfen den Zähler **als Zähler** — nach einem vollständigen Lauf muss er auf der Gesamtzahl stehen — oder seine Konsistenz mit der Tabelle. Keiner benutzt ihn als Sollwert für nachzuholende Kunden. | Genau das verbietet `02_DATENVERTRAG.md` §6, und nur das. Alle dreizehn Fundstellen in den Testdateien einzeln nachgesehen. |

---

## 4. Abweichungen von den Vorgaben

Keine.

---

## 5. Was gefunden wurde

| Fund | Auswirkung | eingegriffen? |
|---|---|---|
| **Der rote Test war lokal nicht reproduzierbar.** In 20 provozierten Abstürzen (zehn Durchläufe je mit einem und mit sechs Arbeitern) wichen `kunden_erledigt` und die Anzahl Zeilen in `kunde` **kein einziges Mal** voneinander ab. Auch fünf vollständige Testläufe vor der Korrektur waren grün. | Die Lücke existiert trotzdem und ist durch den Aufbau belegbar: der Kunde wird festgeschrieben, danach — in einem zweiten Schreibvorgang — der Zähler. Stirbt der Prozess dazwischen, hinkt der Zähler um eins hinterher. Genau die Zahlen aus dem Korrekturplan (Zähler 8, geholt 11; Zähler 13, geholt 6) passen auf diese Lücke. Auf dieser Maschine trifft der harte Abbruch das Zeitfenster offenbar nie, auf der des Prüfers in vier von fünf Läufen. | ja — die Korrektur ist unabhängig von der Reproduzierbarkeit richtig und von `02_DATENVERTRAG.md` §6 vorgeschrieben |
| Der Zähler bleibt nach einem Absturz um bis zu eins hinter der Tabelle zurück | Kein Produktfehler mehr, sondern Vertragslage: §6 erklärt den Zähler ausdrücklich zur Anzeige. Beim Fortsetzen wird er aus der Tabelle neu gesetzt (`pipeline.py:154`), danach stimmt er wieder. Neu geprüft in `test_harter_abbruch_und_wiederaufnahme`. | nein — kein Eingriff nötig |
| Ein zuvor gescheiterter Suchbegriff lief jetzt durch | Derselbe Suchbegriff, der zwei Stunden zuvor mit 85 Sekunden Frist in den Timeout lief, brauchte mit 175 Sekunden Frist **80 Sekunden** und war erfolgreich. Das bestätigt K2 von der anderen Seite: nicht der Aufrufweg war das Problem, sondern die zu knappe Frist. | — |
| **Beim Beenden des Prozesses wartet Python auf abgebrochene Abfragen.** Der Lauf gibt einen überzogenen Aufruf sofort auf (`shutdown(wait=False)`), aber `concurrent.futures` hängt sich in das Ende des Programms und wartet dort auf jeden noch laufenden Arbeiterthread. Aufgefallen, weil der 180-Sekunden-Test nach bestandener Prüfung weitere acht Minuten stand — die künstliche Datenquelle war auf 600 Sekunden Wartezeit eingestellt. | Im Test behoben, indem die künstliche Wartezeit auf 200 Sekunden gekürzt wurde. **Im Betrieb bleibt der Effekt:** nach einem Abbruch kann sich das Beenden des Programms um bis zu die Restlaufzeit des Apify-Aufrufs verzögern, also höchstens 175 Sekunden. Der Lauf selbst steht sofort, die Daten sind geschrieben — es verzögert sich nur das Schliessen. | nein — ausserhalb von K1 bis K3. Für Phase 5 vermerkt, wo das Beenden des Webservers eine Rolle spielt |

---

## 6. Messwerte

### 6.1 Fünf vollständige Testläufe (K1)

Jeder Lauf ist die komplette Suite, nicht einzelne Tests.

| Lauf | Ergebnis | Dauer |
|---|---|---|
| 1 | 114 grün, 1 übersprungen | 8.85 s |
| 2 | 114 grün, 1 übersprungen | 8.70 s |
| 3 | 114 grün, 1 übersprungen | 8.56 s |
| 4 | 114 grün, 1 übersprungen | 8.79 s |
| 5 | 114 grün, 1 übersprungen | 8.61 s |

Gemessen nach der letzten Änderung an den Testdateien, nicht davor.

Die im Korrekturplan genannte Reihenfolge ist dabei jedes Mal enthalten:
`test_harter_abbruch_und_wiederaufnahme[1]` läuft vor `[6]`, so wie pytest die
Datei abarbeitet.

Der übersprungene Test ist `test_timeout_mit_echten_180_sekunden`, siehe 6.2.

### 6.2 Timeout auf 180 Sekunden (K2)

| Messung | Wert |
|---|---|
| Vorgabe `03_ENTSCHEIDUNGEN.md` C | 180 Sekunden |
| Frist des Laufs (Aussenschutz, gilt für jeden Provider) | 180 Sekunden |
| Frist, die Apify bekommt | 175 Sekunden — fünf Sekunden Vorsprung, damit der Provider entscheidet und aufräumt |
| Gemessen mit einem Provider, der nie antwortet | **180.03 s**, danach ③ `NICHT_MOEGLICH (kein Ergebnis)`, ein Aufruf, kein Retry |
| Schneller Ersatz im Alltag | `test_haengender_provider_endet_in_datei_drei` mit 0.3 s |

Reproduzieren:

```bash
LANGSAME_TESTS=1 python -m pytest test_phase2_abnahme.py::test_timeout_mit_echten_180_sekunden -q --durations=1
```

### 6.3 Erfolgreicher echter Apify-Abruf (K3)

Ein Kunde, erfundene Kundennummer, öffentliches Geschäft in Zug als
Suchbegriff. Keine Datei aus `Daten/` beteiligt. Genau dieser Suchbegriff war
zwei Stunden zuvor mit der 90-Sekunden-Frist in den Timeout gelaufen.

| Prüfpunkt aus K3 | Ergebnis |
|---|---|
| Lauf endet mit Erfolg, nicht im Timeout | **ja** — Protokoll: „Apify: 6 Treffer", keine Timeout-Warnung, kein `TIMED-OUT` |
| Dauer | **80 Sekunden** (21:31:29 bis 21:32:49), Gesamtzeit des Befehls 80.5 s |
| Alle Kandidatenfelder befüllt | **14 von 14** bei allen sechs Treffern, keine einzige leere Zelle |
| Spalten der Ausgabedatei | stimmen mit `OUTPUT_COLUMNS` überein |
| `score`, `grund`, `qualitaet` | in allen sechs Zeilen befüllt |
| Entscheid | ② `PRUEFUNG (keine Strassentreffer)` — gesucht war eine Hausnummer, die keiner der sechs Treffer hat |
| Datenbank | Job `FERTIG` (1 von 1), ein Kunde mit `ergebnis = pruefung`, **sechs** Kandidaten mit Score (0.0 bis 100.0) und Entscheid `vorgeschlagen` |
| Apify-Lauf sauber beendet, nicht verwaist | **ja** — der Lauf endete von selbst mit `SUCCEEDED`. Wäre er das nicht, stünde im Protokoll eine Warnung und ein Abbruch; beides fehlt |
| Verschachtelte Felder | `location` 36–37 Zeichen, `openingHours` 330–333 Zeichen, `website` bei allen sechs gefüllt — die Umwandlung in `Candidate` arbeitet über den neuen Aufrufweg genauso wie über den alten |

Damit ist die in `FINDINGS_PHASE_3.md` Abschnitt 6.4 selbst gemeldete Lücke
geschlossen: `start()` plus `wait_for_finish()` liefert im Erfolgsfall
vollständige Daten.

---

## 7. Für die nächste Phase

Unverändert gegenüber `FINDINGS_PHASE_3.md` Abschnitt 7, mit zwei Ergänzungen:

- **Der Kaltstart bleibt der offene Punkt**, jetzt aber ohne Risiko für die
  Daten: gemessen wurden bisher 80, 83, 87 und 91 Sekunden gegen eine Frist von
  180. Die zehn aufeinanderfolgenden Aufrufe in Phase 4 beantworten weiterhin
  die Frage, warum das Betriebsprotokoll rund 17 Sekunden nennt.
- **Die Regel aus K1 ist übernommen:** ein Kriterium gilt erst als grün, wenn
  der vollständige Testlauf mehrfach hintereinander grün ist. Für diese Runde
  fünfmal, ab jetzt bei jeder Abgabe.
- **Für Phase 5 vermerkt:** nach einem Abbruch kann das Beenden des Programms
  bis zu 175 Sekunden dauern, weil Python auf den abgebrochenen Apify-Aufruf
  wartet (Abschnitt 5). Beim Webserver fällt das auf — er reagiert dann noch,
  beendet sich aber verzögert. Behebbar, gehört aber nicht in diese Runde.

---

## 8. Zeit

| Arbeitspaket | grober Aufwand |
|---|---|
| Korrekturplan und die zwei Vertragsänderungen einlesen | 0.25 h |
| K1: Test auf die Tabelle umgestellt, Reproduktionsversuch mit 20 Abstürzen | 0.75 h |
| K2: Wert in Code und vier Tests nachgezogen, langsamer Nachweis | 0.5 h |
| K3: echter Apify-Abruf und Auswertung | 0.25 h |
| Fünf vollständige Testläufe | 0.25 h |
| Findings | 0.5 h |
| **gesamt** | **≈ 2.5 h** |
