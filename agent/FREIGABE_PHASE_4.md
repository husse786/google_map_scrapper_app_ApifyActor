# FREIGABE — Phase 4

Geprüft am 03.08.2026.

**Ergebnis: freigegeben. Phase 5 kann starten.**

Die wichtigste Leistung dieser Phase ist nicht der Code, sondern dass sie eine
meiner zentralen Vorgaben widerlegt hat, statt sie zu bestätigen.

---

## 1. Nachgerechnet

| Prüfung | Ergebnis |
|---|---|
| Drei vollständige Testläufe | 3 × 155 grün + 1 übersprungen |
| Kategorieerkennung gegen echte Firmennamen | **kein Fehlalarm** |

Geprüft wurden unter anderem `Bar Rouge`, `Cafe Federal`, `Hotel Bellevue
Palace`, `Restaurant Krone`, `Coop Pronto`, `Volg Dorfladen` — keiner löst aus.
`Bar`, `Boucherie`, `Restaurant`, `Boulangerie Patisserie` lösen aus. Die Regel
greift nur, wenn der Titel **ausschliesslich** aus Kategoriewörtern besteht.
Richtig konservativ.

Einzige Untererkennung: `Bar Tabak Kiosk` löst nicht aus, weil `Tabak` fehlt.
Untererkennung ist die sichere Richtung. Kein Handlungsbedarf.

Die Messungen selbst konnte ich nicht nachstellen — sie brauchen die realen
Dateien und einen Apify-Zugang. Sie sind schlüssig dokumentiert und intern
widerspruchsfrei.

---

## 2. Entscheidungen des Prüfers

### E1 — Fehlende Pflichtspalte blockiert · **übernommen**

Sein Vorschlag ist richtig. `03_ENTSCHEIDUNGEN.md` D sagte, alle drei Prüfungen
warnen und keine blockiert. Für die Pflichtspalten war das falsch: Ohne
`SearchString`, `PLZ` oder `KundenNr` kann der Lauf nicht arbeiten. Eine
wegklickbare Warnung führt nur in einen Abbruch nach dem Start.

`03 D` ist geändert. Die anderen beiden Prüfungen bleiben Warnungen.

### E2 — Kategoriewörter · **freigegeben**

77 Einträge, mehrsprachig. Vom Prüfer gegen echte Firmennamen getestet, keine
Fehlalarme. Die Liste ist ab jetzt festgeschrieben; Änderungen nur über einen
Korrekturplan — dieselbe Regel wie für `GENERIC_FIRST_WORDS`.

---

## 3. Meine Vorgabe war falsch

`03_ENTSCHEIDUNGEN.md` D nannte die Kostenstellen-Prüfung „den wirkungsvollsten
Punkt im ganzen Projekt", gestützt auf 4'288 von 5'188 Prüfzeilen.

Gemessen: **14 und 11 betroffene Zeilen**, davon je eine als „keine
Strassentreffer". Neun der vierzehn landeten trotzdem sauber in ①.

Die 4'288 waren nicht erfunden — sie stammen aus den V1-Batches. Zwei Dinge
haben sich seither geändert: der ERP-Export ist besser geworden (3.9% → 1.6%),
und die bestehende Vorverarbeitung entfernt vom Rest nochmals zwei Drittel.

Ich habe eine Zahl aus einem alten Betriebsprotokoll als heutige Lage behandelt
und darauf ein Arbeitspaket als wichtigsten Hebel des Projekts aufgebaut. Der
Entwickler hat das gemessen statt geglaubt. Das ist der richtige Umgang mit
einer Vorgabe.

Der Nebenbefund passt dazu: `KST` kommt in 18'000 realen Zeilen **zweimal** vor.
Was tatsächlich auslöst, ist die zweite Hälfte der Regel — Strassenfelder aus
reinen Ziffern. Die Prüfung bleibt trotzdem: Sie kostet nichts und schadet nicht.

