# 00 — START HIER

Du bist der **Entwickler** in diesem Projekt. Lies dieses Dokument vollständig,
bevor du eine Zeile schreibst.

---

## Rollen

| Rolle | Wer | Tut |
|---|---|---|
| Auftraggeber | Husey | entscheidet, gibt frei |
| Architekt / Prüfer | Claude (Chat) | Phasenplan, Datenvertrag, Abnahme, Korrekturpläne |
| **Entwickler** | **du (Claude Code)** | baut die Phasen, schreibt Findings |

Du entwirfst die Architektur nicht neu. Sie steht in `UMBAUPLAN_WEBAPP.md`.
Du triffst keine Fachentscheidungen. Sie stehen in `03_ENTSCHEIDUNGEN.md`.

---

## Ablauf pro Phase

```
1. Phase in 01_PHASENPLAN.md lesen  →  Umfang, Nicht-Umfang, Abnahmekriterien
2. Bauen
3. Abnahmekriterien selbst prüfen   →  müssen ALLE grün sein
4. FINDINGS_PHASE_N.md schreiben    →  Vorlage: 04_FINDINGS_VORLAGE.md
5. Stopp. Warten auf Freigabe oder Korrekturplan.
```

Nach jeder Phase ist Schluss. Nicht in die nächste Phase weiterlaufen.
Der Prüfer liest die Findings und gibt entweder frei oder liefert
`KORREKTURPLAN_PHASE_N.md`. Korrekturen werden zu Version 1.1, 1.2, … gezählt.

---

## Wann du weiterarbeitest (der Normalfall)

Arbeite durch, ohne zu fragen, wenn:

- eine Bibliothek gewählt werden muss und `03_ENTSCHEIDUNGEN.md` nichts sagt
- Datei- und Ordnernamen, Funktionsnamen, Klassenaufteilung anstehen
- Tests geschrieben werden müssen
- ein Randfall auftritt, den kein Dokument abdeckt

Im letzten Fall: **triff eine Annahme, halte dich an das nächstliegende
Muster im Datenvertrag, und schreib die Annahme in die Findings** unter
„Getroffene Annahmen". Nicht anhalten. Der Prüfer korrigiert sie, falls nötig.

## Wann du anhältst (die Ausnahme)

Nur bei diesen vier Dingen:

1. Ein Abnahmekriterium ist nicht erfüllbar, ohne den Datenvertrag zu brechen.
2. Ein Wert aus `03_ENTSCHEIDUNGEN.md` würde in der Praxis nachweislich falsche
   Daten ins ERP schreiben — mit Beleg aus einem Testlauf.
3. Zugangsdaten oder externe Freigaben fehlen (Apify-Token, Google-Key, SMTP).
   Ebenso: echte Kundendaten wurden versehentlich committet.
4. Zwei Dokumente widersprechen sich.

In allen vier Fällen: Findings schreiben, den Widerspruch benennen, stoppen.

---

## Unverhandelbare Regeln

**Die ERP-Datei ist heilig.** Datei ① wird ohne Prüfung ins ERP importiert.
Eine falsche Adresse dort ist schlimmer als hundert Fälle in Datei ②.
Im Zweifel immer Datei ② wählen.

**Jede Entscheidung muss begründet in der Ausgabe stehen.** Jede Zeile trägt
`score` und `grund` in Klartext. Kein Datensatz verlässt das System mit einem
Pauschallabel. Der heutige Code verwirft die Score-Spalte — das ist einer der
Fehler, die du behebst, nicht ein Muster, dem du folgst.

**Kein Kunde geht verloren.** Jeder Kunde aus der Eingabedatei landet in genau
einer der drei Ausgabedateien. Nie in zweien, nie in keiner. Das ist prüfbar
und wird in jeder Phase geprüft.

**Das Repository ist öffentlich. Keine echten Kundendaten hinein.** Nicht als
Testdatei, nicht als Beispiel im Commit, nicht als Zitat in den Findings.
Details in `05_TESTDATEN.md`. Automatisierte Tests laufen gegen die Fixture.

**Kein Overengineering.** Ein Nutzer, ein Job zur Zeit. Kein Login, kein Redis,
kein Celery, kein React, kein Kubernetes. Wenn dir eine Abstraktion einfällt,
die „später mal nützlich sein könnte" — nicht bauen.

**Fachlogik wird übernommen, nicht neu erfunden.** `data_cleaner.py` ist an
5'000 echten Kunden erprobt. Du reparierst benannte Fehler darin. Du schreibst
das Scoring nicht neu, wechselst die Fuzzy-Bibliothek nicht und änderst keine
Gewichtung, die nicht in `03_ENTSCHEIDUNGEN.md` steht.

---

## Dokumente in diesem Ordner

| Datei | Inhalt |
|---|---|
| `00_START_HIER.md` | dieses Dokument |
| `01_PHASENPLAN.md` | 7 Phasen mit Umfang und Abnahmekriterien |
| `02_DATENVERTRAG.md` | Spalten, Zustände, Gründe, DB-Schema — **verbindlich** |
| `03_ENTSCHEIDUNGEN.md` | feste Werte und Technikwahl — **nicht abweichen** |
| `04_FINDINGS_VORLAGE.md` | Aufbau deines Berichts pro Phase |
| `05_TESTDATEN.md` | Fixture, Datenschutz — **das Repo ist öffentlich** |
| `testdaten/fixture_optimierte_daten.csv` | erfundene Testdaten mit allen Grenzfällen |
| `UMBAUPLAN_WEBAPP.md` | Gesamtbild, Begründungen, was bewusst wegfällt |
| `webapp_prototyp.html` | Zielbild der Oberfläche — Ablauf und Texte sind verbindlich, CSS nicht |

Bei Widerspruch gilt: `03_ENTSCHEIDUNGEN.md` > `02_DATENVERTRAG.md` >
`01_PHASENPLAN.md` > `UMBAUPLAN_WEBAPP.md` > Prototyp.

---

## Sprache

Code, Variablennamen und Commits auf Englisch.
Alles, was der Nutzer sieht — Oberfläche, Fehlermeldungen, Gründe in der CSV,
Mailtexte — auf **Deutsch**. Der Nutzer ist ein Schweizer Sachbearbeiter ohne
IT-Hintergrund. Keine Fachbegriffe, keine Abkürzungen, keine Stacktraces.
Schweizer Schreibweise: kein ß, Tausendertrennung mit Apostroph (2'513).
