# Kundendaten anreichern

Diese Anwendung nimmt eine Liste von ERP-Kunden, sucht jeden davon auf Google
Maps und gibt drei Dateien zurück:

| Datei | Inhalt |
|---|---|
| `fertig_fuer_erp.csv` | eindeutig zugeordnet, kann direkt importiert werden |
| `zur_pruefung.csv` | unklar — ein Mensch entscheidet. Der Grund steht in jeder Zeile |
| `nicht_moeglich.csv` | nichts gefunden. Adresse im ERP prüfen, dann neu versuchen |

Bedient wird sie im Browser. Wer sie benutzt, installiert nichts — er öffnet
einen Link.

**Jede Zeile jeder Ausgabedatei trägt einen Score und einen deutschen
Klartextgrund.** Niemand muss raten, warum ein Kunde dort gelandet ist, wo er
gelandet ist. Und jeder Kunde aus der Eingabe steht in genau einer der drei
Dateien — nie in zweien, nie in keiner.

---

## Für den täglichen Gebrauch

### Anwendung starten

Im Terminal, im Projektordner:

```bash
source venv/bin/activate
python webapp.py
```

Dann im Browser `http://localhost:8000` öffnen. Beenden mit `Strg+C`.

Damit auch andere im Firmennetz zugreifen können:

```bash
python webapp.py --offen
```

Die Adresse lautet dann `http://<name-dieses-rechners>:8000`. Dieser Rechner
muss laufen, solange jemand die Anwendung benutzt.

### Der Ablauf, fünf Seiten

1. **Art wählen** — zwei Möglichkeiten:
   * **Erstanreicherung**: Nur Name und Adresse sind bekannt. Jeder Kunde wird
     auf Google Maps gesucht. Spalten: `SearchString;PLZ;Stadt;KundenNr`
   * **Auffrischen**: Die Google-ID steht schon im ERP. Die Daten werden direkt
     über die ID geholt. Spalten: `placeId;lat;lng;KundenNr` — `lat` und `lng`
     sind freiwillig und dienen nur der Prüfung, ob der Betrieb noch am selben
     Ort steht.
2. **Datei hochladen** — die Anwendung prüft sie sofort und sagt, was auffällt:
   fehlende Spalten, unvollständige Suchbegriffe, Zeilen ohne Strassennamen,
   Namen, die nur eine Branche sind. Fehlt eine Pflichtspalte, geht es nicht
   weiter. Alle anderen Hinweise
   sind nur Hinweise; Sie entscheiden, ob Sie trotzdem starten. Hier können Sie
   auch eine Mailadresse hinterlegen.
3. **Lauf** — Fortschritt, geschätzte Restzeit, Abbruch-Knopf. Das Fenster darf
   geschlossen werden, der Lauf geht weiter.
4. **Ergebnis** — die drei Dateien zum Herunterladen. Gibt es Fälle zur Prüfung,
   steht hier der Knopf *Fälle prüfen*.
5. **Prüfung** — die Fälle, bei denen der Abgleich nicht entscheiden konnte,
   entscheiden Sie hier im Browser statt in Excel. Links steht, was im ERP
   steht; rechts, was Google gefunden hat — jeder Treffer mit seinem Wert und
   dem Grund. Ein Klick wählt einen Treffer, oder Sie wählen *Keiner passt*.
   Mit der Tastatur geht es schneller: `1` bis `9` wählt einen Treffer, `0`
   steht für *Keiner passt*, und der nächste Fall steht sofort da. Jeder
   entschiedene Fall wandert augenblicklich in *Fertig fürs ERP* — Sie
   importieren am Ende eine Datei statt zwei. Aufhören und später weitermachen
   ist jederzeit möglich; der Stand bleibt.

### Wenn etwas dazwischenkommt

* **Fenster geschlossen?** Der Lauf läuft weiter. Seite wieder öffnen, der
  Stand ist da.
* **Rechner neu gestartet, Strom weg, Programm beendet?** Beim nächsten Start
  bietet die Startseite an, den Lauf fortzusetzen. Es wird kein Kunde doppelt
  gesucht und keiner ausgelassen.
