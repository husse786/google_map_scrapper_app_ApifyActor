# FREIGABE — Phase 7, Version 1.4

Geprüft am 04.08.2026. Branch geklont, gepinnte Fassungen installiert,
fünf Läufe, Gegenprobe am Fortsetz-Fund.

**Ergebnis: freigegeben. Phase 7 ist abgeschlossen. Phase 8 kann starten.**

---

## 1. Nachgerechnet

| Prüfung | Ergebnis |
|---|---|
| Fünf vollständige Läufe unter `requirements.txt` | 5 × **305 grün** + 1 übersprungen |
| `data_cleaner.py` unangetastet | bestätigt — steht nicht im Diff |
| Grund wird am fertigen Datensatz berichtigt, nicht neu gebaut | bestätigt |
| Fortsetz-Absicherung ist belastbar | **gegengeprüft** — s. unten |

**Gegenprobe zum Fortsetz-Fund.** Ich habe die beiden Zeilen auskommentiert, die
den Grund beim Fortsetzen erhalten, und den Test erneut gefahren:

```
mit der Zeile:    2 passed
ohne die Zeile:   FAILED test_der_richtige_grund_ueberlebt_das_fortsetzen
```

Der Test sichert einen echten Rückfall ab, keinen gedachten.

---

## 2. Der Fund, der nicht im Plan stand

Der Korrekturplan verlangte, den Grund beim Ausfall richtigzustellen. Er hat
gesehen, dass die Korrektur **das Fortsetzen nicht überlebt hätte**:
`_aus_datenbank` leitet die Entscheidung eines bereits verarbeiteten Kunden neu
her, im Modus A über die Fachlogik aus einer Gruppe ohne Kandidaten — und
dabei wäre der Kunde auf den alten, falschen Satz zurückgefallen.

**Das ist der Weg, den die Anwendung selbst empfiehlt.** Nach zehn Fehlschlägen
sagt die Meldung „bitte den Lauf fortsetzen". Genau dort wäre die Korrektur
verschwunden.

Ohne diese Zeile wäre K1 nur an der Oberfläche behoben gewesen. Ein
Abnahmekriterium hätte den Unterschied nicht gezeigt — der erste Lauf war
korrekt, der fortgesetzte nicht. Diese Sorte Lücke findet man nur, indem man
fragt, was der Nutzer als Nächstes tut.

Die Unterscheidung, wie der Fall wiedererkannt wird, ist ebenfalls richtig
getroffen: Modus A am gespeicherten `grund`, Modus B an `qualitaet`, weil dort
`kein Ergebnis` ausschliesslich aus einem Ausfall entstehen kann.

---

## 3. Bestätigt

| Punkt | Urteil |
|---|---|
| Feld berichtigen statt Zeile neu bauen | **bestätigt.** Eine selbstgebaute Zeile müsste alle Vertragsspalten nachbilden und liefe auseinander, sobald `02` sich ändert. Die richtige Entscheidung, und gut begründet |
| `qualitaet`, `score` und Zieldatei unverändert aus der Fachlogik | bestätigt — `02_DATENVERTRAG.md` §3 unberührt |
| Zwei Zustände, zwei Sätze | bestätigt. „Kam nicht zurück, bitte später auffrischen" gegen „lieferte keinen einzigen Treffer" — verschiedene Handlungen für verschiedene Lagen |

---

## 4. Rückblick auf vier Runden

Der Ausgangsbefund war der schwerwiegendste des Projekts: Ein Lauf über 2'500
Kunden hätte alle nach ③ geschrieben, sich `FERTIG` genannt und drei Dateien
hingelegt — eine davon eine Lüge. Der Fehler stand seit Phase 2 im Code, an
Entwickler und Prüfer vorbei.

Vier Runden, jedes Mal derselbe Satz an einer anderen Stelle:

| Runde | Stelle |
|---|---|
| 1.0 | Sechs bekannte Apify-Fehlerarten stoppen den Lauf |
| 1.1 | Auch unbekannte Apify-Fehler — ein API-Fehler ist nie „nichts gefunden" |
| 1.2 | Fassungen festgenagelt; die Anwendung war ohne Pins nicht installierbar |
| 1.3 | Zeitüberschreitung ist keine Antwort — Vorgabe `03 C` war falsch |
| 1.4 | Der richtige Grund überlebt jetzt auch das Fortsetzen |

Vier Runden sind viel. Zwei davon gingen auf falsche Vorgaben des Prüfers
zurück (`03 C`, und ein Korrekturplan, der nur das Testproblem sah statt der
kaputten Installation). Der Lauf sagt jetzt in jeder Lage die Wahrheit über
sich selbst.

---

## 5. Stand

| Phase | Status |
|---|---|
| 1 Kern repariert und entkoppelt | freigegeben |
| 2 Provider und Datenmodell | freigegeben |
| 3 Worker, Parallelität, Wiederaufnahme | freigegeben (v1.1) |
| 4 Upload-Validierung und Messung | freigegeben |
| 5 Weboberfläche | freigegeben |
| 6 Modus B | freigegeben, Produktivsperre bis Live-Abruf |
| 7 Mail und Härtung | **freigegeben (v1.4)** |
| 8 Prüfmaske | offen |

**Offen beim Auftraggeber:** SMTP-Freigabe durch ICT und ein echter Versand über
das Firmen-Relais; Google Places aufschalten und ein Live-Abruf für Modus B;
die Zulässigkeit eines privaten Gmail-Kontos für Firmendaten.

**Nach Phase 8:** die Aufräumrunde für `logger_config.py`,
`clean_input_data.py`, `csv_processor.py`, `csv_postprocessor.py` und
`data_cleaner.py.bak` — eine Entscheidung je Datei.

---

Phase 8 startet nach `01_PHASENPLAN.md`.
