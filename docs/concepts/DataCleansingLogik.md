# Datenbereinigungs-Logik

## Anhang: Detaillierte Logik des Datenbereinigungs-Moduls (`data_cleaner.py`)

### 1. Grundprinzip

Das Ziel des `DataCleaner`-Moduls ist nicht mehr, den *einen besten* Treffer zu finden, sondern **alle plausiblen Treffer zu behalten** und nur **eindeutig falsche Ergebnisse auszusortieren**. Das oberste Gebot ist, dass keine `KundenNr` aus der finalen Ergebnisliste verloren geht.

Die Logik wird nur auf `KundenNr` angewendet, die mehr als ein Ergebnis in der `optimierte_daten.csv` haben. Kunden mit nur einem Ergebnis werden ohne Prüfung als korrekt übernommen.

### 2. Vorbereitung: Text-Normalisierung

Bevor ein Vergleich stattfindet, werden alle relevanten Textfelder (`SearchString`, Google-`title`, Google-`street`) temporär "normalisiert", um die Vergleichsqualität zu erhöhen. Die Originaldaten bleiben unberührt. Die Normalisierung umfasst:

* Umwandlung in Kleinbuchstaben.
* Ersetzung gängiger Abkürzungen (z.B. `str.` → `strasse`).
* Auflösung von Umlauten (z.B. `ü` → `ue`).

### 3. Kernlogik: Die stufenweise Filterung

Der Algorithmus unterscheidet zwischen zwei Hauptszenarien, basierend auf dem Inhalt des `SearchString`.

#### Szenario A: Der `SearchString` enthält KEINE Strassenangabe

Wenn die Suche breit angelegt ist, ist der Titel das entscheidende Kriterium.

* **Regel A.1 (Plausible Titel finden):** Das System vergleicht den normalisierten Kern-Namen aus dem `SearchString` mit dem normalisierten `title` jedes Ergebnisses. Alle Ergebnisse, die eine hohe textuelle Ähnlichkeit aufweisen (basierend auf einem Schwellenwert, z.B. > 85%), werden als "plausibel" markiert und für die Endauswahl behalten.
* **Regel A.2 (Fallback bei null Treffern):** Sollte die Titel-Prüfung nach Regel A.1 kein einziges plausibles Ergebnis liefern, bricht der Filterprozess für diesen Kunden ab. Um Datenverlust zu vermeiden, werden **alle** ursprünglich von Google gelieferten Ergebnisse für diesen Kunden als korrekt gewertet.

#### Szenario B: Der `SearchString` enthält EINE Strassenangabe

Wenn die Suche spezifisch für einen Ort ist, hat die Adresse die höchste Priorität.

* **Regel B.1 (Filter 1: Strasse hat Vorrang):** Das System vergleicht die normalisierte `street` aus den Google-Ergebnissen mit der normalisierten Strassenangabe im `SearchString`. Es werden **nur** die Ergebnisse für die weitere Prüfung behalten, bei denen eine Übereinstimmung gefunden wird.
* **Regel B.2 (Stopp-Bedingung):** Ist nach dem Strassen-Filter nur noch **ein** Ergebnis übrig, wird dieses als korrekt akzeptiert und der Prozess für diesen Kunden ist beendet.
* **Regel B.3 (Filter 2: Titel als Tie-Breaker):** Sind nach dem Strassen-Filter **mehr als ein** Ergebnis übrig, wird als Nächstes ein Titel-Abgleich (wie in Regel A.1) durchgeführt, um die Liste weiter zu verfeinern. Alle Ergebnisse, die hier durchfallen, werden aussortiert.
* **Regel B.4 (Fallback bei null Treffern):** Wenn die Kombination aus Strassen- und Titel-Filter zu **null** Ergebnissen führt (z.B. weil der Titel im `SearchString` veraltet ist), wird der Titel-Filter ignoriert. Stattdessen werden **alle** Ergebnisse behalten, die zumindest die Strassen-Prüfung (Regel B.1) bestanden haben.
