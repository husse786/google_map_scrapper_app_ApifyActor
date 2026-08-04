# KORREKTURPLAN — Phase 7, Version 1.2 → 1.3

Geprüft am 04.08.2026. Branch geklont, Fassungen installiert, fünf Läufe.

---

## Gesamturteil

**K1 und K2 sind erledigt und belegt.** Ein einziger Punkt bleibt — und der ist
keine Korrektur an der Arbeit, sondern eine Entscheidung, die der Entwickler
korrekt an mich weitergereicht hat.

---

## 1. Nachgerechnet

| Prüfung | Ergebnis |
|---|---|
| Fünf vollständige Läufe unter `apify-client==2.0.0` | 5 × **297 grün** + 1 übersprungen |
| Pins stimmen mit dem Code überein | bestätigt — `call()` in 2.0.0 hat `timeout_secs` und `wait_secs`, genau wie `apify_provider.py:189` und `:201` sie aufruft |
| K1a versionsfeste Testkonstruktion | bestätigt |
| K2 Netzfehler ≠ „gelöscht" | bestätigt |

**Der Pin-Befund ist grösser als mein Korrekturplan.** Ich hatte nur das
Testproblem gesehen. Gemessen wurde: Ein frischer `pip install` ohne Pins wäre
mit `TypeError` gestartet, bevor eine einzige Anfrage rausgeht. Die Anwendung
war nicht installierbar — nicht „fragil", sondern kaputt bei jeder Neuinstallation.

Dass die Findings die Behauptungen der Vorsession nicht übernommen, sondern
empirisch gegengemessen haben, ist die richtige Arbeitsweise.

---

## 2. Der eine offene Punkt

### K1 — Zeitüberschreitung ist keine Antwort · **hoch**

**Der Entwickler hat die Stelle richtig erkannt und richtig nicht angefasst.**
`_mit_frist` in `pipeline.py` gibt bei Ablauf der Frist `None` zurück, was zur
leeren Liste wird — in Modus B also erneut zu „bei Google gelöscht".
Er hat nicht eingegriffen, weil `03_ENTSCHEIDUNGEN.md C` den Timeout
ausdrücklich als „wie leeres Ergebnis → ③" regelt und `03` laut `CLAUDE.md` den
Korrekturplan schlägt.

**Genau so soll es laufen.** Eine Vorgabe wird nicht eigenmächtig umgangen, auch
wenn sie falsch aussieht — sie wird gemeldet.

**Die Vorgabe war falsch. Sie ist geändert.**

Der Grund ist derselbe, der diese ganze Phase trägt und den er selbst
formuliert hat: Ein Apify-Fehler ist nie „nichts gefunden". Eine
Zeitüberschreitung ebenso wenig. In beiden Fällen wurde die Frage nicht
beantwortet — das ist kein Ergebnis.

`03_ENTSCHEIDUNGEN.md` C lautet jetzt:

| Verhalten bei Timeout | wie ein Netzfehler, zählt zu den zehn hintereinander |
| Retry nach Timeout | keiner |

**Zu tun.** `_mit_frist` wirft bei Ablauf der Frist
`QuelleNichtVerfuegbar(<deutsche Meldung>, endgueltig=False)` statt `None`
zurückzugeben. Der Abbruch durch den Nutzer bleibt unverändert — das ist ein
anderer Rückgabeweg und keine Zeitüberschreitung.

Die Beschreibung von `_mit_frist` wird mitgezogen; sie zitiert die alte Regel.

**Wirkung, zu belegen:**

- Ein einzelner Timeout kostet weiterhin genau einen Kunden
- Zehn hintereinander beenden den Lauf mit `FEHLER` statt mit `FERTIG` und
  vollen ③-Dateien
- In Modus B entsteht aus einem Timeout nie mehr die Aussage „gelöscht"

Nicht anfassen: die 180 Sekunden, die 30 Sekunden für Google, die Grenze von
zehn, das Verhalten bei Abbruch durch den Nutzer.

---

## 3. Bestätigt

| Punkt | Urteil |
|---|---|
| Pin auf `apify-client==2.0.0` statt Anhebung auf 3.1.1 | **bestätigt.** Der richtige Zug: erst festnageln, was nachweislich läuft. Eine Anhebung berührt `call()`, `wait_for_finish()` und die Fehlerbehandlung — das ist eine eigene Runde, keine Nebensache in einem Korrekturplan |
| `thefuzz` mitgepinnt | **bestätigt.** Alle Schwellenwerte aus `03 B` sind an dessen Verhalten gemessen. Eine andere Fassung verschiebt sie lautlos |
| Begründungen als Kommentar in `requirements.txt` | **bestätigt.** Wer die Fassung anheben will, liest zuerst, was daran hängt |
| K2 gemessen statt behauptet (100 Kunden: 100 × „gelöscht" → 0) | **bestätigt** |
| Behauptungen der Vorsession nachgemessen statt übernommen | **bestätigt** |

---

## 4. Zur Kenntnis

`apify-client 2.0.0` ist eine ältere Fassung. Das ist für den Moment richtig,
aber kein Dauerzustand — irgendwann kommt ein Grund zum Anheben
(Sicherheitslücke, neue Apify-Schnittstelle). Dann ist es eine eigene Runde mit
eigenem Plan, nicht ein Nebenbei. Der Kommentar in `requirements.txt` sorgt
dafür, dass derjenige weiss, was daran hängt.

---

## 5. Anweisung für Version 1.3

Umfang ist K1. Sonst nichts.

Danach `agent/findings/FINDINGS_PHASE_7_v1.3.md` mit fünf vollständigen Läufen
und dem Nachweis der drei Wirkungen aus Abschnitt 2. Dann stoppen.

Damit ist Phase 7 abgeschlossen. Es folgt Phase 8 — die Prüfmaske.
