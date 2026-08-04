# Findings — Phase 7, Version 1.0

Datum: 04.08.2026
Bearbeitete Phase: 7 — Mail und Härtung
Status: fertig

Testlauf: `python -m pytest` → **277 grün, 1 übersprungen**, fünfmal
hintereinander (14.37 / 14.59 / 14.65 / 14.58 / 14.46 s). Aufteilung:
8 + 40 + 52 + 20 + 40 + 36 + 47 aus den Phasen 1 bis 6, **35 neu**.

Der Mailversand wurde zusätzlich gegen einen echten SMTP-Server geprüft, nicht
nur gegen einen Ersatz (Abschnitt 6.1).

---

## 1. Abnahmekriterien

| # | Kriterium | Status | Beleg |
|---|---|---|---|
| 1 | Mail wird in allen drei Fällen versendet, Betreff nennt Dateiname und Ergebnis | grün | `test_mail_bei_fertig`, `test_mail_bei_abgebrochen`, `test_mail_bei_fehler` — je ein vollständiger Lauf über den `Worker`. Der Betreff lautet «Kundendaten anreichern: InputData.csv - fertig» und entsprechend «- abgebrochen» und «- gestoppt» (`test_betreff_nennt_dateiname_und_ergebnis`). Echter Versand in Abschnitt 6.1. |
| 2 | Ohne SMTP-Konfiguration läuft der Job normal durch | grün | `test_ohne_smtp_laeuft_der_job_normal_durch`: der Lauf endet `FERTIG`, alle drei Dateien liegen da, und ins Protokoll wird geschrieben, was verschickt worden wäre. `test_ohne_adresse_wird_nichts_versendet`, `test_unerreichbarer_server_wirft_nichts`. |
| 3 | Erschöpftes Kontingent führt zu `FEHLER` mit deutscher Erklärung, nicht zu einem Absturz | grün | `test_erschoepftes_kontingent_stoppt_den_lauf` prüft Zustand und Text; `test_erschoepftes_kontingent_ist_kein_absturz` prüft, dass beim Aufrufer keine Ausnahme ankommt; `test_erschoepftes_kontingent_schreibt_keine_halben_dateien`; `test_verarbeitete_kunden_bleiben_nach_dem_stopp` zeigt, dass der Lauf danach zu Ende geführt werden kann. |
| 4 | README beschreibt Einrichtung so, dass jemand ohne Vorkenntnisse dem Ablauf folgen kann | grün | Vollständig neu geschrieben, sieben nummerierte Schritte von «Python installieren» bis «Ausprobieren, ohne etwas zu verbrauchen». `test_readme_erklaert_die_einrichtung` und drei weitere Tests halten fest, dass die Anleitung zur Anwendung passt, die es gibt. |

---

## 2. Geänderte und neue Dateien

| Datei | neu / geändert | Was |
|---|---|---|
| `mail.py` | neu | Betreff, Text und Versand. Fehlt etwas — Adresse, SMTP-Angaben, Server —, wird protokolliert und `False` zurückgegeben. Diese Datei wirft nichts. |
| `place_provider.py` | geändert | `QuelleNichtVerfuegbar` mit `meldung` (deutsch, für den Nutzer) und `endgueltig` (Weitermachen sinnlos, ja oder nein). |
| `apify_provider.py` | geändert | Sechs Fehlerarten von Apify mit einer Handlungsanweisung je Art, dazu die Erkennung am Text, falls Apify keinen Typ mitschickt. Netzfehler gelten als vorübergehend. |
| `pipeline.py` | geändert | Endgültige Fehler beenden den Lauf mit `FEHLER` und der Meldung des Providers — kein Stacktrace. Vorübergehende werden gezählt: zehn hintereinander beenden ihn ebenfalls. |
| `worker.py` | geändert | Nach jedem Lauf wird Bescheid gegeben, bei `FERTIG`, `ABGEBROCHEN` und `FEHLER`. |
| `webapp.py` | geändert | Adressfeld beim Start, Hinweis auf der Laufseite, Erklärung des Fehlers auf der Ergebnisseite. |
| `templates/datei.html`, `templates/lauf.html`, `static/stil.css` | geändert | Das Adressfeld und die beiden Texte dazu. |
| `config.template.py` | geändert | Sechs SMTP-Einträge, alle freiwillig. |
| `README.md` | **neu geschrieben** | 272 Zeilen: täglicher Gebrauch, Einrichtung in sieben Schritten, eine Tabelle «Wenn etwas nicht klappt», Wartung. |
| `test_phase7_abnahme.py` | neu | 35 Tests. |

