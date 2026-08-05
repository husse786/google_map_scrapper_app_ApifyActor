# Findings — Phase 8, Version 1.1

Datum: 05.08.2026
Bearbeitete Phase: 8 — Prüfmaske im Browser, Korrekturrunde nach
`KORREKTURPLAN_PHASE_8.md`
Status: fertig

Umfang dieser Runde: **K1**. Sonst nichts.

Testlauf: `venv/bin/python -m pytest` → **333 grün, 1 übersprungen**, fünfmal
hintereinander (Abschnitt 6.1). Fassungen unverändert: `apify-client` 2.0.0,
`thefuzz` 0.22.1.

---

## 1. Abnahmekriterien

### Der Punkt des Korrekturplans

| # | Punkt | Status | Beleg |
|---|---|---|---|
| K1 | `qualitaet` bleibt umlautfrei | grün | `OK (geprueft)` und `NICHT_MOEGLICH (geprueft)`. Vier Tests, die die Regel festhalten — gegen den Vertrag und gegen das, was tatsächlich geschrieben wird (Abschnitt 6.2) |

### Die sechs Kriterien der Phase

Unverändert grün. Diese Runde ändert zwei Zeichenketten und nichts am Verhalten:
Dieselben Fälle, dieselben Dateien, dieselben Wege. Die 23 Tests aus v1.0 laufen
unverändert durch.

**Zur Zahl 333 statt 329:** vier Tests sind dazugekommen. Der eine übersprungene
ist weiterhin der 180-Sekunden-Langläufer aus Phase 2.

---

## 2. Geänderte Dateien

| Datei | Was |
|---|---|
| `pruefmaske.py` | `GEWAEHLT_QUALITAET` und `KEINER_QUALITAET` auf die Schreibweise aus `02_DATENVERTRAG.md` §3. Der Kommentar darüber begründet jetzt die Schreibweise, statt die Werte zu rechtfertigen — die stehen seit dieser Runde im Vertrag. |
| `test_phase8_abnahme.py` | Vier Tests für K1. |
| `agent/findings/FINDINGS_PHASE_8_v1.1.md` | Dieses Dokument. |

**Nicht angefasst, wie verlangt:** die Grundtexte. «Von Hand geprüft und
ausgewählt: …» und «Von Hand geprüft: keiner der gefundenen Treffer gehört zu
diesem Kunden.» tragen ihre Umlaute weiterhin — `grund` ist freies Deutsch.
Ebenso unberührt: Routen, Vorlagen, Stile, `db.py`, das Schema.

---

## 3. Getroffene Annahmen

| Situation | Entscheidung | Warum |
|---|---|---|
| Wie wird die Regel festgehalten, damit sie nicht wieder verlorengeht? | Zwei Wege statt einem: gegen die Liste in `02 §3`, und gegen die Werte, die ein echter Lauf samt Entscheidungen tatsächlich schreibt. | Ein Test allein gegen die Konstanten hätte nur diese zwei Werte gedeckt. Der Vertrag ist die Vorgabe, also wird gegen ihn geprüft — und weil ein Dokument still veralten kann, zusätzlich gegen das, was in Datenbank und CSV landet. Beide Wege fielen bei der Gegenprobe um (Abschnitt 6.3). |
| Der Test liest `02_DATENVERTRAG.md` und zerlegt die Tabelle aus §3. | So gebaut. | Damit ist der Vertrag die Quelle und nicht eine im Testcode abgeschriebene Liste, die beim nächsten neuen Wert vergessen wird. Gelesen werden die siebzehn Werte aus §3, nicht die Tabellen der anderen Abschnitte. |
| Ein Kunde, der unter der alten Schreibweise entschieden wurde | Keine Umstellung gebaut. | Phase 8 ist nicht freigegeben und war nie im Betrieb; es gibt keine Datenbank mit alten Werten. Eine Umstellung für einen Datenbestand, den es nicht gibt, wäre genau das, was `03 E` ausschliesst. Der Vollständigkeit halber in Abschnitt 5 vermerkt. |

---

## 4. Abweichungen von den Vorgaben

Keine. Die beiden Werte stehen jetzt in `02_DATENVERTRAG.md` §3 in der dort
festgelegten Schreibweise, und die Abweichung aus v1.0 ist damit erledigt.

---

## 5. Was gefunden wurde

| Fund | Datei / Stelle | Auswirkung | eingegriffen? |
|---|---|---|---|
| **Die Regel galt schon vorher überall, nur nirgends aufgeschrieben.** Alle fünfzehn Werte aus §3 waren umlautfrei — `PRUEFUNG` statt `PRÜFUNG`, `(ID ungueltig)` statt `(ID ungültig)`. Erkennbar Absicht, aber als Muster, dem man ansehen musste, dass es eins ist. | `02_DATENVERTRAG.md` §3 | Ich habe das Muster in v1.0 nicht gelesen und die zwei neuen Werte in gewöhnlichem Deutsch geschrieben. Genau so gehen stillschweigende Regeln verloren. | **ja** — der Vertrag nennt die Regel jetzt ausdrücklich, und ein Test hält sie fest |
| **`fortschritt()` erkennt entschiedene Fälle am `qualitaet`-Wert.** Ein Kunde, der unter der alten Schreibweise entschieden worden wäre, würde nach dieser Runde nicht mehr als entschieden gezählt. | `pruefmaske.py`, `fortschritt` | Ohne Wirkung: Phase 8 ist nicht freigegeben, es gibt keinen solchen Datenbestand. Vermerkt, weil es bei einer bereits laufenden Phase eine Umstellung gebraucht hätte — und weil es zeigt, was ein `qualitaet`-Wert alles trägt. | **nein** — nichts umzustellen |

