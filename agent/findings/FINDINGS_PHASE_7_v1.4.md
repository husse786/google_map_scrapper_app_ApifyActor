# Findings — Phase 7, Version 1.4

Datum: 05.08.2026
Bearbeitete Phase: 7 — Mail und Härtung, vierte und letzte Korrekturrunde nach
`KORREKTURPLAN_PHASE_7_v1.3.md`
Status: fertig

Umfang dieser Runde: **K1**. Sonst nichts.

Testlauf: `venv/bin/python -m pytest` → **305 grün, 1 übersprungen**, fünfmal
hintereinander (Abschnitt 6.1). Fassungen unverändert: `apify-client` 2.0.0,
`thefuzz` 0.22.1.

---

## 1. Abnahmekriterien

### Der Punkt des Korrekturplans

| # | Punkt | Status | Beleg |
|---|---|---|---|
| K1 | Ein ausgefallener Kunde behauptet nicht mehr, die Suche habe nichts geliefert | grün | `_einen_kunden` stellt den Grund richtig, wo `Ausgefallen()` zurückkommt. `data_cleaner.py` unangetastet. Drei Tests, dazu die zwei Sätze nebeneinander gemessen (Abschnitt 6.2) |

### Die zwei verlangten Nachweise

| Nachweis | Status | Beleg |
|---|---|---|
| Ein Kunde, dessen Abfrage in die Frist läuft, landet in ③ mit dem neuen Grund | grün | `test_ausgefallene_abfrage_behauptet_nicht_die_suche_habe_nichts_geliefert` — zehn Kunden, einer hängt, und genau `900001` steht in ③ mit «nicht geprüft» |
| Ein Kunde, für den die Quelle antwortet und nichts liefert, behält den alten | grün | `test_echtes_leeres_ergebnis_behaelt_seinen_grund` — der Satz aus `data_cleaner.py` steht weiterhin da, wo er hingehört |

### Die vier Kriterien der Phase

Unverändert grün. An Mailversand, Fehlertexten und README wurde in dieser Runde
nichts geändert.

**Zur Zahl 305 statt 302:** drei Tests sind dazugekommen. Der eine
übersprungene ist weiterhin der 180-Sekunden-Langläufer aus Phase 2; er ist von
dieser Runde nicht berührt — sie ändert keinen Zeitwert und keinen Zählerstand,
nur einen Satz in der CSV.

---

## 2. Geänderte und neue Dateien

| Datei | neu / geändert | Was |
|---|---|---|
| `pipeline.py` | geändert | Neue Meldung `AUSGEFALLENE_ABFRAGE_GRUND`. `_einen_kunden` stellt den Grund richtig, wenn `Ausgefallen()` zurückkam; `_aus_datenbank` hält ihn beim Fortsetzen. Neue Hilfsmethode `_grund_bei_ausfall_richtigstellen`. |
| `test_phase7_abnahme.py` | geändert | Drei Tests für K1 v1.4, dazu zwei Provider-Attrappen (`AntwortetLeer`, `AntwortetSauber`). |
| `agent/findings/FINDINGS_PHASE_7_v1.4.md` | neu | Dieses Dokument. |

**Nicht angefasst:** `data_cleaner.py`, `02_DATENVERTRAG.md`, `modus_b.py`, die
Grenze von zehn, die Zeitwerte, das Verhalten bei Abbruch.

---

## 3. Getroffene Annahmen

| Situation | Entscheidung | Warum |
|---|---|---|
| Der Korrekturplan sagt «der Lauf schreibt die ③-Zeile selbst». Ganz neu bauen oder die fertige Zeile berichtigen? | Die fertige Zeile berichtigen: `qualitaet`, `score` und Datei kommen unverändert aus der Fachlogik, nur `grund` wird gesetzt. | Eine selbst gebaute Zeile müsste alle Vertragsspalten aus `02` nachbilden und liefe auseinander, sobald sich dort etwas ändert. So bleibt genau ein Feld in der Hand des Laufs — das, über das der Korrekturplan spricht. Der Effekt ist derselbe, die Angriffsfläche kleiner. |
| Beim Fortsetzen wird die Entscheidung aus der Datenbank neu hergeleitet — dabei fiel der Kunde auf den alten Satz zurück. | Mitbehoben. `_aus_datenbank` erkennt den Fall am gespeicherten Grund und hält ihn. | Ohne diese Zeile hielte die Korrektur genau bis zu dem Schritt, zu dem die Anwendung selbst auffordert: «Bitte den Lauf fortsetzen» steht in der Meldung nach zehn Fehlschlägen. Das wäre keine halbe Behebung, sondern gar keine. Siehe Abschnitt 5. |
| Woran erkennt das Fortsetzen den Fall? Im Modus A tragen beide Ursachen dieselbe `qualitaet`. | Am gespeicherten `grund`. | Im Modus B genügt `qualitaet`, weil dort `NICHT_MOEGLICH (kein Ergebnis)` nur aus einem Ausfall entsteht. Im Modus A entsteht derselbe Wert auch aus einer echten Leermeldung — der Grund ist das einzige Feld, das die beiden auseinanderhält. Ein neuer `qualitaet`-Wert wäre die Alternative gewesen, und der ist ausdrücklich ausgeschlossen. |
| Wortlaut des neuen Grundes. | «Die Abfrage bei der Datenquelle kam nicht zurück; dieser Kunde wurde nicht geprüft. Ob es einen Treffer gibt, ist damit offen — bitte den Kunden später noch einmal auffrischen.» | Nah am Vorschlag des Korrekturplans, aber im Satzbau wie der Modus-B-Text aus v1.2, damit der Sachbearbeiter in beiden Dateien dieselbe Sprache liest. Schweizer Schreibweise, Handlungsanweisung am Schluss. |

