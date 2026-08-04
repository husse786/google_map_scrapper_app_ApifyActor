# Findings — Phase 5, Version 1.0

Datum: 04.08.2026
Bearbeitete Phase: 5 — Weboberfläche
Status: fertig

Testlauf: `python -m pytest` → **191 grün, 1 übersprungen**, fünfmal
hintereinander (13.42 / 14.64 / 13.69 / 13.80 / 13.74 s). Aufteilung:
8 + 40 + 49 + 20 + 40 aus den Phasen 1 bis 4, **35 neu**.

Zusätzlich von Hand im Browser durchgespielt, mit Bildschirmfotos belegt:
Seitenablauf, Tastaturfokus, Abbruch, Serverstopp mitten im Lauf und
Wiederaufnahme per Klick.

---

## 1. Abnahmekriterien

| # | Kriterium | Status | Beleg |
|---|---|---|---|
| 1 | Vollständiger Durchlauf mit `FakeProvider` ohne Terminal, nur im Browser | grün | `test_vollstaendiger_durchlauf_ohne_terminal` geht den ganzen Weg über HTTP. Von Hand nachgespielt: Art wählen → Datei → Lauf → Ergebnis mit 6 / 3 / 1 Kunden, entsprechend der Fixture. |
| 2 | Fortschrittsanzeige aktualisiert sich ohne Neuladen | grün | `test_stand_ist_ein_ausschnitt_keine_ganze_seite` (der Ausschnitt trägt `hx-trigger="every 5s"` und ist kein ganzes Dokument), `test_fortschritt_waechst_waehrend_des_laufs` (die Zahl steigt und sinkt nie), `test_stand_schickt_am_ende_zur_ergebnisseite`. |
| 3 | Browserfenster schliessen und wieder öffnen: Lauf läuft weiter, Stand stimmt | grün | `test_fenster_schliessen_und_wieder_oeffnen` — zwei getrennte Sitzungen, der Lauf überlebt die erste. `test_startseite_fuehrt_zum_laufenden_auftrag`. |
| 4 | Alle drei Dateien laden korrekt herunter, Semikolon, `utf-8-sig` | grün | `test_dateien_laden_mit_semikolon_und_bom` je Datei: Antwort beginnt mit dem BOM, Kopfzeile mit Semikolon, kein Komma. `test_umlaute_kommen_unbeschaedigt_an`. |
| 5 | Keine englische Zeichenkette in der Oberfläche, kein Stacktrace sichtbar | grün | `test_keine_englischen_woerter_in_der_oberflaeche` über acht Seiten inklusive Fehlerseiten, dazu `test_unbekannte_seiten_zeigen_keinen_stacktrace`, `test_kaputte_datei_wird_verstaendlich_gemeldet`. Ein echter Fund dazu in Abschnitt 5. |
| 6 | Bedienbar mit Tastatur, Fokus sichtbar | grün mit Einschränkung | `test_fokus_ist_sichtbar`, `test_jede_handlung_ist_ein_knopf_oder_ein_verweis` (kein `onclick`), `test_jede_seite_hat_genau_eine_haupthandlung`. Im Browser bestätigt: Tabulator setzt einen deutlich sichtbaren Rahmen. Einschränkung zur Auslösung per Tastatur in Abschnitt 5. |
| 7 | Server in unter 10 Sekunden beendbar, Auftrag danach `LAEUFT`, Fortsetzung wird angeboten | grün | `test_server_beendet_sich_unter_zehn_sekunden` startet einen echten uvicorn in einem Unterprozess. Von Hand gemessen: **0.26 s**, Auftrag stand danach auf `LAEUFT` bei 6 von 10 Kunden, die Startseite bot ihn an, ein Klick beendete ihn sauber bei 10 von 10 (Abschnitt 6.2). |

---

## 2. Geänderte und neue Dateien

