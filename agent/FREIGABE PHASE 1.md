# FREIGABE — Phase 1

Geprüft am 03.08.2026. Code aus dem Repository gezogen und selbst ausgeführt,
nicht aus dem Bericht übernommen.

**Ergebnis: freigegeben. Keine Korrekturrunde. Phase 2 kann starten.**

---

## 1. Nachgerechnete Kriterien

| Prüfung | Ergebnis |
|---|---|
| Die 8 Strassenpaare aus `03_ENTSCHEIDUNGEN.md` B1 | 8 von 8 korrekt |
| Fixture 900001–900010 gegen `05_TESTDATEN.md` | 10 von 10 korrekt |
| Kunde in mehr als einer Ausgabedatei | keiner |
| `score` und `grund` in allen drei Dateien befüllt | keine Lücke |
| `pytest` | 48 grün |
| Klartextgründe ohne Fachsprache | bestanden |
| Zahlen der Wechslertabelle | gehen auf: 201−28=173 · 189−38+1=152 |
| Echte Kundendaten in den Findings | keine |

Meine Rückfragen aus der Vorprüfung sind beantwortet. Die scheinbare Lücke
zwischen 229 Wechslern und 173 Differenz war eine Verkürzung im Kurzbericht,
nicht in den Findings.

---

## 2. Bestätigte Eigenentscheide

| Entscheid | Urteil |
|---|---|
| Ergebnisse in `<dateiname>_ergebnis/` | **bestätigt** und in `02_DATENVERTRAG.md` §2 übernommen. Der Vertrag hatte diese Lücke — der Entwickler hat sie richtig geschlossen |
| `main.py` und `ui_manager.py` gelöscht | **bestätigt**, über `git show main:main.py` abgesichert |
| B1 auf drei Ausprägungen erweitert (Strasse, PLZ, leere Zeilen) | **bestätigt**. Der Phasenplan nannte nur eine; die anderen beiden verletzen dieselbe Invariante. Richtig erkannt |
| „Exakt" in B2 = zeichengleich nach Normalisierung, beidseitig Hausnummer | **bestätigt**, strenger als der Fuzzy-Vergleich, im Zweifel ② |

---

## 3. Befunde, die über den Auftrag hinausgingen

Drei Dinge, die weder im Phasenplan standen noch dem Prüfer aufgefallen waren:

1. **Vier falsche Adressen in batch_4**, bei Kunden, die vorher wie nachher in ①
   stehen — nur mit anderem Treffer. Ohne B2 wären sie ins ERP gegangen, ohne in
   irgendeiner Statistik aufzufallen. Genau der Fehlertyp, wegen dem AP0 vor den
   Umbau gestellt wurde.
2. **Die acht Alttests liefen nie unter pytest** (Klasse mit `__init__` wird nicht
   eingesammelt). Die Testabdeckung war faktisch null.
3. **Alttest 6 prüfte nicht, was er zu prüfen vorgab** — beide Titel lagen über 80,
   der dynamische Abstand wurde nie berührt.

---

## 4. Ausdrücklich nicht zu ändern

Bleibt so, auch wenn es überrascht:

- **② wächst um rund 7 Prozentpunkte.** Gewollt. Ungeprüfte Einzeltreffer und
  Treffer an Nachbarstrassen gehören nicht automatisch ins ERP. Ob die Menge
  handhabbar bleibt, entscheidet sich nach Phase 4 (Upload-Validierung).
  Vorher wird an keiner Schwelle gedreht.
- **`OK (Einzeltreffer)` ist mit rund 1'100 Kunden die grösste ①-Gruppe.**
  Erklärbar: Nach dem PLZ-Filter bleibt oft nur ein Treffer. Erneut betrachten
  in Phase 4, nicht jetzt.
- **Kurzkürzel-Schwäche von `token_set_ratio`** (`bp`, `LS`, `DLZ`) bleibt
  unangetastet, wie in `03_ENTSCHEIDUNGEN.md` B3 festgelegt.

---

## 5. Vertragsänderung aus dieser Phase

`02_DATENVERTRAG.md` §2 wurde ergänzt:

> Die drei Dateien werden in einen Ordner `<eingabedateiname>_ergebnis/` neben
> der Eingabedatei geschrieben.

Ab sofort verbindlich, nicht mehr Entscheidung des Entwicklers.

---

## 6. Hinweis an den Auftraggeber

Auf dem Stand, der Phase 1 enthält, fehlen `main.py` und `ui_manager.py`.
Die alte Tkinter-Anwendung ist dort nicht mehr startbar — das ist gewollt.

Falls **Batch 5** noch mit der alten Anwendung gefahren werden soll, muss dafür
ein Stand ohne Phase 1 verwendet werden (`git show`/`git checkout` auf den
Commit davor). Sonst kein Handlungsbedarf.

---

Phase 2 startet nach `01_PHASENPLAN.md`.