---

## 4. Abweichungen von den Vorgaben

Keine. `qualitaet` bleibt `NICHT_MOEGLICH (kein Ergebnis)`, `02_DATENVERTRAG.md`
§3 unverändert, `data_cleaner.py` unangetastet.

---

## 5. Was gefunden wurde

| Fund | Datei / Stelle | Auswirkung | eingegriffen? |
|---|---|---|---|
| **Der richtige Grund hätte das Fortsetzen nicht überlebt.** `_aus_datenbank` leitet die Entscheidung eines bereits verarbeiteten Kunden neu her — im Modus A über `data_cleaner`, aus einer Gruppe ohne Kandidaten. Der Kunde wäre dabei auf «lieferte keinen einzigen Treffer» zurückgefallen. | `pipeline.py`, `_aus_datenbank` | Der Weg, auf dem dieser Kunde am ehesten wieder vorbeikommt: Der Lauf stoppt nach zehn Fehlschlägen und sagt dem Sachbearbeiter, er solle fortsetzen. Genau dann wäre der berichtigte Satz wieder verschwunden. | **ja** — ohne das wäre K1 nur an der Oberfläche behoben. Test: `test_der_richtige_grund_ueberlebt_das_fortsetzen` |
| **Im Modus B stellte sich die Frage nicht.** Dort trägt ein ausgefallener Kunde seit v1.2 den eigenen Text über `erreichbar`, und `qualitaet` genügt dem Fortsetzen zur Unterscheidung. | `modus_b.py`, `pipeline.py` | Kein Eingriff nötig. Erwähnt, weil die beiden Modi die gleiche Sache jetzt auf zwei Wegen lösen — beide korrekt, aber nicht symmetrisch. | **nein** — funktioniert, und Vereinheitlichen wäre Umbau ohne Anlass |

---

## 6. Messwerte

### 6.1 Fünf vollständige Testläufe

Am sauberen Arbeitsbaum, ohne Änderungen zwischen den Läufen.

| Lauf | Ergebnis | Dauer |
|---|---|---|
| 1 | 305 grün, 1 übersprungen | 22.42 s |
| 2 | 305 grün, 1 übersprungen | 21.93 s |
| 3 | 305 grün, 1 übersprungen | 21.87 s |
| 4 | 305 grün, 1 übersprungen | 21.64 s |
| 5 | 305 grün, 1 übersprungen | 21.81 s |

### 6.2 Der Nachweis für K1

Zweimal derselbe Zustand — Datei ③, `NICHT_MOEGLICH (kein Ergebnis)`,
`score` 0.0 — aus zwei verschiedenen Ursachen. Gemessen, erfundene Kundennummern.

**Die Abfrage lief in die Frist. Es wurde gefragt, aber nicht geantwortet:**

> Die Abfrage bei der Datenquelle kam nicht zurück; dieser Kunde wurde nicht
> geprüft. Ob es einen Treffer gibt, ist damit offen — bitte den Kunden später
> noch einmal auffrischen.

**Die Quelle hat geantwortet und nichts gefunden. Das ist ein Ergebnis:**

> Die Suche nach "Muster Laden 1, Hauptstrasse 1, 5620 Musterdorf" lieferte
> keinen einzigen Treffer.

Der zweite Satz stammt unverändert aus `data_cleaner.py` und steht weiterhin
genau dort, wofür er geschrieben wurde. Der erste ist neu und steht nur da, wo
der Lauf weiss, dass er keine Antwort bekommen hat.

Vorher trugen beide Fälle den zweiten Satz.

