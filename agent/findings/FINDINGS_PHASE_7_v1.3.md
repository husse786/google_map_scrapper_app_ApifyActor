# Findings — Phase 7, Version 1.3

Datum: 04.08.2026
Bearbeitete Phase: 7 — Mail und Härtung, dritte Korrekturrunde nach
`KORREKTURPLAN_PHASE_7_v1.2.md`
Status: fertig

Umfang dieser Runde: **K1**. Sonst nichts.

Testlauf: `venv/bin/python -m pytest` → **302 grün, 1 übersprungen**, fünfmal
hintereinander (Abschnitt 6.1). Fassung unverändert: `apify-client` 2.0.0.

---

## 1. Abnahmekriterien

### Der Punkt des Korrekturplans

| # | Punkt | Status | Beleg |
|---|---|---|---|
| K1 | Zeitüberschreitung ist keine Antwort | grün | `_mit_frist` wirft `QuelleNichtVerfuegbar(ZEITUEBERSCHREITUNG_MELDUNG, endgueltig=False)` statt `None` zurückzugeben. Fünf neue Tests, dazu ein gemessener Vorher/Nachher-Lauf über 100 Kunden in beiden Modi (Abschnitt 6.2) |

### Die drei verlangten Wirkungen

| Wirkung | Status | Beleg |
|---|---|---|
| Ein einzelner Timeout kostet weiterhin genau einen Kunden | grün | `test_ein_einzelner_timeout_kostet_genau_einen_kunden`: zehn Kunden, nur der erste hängt → `FERTIG`, und in ③ steht genau `900001`. Zusätzlich mit dem echten Wert von 180 Sekunden: `test_timeout_mit_echten_180_sekunden` (Abschnitt 6.3) |
| Zehn hintereinander beenden den Lauf mit `FEHLER` statt mit `FERTIG` und vollen ③-Dateien | grün | `test_zehn_timeouts_hintereinander_stoppen_den_lauf`. Gemessen: 100 → 11 Aufrufe, `FEHLER`, keine Ausgabedateien (Abschnitt 6.2) |
| In Modus B entsteht aus einem Timeout nie mehr die Aussage «gelöscht» | grün | `test_timeout_im_modus_b_sagt_nie_geloescht`. Gemessen: vorher 100 von 100 Kunden mit «gelöscht», jetzt 0 (Abschnitt 6.2) |

### Die vier Kriterien der Phase

Unverändert grün. An Mailversand, Fehlertexten und README wurde in dieser Runde
nichts geändert.

**Zur Zahl 302 statt 297:** fünf Tests sind dazugekommen. Der eine
übersprungene ist weiterhin der Langläufer aus Phase 2 — der ist in dieser Runde
einmal eigens gelaufen, siehe 6.3.

---

## 2. Geänderte und neue Dateien

| Datei | neu / geändert | Was |
|---|---|---|
| `pipeline.py` | geändert | `_mit_frist` wirft bei Ablauf der Frist `QuelleNichtVerfuegbar(…, endgueltig=False)`. Neue Meldung `ZEITUEBERSCHREITUNG_MELDUNG`. Beschreibung und Protokollzeile nachgezogen — beide zitierten die alte Regel. |
| `test_phase7_abnahme.py` | geändert | Fünf Tests für K1 v1.3, dazu zwei Provider-Attrappen (`HaengtImmer`, `HaengtEinmal`). |
| `test_phase2_abnahme.py` | geändert | `test_haengender_provider_endet_in_datei_drei` heisst jetzt `…_blockiert_den_lauf_nicht` und erwartet den Stopp statt zehn Zeilen in ③. Siehe Abschnitt 3. |
| `test_phase3_abnahme.py` | geändert | `test_timeout_gilt_je_aufruf_nicht_je_lauf` arbeitet mit neun statt zwölf Kunden. Siehe Abschnitt 3. |
| `agent/findings/FINDINGS_PHASE_7_v1.3.md` | neu | Dieses Dokument. |

