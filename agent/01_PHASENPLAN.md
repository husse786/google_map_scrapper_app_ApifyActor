# 01 — PHASENPLAN

Sieben Phasen. Jede endet mit etwas Lauffähigem und mit Kriterien, die du
**selbst prüfen** kannst. Nach jeder Phase: Findings schreiben, stoppen.

Abnahmekriterien sind keine Vorschläge. Ist eines rot, ist die Phase nicht fertig.

---

## Phase 1 — Kern reparieren und aus der GUI lösen

**Ziel:** Die erprobte Fachlogik läuft ohne Tkinter, mit behobenen Fehlern und
mit nachvollziehbarer Ausgabe.

### Umfang

**B1 — Doppelzählung beheben.**
In `data_cleaner.py`, Stufe 4: Bei null Strassentreffern werden dieselben Zeilen
erst nach `rejected_results` und danach nochmals nach `review_results`
geschrieben. Nachgewiesen an `testfile_optimierte_daten.csv`: Kunde 107 und 110
stehen mit **allen** Zeilen in beiden Dateien. Ein Kunde gehört in genau eine
Ausgabedatei.

**B2 — Strassenvergleich korrigieren.**
`fuzz.partial_ratio` → `fuzz.ratio`, Schwelle ≥ 90. Werte und Belege in
`03_ENTSCHEIDUNGEN.md` B1.

**B3 — Einzeltreffer prüfen.**
Regel aus `03_ENTSCHEIDUNGEN.md` B2 einbauen.

**B4 — `score` und `grund` in die Ausgabe.**
Die Zeile, die `score` vor dem Schreiben verwirft, entfällt. Jede Ausgabezeile
bekommt zusätzlich einen deutschen Klartextgrund nach `02_DATENVERTRAG.md` §4.

**B5 — Entkoppeln.**
Fachlogik ohne Tkinter aufrufbar. `main.py` und `ui_manager.py` werden nicht
mehr gebraucht. Eine schlanke CLI genügt, um die Kette anzustossen.

### Nicht in dieser Phase

Keine Datenbank, kein Web, kein Provider-Interface, keine neue Scoring-Logik.

### Abnahmekriterien

- [ ] `pytest` grün, inklusive der bestehenden Tests aus `test_data_cleaner.py`
- [ ] Neuer Test: keine `KundenNr` erscheint in mehr als einer der drei Ausgabedateien
- [ ] Neuer Test: Summe der Kunden über alle drei Dateien = Anzahl Kunden in der Eingabe
- [ ] Neuer Test: alle sieben Beispielpaare aus `03_ENTSCHEIDUNGEN.md` B1 werden korrekt entschieden
- [ ] Neuer Test: Einzeltreffer-Regel B2 greift, Rebranding-Fall (gleiche Adresse, anderer Name) bleibt in ①
- [ ] `score` und `grund` sind in allen drei Ausgabedateien befüllt, keine leeren Werte
- [ ] Alle 10 Fälle aus `agent/testdaten/fixture_optimierte_daten.csv` landen
      dort, wo `05_TESTDATEN.md` es vorgibt — insbesondere 900002 und 900009
      **nur noch in einer** Datei, und 900005 (Rebranding) weiterhin in ①
- [ ] **Vergleichslauf dokumentiert.** Zwei Läufe, vor und nach den Korrekturen:
      - gegen die Fixture: vollständig, inklusive Einzelfällen, in den Findings
      - gegen die reale Datei (Pfad von Husey, liegt unter `Daten/`):
        **nur aggregiert** in den Findings — Verteilung auf ①/②/③ vorher und
        nachher, Anzahl Wechsler je Richtung, Begründungsmuster.
        Die Einzelfallliste wird als CSV unter `Daten/` abgelegt und **nicht
        committet**. Regeln in `05_TESTDATEN.md`.

Das letzte Kriterium ist das wichtigste. Ohne diesen Vergleich weiss niemand,
was die Korrekturen bewirkt haben.

---

## Phase 2 — Provider und Datenmodell

**Ziel:** Datenquelle ist austauschbar, jeder Kandidat wird gespeichert.

### Umfang

- `PlaceProvider`-Protokoll und `Candidate`-Dataclass nach `02_DATENVERTRAG.md` §7
- `ApifyProvider` aus dem heutigen `apify_wrapper.py`, mit **90-Sekunden-Timeout**
- SQLite-Schema exakt nach `02_DATENVERTRAG.md` §5, inklusive beider Indizes
- Zugriffsschicht: Job anlegen, Kunde schreiben, Kandidaten schreiben, Fortschritt lesen
- Ein `FakeProvider` mit festen Antworten aus Dateien — damit alle folgenden
  Phasen ohne Apify-Kosten testbar sind