* **Lauf abgebrochen?** Die bis dahin verarbeiteten Kunden sind gespeichert.
  Ausgabedateien gibt es keine — ein halber Lauf ist kein Ergebnis.
* **Mail hinterlegt?** Sie kommt in allen drei Fällen: fertig, abgebrochen,
  gestoppt. Der Betreff nennt den Dateinamen und das Ergebnis.

### Die CSV-Datei

Semikolon als Trennzeichen, erste Zeile die Spaltennamen. In Excel:
*Speichern unter → CSV UTF-8 (durch Trennzeichen getrennt)*.

Höchstens 10'000 Zeilen pro Datei. Grössere Dateien bitte aufteilen.

Die Kundennummer wird nie zur Suche verwendet. Sie wird unverändert
mitgeführt, damit die Ergebnisse beim Import wieder zugeordnet werden können.

---

## Einrichtung auf einem neuen Rechner

Einmalig, etwa zwanzig Minuten. Die Befehle werden im Terminal eingegeben
(macOS: *Terminal*, Windows: *Eingabeaufforderung*), jeweils mit Enter
bestätigt.

### 1. Python installieren

Nötig ist **Python 3.11 oder neuer**. Prüfen:

```bash
python3 --version
```

Kommt eine Fehlermeldung oder eine kleinere Zahl als 3.11, Python von
[python.org](https://www.python.org/downloads/) herunterladen und installieren.

### 2. Projekt holen

```bash
git clone https://github.com/husse786/google_map_scrapper_app_ApifyActor.git
cd google_map_scrapper_app_ApifyActor
```

### 3. Virtuelle Umgebung anlegen

Das ist ein eigener Ordner für die benötigten Zusatzprogramme, damit sie sich
nicht mit anderen Projekten in die Quere kommen.

```bash
python3 -m venv venv
source venv/bin/activate
```

Unter Windows lautet die zweite Zeile `venv\Scripts\activate`.

Vor der Eingabezeile steht danach `(venv)`. Das muss bei jedem neuen
Terminalfenster erneut gemacht werden.

### 4. Zusatzprogramme installieren

```bash
pip install -r requirements.txt
```

### 5. Zugangsdaten eintragen

Zuerst die Vorlage kopieren:

```bash
cp config.template.py config.py
```

Dann eine Datei namens `.env` im Projektordner anlegen, mit diesem Inhalt:

```
APIFY_API_TOKEN=hier_den_token_einsetzen
ACTOR_ID=hier_die_actor_id_einsetzen
```

Beides steht im Apify-Konto. **Diese Datei gehört niemandem sonst** — sie ist
von der Versionsverwaltung ausgenommen und darf nicht weitergegeben werden.

Freiwillig, je nach Bedarf:

```
GOOGLE_API_KEY=schluessel_fuer_das_auffrischen
SMTP_SERVER=mail.firma.ch
SMTP_ABSENDER=anreicherung@firma.ch
SMTP_PORT=25
SMTP_BENUTZER=
SMTP_PASSWORT=
```

* **`GOOGLE_API_KEY`** braucht nur, wer die Art *Auffrischen* benutzt.
* **SMTP** braucht nur, wer eine Mail bekommen will. Fehlt es, läuft alles
  normal weiter; ins Protokoll wird geschrieben, was verschickt worden wäre.

### 6. Ausprobieren, ohne etwas zu verbrauchen

Die Anwendung kann mit vorbereiteten Antworten laufen. Dabei wird nichts bei
Apify abgefragt und nichts abgerechnet:

```bash
python webapp.py --antworten agent/testdaten/fixture_optimierte_daten.csv
```

Für den echten Betrieb:

```bash
python webapp.py --quelle echt
```

### 7. Wenn andere im Firmennetz zugreifen sollen

`python webapp.py --offen` starten. Damit das funktioniert, muss Port 8000
eingehend freigegeben sein. Das braucht Administratorrechte auf diesem Rechner;
falls sie fehlen, genügt eine kurze Anfrage an die ICT.

Den Rechnernamen statt der IP-Adresse verwenden — sonst bricht der Link nach
jedem Neustart.

---

## Wenn etwas nicht klappt

| Meldung oder Beobachtung | Was zu tun ist |
|---|---|
| «Das monatliche Guthaben bei Apify ist aufgebraucht» | Guthaben aufstocken oder bis zum nächsten Abrechnungsmonat warten. Der Lauf lässt sich danach fortsetzen, die verarbeiteten Kunden bleiben. |
| «Der Apify-Token wird nicht akzeptiert» | Eintrag `APIFY_API_TOKEN` in `.env` prüfen, notfalls im Apify-Konto einen neuen erzeugen. |
| «Apify ist nicht erreichbar» | Internetverbindung prüfen, dann fortsetzen. Ein kurzer Aussetzer stoppt den Lauf nicht; erst zehn Fehlschläge hintereinander tun es. |
| «In der Datei fehlt die Spalte …» | Die erste Zeile der CSV muss die Spaltennamen enthalten, getrennt mit Semikolon. |
| «Es liegt noch ein unerledigter Auftrag vor» | Es läuft immer nur ein Auftrag. Den offenen fortsetzen oder abbrechen. |
| Die Seite lässt sich nicht öffnen | Läuft `python webapp.py` noch? Im Terminal nachsehen. |
| Etwas anderes | `logs/webapp.log` und `logs/bereinigung.log` enthalten die technischen Einzelheiten. |

---

## Für die Wartung

### Kommandozeile

Dieselbe Fachlogik ohne Browser — für Wartung, Fehlersuche und lange Läufe:

```bash
python cli.py pruefen Daten/DEINEDATEI.csv           # nur prüfen
python cli.py lauf Daten/DEINEDATEI.csv --quelle echt
python cli.py lauf Daten/DEINEDATEI.csv --modus B --quelle echt
python cli.py fortsetzen Daten/DEINEDATEI.csv --quelle echt
python cli.py bereinigen Daten/ANGEREICHERT.csv      # nur den Cleaner
```

`Strg+C` bricht ab, ohne die verarbeiteten Kunden zu verlieren.

### Tests

```bash
python -m pytest
```

Ein Test dauert drei Minuten und ist deshalb übersprungen. Ihn mitlaufen
lassen:

```bash
LANGSAME_TESTS=1 python -m pytest
```

### Aufbau

```
webapp.py             Weboberfläche (FastAPI, Jinja2, HTMX)
cli.py                Kommandozeile
upload_pruefung.py    Prüft die Eingabedatei, bevor der Lauf startet
worker.py             Der Lauf im Hintergrund: starten, abbrechen, fortsetzen
pipeline.py           Ein Lauf: Eingabe → Datenquelle → Datenbank → drei Dateien
data_cleaner.py       Das Scoring: welcher Treffer ist der richtige (Modus A)
modus_b.py            Auffrischen über die Google-ID: Prüfung statt Scoring
place_provider.py     Candidate und die Schnittstelle zu den Datenquellen
apify_provider.py     Datenquelle Apify — kennt als einziges Modul deren Felder
google_provider.py    Datenquelle Google Place Details (Modus B)
fake_provider.py      Datenquelle mit festen Antworten, für Tests ohne Kosten
db.py                 SQLite: Jobs, Kunden, Kandidaten
mail.py               Benachrichtigung am Ende eines Laufs
config.py             Zugangsdaten (nicht in der Versionsverwaltung)
```

Wo welche Daten liegen:

```
laufdaten/uploads/        hochgeladene Dateien und ihre Ergebnisordner
laufdaten/laeufe.sqlite   alle Läufe, Kunden und Kandidaten
logs/                     Protokolle
```

Beides ist von der Versionsverwaltung ausgenommen: dort stehen echte
Kundendaten.

### Wie entschieden wird

Die Fachlogik, die Schwellenwerte und ihre Begründungen stehen in `agent/`:

* `02_DATENVERTRAG.md` — Spalten, Zustände, Datenbankschema
* `03_ENTSCHEIDUNGEN.md` — feste Werte: Schwellen, Timeouts, Grenzen
* `agent/findings/` — was in jeder Ausbaustufe gemessen und gefunden wurde

Diese Dateien sind verbindlich. Wer eine Schwelle ändern will, ändert sie
zuerst dort.
