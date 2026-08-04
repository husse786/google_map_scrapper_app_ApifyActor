# KORREKTURPLAN — Phase 7, Version 1.3 → 1.4

Geprüft am 04.08.2026. **Ein Punkt. Danach ist Phase 7 abgeschlossen.**

---

## 1. Nachgerechnet

| Prüfung | Ergebnis |
|---|---|
| Fünf vollständige Läufe unter den gepinnten Fassungen | 5 × **302 grün** + 1 übersprungen |
| `_mit_frist` wirft bei Zeitüberschreitung | bestätigt |
| Abbruch durch den Nutzer bleibt `None` | bestätigt — anderer Rückgabeweg, unberührt |
| Zwei angepasste Alttests | beide korrekt begründet |

Der Phase-3-Test von zwölf auf neun Kunden zu senken war richtig: Bei zwölf
hätte der Stopp nach dem zehnten die eigentliche Frage verdeckt, ob der Timeout
je Aufruf oder je Lauf greift. Dass zehn stoppen, prüft jetzt ein eigener Test.
Die Trennung ist sauberer als vorher.

---

## 2. Der letzte Punkt

### K1 — Ein ausgefallener Kunde behauptet weiterhin, die Suche habe nichts geliefert

**Sein Befund, bestätigt.** In Modus A trägt ein Kunde, dessen Abfrage nicht
zurückkam, den Grund:

> Die Suche nach "…" lieferte keinen einzigen Treffer.

Das stimmt nicht. Es wurde gefragt, aber nicht geantwortet.

**Seine Einordnung ist richtig, seine Zurückhaltung war es auch** — der Text
steht in `data_cleaner.py`, und `CLAUDE.md` schützt diesen Bestandscode.

**Aber die Behebung braucht `data_cleaner.py` gar nicht anzufassen.** Die
Unterscheidung existiert bereits: `pipeline.py:336` gibt bei einem
nicht-endgültigen Fehlschlag `Ausgefallen()` zurück. An dieser Stelle **weiss
der Lauf**, dass es kein leeres Ergebnis war, sondern eine gescheiterte Abfrage.
Er reicht diese Information nur nicht weiter, sondern baut eine kandidatenlose
Gruppe, die die Fachlogik zwangsläufig als „nichts gefunden" liest.

**Zu tun.** Wo `Ausgefallen()` zurückkommt, schreibt der Lauf die ③-Zeile selbst,
mit einem Grund, der sagt was war — etwa:

> Die Abfrage bei der Datenquelle kam nicht zurück. Der Kunde wurde nicht
> geprüft. Bitte erneut versuchen.

`qualitaet` bleibt `NICHT_MOEGLICH (kein Ergebnis)` — kein neuer Wert, keine
Änderung an `02_DATENVERTRAG.md` §3. `data_cleaner.py` bleibt unangetastet; sein
Text gilt weiterhin für den Fall, für den er geschrieben wurde: Die Quelle hat
geantwortet, und die Antwort war leer.

**Warum das trotz kleiner Menge zählt.** Höchstens neun Zeilen je Lauf, richtig.
Aber die Handlung, die der Text auslöst, ist falsch: Wer liest, Google habe
nichts, prüft die Adresse im ERP und ändert womöglich einen intakten Datensatz.
Wer liest, die Abfrage sei nicht zurückgekommen, versucht es erneut. Dasselbe
Muster wie im Modus-B-Fall, nur milder — und die letzte Stelle, an der es noch
steht.

**Zu belegen:** Ein Kunde, dessen Abfrage in die Frist läuft, landet in ③ mit
dem neuen Grund; ein Kunde, für den die Quelle antwortet und nichts liefert,
behält den alten. Fünf vollständige Läufe.

---

## 3. Bestätigt

| Punkt | Urteil |
|---|---|
| Vorher/Nachher gegen den Vorstand im eigenen Arbeitsbaum gemessen | **bestätigt.** Nicht behauptet, sondern gegen `85e2b8c` gefahren |
| 180-Sekunden-Langläufer eigens durchlaufen lassen | **bestätigt.** Der Nachweis „ein Timeout kostet genau einen Kunden" am echten Wert statt am verkürzten |
| Eigener Test, dass der Abbruch unberührt bleibt | **bestätigt.** Genau die Stelle, an der eine Änderung dieser Art danebengreifen kann |
| Protokollzeile und Beschreibung mitgezogen | **bestätigt.** Beide zitierten die alte Regel wörtlich |

---

## 4. Anweisung für Version 1.4

Umfang ist K1. Sonst nichts. **Dies ist die letzte Runde zu Phase 7.**

Danach `agent/findings/FINDINGS_PHASE_7_v1.4.md`, committen, pushen, stoppen.

Es folgt Phase 8 — die Prüfmaske. Die Aufräumrunde für die vier toten Module
(`logger_config.py`, `clean_input_data.py`, `csv_processor.py`,
`csv_postprocessor.py`, dazu `data_cleaner.py.bak`) kommt danach.