---

## 3. Getroffene Annahmen

| Situation | Entscheidung | Warum |
|---|---|---|
| Woher kommt die Adresse? | Ein freiwilliges Feld auf der Datei-Seite, direkt über «Lauf starten». Sie wird im Job gespeichert (`job.email`, §5). | Dort steht der Nutzer ohnehin, und dort entscheidet er, ob er wartet oder nicht. Freiwillig, weil ein kurzer Lauf keine Mail braucht. |
| Was, wenn der Mailserver nicht antwortet? | Protokollieren, sonst nichts. | Ein fertiger Lauf darf nicht nachträglich zu einem Fehler werden, weil der Mailserver hustet. Die Dateien liegen bereit, der Stand steht in der Oberfläche. |
| Welche Apify-Fehler beenden den Lauf? | Kontingent erschöpft, Ausgabenlimit erreicht, Token ungültig oder fehlend, fehlende Rechte, Actor nicht gefunden. | Bei diesen fünf bringt der 500. Versuch dasselbe wie der erste. Weiterlaufen würde 2'500 Kunden in ③ schreiben — ein Lauf, der wie ein Ergebnis aussieht und keines ist. |
| Und «Netz weg»? | Gilt als vorübergehend. Der Lauf verträgt neun Fehlschläge hintereinander; beim zehnten gibt er auf, mit derselben Erklärung. | Ein Aussetzer von zwei Sekunden darf einen Lauf über Stunden nicht töten. Fällt die Verbindung wirklich aus, ist nach zehn Kunden Schluss statt nach 2'500. Die Zahl ist gegriffen — sie soll gross genug für einen Schluckauf und klein genug sein, dass kaum Kunden falsch in ③ landen. |
| Was steht im Betreff? | «Kundendaten anreichern: <Dateiname> - <fertig/abgebrochen/gestoppt>», mit schlichtem Bindestrich. | Ein Gedankenstrich zwingt jedes Mailprogramm zur Umkodierung; im Postfach steht dann `=?utf-8?b?4oCU?=` mitten im Betreff. Beim echten Versand gesehen (Abschnitt 6.1). |
| `FEHLER` heisst in der Oberfläche jetzt «Gestoppt» | Umbenannt. | «Abgebrochen» stand schon für den Abbruch durch den Nutzer. Zwei verschiedene Dinge brauchen zwei Wörter, sonst sucht der Sachbearbeiter den Knopf, den er nie gedrückt hat. |
| Die Erklärung des Fehlers | Steht auf der Ergebnisseite, nicht nur im Protokoll. | Sie ist für den Nutzer geschrieben und enthält die Handlungsanweisung. Im Log nützt sie ihm nichts. |
| Mail bei einem Lauf ohne Adresse | Keine, nur eine Zeile im Protokoll. | Kein Grund, den Betrieb mit einer Fehlermeldung zu behelligen. |

---

## 4. Abweichungen von den Vorgaben

Keine. Der Umfang der Phase — Mail bei den drei Zuständen, Adresse je Job,
SMTP aus der Konfiguration, Fehlertexte für die drei häufigen Fälle, README —
ist vollständig umgesetzt.

---

## 5. Was gefunden wurde