| Datei | neu / geändert | Was |
|---|---|---|
| `webapp.py` | neu | FastAPI-Anwendung, vier Seiten plus Fehlerseite, Download der drei Dateien, Statusausschnitt für HTMX, Start über `python webapp.py`. |
| `templates/` | neu | Sieben Jinja2-Vorlagen: Grundgerüst, Art wählen, Datei, Lauf, Statusausschnitt, Ergebnis, Fehler. |
| `static/stil.css` | neu | 181 Zeilen, ohne Framework. Der Prototyp ist für CSS nicht verbindlich. |
| `static/htmx.min.js` | neu | HTMX 2.0.4, mitgeliefert statt von einem fremden Server geladen — die Anwendung läuft im Firmennetz und soll ohne Internet funktionieren. |
| `upload_pruefung.py` | geändert | Eine fehlende Pflichtspalte weist die Datei jetzt ab, statt nur zu warnen (`03_ENTSCHEIDUNGEN.md` D, Entscheid E1 der Freigabe zu Phase 4). Kopfkommentar an die widerlegte Annahme angepasst. |
| `worker.py` | geändert | `starten()` nimmt die bereits bekannte Kundenzahl entgegen, damit die Statusseite nicht kurz „0 von 0" zeigt. |
| `db.py` | geändert | `ergebnis_zaehlen()` und `zuletzt_verarbeitet()` für die Statusanzeige. |
| `test_phase4_abnahme.py` | geändert | Zwei Tests auf den neuen Entscheid E1 nachgezogen. |
| `test_phase5_abnahme.py` | neu | 35 Tests. |
| `README.md` | geändert | Abschnitt „Bedienung im Browser"; zwei überholte Stellen berichtigt. |
| `requirements.txt` | geändert | `fastapi`, `uvicorn`, `jinja2`, `python-multipart`, `httpx`. |
| `.gitignore` | geändert | `laufdaten/` — dort liegen hochgeladene Kundendateien und die Datenbank. |

Nicht angefasst: `data_cleaner.py`, `pipeline.py`, die Provider, `cli.py`.

---

## 3. Getroffene Annahmen

| Situation | Entscheidung | Warum |
|---|---|---|
| Wo liegen hochgeladene Dateien? | `laufdaten/uploads/<dateiname>`, Ergebnisse daneben in `<dateiname>_ergebnis/`. | Genau der Vorschlag aus den Findings zu Phase 3. Die Wiederaufnahme findet die Datei über `job.dateiname`, ohne dass das Schema eine Spalte für den Pfad braucht. **Nebenwirkung:** zwei Läufe derselben Datei überschreiben einander. Bei einem Nutzer und einem Auftrag ist das kein Problem. |
| Prototyp nennt „Rund 2 Stunden für 2'500 Kunden" | Entfernt, ersatzlos. Die Kacheln nennen keine Dauer mehr. | Die Zahl ist seit Phase 4 nicht belegt (17 s je Aufruf im Protokoll gegen 80 s gemessen). Eine falsche Zusage ist schlimmer als keine. |
| Prototyp nennt „Wir schicken eine Mail, sobald er fertig ist" | Ersetzt durch „Öffnen Sie die Seite später wieder, um den Stand zu sehen." | Mailversand ist Phase 7. Eine Mail zu versprechen, die nicht kommt, wäre die schlechteste Variante. |
| Restzeit | Aus dem laufenden Lauf gerechnet: verstrichene Zeit geteilt durch erledigte Kunden, mal die offenen. Erst ab drei Kunden, davor „lässt sich noch nicht abschätzen". | So verlangt. Diese Schätzung stimmt immer, weil sie nur misst, was dieser Lauf auf diesem Rechner braucht — unabhängig davon, wie die Apify-Frage ausgeht. |
| Modus B (Auffrischen) | Kachel sichtbar, aber gesperrt, mit dem Hinweis „Noch nicht verfügbar". Der Aufruf `/datei?modus=B` führt auf eine Fehlerseite in Klartext. | Der Prototyp ist für Ablauf und Reihenfolge verbindlich; die Kachel gehört dazu. Gebaut wird Modus B in Phase 6 — hier steht keine Zeile Vorbau. |
| Ergebnisseite nach einem Abbruch | Zeigt „Abgebrochen" und **keine** Download-Verweise. | Ein abgebrochener Lauf hat kein vollständiges Ergebnis. Dateien anzubieten, in denen die noch nicht verarbeiteten Kunden fehlen, würde die Invariante aus §2 unsichtbar verletzen. |
| Serverstopp | Der Prozess beendet sich hart (`os._exit`), nachdem uvicorn den Stopp eingeleitet hat. Der laufende Auftrag bleibt bewusst auf `LAEUFT`. | Sonst wartet Python auf abgebrochene Abfragen — bis zu 175 Sekunden (Befund aus Phase 3). Der Auftrag ist nach jedem Kunden gespeichert; genau dafür wurde die Wiederaufnahme gebaut. Der harte Stopp gilt nur im Serverbetrieb, nicht im Test (`zustand['harter_stopp']`). |
| HTMX | Als Datei mitgeliefert statt von einem fremden Server geladen. | Die Anwendung läuft auf einem PC im Firmennetz. Eine Oberfläche, die ohne Internet nicht funktioniert, wäre in Stufe 1 des Betriebs (`UMBAUPLAN_WEBAPP.md` §10) unbrauchbar. |
| Datei-Auswahlfeld | Das native Feld liegt unsichtbar hinter einer eigenen Beschriftung, dazu sechs Zeilen JavaScript für den gewählten Dateinamen. | Begründung in Abschnitt 5 — es ist der einzige Weg, das englische „Choose File" loszuwerden. |
| Wer den Lauf abbricht, sieht die Ergebnisseite | Weiterleitung auf `/ergebnis/<nr>` mit der Erklärung, was gespeichert ist. | Sonst bliebe der Nutzer auf einer Statusseite stehen, die sich nicht mehr bewegt. |

