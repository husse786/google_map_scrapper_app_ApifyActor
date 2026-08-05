# 02 — DATENVERTRAG

Verbindlich. Namen, Spalten und Zustände werden nicht umbenannt, auch nicht
„zur Vereinheitlichung". Der Prüfer testet gegen genau diese Bezeichner.

---

## 1. Eingabedateien

Immer: Semikolon-getrennt, `utf-8-sig`, alle Felder als String einlesen
(`dtype=str`), nie als Zahl. PLZ `5620` darf nie zu `5620.0` werden.

### Modus A — Text (Erstanreicherung)

| Spalte | Pflicht | Beispiel |
|---|---|---|
| `SearchString` | ja | `Denner, Hauptstrasse 5, 5620 Bremgarten` |
| `PLZ` | ja | `5620` |
| `Stadt` | nein | `Bremgarten AG` |
| `KundenNr` | ja | `200147` |

`SearchString` hat drei kommagetrennte Teile: **Titel, Strasse+Nr, PLZ Stadt**.
Fehlt einer, ist die Zeile unvollständig.

`KundenNr` wird **nie** zur Suche verwendet. Sie wird unverändert durchgereicht
und muss in allen drei Ausgabedateien stehen.

### Modus B — placeId (Auffrischen)

| Spalte | Pflicht | Beispiel |
|---|---|---|
| `placeId` | ja | `ChIJVXealLU_xkcRja_At0z9AGY` |
| `lat` | nein | `47.3512` |
| `lng` | nein | `8.2401` |
| `KundenNr` | ja | `200147` |

`lat`/`lng` suchen nicht. Sie prüfen, ob der Betrieb noch am selben Ort ist.

---

## 2. Ausgabedateien

Genau drei, in beiden Modi identisch benannt:

| Datei | Bedeutung |
|---|---|
| `fertig_fuer_erp.csv` | automatisch akzeptiert, direkt importierbar |
| `zur_pruefung.csv` | unklar, Mensch entscheidet |
| `nicht_moeglich.csv` | kein verwertbares Ergebnis |

**Ablageort.** Die drei Dateien tragen feste Namen und würden sich bei mehreren
Läufen überschreiben. Sie werden deshalb in einen Ordner neben der Eingabedatei
geschrieben: `<eingabedateiname>_ergebnis/`. Beispiel:
`InputData_Prod.csv` → `InputData_Prod_ergebnis/fertig_fuer_erp.csv`.

**Invariante:** Jede `KundenNr` aus der Eingabe erscheint in **genau einer**
dieser Dateien. Nie in zweien, nie in keiner.

> Der heutige Code verletzt das: Bei null Strassentreffern landen dieselben
> Zeilen in `aussortiert` **und** `zur_pruefung`. Das ist Fehler B1 (Phase 1).

`aussortiert.csv` bleibt als **Diagnosedatei** bestehen, ist aber keine der
drei Ausgaben und unterliegt der Invariante nicht.

### Spalten der Ausgabedateien

```
KundenNr ; SearchString ; PLZ ; Stadt ;
title ; address ; street ; postalCode ; city ;
openingHours ; phone ; phoneUnformatted ; website ;
permanentlyClosed ; temporarilyClosed ; cid ; placeId ; location ;
qualitaet ; score ; grund
```

Die letzten drei sind neu und **Pflicht in allen drei Dateien**.
`score` wird nicht verworfen.

---

## 3. `qualitaet` — erlaubte Werte

Abschliessende Liste. Keine neuen Werte ohne Korrekturplan.

| Wert | Datei | Entstehung |
|---|---|---|
| `OK (Strasse)` | ① | genau 1 Strassentreffer |
| `OK (Score)` | ① | genau 1 Treffer ≥ 80 |
| `OK (Dynamisch)` | ① | Abstand Platz 1 zu 2 ≥ 30 |
| `OK (Einzeltreffer)` | ① | 1 Überlebender, Zusatzprüfung bestanden |
| `OK (ID)` | ① | Modus B, Direktabruf plausibel |
| `PRUEFUNG (mehrere hohe Treffer)` | ② | 2+ Treffer ≥ 80 |
| `PRUEFUNG (kein klarer Treffer)` | ② | kein Treffer ≥ 80, Abstand < 30 |
| `PRUEFUNG (keine Strassentreffer)` | ② | keine Strasse passt |
| `PRUEFUNG (keine PLZ-Treffer)` | ② | keine PLZ passt |
| `PRUEFUNG (Einzeltreffer unsicher)` | ② | 1 Überlebender, Zusatzprüfung nicht bestanden |
| `PRUEFUNG (geschlossen)` | ② | Modus B, `permanentlyClosed` |
| `PRUEFUNG (Standort abweichend)` | ② | Modus B, Distanz > 200 m |
| `OK (geprueft)` | ① | von Hand in der Prüfmaske gewählt (Phase 8) |
| `NICHT_MOEGLICH (geprueft)` | ③ | in der Prüfmaske: keiner der Treffer passt (Phase 8) |
| `NICHT_MOEGLICH (kein Ergebnis)` | ③ | API lieferte nichts |
| `NICHT_MOEGLICH (ID ungueltig)` | ③ | Modus B, placeId unbekannt |
| `NICHT_MOEGLICH (Eingabe unbrauchbar)` | ③ | Pflichtfeld fehlt oder leer |