| Fund | Auswirkung | eingegriffen? |
|---|---|---|
| **Ein Kontingentfehler war bisher nicht von «nichts gefunden» zu unterscheiden.** `ApifyProvider` gab bei jedem Fehler eine leere Liste zurück. Bei erschöpftem Guthaben hätte ein Lauf über 2'500 Kunden alle in ③ geschrieben, den Zustand `FERTIG` gemeldet und drei Dateien hingelegt — eine davon mit 2'500 Kunden «nichts gefunden». | Das ist die schlimmste Sorte Fehler: er sieht aus wie ein Ergebnis. Seit Phase 2 als offener Punkt gemeldet, jetzt behoben. | ja |
| **Der Gedankenstrich im Betreff wird umkodiert.** Beim Versand gegen einen echten SMTP-Server stand im Betreff `=?utf-8?b?4oCU?=` statt eines Strichs. | Aufgefallen nur, weil die Nachricht wirklich durch `smtplib` ging — der Ersatzserver im Test hätte das Objekt weitergereicht, ohne es zu kodieren. Dieselbe Lehre wie beim englischen «Choose File» in Phase 5. | ja, schlichter Bindestrich |
| **«Abgebrochen» stand für zwei verschiedene Dinge.** Der Nutzerabbruch und der technische Stopp trugen dieselbe Überschrift. | Wer eine Mail mit «abgebrochen» bekommt, sucht nach dem Kollegen, der auf den Knopf gedrückt hat. | ja, `FEHLER` heisst jetzt «Gestoppt» |
| Das README beschrieb eine Anwendung, die es nicht mehr gibt | «Desktop-Anwendung mit grafischer Benutzeroberfläche», «Thread-Pool (4 Worker)», `main.py`, `_eindeutig.csv` — Stand vor Phase 1. Vier Phasen lang mitgeschleppt und nur an den Rändern geflickt. | ja, neu geschrieben. Vier Tests halten fest, dass keine der alten Bezeichnungen zurückkommt |
| `logger_config.py` hat weiterhin keinen Aufrufer | Seit Phase 2 gemeldet. Die Datei konfiguriert einen Logger, den niemand benutzt; `cli.py` und `webapp.py` richten ihr Protokoll selbst ein. | nein — Löschen ist keine Härtung, sondern Aufräumen, und das gehört in eine eigene Runde |
| `csv_processor.py`, `csv_postprocessor.py`, `clean_input_data.py`, `data_cleaner.py.bak` sind ohne Aufrufer | Seit Phase 1 und 2 gemeldet, unverändert. Zusammen rund 400 Zeilen toter Code. Der Umbauplan §2 will `csv_processor` und `csv_postprocessor` behalten. | nein — gemeldet, siehe Abschnitt 7 |

---

## 6. Messwerte

### 6.1 Echter Mailversand

Gegen einen tatsächlich sprechenden SMTP-Server auf `127.0.0.1`, nicht gegen
einen Ersatz im Testrahmen. Was beim Server ankam:

```
Subject: Kundendaten anreichern: InputData_Prod.csv - fertig
From: anreicherung@example.ch
To: sachbearbeiter@example.ch
Content-Type: text/plain; charset="utf-8"

Der Lauf zur Datei «InputData_Prod.csv» ist fertig.

2'513 Kunden verarbeitet.

Die drei Dateien liegen bereit:
  Fertig fuers ERP: fertig_fuer_erp.csv
  Zur Pruefung: zur_pruefung.csv
  Nicht moeglich: nicht_moeglich.csv

Ordner: /pfad

Zum Herunterladen die Anwendung im Browser öffnen.
```

Umlaute, Guillemets und die Schweizer Tausendertrennung kommen unbeschädigt an.
Beim ersten Versuch stand im Betreff `=?utf-8?b?4oCU?=` — siehe Abschnitt 5.

### 6.2 Verhalten bei erschöpftem Kontingent

Zwanzig Kunden, ab dem vierten meldet Apify das Guthaben als aufgebraucht:

| Messung | Wert |
|---|---|
| Zustand des Jobs | `FEHLER` |
| Meldung in der Datenbank | «Das monatliche Guthaben bei Apify ist aufgebraucht. Der Lauf wurde gestoppt, damit keine halben Ergebnisse entstehen. Bitte das Guthaben aufstocken …» |
| Ausnahme beim Aufrufer | keine |
| Geschriebene Ausgabedateien | keine |
| Verarbeitete Kunden in der Datenbank | 3, erhalten |
| Nach dem Fortsetzen | `FERTIG`, 20 von 20, jeder Kunde in genau einer Datei |
| Mail | Betreff «… - gestoppt», Text enthält die Handlungsanweisung |

### 6.3 Verhalten bei unterbrochener Verbindung

| Fall | Ergebnis |
|---|---|
| Jeder zweite Aufruf scheitert (20 Kunden) | `FERTIG`, alle 20 Kunden verteilt — ein Schluckauf stoppt nichts |
| Jeder Aufruf scheitert (40 Kunden) | `FEHLER` nach höchstens 12 Aufrufen statt nach 40, Meldung «Apify ist nicht erreichbar … Bitte die Verbindung prüfen und den Lauf danach fortsetzen» |