---

## 4. Konsequenz 1 — die Prüfmaske wird gebaut

Nach der Validierung bleiben **713 und 840 Prüffälle**, also 28% und 33% aller
Kunden. Über fünf Batches sind das mehrere tausend Fälle.

Die Zusammensetzung entscheidet die Frage:

| Anteil | Ursache | wegvalidierbar? |
|---|---|---|
| 58–64% | andere Strasse | nein |
| 19–22% | gleiche Strasse, andere Hausnummer | nein |

Das ist die Grenze des Abgleichs, kein Eingabefehler, und vor dem Lauf nicht
erkennbar. Es gibt nichts, was diese Menge kleiner macht.

Mehrere tausend Fälle in Excel durchzugehen ist keine Arbeitsweise, die man
einem Kollegen zumutet. **Phase 8 ist aufgenommen**, mit sechs
Abnahmekriterien. `03 E` ist entsprechend geändert.

Die Datengrundlage steht seit Phase 2 vollständig in der Tabelle `kandidat` —
mit `score`, `entscheid` und `grund` je Kandidat. Diese Entscheidung von damals
zahlt sich jetzt aus: Phase 8 ist Oberfläche, keine Migration.

---

## 5. Konsequenz 2 — Apify ist fünfmal langsamer als im Protokoll

Der Kaltstart ist widerlegt: Der erste von zehn Aufrufen war mit 63.6 s der
schnellste, Median 79.5 s, keiner über 180 s. Damit ist die Fristerhöhung aus
Phase 3 bestätigt und die Kaltstart-Hypothese vom Tisch.

Es bleibt eine grössere Frage: Das Betriebsprotokoll nennt rund 17 Sekunden je
Aufruf, gemessen werden rund 80 — bei gleicher Konfiguration und denselben
Kundenzeilen. Hochgerechnet **12 Stunden statt zwei** für einen Batch.

**Das ist kein Code-Problem und keine Aufgabe für den Entwickler.** Seine
Vermutung — die Speichergrenze des Apify-Kontos trägt sechs gleichzeitige Läufe
nicht — ist plausibel und nur in der Apify-Konsole prüfbar.

**Aufgabe für den Auftraggeber:** In der Apify-Konsole nachsehen, ob
gleichzeitige Läufe wegen der Speichergrenze in eine Warteschlange geraten, und
was der Kontoplan an Arbeitsspeicher zulässt.

Was daran hängt:

- **Der Prototyp nennt „Rund 2 Stunden".** Diese Zahl ist bis zur Klärung nicht
  belegt. Phase 5 zeigt keine Gesamtdauer an, sondern nur den Fortschritt und
  eine Restzeit aus den bereits verarbeiteten Kunden — die stimmt in jedem Fall.
- **Mail und Statusseite werden zentral statt Beiwerk.** Bei zwölf Stunden ist
  „Fenster schliessen, wir schicken eine Mail" kein Komfort, sondern der
  einzige gangbare Ablauf.
- **Betrieb auf dem eigenen PC wird zum Nachtlauf.** Der Rechner muss über Nacht
  laufen. Das verschiebt das Gewicht Richtung Server, ohne dass es ein Blocker
  wird.

---

## 6. Änderungen an den Vorgaben

| Datei | Änderung |
|---|---|
| `03_ENTSCHEIDUNGEN.md` D | Pflichtspalte blockiert; Kostenstellen-Einschätzung durch Messung ersetzt; Kategorieliste freigegeben |
| `03_ENTSCHEIDUNGEN.md` E | Prüfmaske von „wird nicht gebaut" zu Phase 8 |
| `01_PHASENPLAN.md` | Phase 8 mit Umfang und sechs Abnahmekriterien |

---

Phase 5 startet nach dem aktualisierten `01_PHASENPLAN.md`.
Die Anzeige der Gesamtdauer entfällt, solange die Laufzeitfrage offen ist.
