# Konzept: Modul zur Datenbereinigung

## 1. Zielsetzung

Das Ziel dieses neuen Moduls ist die qualitative Verfeinerung der durch den Apify Actor angereicherten Daten.  
Nach der ersten Optimierungsphase (`optimierte_daten.csv`) kommt es vor, dass für eine einzelne **KundenNr** mehrere potenzielle Treffer existieren.  
Diese Mehrfachtreffer können sowohl korrekte Varianten (z. B. mehrere Filialen) als auch unplausible Ergebnisse (z. B. thematisch ähnliche, aber falsche Geschäfte) enthalten.

Dieses Modul implementiert eine **nachgelagerte Bereinigungslogik**, die für jede KundenNr den plausibelsten Treffer auswählt und diesen von den weniger relevanten Duplikaten trennt.  
Das Hauptziel ist, die finale Ergebnisliste auf genau **einen, bestmöglichen Eintrag pro Kunde** zu reduzieren und dabei sicherzustellen, dass **kein Kunde aus der finalen Liste verloren geht.**

---

## 2. Entwicklungsplan in zwei Phasen

Die Entwicklung erfolgt in zwei getrennten Phasen, um eine isolierte Implementierung und gründliche Tests der komplexen Filterlogik zu ermöglichen.

---

### **Phase 1: Manuelles Bereinigungs-Tool (Getrennter Workflow)**

In dieser Phase wird die Bereinigung als separate, vom Benutzer manuell ausgelöste Funktion entwickelt.

#### **Neues Modul (`data_cleaner.py`)**

- Eine neue, eigenständige Komponente wird erstellt, die die gesamte Bereinigungslogik kapselt.  
- Die Kernfunktion nimmt den Pfad zu einer `optimierte_daten.csv`-Datei entgegen.  
- Sie implementiert ein **Scoring-Modell**, um für Gruppen von Mehrfachtreffern den besten Eintrag zu identifizieren.  
- Als Ergebnis werden zwei neue CSV-Dateien erzeugt:  
  - `bereinigte_daten.csv`  
  - `aussortierte_ergebnisse.csv`

#### **Anpassung der Benutzeroberfläche (`ui_manager.py`)**

- Die GUI wird um einen zweiten Button erweitert, z. B. mit der Beschriftung **„Optimierte Datei bereinigen“**.  
- Dieser Button öffnet einen Dateidialog, in dem der Benutzer die zu bereinigende `optimierte_daten.csv`-Datei auswählen kann.

#### **Integration in die Hauptanwendung (`main.py`)**

- Die `MainApplication`-Klasse wird um eine neue Methode erweitert, die den Bereinigungsworkflow steuert.  
- Der Prozess wird in einem separaten Thread ausgeführt, um die UI reaktionsfähig zu halten.

---

### **Phase 2: Automatisierte Integration (Zukünftiger Schritt)**

Nach erfolgreichem Test von Phase 1 wird der Prozess nahtlos in den bestehenden Workflow integriert.

- **UI-Anpassung:** Der separate „Bereinigen“-Button wird entfernt.  
- **Automatisierter Dialog:**  
  Am Ende des Anreicherungsprozesses (nach dem Schreiben der `optimierte_daten.csv`) wird dem Benutzer ein Dialogfenster angezeigt mit der Frage:  
  _„Möchten Sie die Ergebnisse jetzt bereinigen?“_ (Ja/Nein).  
- **Automatisierter Aufruf:**  
  Bei Auswahl von „Ja“ wird der Bereinigungsprozess aus Phase 1 automatisch gestartet, ohne dass der Benutzer die Datei erneut auswählen muss.

---

## 3. Kernlogik: Das Scoring-Modell

Um den „besten“ Treffer aus einer Gruppe von Duplikaten objektiv zu bestimmen, wird ein **gewichtetes Punktesystem** implementiert.  
Jedes Ergebnis erhält einen Gesamt-Score, der sich aus zwei Kriterien zusammensetzt.

---

### **Kriterium A: Titel-Ähnlichkeit (max. 100 Punkte)**

- Dieses Kriterium bewertet die textuelle Ähnlichkeit zwischen dem Unternehmensnamen im ursprünglichen `SearchString` und dem von Google gelieferten `title`.  
- **Berechnung:**
  Mittels einer etablierten Methode zur String-Ähnlichkeitsmessung (z. B. _Levenshtein-Distanz* via `thefuzz`-Bibliothek) wird ein Score zwischen 0 (keine Ähnlichkeit) und 100 (identisch) ermittelt.
- **Zweck:**
  Diese Methode ist tolerant gegenüber leichten Namensabweichungen (z. B. „Müller AG“ vs. „Müller & Söhne“), bewertet aber thematisch falsche Treffer (z. B. „Spar“ vs. „Coop“) mit einem niedrigen Score.

---

### **Kriterium B: Strassen-Übereinstimmung (Bonus: 50 Punkte)**

- Dieses Kriterium dient als starker **„Tie-Breaker“**, wenn mehrere Ergebnisse eine ähnlich hohe Titel-Ähnlichkeit aufweisen.
- **Bedingung:**
  Die Prüfung wird nur durchgeführt, wenn im *SearchString_ eine Strassenangabe vorhanden ist.
- **Berechnung:**
  Wenn die von Google gelieferte *street_ im _SearchString_ enthalten ist, werden **50 Bonuspunkte** zum Gesamt-Score addiert.

---

## 4. Der Auswahlprozess

Für jede **KundenNr** mit mehr als einem Ergebnis wird folgender Prozess durchlaufen:

1. **Score-Berechnung:**
   Für jede Ergebniszeile wird der Gesamt-Score (Titel-Score + Strassen-Bonus-Score) berechnet.
2. **Ranking:**
   Die Ergebnisse werden absteigend nach ihrem Gesamt-Score sortiert.
3. **Auswahl:**
   - Die Zeile mit dem höchsten Gesamt-Score wird als „bester Treffer“ identifiziert.
   - Dieser „beste Treffer“ wird in die finale `bereinigte_daten.csv`-Datei geschrieben.
   - Alle anderen Ergebnisse für diese KundenNr werden in die `aussortierte_ergebnisse.csv` verschoben.
