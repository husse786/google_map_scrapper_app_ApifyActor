# Anhang: Detaillierte Logik des Datenbereinigungs-Moduls (`data_cleaner.py`)

## 1. Grundprinzip

Das Ziel des `DataCleaner`-Moduls ist es, **alle plausiblen Treffer zu behalten** und nur **eindeutig falsche Ergebnisse auszusortieren**, um die Datenqualität zu maximieren. Das oberste Gebot ist, dass keine `KundenNr` aus der finalen Ergebnisliste verloren geht.

Die Logik wird nur auf `KundenNr` angewendet, die mehr als ein Ergebnis haben. Kunden mit nur einem Ergebnis werden ohne Prüfung als korrekt übernommen.

## 2. Das Scoring-Modell

Um die Plausibilität jedes Ergebnisses objektiv zu bewerten, wird ein gewichtetes Punktesystem verwendet. Jedes Ergebnis erhält einen **Gesamt-Score**.

### 2.1. Vorbereitung: Text-Normalisierung

Vor jedem Vergleich werden die relevanten Texte (`SearchString`, `title`, `street`) temporär "normalisiert" (Kleinbuchstaben, Ersetzung von Abkürzungen und Umlauten), um die Vergleichsqualität zu erhöhen. Die Originaldaten bleiben dabei unberührt.

### 2.2. Kriterium A: Gewichteter Titel-Score (max. 100 Punkte)

Der Titel-Score setzt sich aus zwei Teilen zusammen, um sowohl den Markennamen als auch den Gesamtkontext zu bewerten:

* **Kern-Namen-Score (70% Gewichtung):** Vergleicht nur das erste Wort des Such-Titels mit dem ersten Wort des Google-Titels. Dies priorisiert die Übereinstimmung der Marke (z.B. "Denner" vs. "Denner").
* **Gesamt-Titel-Score (30% Gewichtung):** Vergleicht den gesamten Titel aus dem `SearchString` mit dem gesamten Google-`title`, um zusätzliche Übereinstimmungen (z.B. "Supermarkt") zu belohnen.

### 2.3. Kriterium B: Strassen-Bonus (Bonus: 50 Punkte)

Dies ist ein starker Bonus, der als "Tie-Breaker" dient.

* Wenn der `SearchString` eine Strasse enthält und diese mit der `street`-Angabe des Google-Ergebnisses übereinstimmt, erhält das Ergebnis **+50 Bonuspunkte**.

## 3. Kernlogik: Die stufenweise Filterung

Der Algorithmus unterscheidet zwischen zwei Hauptszenarien:

### Szenario A: Der `SearchString` enthält KEINE Strassenangabe

* **Regel A.1 (Plausible Titel finden):** Für jedes Ergebnis wird der **Gesamt-Score** (hier nur der gewichtete Titel-Score) berechnet. Alle Ergebnisse, deren Score über einem definierten Schwellenwert liegt (aktuell **80**), gelten als "plausibel" und werden behalten.
* **Regel A.2 (Fallback):** Sollte kein einziges Ergebnis den Schwellenwert erreichen, werden alle ursprünglichen Ergebnisse für diesen Kunden behalten, um Datenverlust zu vermeiden.

### Szenario B: Der `SearchString` enthält EINE Strassenangabe

Hier hat die Adresse die höchste Priorität.

* **Regel B.1 (Filter 1: Strasse):** Das System behält zuerst **nur** die Ergebnisse, deren `street`-Wert eine hohe Ähnlichkeit mit der Angabe im `SearchString` aufweist.
* **Regel B.2 (Stopp-Bedingung):** Ist nach dem Strassen-Filter nur noch **ein** Ergebnis übrig, wird dieses akzeptiert.
* **Regel B.3 (Filter 2: Titel):** Sind mehrere Ergebnisse übrig, wird die Titel-Logik aus Szenario A angewendet, um die Liste weiter zu verfeinern.
* **Regel B.4 (Fallback):** Führt die Kombination aus Strassen- und Titel-Filter zu null Ergebnissen, werden alle Ergebnisse behalten, die zumindest den Strassen-Filter (Regel B.1) bestanden haben.
