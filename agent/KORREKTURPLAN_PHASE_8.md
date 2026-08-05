# KORREKTURPLAN — Phase 8, Version 1.0 → 1.1

Geprüft am 04.08.2026. **Ein Punkt, eine Zeichenkette.**

---

## Gesamturteil

**Die Phase ist inhaltlich fertig und gut gebaut.** Alle sechs Abnahmekriterien
erfüllt, 23 eigene Tests, fünf vollständige Läufe mit 329 grün, Schema
unangetastet. Die Abweichung, die er zur Entscheidung vorgelegt hat, wird
**angenommen** — nur die Schreibweise muss angeglichen werden.

---

## 1. Nachgerechnet

| Prüfung | Ergebnis |
|---|---|
| Fünf vollständige Läufe | 5 × **329 grün** + 1 übersprungen |
| Phase-8-Tests einzeln | 23 grün |
| `db.py` im Diff | **nein** — keine Schemaänderung, wie in `02 §5` verlangt |
| Grundtexte nennen Werte statt Regeln | bestätigt |

---

## 2. Die Abweichung — angenommen

Zwei neue `qualitaet`-Werte für von Hand entschiedene Kunden. `02 §3` nannte
seine Liste abschliessend, also war die Vorlage zur Entscheidung richtig.

**Seine Begründung trägt.** Die drei Auswege ohne neuen Wert führen alle dazu,
dass eine Zeile über sich selbst etwas Falsches sagt:

- einen vorhandenen `OK (…)`-Wert setzen → behauptet eine automatische Regel,
  die nie gegriffen hat
- `PRUEFUNG (…)` in der ERP-Datei stehen lassen → sagt „ungeklärt", obwohl geklärt
- `NICHT_MOEGLICH (kein Ergebnis)` für „keiner passt" → sagt, es gab nichts,
  obwohl es Treffer gab und ein Mensch sie verworfen hat

Genau das Muster, das Phase 7 in vier Runden ausgeräumt hat. Und der ERP muss
unterscheiden können, ob ein Datensatz automatisch oder von Hand entschieden
wurde — das ist der Massstab dieses Projekts.

`02_DATENVERTRAG.md` §3 ist ergänzt. Die Werte sind ab jetzt Vorgabe.

---

## 3. Zu beheben

### K1 — `qualitaet` bleibt umlautfrei

**Befund.** `OK (geprüft)` und `NICHT_MOEGLICH (geprüft)` tragen ein `ü`. Alle
fünfzehn bestehenden Werte sind umlautfrei, und zwar erkennbar absichtlich:

```
PRUEFUNG (…)          nicht PRÜFUNG
NICHT_MOEGLICH (…)    nicht NICHT_MÖGLICH
(ID ungueltig)        nicht (ID ungültig)
```

`qualitaet` ist der Schlüssel, den der ERP-Import liest — dort ist ein Umlaut
ein Zeichenkodierungsrisiko, das niemand beim Import sucht. `grund` ist freier
Text und darf Umlaute tragen; dort sind sie richtig.

**Zu tun.**

```
OK (geprüft)              →  OK (geprueft)
NICHT_MOEGLICH (geprüft)  →  NICHT_MOEGLICH (geprueft)
```

Nur die beiden Konstanten und die Tests, die sie prüfen. **Die Grundtexte
bleiben unverändert** — „Von Hand geprüft und ausgewählt: …" ist richtig so.

`02_DATENVERTRAG.md` §3 führt die Werte bereits in dieser Schreibweise und
hält die Regel jetzt ausdrücklich fest.

**Zu belegen:** Fünf vollständige Läufe, und ein Test, der sicherstellt, dass
kein `qualitaet`-Wert einen Umlaut enthält — damit die Regel nicht wieder
verlorengeht.

---

## 4. Bestätigt

| Punkt | Urteil |
|---|---|
| Nach jeder Entscheidung neu schreiben, kein „Speichern"-Knopf | **bestätigt.** 44 ms bei realer Grösse gemessen. Ein Knopf, den ein Nutzer nach vierzig Fällen vergisst, wäre der schlechtere Entwurf |
| Zeichenweiser Vergleich vor der ersten Entscheidung | **bestätigt, und der beste Zug der Phase.** Ohne ihn hätte die erste Entscheidung still alle übrigen Zeilen verändert |
| `aussortiert.csv` unverändert durchreichen | **bestätigt.** Sie ist Diagnose, keine Ausgabe, und `kandidat` kennt ihre `AUSSORTIERT (…)`-Werte nicht. Das Schema zu erweitern wäre der falsche Weg gewesen |
| Zwei schwache Zusicherungen nachträglich verschärft | **bestätigt** |
| Mutationsprüfung am tragendsten Verhalten | **bestätigt.** Zu prüfen, ob die eigenen Tests überhaupt beissen, ist mehr als verlangt war |
| Reihenfolgeunabhängigkeit nach dem Fehlschlag im Gesamtlauf | **bestätigt.** Dieselbe Falle wie in Phase 3 — allein grün, im Verbund rot |

---

## 5. Anweisung für Version 1.1

Umfang ist K1. Sonst nichts.

Danach `agent/findings/FINDINGS_PHASE_8_v1.1.md`, committen, pushen, stoppen.

Danach folgt die Aufräumrunde: `logger_config.py`, `clean_input_data.py`,
`csv_processor.py`, `csv_postprocessor.py`, `data_cleaner.py.bak` — eine
Entscheidung je Datei, mit Begründung.