---

## 6. Messwerte

### 6.1 Fünf vollständige Testläufe

| Lauf | Ergebnis | Dauer |
|---|---|---|
| 1 | 333 grün, 1 übersprungen | 23.77 s |
| 2 | 333 grün, 1 übersprungen | 25.04 s |
| 3 | 333 grün, 1 übersprungen | 24.27 s |
| 4 | 333 grün, 1 übersprungen | 24.01 s |
| 5 | 333 grün, 1 übersprungen | 23.94 s |

### 6.2 Was jetzt geschrieben wird

| Fall | `qualitaet` | vorher (v1.0) |
|---|---|---|
| Treffer in der Maske gewählt | `OK (geprueft)` | `OK (geprüft)` |
| «Keiner passt» | `NICHT_MOEGLICH (geprueft)` | `NICHT_MOEGLICH (geprüft)` |

Der `grund` daneben ist unverändert und trägt seine Umlaute:

> Von Hand geprüft und ausgewählt: Muster Kiosk, Wohlerstrasse 18, 5610
> Beispielwil.

> Von Hand geprüft: keiner der gefundenen Treffer gehört zu diesem Kunden.

Aus einer Kodierungsvorsicht sollte keine verstümmelte Sprache werden — dafür
gibt es einen eigenen Test.

### 6.3 Die vier Tests, und dass sie beissen

| Test | Was er festhält |
|---|---|
| `test_der_vertrag_fuehrt_die_beiden_werte_der_pruefmaske` | Beide Konstanten stehen wörtlich in `02_DATENVERTRAG.md` §3 — sie sind Vorgabe, nicht Erfindung des Moduls |
| `test_kein_qualitaet_wert_im_vertrag_traegt_einen_umlaut` | Alle **siebzehn** Werte aus §3, nicht nur die zwei neuen |
| `test_kein_geschriebener_qualitaet_wert_traegt_einen_umlaut` | Die Gegenprobe am Betrieb: nach einem vollständigen Lauf und beiden Arten von Entscheidung trägt kein Wert in Datenbank oder Ausgabedatei einen Umlaut — und jeder steht in §3 |
| `test_der_grund_traegt_seine_umlaute_weiterhin` | Die Regel gilt für `qualitaet`, nicht für den Klartext |

Gegenprobe: mit der alten Schreibweise wieder eingesetzt fallen zwei davon um —
der gegen den Vertrag und der gegen das Geschriebene:

```
mit «geprueft»:  27 passed
mit «geprüft»:   FAILED test_der_vertrag_fuehrt_die_beiden_werte_der_pruefmaske
                 FAILED test_kein_geschriebener_qualitaet_wert_traegt_einen_umlaut
```

Der Test greift also von beiden Seiten: wenn der Code vom Vertrag abweicht, und
wenn ein Umlaut in einen geschriebenen Wert gerät.

### 6.4 Umfang der Änderung

```
pruefmaske.py          2 Zeichenketten, dazu der Kommentar darüber
test_phase8_abnahme.py 4 Tests
```

Kein Verhalten geändert: dieselben Fälle, dieselben Dateien, dieselben Wege.
Die 23 Tests aus v1.0 laufen unverändert durch.

---

## 7. Für die nächste Phase

- **Die Aufräumrunde** ist jetzt dran: `logger_config.py`,
  `clean_input_data.py`, `csv_processor.py`, `csv_postprocessor.py` und
  `data_cleaner.py.bak` — eine Entscheidung je Datei, mit Begründung.
- **Modus B in der Maske** ist weiterhin ungefahren: sie ist modusunabhängig
  gebaut, aber nur an Modus-A-Fällen geprüft, weil Modus B unter der
  Produktivsperre aus `03 B4` steht. Wenn die Sperre fällt, gehört ein Prüffall
  daraus (`PRUEFUNG (geschlossen)`, `PRUEFUNG (Standort abweichend)`) einmal
  durch die Maske gefahren.
- **Die Reihenfolge der Ausgabezeilen** wechselt mit der ersten Entscheidung von
  Eingabe- auf Verarbeitungsreihenfolge (Findings v1.0, Abschnitt 3). Falls das
  ERP daran hängt, ist es jetzt zu sagen.
- **Unverändert beim Auftraggeber:** SMTP-Freigabe durch die ICT und ein echter
  Versand über das Firmen-Relais; Google Places aufschalten und ein Live-Abruf
  für Modus B; die Zulässigkeit eines privaten Gmail-Kontos für Firmendaten.

---

## 8. Zeit

| Arbeitspaket | grober Aufwand |
|---|---|
| Korrekturplan und geänderten §3 einlesen | 0.25 h |
| Zwei Zeichenketten, Kommentar nachziehen | 0.25 h |
| Vier Tests, Gegenprobe | 0.5 h |
| Fünf Testläufe | 0.25 h |
| Findings | 0.25 h |
| **gesamt** | **≈ 1.5 h** |

Zwei Zeichen. Der Aufwand lag darin, die Regel so festzuhalten, dass sie beim
nächsten neuen Wert nicht wieder übersehen wird — und dafür war der Vertrag die
richtige Quelle, nicht eine zweite Liste im Testcode.
