# Dokumentation: Modul zur Datenbereinigung (`data_cleaner.py`)

## 1. Zielsetzung

Das Ziel dieses Moduls ist die  Verfeinerung der durch den Apify Actor angereicherten Daten. Nach der ersten Optimierungsphase (`..._optimierte_daten.csv`) kommt es vor, dass für eine einzelne `KundenNr` mehrere potenzielle Treffer existieren.

Dieses Modul implementiert eine nachgelagerte Bereinigungslogik, um diese Mehrfachtreffer zu analysieren und in drei finale Kategorien ("Körbe") aufzuteilen:

1. **`_eindeutig.csv`:** Enthält alle Ergebnisse, die der Algorithmus mit hoher Sicherheit als korrekt einstuft.
2. **`_zur_pruefung.csv`:** Enthält alle Ergebnisse, bei denen die Situation unklar, mehrdeutig oder unsicher ist. Diese Datei dient als "To-Do-Liste" für die manuelle Nachkontrolle.
3. **`_aussortiert.csv`:** Enthält alle Ergebnisse, die als eindeutig falsch oder irrelevant identifiziert wurden (z.B. ein "Coop"-Ergebnis bei einer "Spar"-Suche).

**Oberstes Gebot:** Kein Kunde geht verloren. Jede `KundenNr` wird am Ende mit mindestens einem Ergebnis in der `_eindeutig.csv`- oder der `_zur_pruefung.csv`-Datei vertreten sein.

Die Logik wird nur auf `KundenNr` angewendet, die mehr als ein Ergebnis haben. Kunden mit nur einem Ergebnis werden ohne Prüfung als **OK** eingestuft.

![Logik Diagram](../../diagrams/datacleansing_logik.svg)

## 2. Entwicklungsplan (Phasen)

Die Implementierung folgte einem zweistufigen Plan, um die Logik isoliert zu testen.

### Phase 1: Manuelles Bereinigungs-Tool (Aktueller Stand)

Die Bereinigung ist als separate, vom Benutzer manuell ausgelöste Funktion implementiert.

* **GUI:** Die Benutzeroberfläche (`ui_manager.py`) wurde um einen zweiten Button erweitert: **"2. Optimierte Datei bereinigen"**.
* **Workflow:** Ein Benutzer führt zuerst die Anreicherung (Button 1) aus. Danach kann er manuell die erstellte `..._optimierte_daten.csv`-Datei auswählen und mit Button 2 den Bereinigungsprozess starten.

### Phase 2: Automatisierte Integration (Zukünftiger Schritt)

Nach erfolgreichen Tests kann der Prozess nahtlos integriert werden.

* **Automatisierter Dialog:** Am Ende des Anreicherungsprozesses könnte ein Dialogfenster fragen: *"Möchten Sie die Ergebnisse jetzt bereinigen?"*
* **Automatisierter Aufruf:** Bei "Ja" wird der Bereinigungsprozess automatisch gestartet, ohne dass der Benutzer die Datei erneut auswählen muss.

## 3. Detaillierte Funktionslogik

Der Algorithmus ist ein mehrstufiger Filter- und Scoring-Prozess.

### 3.1. Der unsichtbare Helfer: Text-Normalisierung

Vor jedem Textvergleich werden die Daten temporär "normalisiert", um die Vergleichsqualität zu erhöhen. Die Originaldaten in der CSV-Datei werden dabei **niemals verändert**.

* Umwandlung in Kleinbuchstaben (z.B. "SPAR" → "spar").
* Ersetzung von Umlauten (z.B. "Müller" → "mueller").
* Ersetzung von Abkürzungen (z.B. "Hauptstr." → "hauptstrasse").
* Ersetzung von Bindestrichen durch Leerzeichen (z.B. "Denner-Satellit" → "denner satellit").

### 3.2. Die "Weiche": Szenario A vs. B

Der Algorithmus prüft den `SearchString`. Da dieser der Struktur `Titel, Strasse, PLZ/Ort` folgt, prüft der Code, ob der zweite Teil (die Strasse) Text enthält. Basierend darauf wird einer von zwei Logik-Pfaden gewählt.

### 3.3. Logik-Pfad A: Szenario A (Keine Strasse im `SearchString`)

*Dieser Fall tritt ein, wenn Sie z.B. "Denner, , 5620..." gesucht haben.*

1. **Gewichtetes Scoring:** Für jedes Ergebnis wird ein **gewichteter Titel-Score** berechnet:
    * **70% Gewichtung:** Ähnlichkeit des *ersten Wortes* (z.B. "Denner" vs "Denner").
    * **30% Gewichtung:** Ähnlichkeit des *gesamten Titels* (z.B. "Denner Satellit" vs "Denner Discount").
2. **Fester Schwellenwert:** Der Code prüft, ob es Treffer gibt, deren Score `>= 80` ist.
    * **Wenn ja:** Alle Treffer `>= 80` werden als `OK` in die `_eindeutig.csv` geschrieben (z.B. alle "Denner"-Varianten). Alle Treffer `< 80` werden in die `_aussortiert.csv` verschoben (z.B. "Coop" und "Migros" im "Spar"-Fall).
    * **Wenn nein:** Der nächste Schritt wird ausgelöst.
3. **Dynamischer Schwellenwert (Das Sicherheitsnetz):**
    * Dies wird **nur** aktiviert, wenn **kein einziges** Ergebnis den 80-Punkte-Schwellenwert erreicht.
    * Der Code prüft den Abstand (`DYNAMIC_THRESHOLD_GAP`) zwischen dem besten und dem zweitbesten Score.
    * **Wenn der Abstand groß ist (`>= 30`):** Der beste Treffer ist ein klarer, relativer Gewinner. Er geht in die `_eindeutig.csv` (Status `OK (Dynamisch)`). Der Rest geht in die `_aussortiert.csv`.
    * **Wenn der Abstand klein ist / Unentschieden:** Die Situation ist unklar. **Alle** Treffer in dieser Gruppe gehen in die `_zur_pruefung.csv`.

### 3.4. Logik-Pfad B: Szenario B (Strasse im `SearchString`)

*Dieser Fall tritt ein, wenn Sie z.B. "Kiosk Wilder Mann, Rheingasse 12, ..." gesucht haben.*

1. **Filter 1: Strasse hat Vorrang:** Der Algorithmus filtert die Gruppe **zuerst** strikt nach der Strasse.
    * Ergebnisse, deren `street`-Wert eine hohe Ähnlichkeit mit der Angabe im `SearchString` aufweist, werden **behalten**.
    * Alle anderen Ergebnisse werden **sofort AUSSORTIERT**.
2. **Stopp-Bedingung & Fallbacks:**
    * **Wenn 0 Treffer:** Die Strassensuche war erfolglos. Die gesamte ursprüngliche Gruppe wird als `ZUR_PRUEFUNG` markiert.
    * **Wenn 1 Treffer:** Dies ist der eindeutige Gewinner und wird als `OK` markiert.
3. **Filter 2: Titel als "Tie-Breaker":**
    * Nur wenn **mehr als 1 Ergebnis** den Strassen-Filter bestanden hat (z.B. "Hotel Krafft" und "Restaurant Krafft" an derselben "Rheingasse 12"), wird die **komplette Logik aus Szenario A** (inkl. Scoring und Schwellenwerten) auf diese reduzierte Auswahl angewendet, um die endgültige Entscheidung zu treffen.