### 6.4 Die sechs Fehlertexte

Jeder Text enthält das Wort «Bitte» und sagt, was zu tun ist —
`test_jeder_endgueltige_fehler_hat_eine_handlungsanweisung` prüft das für alle
sechs Arten. Kein Text enthält ein ß, ein englisches Wort oder eine
Fehlernummer.

| Fall | Was der Nutzer liest, verkürzt |
|---|---|
| Monatsguthaben aufgebraucht | Guthaben aufstocken oder warten, dann fortsetzen |
| Ausgabenlimit erreicht | Limit im Apify-Konto anheben, dann fortsetzen |
| Token ungültig | Eintrag `APIFY_API_TOKEN` in `.env` prüfen, notfalls neu erzeugen |
| Kein Token hinterlegt | Eintrag `APIFY_API_TOKEN` in `.env` prüfen |
| Rechte fehlen | Prüfen, ob der Token zum richtigen Konto gehört |
| Actor nicht gefunden | Eintrag `ACTOR_ID` in `.env` prüfen |
| Netz weg | Verbindung prüfen, danach fortsetzen — verarbeitete Kunden bleiben |

---

## 7. Für die nächste Phase

- **Phase 8 ist die letzte.** Danach ist der Rückweg von Datei ② geschlossen
  und der Sachbearbeiter hat einen ERP-Import statt zwei.
- **Für Phase 8 bereits vorhanden:** `Datenbank.kandidaten_lesen()` gibt jeden
  Kandidaten mit `score`, `entscheid` und `grund` heraus; `kunde.place_id`,
  `lat` und `lng` sind im Modus B gefüllt. Die Maske ist Oberfläche auf
  vorhandenen Daten, wie im Phasenplan vorgesehen.
- **Toter Code, der eine eigene Runde verdient:** `logger_config.py`,
  `clean_input_data.py`, `data_cleaner.py.bak` haben keinen Aufrufer mehr;
  `csv_processor.py` und `csv_postprocessor.py` ebenfalls nicht, sollen laut
  Umbauplan §2 aber bleiben. Zusammen rund 400 Zeilen. Ich habe nichts davon
  angefasst — Löschen im Rahmen einer Mail-Phase wäre der falsche Zeitpunkt.
  **Vorschlag:** eine kurze Aufräumrunde nach Phase 8, mit einer Entscheidung
  je Datei.
- **Der Mailversand ist ungetestet gegen einen echten Firmen-Mailserver.**
  Geprüft ist der Weg durch `smtplib` gegen einen lokalen Server, inklusive
  `STARTTLS`-Aufruf und Anmeldung. Was ein Relais mit Authentifizierung und
  Zertifikatsprüfung daraus macht, zeigt erst der erste echte Versand. Das ist
  dieselbe Art Lücke wie bei Google in Phase 6 — nur kleiner, weil SMTP
  weniger Überraschungen kennt als eine fremde API.
- **Noch offen und ausserhalb der Entwicklung:** die SMTP-Freigabe durch die
  ICT (`UMBAUPLAN_WEBAPP.md` §8). Bis dahin läuft die Anwendung ohne Mail
  vollständig — sie protokolliert nur, was sie verschickt hätte.

---

## 8. Zeit

| Arbeitspaket | grober Aufwand |
|---|---|
| Freigabe und Phase-7-Umfang einlesen | 0.25 h |
| `mail.py` mit Betreff, Text und Versand | 1.0 h |
| Fehlerarten klassifizieren, endgültig gegen vorübergehend | 1.25 h |
| Adressfeld in der Oberfläche, Fehlererklärung auf der Ergebnisseite | 0.75 h |
| README neu geschrieben | 1.25 h |
| Tests (35 neu) | 1.5 h |
| Echter SMTP-Versand und Messungen | 0.5 h |
| Findings | 0.75 h |
| **gesamt** | **≈ 7.25 h** |

Der Mailversand selbst war eine Stunde. Die Zeit ging in die Frage, wann ein
Lauf weiterlaufen darf und wann nicht — und die hat einen Fehler aufgedeckt,
der seit Phase 2 im Code stand: ein erschöpftes Kontingent hätte 2'500 Kunden
in Datei ③ geschrieben und das Ergebnis «fertig» genannt.
