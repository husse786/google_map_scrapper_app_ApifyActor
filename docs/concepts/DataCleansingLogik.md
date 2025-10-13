# Anhang: Detaillierte Logik des Datenbereinigungs-Moduls (`data_cleaner.py`)

## 1. Grundprinzip

Das Ziel des `DataCleaner`-Moduls ist es, für jede `KundenNr` die bestmöglichen Ergebnisse zu identifizieren und sie in drei Kategorien einzuteilen: eindeutig korrekte Treffer, unklare Fälle zur manuellen Prüfung und eindeutig falsche Treffer. Das oberste Gebot ist, dass keine `KundenNr` aus der finalen Ergebnisliste verloren geht.

Die Logik wird nur auf `KundenNr` angewendet, die mehr als ein Ergebnis haben. Kunden mit nur einem Ergebnis werden ohne Prüfung als **OK** eingestuft.

## 2. Kernlogik: Die stufenweise Filterung

Der Algorithmus unterscheidet strikt zwischen zwei Szenarien, die durch den Inhalt des `SearchString` bestimmt werden.

### Szenario A: Der `SearchString` enthält KEINE Strassenangabe

Wenn die Suche breit angelegt ist, wird eine mehrstufige Titel-Bewertung durchgeführt:

1. **Gewichtetes Scoring:** Für jedes Ergebnis wird ein **gewichteter Titel-Score** berechnet (70% Gewichtung auf den Markennamen, 30% auf den gesamten Titel).

2. **Fester Schwellenwert:** Es wird geprüft, ob Ergebnisse einen Score von **`>= 80`** erreichen.
    * **Wenn ja:** Alle Ergebnisse `>= 80` werden als **OK** eingestuft. Alle Ergebnisse `< 80` werden als **AUSSORTIERT** eingestuft.
    * **Wenn nein:** Der nächste Schritt wird ausgelöst.

3. **Dynamischer Schwellenwert (Sicherheitsnetz):** Wenn kein Ergebnis den festen Schwellenwert erreicht, wird der Punkteabstand (`DYNAMIC_THRESHOLD_GAP`) zwischen dem besten und dem zweitbesten Ergebnis geprüft.
    * **Wenn der Abstand groß ist (`>= 30`):** Der beste Treffer wird als "wahrscheinlicher Gewinner" mit der Qualität **OK** akzeptiert. Alle anderen werden als **AUSSORTIERT** eingestuft.
    * **Wenn der Abstand klein ist:** Die Situation ist unklar. Alle Ergebnisse dieser Gruppe werden als **ZUR_PRUEFUNG** markiert.

### Szenario B: Der `SearchString` enthält EINE Strassenangabe

Wenn die Suche spezifisch für einen Ort ist, hat die Adresse die höchste Priorität.

1. **Filter 1: Strasse hat Vorrang:** Das System filtert zuerst **strikt** nach der Strasse.
    * Ergebnisse, deren `street`-Wert eine hohe Ähnlichkeit mit der Angabe im `SearchString` aufweist, werden für den nächsten Schritt **behalten**.
    * Alle anderen Ergebnisse werden **sofort AUSSORTIERT**.

2. **Stopp-Bedingung & Fallbacks:**
    * **Wenn nach dem Strassen-Filter 0 Ergebnisse übrig sind:** Die Strassensuche war erfolglos. Alle ursprünglichen Ergebnisse dieser Gruppe werden als **ZUR_PRUEFUNG** markiert.
    * **Wenn nach dem Strassen-Filter 1 Ergebnis übrig ist:** Dies ist der eindeutige Gewinner und wird als **OK** eingestuft.

3. **Filter 2: Titel als "Tie-Breaker":**
    * Nur wenn **mehr als 1 Ergebnis** den Strassen-Filter bestanden hat, wird die **komplette Logik aus Szenario A** (inkl. gewichtetem Scoring und dynamischem Schwellenwert) auf diese reduzierte Auswahl angewendet, um die endgültige Entscheidung zu treffen.

## 3. Hilfswerkzeuge

* **Text-Normalisierung:** Vor jedem Vergleich werden alle relevanten Texte (`SearchString`, `title`, `street`) temporär "normalisiert" (Kleinbuchstaben, Ersetzung von Abkürzungen und Umlauten), um die Vergleichsqualität zu erhöhen. Die Originaldaten bleiben dabei unberührt.
* **Kein Strassen-Bonus:** In der finalen Implementierung wird **kein Strassen-Bonus** mehr verwendet. Stattdessen wird die Strasse als harter, priorisierter Filter in Szenario B eingesetzt, was wesentlich zuverlässiger ist.