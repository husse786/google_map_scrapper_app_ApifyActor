
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