Nicht angefasst, wie verlangt: die 180 Sekunden, die 30 Sekunden für Google,
die Grenze von zehn, das Verhalten bei Abbruch durch den Nutzer.

---

## 3. Getroffene Annahmen

| Situation | Entscheidung | Warum |
|---|---|---|
| Zwei bestehende Abnahmetests bauten auf der alten Regel auf und wurden rot. | Beide angepasst, mit Begründung im Docstring. | Sie prüften nicht die alte Regel als Selbstzweck, sondern etwas anderes — und das prüfen sie weiterhin. In Phase 2: dass ein hängender Provider den Lauf nicht blockiert (Zeitmessung). In Phase 3: dass der Timeout je Aufruf gilt und nicht je Lauf. Was sich geändert hat, ist nur das erwartete Ende des Laufs. |
| Der Phase-3-Test hatte zwölf Kunden, alle hängend — jetzt über der Grenze von zehn. | Auf neun gesenkt. | Bei zwölf stoppt der Lauf mitten in der zweiten Welle, und dann lässt sich nicht mehr ablesen, ob der Timeout je Aufruf oder je Lauf griff — die beiden Fragen wären vermischt. Neun bleiben unter der Grenze, halten die Zwei-Wellen-Messung intakt und trennen die Fragen sauber. Dass zehn stoppen, prüft ein eigener Test in Phase 7. |
| Der Phase-2-Test nutzt die Fixture, und die hat genau zehn Kunden — also genau die Grenze. | So gelassen, Erwartung auf den Stopp umgestellt. | Die Fixture ist die vorgeschriebene Testdatenquelle (`05_TESTDATEN.md`). Sie zu beschneiden, um einen Stopp zu vermeiden, hätte den Test um seine Aussage gebracht: zehn hängende Kunden **sollen** den Lauf beenden. |
| Wortlaut der Meldung bei Zeitüberschreitung. | Deutscher Text mit Handlungsanweisung, ohne Nennung der Sekundenzahl. | Gleiche Linie wie bei Apify und Google seit v1.1: die Zahl steht im Protokoll, die Meldung sagt dem Sachbearbeiter, was er tun kann. Geprüft auf Schweizer Schreibweise und auf «Bitte». |

---

## 4. Abweichungen von den Vorgaben

Keine. `03_ENTSCHEIDUNGEN.md C` in der geänderten Fassung ist umgesetzt:
Timeout wie ein Netzfehler, zählt zu den zehn, kein Retry.

---

## 5. Was gefunden wurde

| Fund | Datei / Stelle | Auswirkung | eingegriffen? |
|---|---|---|---|
| **Die Protokollzeile zitierte die alte Regel.** Sie schrieb «wird als leeres Ergebnis behandelt» — genau die Aussage, die `03 C` jetzt verneint. | `pipeline.py`, `_mit_frist` | Wer das Protokoll liest, um einen Fehlschlag zu verstehen, hätte den alten Stand gelesen. Sie nennt jetzt die Tatsache: «Zählt als Fehlschlag, nicht als leeres Ergebnis.» | **ja** — gehört zu K1 |
| **Zwei Abnahmetests früherer Phasen hielten die alte Regel fest.** `test_haengender_provider_endet_in_datei_drei` (Phase 2) und `test_timeout_gilt_je_aufruf_nicht_je_lauf` (Phase 3). | siehe Abschnitt 2 | Sie wurden rot, wie es sein soll — eine Verhaltensänderung, die kein Test bemerkt, wäre das schlechtere Zeichen. | **ja** — angepasst, Begründung in Abschnitt 3 |
| **Im Modus A trägt ein ausgefallener Kunde weiterhin den Grund «Die Suche … lieferte keinen einzigen Treffer».** Der Zustand stimmt (③, `NICHT_MOEGLICH (kein Ergebnis)`), der Grundtext ist genau genommen zu bestimmt: gefragt wurde, aber nicht geantwortet. | `data_cleaner.py`, Grundtext bei null Treffern | Deutlich kleiner als der Modus-B-Fall aus K2: hier steht keine Aussage über den Betrieb des Kunden, nur über die Suche. Und seit dieser Runde bleibt es bei höchstens neun solchen Kunden, danach stoppt der Lauf und sagt den wahren Grund. | **nein** — `data_cleaner.py` ist erprobter Bestandscode, an dem laut `CLAUDE.md` nur benannte Fehler behoben werden. Ausserdem ausserhalb von K1. Vorschlag in Abschnitt 7 |

