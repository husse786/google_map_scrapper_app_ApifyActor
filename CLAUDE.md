# CLAUDE.md

## Was hier gebaut wird

Umbau eines Tkinter-Desktoptools zu einer Webapp. Sie reichert
ERP-Kundendaten mit Google-Maps-Daten an und liefert drei CSV-Dateien
für den Import zurück.

Nutzer ist **ein** Sachbearbeiter ohne IT-Hintergrund.

## Deine Rolle

Du bist der Entwickler. Architektur und Fachentscheidungen sind bereits
getroffen und liegen in `agent/`. Du entwirfst nichts neu.

## Vor jeder Arbeit lesen

1. `agent/00_START_HIER.md` — Arbeitsweise, wann stoppen, wann nicht
2. `agent/01_PHASENPLAN.md` — welche Phase, welche Abnahmekriterien
3. `agent/02_DATENVERTRAG.md` — Spalten, Zustände, Schema (verbindlich)
4. `agent/03_ENTSCHEIDUNGEN.md` — feste Werte (höchste Priorität)

Bei Widerspruch: `03` schlägt `02` schlägt `01` schlägt `UMBAUPLAN` schlägt Prototyp.

## Die vier Regeln, die alles andere schlagen

1. **Die ERP-Datei ist heilig.** Eine falsche Adresse in `fertig_fuer_erp.csv`
   ist schlimmer als hundert Fälle in `zur_pruefung.csv`. Im Zweifel Prüfung.
2. **Jeder Kunde landet in genau einer der drei Ausgabedateien.** Nie in zweien,
   nie in keiner.
3. **Jede Zeile trägt `score` und einen deutschen Klartextgrund.** Keine
   Pauschallabels, keine Fachsprache.
4. **Kein Overengineering.** Ein Nutzer, ein Job. Was in `agent/03` unter
   „wird nicht gebaut" steht, wird nicht gebaut — auch nicht vorbereitend.

## Arbeitsweise

Phase bauen → Abnahmekriterien selbst prüfen → `agent/findings/FINDINGS_PHASE_N.md`
schreiben (Vorlage: `agent/04_FINDINGS_VORLAGE.md`) → stoppen.

Nicht in die nächste Phase weiterlaufen. Der Prüfer gibt frei oder liefert
einen Korrekturplan.

**Bei unklaren Randfällen:** Annahme treffen, weiterbauen, Annahme in die
Findings schreiben. Nicht anhalten, nicht nachfragen. Anhalten nur in den vier
Fällen aus `agent/00_START_HIER.md`.

## Sprache

Code und Commits Englisch. Alles, was der Nutzer sieht — Oberfläche,
Fehlermeldungen, Gründe in der CSV, Mails — Deutsch, Schweizer Schreibweise
(kein ß, Tausender mit Apostroph: 2'513). Keine Stacktraces im Interface.

## Bestandscode

`data_cleaner.py` ist an 5'000 echten Kunden erprobt. Benannte Fehler werden
behoben, sonst nichts. Scoring nicht neu schreiben, Fuzzy-Bibliothek nicht
wechseln, Gewichtungen nicht ändern.

`main.py` und `ui_manager.py` entfallen im Umbau.

## Branch

Arbeite auf `umbau/webapp`. `main` trägt den produktiven Stand.