**Schreibweise.** `qualitaet` ist der Schlüssel, den der ERP-Import liest, und
bleibt **umlautfrei**: `ue`, `oe`, `ae` statt `ü`, `ö`, `ä`. Alle Werte dieser
Liste folgen dem. Für `grund` gilt das nicht — dort ist freies Deutsch richtig.

---

## 4. `grund` — Klartext für den Sachbearbeiter

Deutsch, ein Satz, konkret, ohne Fachbegriffe. Nennt **Werte**, nicht Regeln.

Gut:

```
Strasse und Hausnummer stimmen exakt, Name zu 94% ähnlich.
Zwei Treffer gleich gut: "Spar Bremgarten" (91) und "Spar Markt" (88).
Gesucht Wohlerstrasse 23, gefunden Wohlerstrasse 18 und 55.
Im Strassenfeld steht "KST 715611 0" — das ist keine Strasse.
Google meldet den Betrieb als dauerhaft geschlossen.
Standort liegt 1.4 km von der gespeicherten Position entfernt.
```

Schlecht: `Stage 4 failed`, `score < threshold`, `no match`, `siehe Log`.

---

## 5. Datenbank (SQLite)

Eine Datei. Jeder Kandidat wird einzeln gespeichert — nicht nur die Ausgabe-CSV.
Das ist die Grundlage für Transparenz und für eine spätere Prüfmaske.

```sql
CREATE TABLE job (
  id INTEGER PRIMARY KEY,
  modus TEXT NOT NULL,              -- 'A' | 'B'
  dateiname TEXT NOT NULL,
  status TEXT NOT NULL,             -- s. Abschnitt 6
  email TEXT,
  kunden_total INTEGER DEFAULT 0,
  kunden_erledigt INTEGER DEFAULT 0,
  fehlermeldung TEXT,
  erstellt_am TEXT NOT NULL,
  gestartet_am TEXT,
  beendet_am TEXT
);

CREATE TABLE kunde (
  id INTEGER PRIMARY KEY,
  job_id INTEGER NOT NULL REFERENCES job(id),
  kunden_nr TEXT NOT NULL,
  search_string TEXT, plz TEXT, stadt TEXT,
  place_id TEXT, lat TEXT, lng TEXT,        -- Modus B
  ergebnis TEXT,                             -- 'fertig'|'pruefung'|'nicht_moeglich'
  qualitaet TEXT,
  grund TEXT,
  verarbeitet_am TEXT
);
CREATE INDEX idx_kunde_job ON kunde(job_id);
CREATE UNIQUE INDEX idx_kunde_nr ON kunde(job_id, kunden_nr);

CREATE TABLE kandidat (
  id INTEGER PRIMARY KEY,
  kunde_id INTEGER NOT NULL REFERENCES kunde(id),
  title TEXT, street TEXT, postal_code TEXT, city TEXT, address TEXT,
  place_id TEXT, cid TEXT, location TEXT,
  phone TEXT, phone_unformatted TEXT, website TEXT, opening_hours TEXT,
  permanently_closed TEXT, temporarily_closed TEXT,
  score REAL,
  entscheid TEXT,                            -- 'gewaehlt'|'abgelehnt'|'vorgeschlagen'
  grund TEXT
);
CREATE INDEX idx_kandidat_kunde ON kandidat(kunde_id);
```

`idx_kunde_nr` ist die technische Absicherung der Invariante aus Abschnitt 2.

---

## 6. Job-Zustände

```
NEU → VALIDIERT → LAEUFT → FERTIG
                     ↓
            ABGEBROCHEN | FEHLER
```

| Zustand | Bedeutung |
|---|---|
| `NEU` | Datei hochgeladen, noch nicht geprüft |
| `VALIDIERT` | Formatprüfung bestanden, wartet auf Start |
| `LAEUFT` | Worker arbeitet |
| `FERTIG` | alle Kunden verarbeitet, drei Dateien geschrieben |
| `ABGEBROCHEN` | Nutzer hat gestoppt |
| `FEHLER` | technischer Abbruch (Kontingent, Netz, Absturz) |

`kunden_erledigt` wird **nach jedem Kunden** geschrieben, nicht am Ende.
Er dient der **Anzeige**, nicht der Steuerung: bei parallelen Arbeitern hinkt er
naturgemäss hinterher (laufen sechs, und zwei mittlere werden zuerst fertig,
steht der Zähler auf dem tiefsten zusammenhängenden Stand).

**Der Wiederaufsatzpunkt ist die Tabelle `kunde`, nicht der Zähler.**
Fortgesetzt wird für jede `kunden_nr` aus der Eingabe, zu der noch keine Zeile
in `kunde` steht. `kunden_erledigt` wird beim Fortsetzen aus der Tabelle neu
gesetzt. Tests dürfen den Zähler nicht als Sollwert für die Anzahl
nachzuholender Kunden verwenden.

---

## 7. Provider-Schnittstelle

```python
class PlaceProvider(Protocol):
    def fetch_by_text(self, search_string: str, plz: str) -> list[Candidate]: ...
    def fetch_by_id(self, place_id: str) -> Candidate | None: ...
```

`Candidate` ist ein Dataclass mit den Feldern aus Tabelle `kandidat`
(ohne `id`, `kunde_id`, `score`, `entscheid`, `grund`).

Implementierungen: `ApifyProvider` (Modus A), `GoogleProvider` (Modus B).
Beide normalisieren auf `Candidate`. Ausserhalb des Providers darf kein Code
Apify- oder Google-spezifische Feldnamen kennen.