---

## 6. Messwerte

### 6.1 Fünf vollständige Testläufe

Am sauberen Arbeitsbaum, ohne Änderungen zwischen den Läufen.

| Lauf | Ergebnis | Dauer |
|---|---|---|
| 1 | 302 grün, 1 übersprungen | 19.89 s |
| 2 | 302 grün, 1 übersprungen | 19.69 s |
| 3 | 302 grün, 1 übersprungen | 19.86 s |
| 4 | 302 grün, 1 übersprungen | 19.92 s |
| 5 | 302 grün, 1 übersprungen | 19.84 s |

### 6.2 Der Nachweis für K1

100 Kunden, die Datenquelle antwortet nie. Gemessen in beiden Modi, jeweils
gegen den Stand **vor** dieser Runde (Commit `85e2b8c`, in einem eigenen
Arbeitsbaum ausgecheckt) und gegen den Stand danach. Erfundene Kundennummern,
keine echten Daten.

**Modus A**

| Messung | vorher | jetzt |
|---|---|---|
| Aufrufe an die Quelle | 100 | **11** |
| Zustand des Jobs | `FERTIG` | **`FEHLER`** |
| Kunden in der Datenbank | 100 | **9** |
| Zeilen in Datei ③ | 100 | **0** — es wird keine Datei geschrieben |
| Meldung an den Nutzer | keine | siehe unten |

**Modus B**

| Messung | vorher | jetzt |
|---|---|---|
| Aufrufe an die Quelle | 100 | **11** |
| Zustand des Jobs | `FERTIG` | **`FEHLER`** |
| Kunden in der Datenbank | 100 | **9** |
| Zeilen in Datei ③ | 100 | **0** |
| davon mit dem Grund «gelöscht» | **100** | **0** |

Der Grund, den der Sachbearbeiter im Modus B vorher gelesen hätte — hundertmal,
über intakte Kunden, weil die Quelle zu langsam war:

> Zur gespeicherten Google-ID gibt es keinen Eintrag mehr. Der Betrieb wurde
> bei Google gelöscht oder durch einen neuen Eintrag ersetzt.

Der Grund, der jetzt bei den neun Kunden steht:

> Die Abfrage bei Google ist fehlgeschlagen; dieser Betrieb wurde nicht
> geprüft. Ob der Eintrag noch besteht, ist damit offen — bitte den Kunden
> später noch einmal auffrischen.

Und die Meldung in `job.fehlermeldung`, die damit auf der Ergebnisseite und in
der Mail erscheint:

> Die Datenquelle hat mehrfach hintereinander nicht rechtzeitig geantwortet.
> Der Lauf wurde gestoppt, damit keine Kunden fälschlich als «nichts gefunden»
> gelten. Bitte es später noch einmal versuchen und den Lauf fortsetzen — die
> bereits verarbeiteten Kunden bleiben erhalten.

Deutsch, Schweizer Schreibweise, mit Handlungsanweisung, ohne Zahlenwerk. Im
Test geprüft (`'ß' not in …`, `'Bitte' in …`).

### 6.3 Ein einzelner Timeout, mit dem echten Wert

Der Langläufer aus Phase 2 ist in dieser Runde eigens gelaufen, weil er genau
den Fall trifft, den die Änderung berührt:

```
LANGSAME_TESTS=1 venv/bin/python -m pytest test_phase2_abnahme.py -k echten_180
1 passed in 180.92s (0:03:00)
```

Ein Kunde, 180 Sekunden Frist, die Quelle antwortet nicht: der Lauf endet nach
rund 180 Sekunden mit `FERTIG`, der Kunde liegt in ③. Unverändert — ein
einzelner Ausrutscher kostet weiterhin genau einen Kunden, auch am echten Wert.