---

## 4. Abweichungen von den Vorgaben

| Vorgabe | Abweichung | Warum unvermeidbar |
|---|---|---|
| Prototyp: „Rund 2 Stunden für 2'500 Kunden" und „Rund 10 Minuten" auf den Auswahlkacheln | Beide Zeitangaben entfernt | Ausdrückliche Anweisung des Auftraggebers und Konsequenz aus der Freigabe zu Phase 4: keine Gesamtdauer, solange die Laufzeitfrage offen ist. |
| Prototyp: „Wir schicken eine Mail, sobald er fertig ist oder etwas schiefgeht" | Ersetzt | Mailversand ist Phase 7. |
| Prototyp: „Zum Ergebnis springen (Demo)" | Entfällt | War eine Schaltfläche der Vorführung, keine Funktion. |
| Prototyp: Ergebnisseite nennt „2'513 Kunden in 1 Stunde 54 Minuten" | Übernommen, aber gemessen statt vorhergesagt | Das ist die tatsächlich verstrichene Zeit eines fertigen Laufs, keine Prognose. Sie bleibt. |

Sonst folgt die Oberfläche dem Prototyp in Ablauf, Reihenfolge und Wortlaut.
CSS ist eigen, wie erlaubt.

---

## 5. Was gefunden wurde

| Fund | Auswirkung | eingegriffen? |
|---|---|---|
| **Das native Datei-Feld beschriftet sich selbst — auf Englisch.** Im Browser stand „Choose File" und „No file chosen" auf der Upload-Seite. Diese Texte kommen vom Browser, nicht aus dem HTML, und richten sich nach dessen Spracheinstellung. Auf einem englisch eingestellten Browser wäre Kriterium 5 verletzt gewesen, ohne dass es im Quelltext zu sehen ist. | Aufgefallen erst beim Ansehen im echten Browser — kein Test hätte das gefunden, weil der Text nicht im HTML steht. | ja: das Feld liegt unsichtbar hinter einer eigenen Beschriftung, bleibt aber dasselbe Bedienelement (Tastaturzugang und Fokusrahmen bleiben) |
| **Auslösen per Tastatur liess sich nicht abschliessend prüfen.** Der Fokus wandert korrekt und ist deutlich sichtbar (Bildschirmfoto), das fokussierte Element ist ein echtes `<button type="submit">` in einem Formular. Eingabe- und Leertaste haben die Kachel in meiner Browsersteuerung trotzdem nicht ausgelöst. | Vermutlich eine Grenze der Fernsteuerung — synthetische Tastenereignisse lösen nicht immer die Standardaktion aus. Ein echter Browser mit echter Tastatur verhält sich anders. **Belegt ist:** ausschliesslich native Bedienelemente, kein `onclick`, sichtbarer Fokus. **Nicht belegt ist:** das tatsächliche Auslösen per Taste. | nein — ich melde es lieber, als es als geprüft auszugeben. Bitte einmal von Hand nachtasten |
| Der Prototyp verspricht eine Mail | Siehe Abschnitt 4. Bei einer Laufzeit von möglicherweise zwölf Stunden (Phase 4) ist das kein Komfort, sondern der wichtigste Teil des Ablaufs. Phase 7 sollte entsprechend gewichtet werden. | nein — gemeldet |
| Die Statusseite zeigte kurz „0 von 0 Kunden" | Der Auftrag entsteht, bevor der Lauf die Datei gelesen hat. Die Kundenzahl ist zu diesem Zeitpunkt aber schon bekannt — aus der Prüfung beim Hochladen. | ja, sie wird durchgereicht |
| `apify_wrapper.py` stand noch in der Modulübersicht des README | Die Datei ist seit Phase 2 gelöscht. | ja, Eintrag entfernt |
| `pkill -f` trifft die eigene Shell | Beim Aufräumen der Testserver hat sich mein eigenes Kommando abgeschossen, weil das Suchmuster in seiner eigenen Befehlszeile steht. Keine Auswirkung auf das Produkt, nur auf meine Messungen. | — |

---

## 6. Messwerte

### 6.1 Der Weg durch die Oberfläche

Von Hand im Browser, mit der Fixture als Datenquelle:

