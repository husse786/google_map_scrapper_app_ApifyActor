# FREIGABE — Abschlussrunde, Teile 2a und 2

Geprüft am 04.08.2026.

**Ergebnis: freigegeben. Der Umbau ist abgeschlossen.**

---

## 1. Nachgerechnet

| Prüfung | Ergebnis |
|---|---|
| Drei vollständige Läufe | 3 × **383 grün** + 1 übersprungen |
| Sieben Dateien entfernt | bestätigt, alle sieben |
| Alle Einstiegspunkte importieren | bestätigt |

---

## 2. Zwei Fehler in meinem Plan — beide richtig behandelt

**Der Widerspruch bei `data_preprocessor.py`.** Zeile 79 sagte „erst nach Teil 1
löschen", Zeile 152 verlangte, die Datei stehe noch da. Mein Nachtrag zum
Kriterium ist nicht durchgeschlagen. Und Zeile 148 sagte „sechs" — es waren
sieben.

Er hat Tabelle, Freigabe §5 und den Auftrag gegen ein Kriterium abgewogen, das
die Runde selbst überholt hatte, und gelöscht. Das ist die richtige Entscheidung
und die richtige Art, sie zu treffen: entscheiden, begründen, melden — statt
anzuhalten oder stillschweigend eine Seite zu wählen.

**Die Reihenfolge im README.** Mein Plan verlangte die Prüfmaske „zwischen Lauf
und Ergebnis". Der Schrittanzeiger der Anwendung lautet aber *… Ergebnis ·
Prüfung*, und die Maske wird von der Ergebnisseite aus erreicht.

Seine Begründung ist besser als meine Vorgabe: Ein Handbuch, das eine andere
Reihenfolge behauptet als der Bildschirm zeigt, führt genau den Nutzer in die
Irre, für den es geschrieben ist. Übernommen.

---

## 3. Der Befund, der ausblieb

Mein Plan rechnete damit, dass sich die Phase-4-Zahlen verschieben, und
verlangte sie vorher/nachher in den Findings. **Sie haben sich nicht
verschoben** — alle Phase-4-Fixtures verwenden vollständige Suchbegriffe, die
Überschneidung kam dort nie vor. Sichtbar wurde sie erst, als Teil 1 die vierte
Prüfung dazustellte.

Dass er die Zahlen trotzdem gemessen und gegen den Vorstand geprüft hat, statt
„keine Änderung" zu schreiben, ist der Unterschied zwischen Melden und Belegen.

---

## 4. Bestätigt

| Punkt | Urteil |
|---|---|
| Kategorieprüfung **nicht** angefasst | **bestätigt, und gut begründet.** Der Titelteil existiert immer; „der Name ist nur eine Branche" bleibt auch bei `Restaurant` ohne Komma wahr. Eine wahre zweite Aussage zu unterdrücken ist etwas anderes, als eine falsche zu entfernen |
| Eigener Testfehler gefunden und benannt | **bestätigt.** `data_cleaner.py.bak` auf `data_cleaner` zurückzuführen wäre ein Wächter gewesen, der ein lebendes Modul verboten hätte. Selbst gefunden, selbst gemeldet |
| Testzahl 363 → 384 statt unverändert | **bestätigt.** Mein Kriterium „unveränderte Testzahl" war unhaltbar, weil der Modulwächter aus Phase 2 über alle `*.py` parametrisiert ist und mit sechs Modulen schrumpft. Kein Test wurde entfernt oder abgeschwächt |
| Wächtertests halten jede Löschung fest | **bestätigt** |

---

## 5. Der Umbau

**383 Tests.** Aus einer Tkinter-Anwendung mit vier Schritten und vier bekannten
Fehlern ist eine Webanwendung geworden, die ein Sachbearbeiter ohne
IT-Hintergrund allein bedient.

| | |
|---|---|
| Phasen | 8, dazu eine Abschlussrunde |
| Korrekturrunden | 11 |
| davon durch falsche Vorgaben des Prüfers ausgelöst | 4 |

**Fünf Fehler, die ohne diesen Umbau ins ERP gegangen wären:**

1. `Dorfstrasse` galt als `Oberdorfstrasse` — vier falsche Adressen allein in
   batch_4, in keiner Statistik sichtbar
2. Einzeltreffer gingen ungeprüft ins ERP
3. Kunden standen gleichzeitig in zwei Ausgabedateien
4. Ein erschöpftes Apify-Kontingent hätte 2'500 Kunden nach ③ geschrieben und
   den Lauf `FERTIG` genannt
5. Ein Netzausfall im Modus B hätte gemeldet, der Kunde sei bei Google gelöscht

**Zwei Funktionen, die beim Umbau still verschwunden waren und
wiederhergestellt wurden:** die sechs parallelen Worker aus `main.py`, und die
Prüfung auf unvollständige Suchbegriffe aus `data_preprocessor.py`. Beide fielen
weg, weil beim Löschen einer Datei niemand fragte, was ausser dem
Offensichtlichen darin steckte.

---

## 6. Was noch offen ist

### Eine letzte kurze Runde: die historischen Dokumente

`WORKFLOW_AND_HANDOFF.md` und `docs_old/` beschreiben den Ablauf vor dem Umbau
und nennen Dateien, die es nicht mehr gibt. Sein Hinweis ist richtig.

**Nicht umschreiben — als historisch kennzeichnen.** Ein Kopfabsatz je Dokument:
Stand, Gültigkeit, und wohin man stattdessen sieht (`README.md` für den Betrieb,
`agent/` für den Umbau).

Das ist kein Schönheitsfehler. `WORKFLOW_AND_HANDOFF.md` hat den Prüfer während
dieses Umbaus **zweimal** in die Irre geführt: die „~2 hours", aus denen eine
Laufzeitvorgabe wurde, und die 4'288 Kostenstellen-Zeilen, aus denen „der
wirkungsvollste Punkt im ganzen Projekt" wurde. Beide waren zum Zeitpunkt der
Notiz richtig und später falsch — ohne dass das Dokument es sagte.

### Beim Auftraggeber

| Punkt | Blockiert |
|---|---|
| SMTP-Freigabe, dann ein echter Versand über das Firmen-Relais | Mailversand im Betrieb |
| Google Places aufschalten, Kreditkarte, ein Live-Abruf | **Produktivsperre Modus B** (`03 B4`) |
| Privates Gmail-Konto für Firmendaten zulässig? | Betrieb Modus B |
| Merge `umbau/webapp` → `main` | Produktivbetrieb |
| Batch 5 | offen seit April |

Modus A ist ohne Vorbehalt einsatzbereit.