### 6.4 Die fünf neuen Tests

| Test | Was er festhält |
|---|---|
| `test_zeitueberschreitung_ist_kein_leeres_ergebnis` | `_mit_frist` wirft, statt `None` zu liefern. Nicht endgültig, deutsche Meldung mit Handlungsanweisung |
| `test_ein_einzelner_timeout_kostet_genau_einen_kunden` | Zehn Kunden, einer hängt → `FERTIG`, alle zehn in genau einer Datei, in ③ steht genau der eine |
| `test_zehn_timeouts_hintereinander_stoppen_den_lauf` | 100 Kunden → 11 Aufrufe, `FEHLER`, keine Ausgabedateien, Meldung im Job |
| `test_timeout_im_modus_b_sagt_nie_geloescht` | Kein Kunde trägt «gelöscht»; alle tragen `NICHT_MOEGLICH (kein Ergebnis)` und «nicht geprüft» |
| `test_abbruch_bleibt_von_der_aenderung_unberuehrt` | Abbruch durch den Nutzer liefert weiterhin `None` und wirft nicht — der Korrekturplan verlangt das ausdrücklich |

### 6.5 Wo eine Zeitüberschreitung jetzt hinführt

| Fall | Verhalten |
|---|---|
| Ein Timeout, danach antwortet die Quelle wieder | Kunde nach ③, Zähler zurück auf null, Lauf läuft weiter |
| Bis zu neun Timeouts hintereinander | dasselbe, je einer kostet einen Kunden |
| Zehn hintereinander | Lauf stoppt, `FEHLER`, keine Ausgabedateien, Meldung an den Nutzer |
| Abbruch durch den Nutzer während des Wartens | `ABGEBROCHEN`, unverändert |

---

## 7. Für die nächste Phase

- **Der Grundtext im Modus A** (letzter Fund in Abschnitt 5). «Die Suche lieferte
  keinen einzigen Treffer» ist bei einem Timeout zu bestimmt. Kleiner Fall, weil
  keine Aussage über den Betrieb des Kunden darin steht und der Lauf nach zehn
  ohnehin stoppt. `data_cleaner.py` ist Bestandscode — wenn das geändert werden
  soll, ist es eine benannte Aufgabe, kein Nebenbei.
- **Damit ist Phase 7 aus meiner Sicht abgeschlossen.** K1 und K2 aus der ersten
  Runde, K1 a/b und K2 aus der zweiten, K1 aus dieser. Es folgt Phase 8, die
  Prüfmaske.
- **`apify-client` bleibt auf 2.0.0.** Eine Anhebung berührt `call()`,
  `wait_for_finish()` und die Fehlerbehandlung — eigene Runde, wie in v1.2
  gemessen und vom Prüfer bestätigt.
- **Der Aufräumvorschlag steht weiterhin:** `logger_config.py`,
  `csv_processor.py`, `csv_postprocessor.py`, `clean_input_data.py`,
  `data_cleaner.py.bak`. Eine Runde nach Phase 8.
- **Unverändert beim Auftraggeber:** SMTP-Freigabe durch die ICT, ein echter
  Versand über das Firmen-Relais, und der Live-Abruf für Modus B.

---

## 8. Zeit

| Arbeitspaket | grober Aufwand |
|---|---|
| Korrekturplan und geändertes `03 C` einlesen | 0.25 h |
| `_mit_frist`, Meldung, Protokollzeile | 0.5 h |
| Zwei bestehende Abnahmetests nachziehen | 0.5 h |
| Fünf neue Tests | 0.5 h |
| Vorher/Nachher messen, Langläufer, fünf Testläufe | 0.75 h |
| Findings | 0.5 h |
| **gesamt** | **≈ 3.0 h** |

Die Änderung selbst war eine Zeile. Der Aufwand lag darin, dass zwei Tests
früherer Phasen die alte Regel festhielten — und das war kein Ärgernis, sondern
der Beleg, dass sie etwas prüfen. Ein stiller Durchlauf wäre das schlechtere
Zeichen gewesen.