| Schritt | Beobachtung |
|---|---|
| Startseite | „Was haben Sie zu den Kunden?", zwei Kacheln, die zweite gesperrt mit Hinweis |
| Tabulatortaste | Fokusrahmen deutlich sichtbar auf der ersten Kachel |
| Datei hochladen | 10 Kunden erkannt, Hinweis zur Kostenstelle mit Beispielzeile |
| Lauf | „Läuft", Fortschrittsbalken, drei Zähler, „Die verbleibende Zeit lässt sich noch nicht abschätzen." |
| Ergebnis | „Fertig", 10 Kunden, drei Kacheln mit 6 / 3 / 1 und je einem Download |

Die Verteilung 6 / 3 / 1 entspricht Zeichen für Zeichen dem, was Phase 1 aus
derselben Fixture erzeugt hat.

### 6.2 Serverstopp mitten im Lauf

Echter uvicorn, echter Lauf mit künstlich langsamer Datenquelle, Stopp per
Strg+C-Signal:

| Messung | Wert |
|---|---|
| Zeit vom Signal bis der Prozess weg ist | **0.26 s** (Grenze: 10 s) |
| Rückgabewert | 0 |
| Status in der Datenbank danach | `LAEUFT`, 6 von 10 Kunden |
| Startseite nach dem Neustart | „Ein Auftrag ist noch offen … 6 von 10 Kunden sind bereits verarbeitet" |
| Nach einem Klick auf „Auftrag fortsetzen" | `FERTIG`, 10 von 10, zehn verschiedene Kundennummern, drei Dateien geschrieben |

Ohne den harten Stopp hätte das Beenden bis zu 175 Sekunden gedauert — der
Befund aus Phase 3, hier eingelöst.

### 6.3 Umfang

| | |
|---|---|
| `webapp.py` | 520 Zeilen |
| Vorlagen | 7 Dateien, 303 Zeilen |
| CSS | 181 Zeilen |
| Fremdcode | HTMX 2.0.4, 51 KB, mitgeliefert |
| Tests | 35 neu, davon einer mit echtem uvicorn im Unterprozess |

---

## 7. Für die nächste Phase

- **Phase 7 wird wichtiger, als der Plan sie gewichtet.** Wenn ein Lauf zwölf
  Stunden dauert (offene Frage aus Phase 4), ist die Mail nicht Komfort,
  sondern der einzige gangbare Ablauf. Die Statusseite sagt heute „Öffnen Sie
  die Seite später wieder" — das trägt für zwei Stunden, nicht für zwölf.
- **Für Phase 6 (Modus B):** Die gesperrte Kachel und der Zweig
  `/datei?modus=B` sind die einzigen Stellen, die anzufassen sind. Der
  restliche Ablauf — Prüfung, Start, Status, Ergebnis — ist vom Modus
  unabhängig, weil er nur mit `Worker` und der Datenbank spricht.
- **Für Phase 8 (Prüfmaske):** Die Ergebnisseite ist der natürliche Einstieg.
  Die Daten liegen vollständig in `kandidat`, und `Datenbank.kandidaten_lesen()`
  gibt sie mit `score`, `entscheid` und `grund` heraus.
- **Offen und bewusst nicht gebaut:** kein Aufräumen alter Läufe. `laufdaten/`
  wächst mit jedem Upload. Bei einem Nutzer und wenigen Läufen im Monat ist das
  auf Jahre unkritisch; eine Aufräumfunktion gehört in die Härtung.
- **Bitte einmal von Hand nachtasten:** ob sich die Kacheln und Knöpfe wirklich
  mit der Eingabetaste auslösen lassen (Abschnitt 5). Alles andere an Kriterium
  6 ist belegt.

---

## 8. Zeit

| Arbeitspaket | grober Aufwand |
|---|---|
| Freigabe, geänderte Vorgaben und Prototyp einlesen | 0.5 h |
| Entscheid E1 aus Phase 4 nachziehen (Pflichtspalte blockiert) | 0.25 h |
| Vorlagen und CSS | 1.5 h |
| `webapp.py` | 2.0 h |
| Sauberes Beenden, Wiederaufnahme über die Oberfläche | 0.75 h |
| Tests (35 neu) | 2.0 h |
| Durchgang im echten Browser, Bildschirmfotos, Messungen | 1.0 h |
| Findings | 0.75 h |
| **gesamt** | **≈ 8.75 h** |

Der teuerste Fehler wäre gewesen, den Durchgang im echten Browser wegzulassen.
Das englische „Choose File" steht in keinem Quelltext und hätte kein Test
gefunden — es wäre erst dem Sachbearbeiter aufgefallen.
