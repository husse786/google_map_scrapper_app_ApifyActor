# Umbauplan — von Tkinter-Tool zur Webapp

> Stand: 03.08.2026. Ergänzt `VERBESSERUNGEN_CHECKLIST.md`, ersetzt sie nicht.
> Die Checkliste beschreibt Reparaturen am heutigen System, dieses Dokument den Umbau.

---

## 1. Zielbild

Ein Kollege (nicht IT-affin) öffnet einen Link im Intranet, lädt eine CSV hoch,
wartet, und lädt drei Dateien herunter. Mehr Bedienung gibt es nicht.

**Zwei Einstiege:**

| | Modus 1 — Adresse | Modus 2 — placeId |
|---|---|---|
| Input | `SearchString;PLZ;Stadt;KundenNr` | `placeId;lat;lng;KundenNr` |
| Ablauf | Suchen → Kandidaten → Scoring | Direktabruf + Kurzprüfung |
| Datenquelle | Apify | Google Place Details |
| Dauer (2'500 Kunden) | ~2 Stunden | ~10 Minuten |

**Drei Ausgaben, in beiden Modi identisch:**

| Datei | Inhalt |
|---|---|
| ① `fertig_fuer_erp.csv` | automatisch akzeptiert, direkt importierbar |
| ② `zur_pruefung.csv` | unklar — Mensch entscheidet |
| ③ `nicht_moeglich.csv` | kein Treffer / ungültige ID — evtl. neuer Versuch |

**Massstab:** Transparenz und gute Lösung, nicht Perfektion.
Im Zweifel Datei ② statt falscher Adresse in Datei ①.

---

## 2. Was aus dem heutigen Code bleibt

| Modul | Status |
|---|---|
| `data_cleaner.py` | **bleibt** — Kernwert, an 5'000 Kunden erprobt (mit Korrekturen, s. 6.) |
| `data_preprocessor.py` | **bleibt** — wird zur Upload-Validierung erweitert |
| `apify_wrapper.py` | **bleibt** — wird hinter Provider-Schnittstelle gelegt |
| `csv_postprocessor.py` | **bleibt** |
| `data_consolidator.py` | **bleibt** — Batch-Zusammenführung |
| `csv_processor.py` | **bleibt** |
| `main.py` | **weg** — Orchestrierung ist an Tkinter geklebt |
| `ui_manager.py` | **weg** |
| `clean_input_data.py` | **weg** — Einmalskript mit festem Pfad |

Rund 80% der Fachlogik wird übernommen. Neu ist die Hülle, nicht der Kern.

---

## 3. Datenquellen — eine Schnittstelle, zwei Implementierungen

```python
class PlaceProvider:
    def fetch_by_text(self, search_string: str, plz: str) -> list[Candidate]: ...
    def fetch_by_id(self, place_id: str) -> Candidate | None: ...
```

- `ApifyProvider` — Modus 1. Liefert zusätzlich gescrapte Kontaktdaten
  (Website-E-Mails, Telefonnummern), die Google Places nicht hat.
- `GoogleProvider` — Modus 2. Place Details per ID: Sekunden statt Minuten,
  Bruchteil der Kosten.

Umschaltbar per Konfiguration. Fällt eine Quelle aus, wird gewechselt statt umgebaut.

**Vor dem Aufschalten von Google klären:** Kreditkarten-Hinterlegung ist Pflicht
(auch im Gratiskontingent), und ein privates Gmail-Konto für Firmendaten sollte
mit ICT/Datenschutz abgestimmt sein, bevor produktiv damit gearbeitet wird.

---

## 4. Datenmodell (SQLite)

Der Punkt, an dem sich Transparenz entscheidet: **jeder Google-Kandidat wird
einzeln gespeichert**, nicht nur die exportierte CSV.

```
job
  id, modus, dateiname, status, erstellt_am, gestartet_am, beendet_am,
  kunden_total, kunden_erledigt, fehlermeldung, email

kunde
  id, job_id, kunden_nr, search_string, plz, stadt,
  place_id, lat, lng,            -- nur Modus 2
  ergebnis,                       -- fertig | pruefung | nicht_moeglich
  grund                           -- Klartext

kandidat
  id, kunde_id, title, street, postal_code, city, place_id, location,
  phone, website, opening_hours,
  score,                          -- wird NICHT verworfen
  entscheid,                      -- gewaehlt | abgelehnt | vorgeschlagen
  grund                           -- "Strasse+Nr exakt, Name 94%"
                                  -- "Hausnummer 18 statt 23"
```

**Warum das zählt:**

1. Die Ausgabe-CSV enthält `score` und `grund` — heute wird die Score-Spalte
   vor dem Schreiben verworfen und `qualitaet` ist ein Pauschallabel.
2. Nach einem Lauf ist auswertbar, *warum* Fälle in ② landen. Erst damit lässt
   sich entscheiden, ob eine Prüfmaske nötig ist.
3. Eine spätere Prüfmaske ist dann reine Oberfläche auf vorhandenen Daten —
   keine Datenmigration.

---

## 5. Job-Ablauf

```
NEU → VALIDIERT → LAEUFT → FERTIG
                     ↓
            ABGEBROCHEN | FEHLER
```

- **Fortschritt** wird nach jedem Kunden in die DB geschrieben. Ein Absturz
  kostet einen Kunden, nicht zwei Stunden.
- **Wiederaufnahme:** Beim Start prüft die App auf einen Job im Status `LAEUFT`
  und bietet Fortsetzung ab dem letzten erledigten Kunden an.
- **Abbruch-Button** stoppt den laufenden Apify-Run wirklich, nicht nur die Anzeige.
- **Harte Obergrenze** Zeilen pro Upload — Schutz vor versehentlichem
  Kontingent-Verbrauch.
- **Mail** bei `FERTIG`, `FEHLER`, `ABGEBROCHEN` (Adresse pro Job hinterlegbar).

---

## 6. Arbeitspakete in Reihenfolge

### AP0 — Vier Fehler im heutigen Cleaner beheben
*Vor dem Umbau, weil sie sonst mitwandern.*

| | Fund | Datei |
|---|---|---|
| a | Zeilen landen **doppelt** in `aussortiert` und `zur_pruefung` (Stufe 4, 0 Strassentreffer) — verfälscht alle bisherigen Statistiken | `data_cleaner.py` |
| b | `_street_matches` nutzt `partial_ratio`: `Dorfstrasse` = `Oberdorfstrasse` → **falsche Strasse kann ins ERP** | `data_cleaner.py` |
| c | `score`-Spalte wird vor dem Schreiben verworfen | `data_cleaner.py` |
| d | Stufe 3 akzeptiert Einzeltreffer ohne Namensprüfung | `data_cleaner.py` |

→ entspricht Checkliste 1, 2, 7 plus einem bisher undokumentierten Fund (a).

### AP1 — Fachlogik von der GUI lösen
`data_cleaner` & Co. bekommen eine aufrufbare Schnittstelle ohne Tkinter.
Danach ist der Kern unabhängig lauffähig und testbar.

### AP2 — Provider-Schnittstelle
`ApifyProvider` aus dem heutigen Wrapper. Timeout pro Call (~90 s) —
fehlt bis heute komplett, ein hängender Run blockiert unbegrenzt.

### AP3 — Datenbank + Job-Modell
SQLite, Schema aus Abschnitt 4, Fortschrittsschreibung.

### AP4 — Worker
Hintergrund-Thread, Wiederaufnahme, Abbruch.

### AP5 — Upload-Validierung
Der grösste Hebel überhaupt. Prüfung **beim Hochladen**, nicht erst am Ende:

- Pflichtspalten vorhanden?
- Sieht das Strassenfeld nach einer Kostenstelle aus (`KST 715611 0`)?
- Ist der Titel nur eine Kategorie (`Boucherie`, `Lebensmittelgeschäft`)?

Meldung im Klartext:
> *312 Zeilen haben im Strassenfeld keinen Strassennamen (Beispiel Zeile 1'204:
> `KST 715611 0`). Diese landen voraussichtlich in Datei ②. Trotzdem starten?*

Von 5'188 Prüfzeilen der Batches 1–4 waren **4'288 = „keine Strassentreffer"**,
also fehlerhafte ERP-Eingabe. Hier liegt mehr Wirkung als in jeder Scoring-Änderung.

### AP6 — Web-Oberfläche
FastAPI + Jinja + HTMX. Vier Seiten: Start (Modus wählen), Upload,
Status, Ergebnis. Ein sichtbarer nächster Schritt pro Seite.

### AP7 — Modus 2
`GoogleProvider` + Kurzprüfung:

| Fall | Ergebnis |
|---|---|
| `permanentlyClosed` | Datei ② |
| Distanz zu hinterlegtem lat/lng > ~200 m | Datei ② (Umzug?) |
| placeId ungültig / kein Treffer | Datei ③ |
| Name geändert (Volg → Spar) | Hinweis, **kein** Prüffall — Rebranding ist normal |

### AP8 — Mailversand
Abhängig von SMTP-Freigabe durch ICT. Bis dahin ersetzt die Statusseite die Mail.

---

## 7. Bewusst NICHT gebaut

- **Login / Nutzerverwaltung** — ein User, im Intranet
- **Job-Queue mit Prioritäten, Redis, Celery** — ein Job zur Zeit
- **WebSockets** — Polling alle 5 Sekunden genügt
- **React / npm / Build-Pipeline** — Upload, Fortschritt, Download
- **Prüfmaske im Browser** — *zurückgestellt, nicht abgelehnt.*
  Etwa 40% des Gesamtaufwands. Ob sie sich lohnt, hängt daran, wie viele
  Prüffälle nach AP5 übrig bleiben. Diese Zahl kennt heute niemand.
  Das Datenmodell (Abschnitt 4) hält sie offen.

---

## 8. Offene Punkte

| Punkt | Wer entscheidet | Blockiert |
|---|---|---|
| Interner Server | ICT | Nein — s. Abschnitt 10 (Betrieb in zwei Stufen) |
| SMTP-Relay | ICT | Nein — AP8, Statusseite überbrückt |
| Google Places aufschalten | Husey (Gmail vorhanden) | Nein — AP7 |
| Gmail-Konto für Firmendaten zulässig? | ICT / Datenschutz | Vor Produktivbetrieb Modus 2 |
| Batch 5 gelaufen? | Husey | Nein, aber Datenlage unklar |

---

## 9. Doku, die mitgezogen werden muss

Aus der bestehenden Checkliste, unverändert gültig:

- `README.md` beschreibt 2 Schritte statt 4
- `flow.md` fehlt Schritt 3
- `ALGORITHM_EXPLAINED.md` Stufe 2 weicht vom Code ab
- `config.template.py` weicht ab: `maxCrawledPlacesPerSearch` 4 statt 6,
  `scrapeDirectories` False statt True

---

## 10. Betrieb in zwei Stufen

Identische Codebasis. Der Unterschied ist eine Zeile.

### Stufe 1 — Husey-PC als Host, Kollege greift per Browser zu

```python
uvicorn.run(app, host="0.0.0.0", port=8000)
```

Der Kollege öffnet `http://husey-pc:8000` im Firmennetz.
**Er installiert nichts, braucht keine Rechte, keine ICT-Freigabe.**
Nur ein Browser — wie bei jeder internen Webseite.

Alles Technische liegt auf Huseys Rechner: App, Datenbank, Apify-Token,
Ergebnisdateien.

**Was einmalig nötig ist (nur auf Huseys PC):**

- Firewall-Regel: Port 8000 eingehend, lokales Netz.
  Braucht Adminrechte auf der eigenen Maschine. Falls nicht vorhanden:
  Zwei-Satz-Anfrage an ICT — deutlich kleiner als ein Serverantrag.
- Rechnername statt IP verwenden, sonst bricht der Link nach jedem Neustart.

**Grenzen, die spürbar werden:**

- Huseys PC ist der Server. Zuklappen, Ruhezustand, Update-Neustart →
  laufender Job stirbt. Bei ~2 Stunden Laufzeit passiert das einmal.
  Wiederaufnahme (AP4) rettet die Daten, nicht die Wartezeit.
- Ohne Husey am Arbeitsplatz kein Zugriff.

**Rückfallweg,** falls das Firmen-WLAN PC-zu-PC-Verbindungen sperrt
(Client-Isolation — in fünf Minuten getestet): App einmalig auf dem PC des
Kollegen einrichten, Desktop-Icon, Browser öffnet `localhost:8000`.
Für ihn identisch, nur mehr Einrichtungsaufwand für Husey.

**Datenschutz:** Echte Kundendaten gehören auf den Arbeitsrechner im Firmennetz,
nicht auf private Hardware. Zum Entwickeln reichen die Testdaten.

### Stufe 2 — interner Server

Link im Intranet, Jobs laufen unabhängig vom Arbeitsplatz weiter,
beide sehen dieselben Jobs.

**Warum in dieser Reihenfolge:** Bei ICT lässt sich mit einem laufenden System
besser argumentieren als mit einem Konzept. Stufe 1 ist genau der Beleg,
den die Anfrage braucht — deshalb auch keine Umgehung von Firewall- oder
Netzwerkregeln: das würde genau dieses Argument zerstören.
