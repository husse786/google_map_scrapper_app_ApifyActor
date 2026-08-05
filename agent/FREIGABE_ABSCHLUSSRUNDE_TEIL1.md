# FREIGABE — Abschlussrunde, Teil 1

Geprüft am 04.08.2026.

**Ergebnis: freigegeben. Weiter mit Teil 2a, dann Teil 2.**

---

## 1. Nachgerechnet

| Prüfung | Ergebnis |
|---|---|
| Drei vollständige Läufe | 3 × **362 grün** + 1 übersprungen |
| Teil 2 unberührt | bestätigt — keine der sieben Dateien im Diff |
| Die vier Arten selbst durchgespielt | bestätigt |

Seine Überlappungsanalyse stimmt genau:

```
'Denner, Hauptstrasse 5, 5620 Bremgarten'   Kostenstelle: False   vollständig
'Denner Bremgarten'                          Kostenstelle: True    falsches Etikett
'Denner, 5620 Bremgarten'                    Kostenstelle: False   nur die neue sieht sie
'Denner, , 5620 Bremgarten'                  Kostenstelle: True    falsches Etikett
```

---

## 2. Der Befund ist schärfer als mein Plan ihn beschrieb

Ich hatte die Rückentwicklung als „diese Zeilen gehen ungewarnt durch"
beschrieben. Tatsächlich waren drei der vier Arten schon gemeldet — nur unter
dem **falschen Namen**. Bei `Denner Bremgarten` gibt es kein Strassenfeld, in
dem eine Kostenstelle stehen könnte.

Und die vierte, ausgerechnet die aus meinem Beispiel, fiel durch jede Prüfung:
Im Strassenfeld steht `5620 Bremgarten` — eine Buchstabenfolge, also schweigt
die Kostenstellenprüfung.

Beides zeigt sich erst beim Messen. Die richtige Reaktion auf einen Plan ist,
seine Annahmen zu prüfen, nicht sie umzusetzen.

---

## 3. Bestätigt

| Punkt | Urteil |
|---|---|
| Zerlegung wörtlich von der Referenz übernommen | **bestätigt.** Genau dafür stand `data_preprocessor.py` noch da |
| Warnung statt Blockade, nur Modus A | bestätigt |
| Mutationsprüfung an den neuen Tests | bestätigt |
| Läufe nach einer Änderung mitten im Ablauf verworfen und neu gefahren | **bestätigt.** Stale Läufe zu melden wäre bequemer gewesen |
| Sechs Läufe statt fünf | bestätigt |
| Die drei Punkte gemeldet statt behoben | **bestätigt** — alle drei lagen ausserhalb des Umfangs. Entscheidung folgt unten |

---

## 4. Entscheidung zu den drei Meldungen

Alle drei werden behoben, als **Teil 2a** vor den Löschungen.

**Die Doppelmeldung wird aufgelöst.** Sein Zögern galt den Phase-4-Tests, die
die Zeilenzahlen festhalten. Aber genau diese Tests hielten eine falsche Aussage
fest: „Kostenstelle im Strassenfeld" bei einer Zeile ohne Strassenfeld. Der
Massstab dieses Projekts ist, dass die Anwendung nichts behauptet, was nicht
stimmt — das gilt auch für einen Prüfbericht.

**«1 Zeilen» wird berichtigt.** Seine Entscheidung, nicht neuen falschen Text zu
schreiben, war richtig. Die vorübergehende Ungleichheit war der Preis dafür und
verschwindet jetzt.

**Das README bekommt die Prüfmaske.** Das ist mein Versäumnis: Ich habe bei der
Abnahme von Phase 5 auf Tkinter-Reste geprüft und bei Phase 8 nicht gefragt, ob
das README die neue Seite überhaupt kennt. Ein Handbuch, das den Schritt nicht
nennt, in dem der Nutzer 840 Entscheidungen trifft, ist unvollständig.

`ABSCHLUSSRUNDE.md` ist entsprechend ergänzt.

---

## 5. Danach

Teil 2 löscht sechs Dateien, `data_preprocessor.py` eingeschlossen — seine
Prüfung ist jetzt nachgebaut und durch eigene Tests abgesichert.
`data_consolidator.py` ebenfalls: Der Auftraggeber hat geklärt, dass das
Aufteilen in Batches eine Umgehung der alten Anwendung war und künftig entfällt.

Damit ist der Umbau abgeschlossen.
