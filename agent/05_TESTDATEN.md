# 05 — TESTDATEN UND DATENSCHUTZ

**Das Repository ist öffentlich.** Jeder kann es ohne Anmeldung lesen.

---

## Harte Regel

Echte Kundendaten gehören **niemals** ins Repository. Weder als Testdatei, noch
als Beispiel in einem Commit, noch als Zitat in einem Findings-Bericht, noch in
einem Log, das mitcommittet wird.

Betroffen sind: Firmennamen echter Kunden, Adressen, Telefonnummern, Webseiten,
Kundennummern aus dem ERP, Google-`placeId` und `cid` echter Betriebe.

`.gitignore` schliesst `Daten/` bereits aus. Das bleibt so. Wenn ein Testlauf
eine Ausgabedatei erzeugt, gehört sie unter `Daten/` und nirgendwo anders.

---

## Zwei Datensätze, zwei Orte

### Fixture — im Repository

`agent/testdaten/fixture_optimierte_daten.csv`

17 Zeilen, 10 Kunden, **vollständig erfunden**. Deckt alle Grenzfälle ab, die
Phase 1 prüfen muss. Grundlage aller automatisierten Tests.

| KundenNr | Fall | Erwartet nach den Korrekturen |
|---|---|---|
| 900001 | 3 Treffer, davon 1 mit passender Strasse, 1 falsche PLZ | ① `OK (Strasse)` |
| 900002 | `KST 715611 0` statt Strasse, 6 Treffer | ② `PRUEFUNG (keine Strassentreffer)` — **und nicht zusätzlich in aussortiert** |
| 900003 | `Dorfstrasse 5` gesucht, `Oberdorfstrasse 5` und `Dorfstrasse 5` gefunden | ① — nur die echte Dorfstrasse darf zählen |
| 900004 | Schreibvariante `Musterhöhe` / `Musterhöche` | ① |
| 900005 | Rebranding: Volg gesucht, Spar an derselben Adresse | ① — **darf nicht** in ② fallen |
| 900006 | Google liefert Strasse ohne Hausnummer | ① |
| 900007 | 2 fast gleiche Treffer, beide hoch | ② `PRUEFUNG (mehrere hohe Treffer)` |
| 900008 | leeres Ergebnis | ③ |
| 900009 | Hausnummer 23 gesucht, 18 und 55 gefunden | ② — **und nicht zusätzlich in aussortiert** |
| 900010 | `St. Beispielstrasse` / `St.Beispielstrasse` | ① |

Gegen den heutigen, unkorrigierten Code erzeugt diese Datei nachweislich beide
Hauptfehler: 900002 und 900009 stehen gleichzeitig in `zur_pruefung` und
`aussortiert`.

### Echte Daten — nur lokal

Husey hält die realen Dateien unter `Daten/` auf seinem Rechner. Sie werden nie
committet. Für den Vergleichslauf in Phase 1 gibt Husey den lokalen Pfad an.

---

## Findings-Berichte

Findings werden committet und sind damit öffentlich. Deshalb:

**Erlaubt:** Zahlen, Anteile, Kategorien, Wechsel zwischen Ausgabedateien,
Namen aus der Fixture (900001–900010).

**Nicht erlaubt:** echte Kundennamen, echte Adressen, echte Kundennummern,
echte `placeId`, Auszüge aus realen Ein- oder Ausgabedateien.

Wenn ein Befund an einem echten Fall hängt, beschreibe das **Muster**, nicht den
Fall: statt „Kunde 4711, Bäckerei Meier, Rain 3" schreibe „ein Kunde, bei dem
Google die Hausnummer weglässt".

### Auswirkung auf Phase 1

Das Abnahmekriterium „Vergleichslauf vor/nach" gilt weiterhin, aber:

- **In den Findings:** nur die aggregierte Verteilung auf ①/②/③ vorher und
  nachher, plus die Anzahl Wechsler je Wechselrichtung mit Begründungsmuster.
- **Einzelfallliste mit Kundennummern:** wird als CSV unter `Daten/` erzeugt
  und bleibt lokal. In den Findings steht nur, dass sie existiert und wo.
- Für die **Fixture** darf die Einzelfallliste vollständig in die Findings —
  die Daten sind erfunden.

---

## Wenn versehentlich echte Daten committet wurden

Nicht einfach im nächsten Commit löschen — die Historie bleibt öffentlich
lesbar. Melden, stoppen, Husey entscheidet über das weitere Vorgehen.
