# FREIGABE — Phase 8, Version 1.1

Geprüft am 04.08.2026.

**Ergebnis: freigegeben. Alle acht Phasen sind abgeschlossen.**

---

## 1. Nachgerechnet

| Prüfung | Ergebnis |
|---|---|
| Fünf vollständige Läufe | 5 × **333 grün** + 1 übersprungen |
| Umfang | zwei Dateien, kein Verhalten geändert |
| Gegenprobe: alte Schreibweise eingesetzt | **zwei Tests fallen um** |

Der Wächter greift von beiden Seiten — wenn der Code vom Vertrag abweicht und
wenn ein Umlaut in einen geschriebenen Wert gerät.

**Vier Tests statt einem war die bessere Antwort.** Den Wächter an den Vertrag
zu hängen statt an eine im Testcode abgeschriebene Liste macht das Dokument zur
Quelle. Eine abgeschriebene Liste wäre beim nächsten neuen Wert vergessen worden.

---

## 2. Bestätigt

| Punkt | Urteil |
|---|---|
| Grundtexte behalten ihre Umlaute | **bestätigt.** `qualitaet` ist Schlüssel, `grund` ist Sprache |
| Kommentar begründet jetzt die Schreibweise statt die Werte | **bestätigt.** Die Werte stehen im Vertrag, dort gehören sie hin |
| `fortschritt()` nicht umgestellt | **bestätigt.** Eine Umstellung für einen Datenbestand, den es nicht gibt, wäre genau das, was `03 E` ausschliesst. Phase 8 war nie im Betrieb |

---

## 3. Der Umbau in acht Phasen

| Phase | Ergebnis | Runden |
|---|---|---|
| 1 | Kern repariert, von Tkinter gelöst | 1 |
| 2 | Provider-Schnittstelle, Datenmodell, `FakeProvider` | 1 |
| 3 | Worker, sechs parallel, Wiederaufnahme, Abbruch | 2 |
| 4 | Upload-Validierung und die Messung, die eine Vorgabe widerlegte | 1 |
| 5 | Weboberfläche, vier Seiten | 1 |
| 6 | Modus B über die gespeicherte placeId | 1 |
| 7 | Mail, und: eine ausgebliebene Antwort ist kein Ergebnis | 5 |
| 8 | Prüfmaske im Browser | 2 |

**333 Tests.** Die Anwendung ist im Browser bedienbar: Datei hochladen, vor dem
Start gewarnt werden, den Lauf verfolgen, ihn nach einem Neustart fortsetzen,
Prüffälle im Browser entscheiden, drei Dateien herunterladen, per Mail
benachrichtigt werden.

**Vier Fehler, die ohne diesen Umbau ins ERP gegangen wären:**

1. Der Strassenvergleich hielt `Dorfstrasse` und `Oberdorfstrasse` für dieselbe
   Strasse — vier falsche Adressen allein in batch_4, in keiner Statistik sichtbar.
2. Einzeltreffer gingen ungeprüft ins ERP.
3. Kunden standen gleichzeitig in zwei Ausgabedateien.
4. Ein erschöpftes Apify-Kontingent hätte 2'500 Kunden nach ③ geschrieben und
   den Lauf `FERTIG` genannt.

Der vierte war der schwerste und hat fünf Runden gebraucht, weil derselbe Satz
an fünf Stellen stand. Zwei dieser Runden gingen auf falsche Vorgaben des
Prüfers zurück.

---

## 4. Was noch aussteht

**Eine Abschlussrunde**, beschrieben in `ABSCHLUSSRUNDE.md`. Sie ist mehr als
Aufräumen: Beim Prüfen der toten Module ist eine **Rückentwicklung**
aufgefallen, die niemandem bisher aufgefallen war.

**Beim Auftraggeber:**

| Punkt | Blockiert |
|---|---|
| SMTP-Freigabe durch ICT, dann ein echter Versand über das Firmen-Relais | Mailversand im Betrieb |
| Google Places aufschalten, Kreditkarte, ein Live-Abruf | **Produktivsperre Modus B** (`03 B4`) |
| Zulässigkeit eines privaten Gmail-Kontos für Firmendaten | Betrieb Modus B |
| Batch 5 | offen seit April |

Keiner dieser Punkte blockiert den Bau. Alle blockieren den Produktivbetrieb
einzelner Teile.