### Nicht in dieser Phase

Kein Web, kein Worker, kein Google.

### Abnahmekriterien

- [ ] Kein Modul ausserhalb von `ApifyProvider` kennt Apify-Feldnamen
- [ ] Der Lauf aus Phase 1 funktioniert unverändert über `ApifyProvider`
- [ ] Derselbe Lauf funktioniert über `FakeProvider` ohne Netzzugriff
- [ ] Timeout nachweisbar: Test mit künstlich verzögertem Provider endet nach ~90 s in ③
- [ ] Nach einem Lauf enthält die Datenbank jeden Kandidaten mit `score` und `entscheid`
- [ ] `idx_kunde_nr` verhindert nachweislich einen doppelten Kunden pro Job

---

## Phase 3 — Worker

**Ziel:** Ein Lauf überlebt geschlossene Browserfenster und Abstürze.

### Umfang

- Hintergrund-Thread, ein Job zur Zeit, zweiter Start wird abgewiesen
- **Sechs parallele Worker** (`03_ENTSCHEIDUNGEN.md` C). Sie lagen im Altcode in
  `main.py` Zeile 235 (`ThreadPoolExecutor(max_workers=6)`) und sind mit dessen
  Löschung in Phase 1 verschwunden. Referenz: `git show a17150e~1:main.py`.
  Ohne sie dauert ein Batch statt rund zwei Stunden ein Vielfaches.
- `kunden_erledigt` nach **jedem** Kunden in die Datenbank
- Zustände nach `02_DATENVERTRAG.md` §6
- Wiederaufnahme: beim Start `LAEUFT` erkennen, ab `kunden_erledigt` fortsetzen
- Abbruch, der den laufenden Apify-Aufruf wirklich beendet
- Am Ende drei CSV-Dateien schreiben

### Abnahmekriterien

- [ ] Prozess wird mitten im Lauf hart beendet, Neustart setzt fort, kein Kunde doppelt, keiner fehlt
- [ ] Abbruch beendet den Lauf in unter 5 Sekunden, Status `ABGEBROCHEN`
- [ ] Zweiter Start bei laufendem Job wird mit Hinweis abgewiesen
- [ ] Fortschrittszahl entspricht während des Laufs jederzeit der Anzahl verarbeiteter Kunden
- [ ] Drei Dateien werden geschrieben, Invariante aus `02_DATENVERTRAG.md` §2 gilt
- [ ] Sechs Worker laufen parallel, nachgewiesen gegen den `FakeProvider`
      (künstliche Verzögerung: Gesamtzeit liegt nahe bei einem Sechstel der
      sequentiellen Zeit)
- [ ] Abbruch und Wiederaufnahme funktionieren **mit** aktiver Parallelität,
      nicht nur sequentiell — kein Kunde doppelt, keiner verloren
- [ ] Der Timeout aus Phase 2 greift weiterhin je Aufruf, nicht je Lauf

---

## Phase 4 — Upload-Validierung

**Ziel:** Der Nutzer erfährt **vor** dem Zweistundenlauf, was schiefgehen wird.

### Umfang

Drei Prüfungen nach `03_ENTSCHEIDUNGEN.md` D. Alle warnen, keine blockiert.
Jede Meldung nennt Anzahl, Beispielzeile im Original und Zeilennummer.
Zusätzlich: Zeilenobergrenze 10'000, Pflichtspalten, Zeilenzahl melden.

### Abnahmekriterien

- [ ] `Emil Frey AG, KST 715611 0, 5745 Safenwil` wird als Kostenstelle erkannt
- [ ] `Denner, Hauptstrasse 5, 5620 Bremgarten` wird **nicht** als Kostenstelle erkannt
- [ ] `Boucherie, Rue des Tilleuls 5, 1800 Vevey` wird als reiner Kategorietitel erkannt
- [ ] Fehlende Pflichtspalte erzeugt eine deutsche Meldung mit Beispielzeile, keinen Stacktrace
- [ ] Datei mit 10'001 Zeilen wird abgewiesen
- [ ] **Messung dokumentiert:** Wie viele Zeilen einer realen Eingabedatei jede
      der drei Prüfungen trifft, und wie viele Prüffälle dadurch voraussichtlich
      entfallen
- [ ] **Laufzeitmessung dokumentiert:** mindestens zehn aufeinanderfolgende
      echte Apify-Aufrufe mit Einzelzeiten. Klärt die offene Frage aus Phase 3,
      warum das Betriebsprotokoll rund 17 Sekunden nennt und Einzelmessungen
      rund 85. Falls Kaltstarts regelmässig über 180 s liegen, ist das ein
      Befund für den Prüfer — die Frist wird nicht eigenmächtig erhöht