| Messung | vorher | jetzt |
|---|---|---|
| Ausgabedatei | ③ | ③ — unverändert |
| `qualitaet` | `NICHT_MOEGLICH (kein Ergebnis)` | unverändert |
| `score` | 0.0 | unverändert |
| `grund` bei ausgefallener Abfrage | «lieferte keinen einzigen Treffer» | «kam nicht zurück; dieser Kunde wurde nicht geprüft» |
| `grund` bei echtem Leerergebnis | «lieferte keinen einzigen Treffer» | unverändert |

Die Handlung, die daran hängt: Wer liest, Google habe nichts, prüft die Adresse
im ERP. Wer liest, die Abfrage sei nicht zurückgekommen, versucht es erneut.

### 6.3 Die drei neuen Tests

| Test | Was er festhält |
|---|---|
| `test_ausgefallene_abfrage_behauptet_nicht_die_suche_habe_nichts_geliefert` | Zehn Kunden, einer läuft in die Frist: `FERTIG`, in ③ steht genau `900001`, mit «nicht geprüft», ohne den alten Satz, `qualitaet` und `score` unverändert |
| `test_echtes_leeres_ergebnis_behaelt_seinen_grund` | Die Quelle antwortet mit nichts: der Satz aus `data_cleaner.py` steht unverändert da |
| `test_der_richtige_grund_ueberlebt_das_fortsetzen` | Lauf stoppt nach zehn Fehlschlägen, wird mit einer funktionierenden Quelle fortgesetzt: die Kunden von vorher behalten ihren Grund und werden nicht erneut abgefragt |

### 6.4 Wo welcher Satz steht

| Fall | Datei | `qualitaet` | Grund |
|---|---|---|---|
| Quelle antwortet, kein Treffer | ③ | `NICHT_MOEGLICH (kein Ergebnis)` | «lieferte keinen einzigen Treffer» |
| Abfrage läuft in die Frist (Modus A) | ③ | `NICHT_MOEGLICH (kein Ergebnis)` | «kam nicht zurück … nicht geprüft» |
| Abfrage scheitert vorübergehend (Modus A) | ③ | `NICHT_MOEGLICH (kein Ergebnis)` | «kam nicht zurück … nicht geprüft» |
| Abfrage scheitert oder läuft in die Frist (Modus B) | ③ | `NICHT_MOEGLICH (kein Ergebnis)` | «Die Abfrage bei Google ist fehlgeschlagen …» (seit v1.2) |
| Id unbekannt, Google sagt es (Modus B) | ③ | `NICHT_MOEGLICH (ID ungueltig)` | «gelöscht oder ersetzt» |
| Zehn Fehlschläge hintereinander | — | — | Lauf stoppt, `FEHLER`, keine Ausgabedateien |

---

## 7. Für die nächste Phase

- **Phase 7 ist damit abgeschlossen.** Vier Runden: K1/K2 (unbekannte
  Apify-Fehler, Beschreibung), K1a/K1b/K2 (versionsfeste Tests, gepinnte
  Fassungen, `google_provider`), K1 (Zeitüberschreitung), K1 (der Grund im
  Modus A). Der rote Faden war jedes Mal derselbe Satz: **eine ausgebliebene
  Antwort ist kein Ergebnis.** Er stand an fünf Stellen, und das war die letzte.
- **Es folgt Phase 8 — die Prüfmaske.** Danach ist der Rückweg von Datei ②
  geschlossen.
- **Die Aufräumrunde danach:** `logger_config.py`, `clean_input_data.py`,
  `csv_processor.py`, `csv_postprocessor.py`, dazu `data_cleaner.py.bak`. Eine
  Entscheidung je Datei.
- **`apify-client` bleibt auf 2.0.0.** Eine Anhebung berührt `call()`,
  `wait_for_finish()` und die Fehlerbehandlung — eigene Runde, wie in v1.2
  gemessen.
- **Unverändert beim Auftraggeber:** SMTP-Freigabe durch die ICT, ein echter
  Versand über das Firmen-Relais, und der Live-Abruf für Modus B.

---

## 8. Zeit

| Arbeitspaket | grober Aufwand |
|---|---|
| Korrekturplan einlesen, Stelle im Code suchen | 0.25 h |
| Grund richtigstellen, Meldung formulieren | 0.5 h |
| Fortsetzen nachziehen (Fund aus Abschnitt 5) | 0.25 h |
| Drei Tests | 0.5 h |
| Messung, fünf Testläufe | 0.5 h |
| Findings | 0.5 h |
| **gesamt** | **≈ 2.5 h** |

Der Hinweis des Prüfers, dass die Behebung `data_cleaner.py` gar nicht braucht,
hat die Runde kurz gemacht: Die Unterscheidung lag schon vor, sie wurde nur
nicht weitergereicht. Gekostet hat die Stelle, die im Korrekturplan nicht stand
— beim Fortsetzen wäre der berichtigte Satz wieder verschwunden, und zwar genau
auf dem Weg, den die Anwendung dem Sachbearbeiter empfiehlt.
