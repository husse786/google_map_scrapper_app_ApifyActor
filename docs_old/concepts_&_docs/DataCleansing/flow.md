> ## ⚠ Historisches Dokument — nicht mehr gültig
>
> **Stand: 25.02.2026**, verschoben nach `docs_old/` am 03.08.2026. Zeigt den
> Ablauf der Tkinter-Anwendung vor dem Umbau zur Webapp.
>
> **Was daraus geworden ist:** Die Zwischendateien `_vollstaendig.csv` und
> `_unvollstaendig.csv` gibt es nicht mehr. Die Prüfung dahinter — hat der
> Suchbegriff alle drei Teile? — war beim Umbau verlorengegangen und ist in der
> Abschlussrunde als Warnung beim Hochladen nachgebaut worden: Der Nutzer sieht
> vor dem Start, wie viele Zeilen betroffen sind, und entscheidet selbst.
> Auch `..._optimierte_daten.csv` entfällt; der Lauf schreibt die drei
> Ausgabedateien direkt.
>
> **Den heutigen Ablauf** beschreibt [`README.md`](../../../README.md) in fünf
> Schritten; `agent/01_PHASENPLAN.md` und `agent/findings/` halten fest, wie er
> entstanden ist.

---

Original Input (testfile.csv)

         │
    Step 0: Pre-Processing (NEW)
         │
    ├── testfile_vollstaendig.csv      (8 Kunden — complete data)
    └── testfile_unvollstaendig.csv    (6 Kunden — missing street)
                                        + "fehlende_teile" column
         │
    Step 1: Enrichment (Flow 1) — use_vollstaendig.csv
         │
    Step 2: Cleansing (Flow 2)
         │
    ├── _eindeutig.csv
    ├──_zur_pruefung.csv
    ├──_aussortiert.csv
    └── _erneut_crawlen.csv