Die Messung entscheidet später, ob eine Prüfmaske gebaut wird. Ohne sie ist die
Frage nicht beantwortbar.

---

## Phase 5 — Weboberfläche

**Ziel:** Der Ablauf aus `webapp_prototyp.html` läuft echt.

### Umfang

FastAPI + Jinja2 + HTMX. Vier Seiten: Art wählen, Datei, Lauf, Ergebnis.
Statusseite pollt alle 5 Sekunden. Downloads der drei Dateien.
Fehlerseite in verständlichem Deutsch.

**Sauberes Beenden.** Befund aus Phase 3: Python wartet beim Beenden des
Prozesses auf abgebrochene Abfragen. Der Lauf steht sofort und die Daten sind
geschrieben, aber das Schliessen kann sich um bis zu 175 Sekunden verzögern.
In der Webapp betrifft das den Serverstopp — für den Nutzer sieht ein Fenster,
das sich drei Minuten nicht schliesst, wie ein Absturz aus.

Der Prototyp ist verbindlich für **Ablauf, Texte und Reihenfolge**, nicht für CSS.
Auf jeder Seite genau eine Haupthandlung.

### Abnahmekriterien

- [ ] Vollständiger Durchlauf mit `FakeProvider` ohne Terminal, nur im Browser
- [ ] Fortschrittsanzeige aktualisiert sich ohne Neuladen
- [ ] Browserfenster schliessen und wieder öffnen: Lauf läuft weiter, Stand stimmt
- [ ] Alle drei Dateien laden korrekt herunter, Semikolon, `utf-8-sig`
- [ ] Keine englische Zeichenkette in der Oberfläche, kein Stacktrace sichtbar
- [ ] Bedienbar mit Tastatur, Fokus sichtbar
- [ ] Server lässt sich während eines laufenden Jobs in **unter 10 Sekunden**
      beenden; danach ist der Job als `LAEUFT` in der Datenbank und wird beim
      nächsten Start zur Fortsetzung angeboten

---

## Phase 6 — Modus B (placeId)

**Ziel:** Auffrischen per gespeicherter ID.

### Umfang

- `GoogleProvider` für Place Details
- Eingabeformat Modus B nach `02_DATENVERTRAG.md` §1
- Plausibilitätsprüfung nach `03_ENTSCHEIDUNGEN.md` B4, Haversine, 200 m
- Zweiter Einstieg in der Oberfläche

Kein Scoring in diesem Pfad. Ein Kunde, eine ID, ein Ergebnis.

### Abnahmekriterien

- [ ] Gültige ID → ① mit `OK (ID)`
- [ ] Unbekannte ID → ③ mit `NICHT_MOEGLICH (ID ungueltig)`
- [ ] `permanentlyClosed` → ② mit verständlichem Grund
- [ ] Position 1.4 km entfernt → ②; Position 150 m entfernt → ①
- [ ] Fehlende `lat`/`lng` → keine Distanzprüfung, kein Prüffall
- [ ] Namensänderung allein löst **keinen** Prüffall aus
- [ ] Beide Modi schreiben identisch aufgebaute Ausgabedateien

---

## Phase 7 — Mail und Härtung

**Ziel:** Der Nutzer muss nicht am Bildschirm warten.

### Umfang

- Mail bei `FERTIG`, `FEHLER`, `ABGEBROCHEN`; Adresse pro Job hinterlegbar
- SMTP aus Konfiguration; fehlt sie, wird protokolliert statt zu scheitern
- Fehlertexte für die häufigen Fälle: Apify-Kontingent erschöpft, Netz weg,
  Token ungültig — jeweils mit Handlungsanweisung
- README für Einrichtung und Start

### Abnahmekriterien

- [ ] Mail wird in allen drei Fällen versendet, Betreff nennt Dateiname und Ergebnis
- [ ] Ohne SMTP-Konfiguration läuft der Job normal durch
- [ ] Erschöpftes Kontingent führt zu `FEHLER` mit deutscher Erklärung, nicht zu einem Absturz
- [ ] README beschreibt Einrichtung so, dass jemand ohne Vorkenntnisse dem Ablauf folgen kann

---

## Übersicht

| Phase | Ergebnis | Von Apify abhängig |
|---|---|---|
| 1 | reparierter Kern, per CLI lauffähig | nein |
| 2 | Provider + Datenbank | nur für einen Test |
| 3 | Worker mit Wiederaufnahme | nein (`FakeProvider`) |
| 4 | Upload-Validierung | nein |
| 5 | Weboberfläche | nein (`FakeProvider`) |
| 6 | Modus B | Google-Key nötig |
| 7 | Mail und Härtung | SMTP nötig |

Phasen 1 bis 5 laufen ohne externe Freigaben und ohne Apify-Kosten durch.
