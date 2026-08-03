# Findings — Phase 3, Version 1.0

Datum: 03.08.2026
Bearbeitete Phase: 3 — Worker
Status: fertig

Branch: `umbau/webapp`, enthält die Freigabe zu Phase 2 und den ergänzten
Phasenplan aus `main`.
Testlauf: `python -m pytest` → **114 grün, 1 übersprungen** (der
90-Sekunden-Lauf aus Phase 2). Aufteilung: 8 + 40 + 47 aus den Phasen 1 und 2,
20 neu.

---

## 1. Abnahmekriterien

| # | Kriterium | Status | Beleg |
|---|---|---|---|
| 1 | Prozess wird mitten im Lauf hart beendet, Neustart setzt fort, kein Kunde doppelt, keiner fehlt | grün | `test_harter_abbruch_und_wiederaufnahme`. Ein echter Unterprozess wird mit `os._exit(9)` getötet — kein `finally`, kein Aufräumen. Danach: alle 20 Kunden in genau einer Datei, 20 verschiedene Kundennummern in der Datenbank, und die Datenquelle wurde für die bereits erledigten Kunden **kein zweites Mal** gefragt. |
| 2 | Abbruch beendet den Lauf in unter 5 Sekunden, Status `ABGEBROCHEN` | grün | `test_abbruch_unter_fuenf_sekunden`. Gemessen bei 200 Kunden mit je 30 s Antwortzeit: **0.10 s** (Abschnitt 6.2). Über die Kommandozeile mit Strg+C: **0.07 s**. |
| 3 | Zweiter Start bei laufendem Job wird mit Hinweis abgewiesen | grün | `test_zweiter_start_wird_abgewiesen` und `test_zweiter_worker_wird_ebenfalls_abgewiesen`. Der Hinweis nennt Auftragsnummer, Dateiname und Stand und ist deutsch, ohne ß. |
| 4 | Fortschrittszahl entspricht während des Laufs jederzeit der Anzahl verarbeiteter Kunden | grün | `test_fortschritt_stimmt_jederzeit`. Während eines Laufs über 24 Kunden wird laufend die Zahl im Job gegen die Anzahl Zeilen in der Tabelle `kunde` gehalten. Der Zähler eilt nie voraus und hinkt nie mehr als einen Kunden hinterher. |
| 5 | Drei Dateien werden geschrieben, Invariante aus `02_DATENVERTRAG.md` §2 gilt | grün | `test_drei_dateien_und_invariante_nach_parallelem_lauf`. Zusätzlich zeichengleich mit dem Ergebnis aus Phase 1. |
| 6 | Sechs Worker laufen parallel, nachgewiesen gegen den `FakeProvider` | grün | `test_sechs_arbeiter_sind_rund_sechsmal_schneller`. Messung über 60 Kunden mit je 0.3 s: 18.32 s mit einem Arbeiter, 3.06 s mit sechs — **Faktor 5.99** (Abschnitt 6.1). Höchstens sechs Abfragen waren gleichzeitig unterwegs, nie sieben. |
| 7 | Abbruch und Wiederaufnahme funktionieren **mit** aktiver Parallelität, kein Kunde doppelt, keiner verloren | grün | Kriterium 1 läuft parametrisiert mit einem und mit sechs Arbeitern. `test_wiederaufnahme_liefert_dasselbe_wie_ein_lauf_am_stueck` vergleicht den unterbrochenen Lauf zeichenweise mit einem Lauf ohne Störung. |
| 8 | Der Timeout aus Phase 2 greift weiterhin je Aufruf, nicht je Lauf | grün | `test_timeout_gilt_je_aufruf_nicht_je_lauf`: zwölf hängende Kunden, sechs Arbeiter, 0.5 s Frist → alle zwölf landen in ③, jeder mit genau einem Aufruf. Gälte die Frist je Lauf, fehlten zehn davon. Der echte Wert 90 s ist unverändert und in Phase 2 gemessen. |

---

## 2. Geänderte und neue Dateien

| Datei | neu / geändert / entfernt | Was |
|---|---|---|
| `worker.py` | neu | Der Lauf im Hintergrund-Thread. Starten, abbrechen, warten, Fortschritt lesen, fortsetzen. Ein Job zur Zeit, geprüft im Prozess **und** gegen die Datenbank. |
| `pipeline.py` | geändert | Sechs Arbeiter statt sequentiell, Abbruch über ein `threading.Event`, `fortsetzen()` für abgestürzte Läufe. Die Ausgabe folgt weiterhin der Reihenfolge der Eingabedatei, nicht der Reihenfolge, in der die Arbeiter fertig werden. |
| `db.py` | geändert | WAL-Modus und Wartezeit, damit Worker-Thread und Statusanzeige gleichzeitig dürfen. `kunde_mit_kandidaten_schreiben()` schreibt beides in **einer** Transaktion. Neu: `offener_job()` und `kunden_total_setzen()`. |
| `apify_provider.py` | geändert | `start()` und `wait_for_finish()` statt `call()` — nur so ist die Lauf-Nummer bekannt, solange der Lauf rechnet, und nur so erreicht ihn der Abbruch. Neu: `abbrechen()`. Neu: fünf Sekunden Reserve, damit der Provider vor dem Notschalter im Lauf entscheidet (Abschnitt 5). |
| `cli.py` | geändert | Der Befehl `lauf` arbeitet über den Worker, zeigt den Fortschritt und bricht bei Strg+C ab. Neu: Befehl `fortsetzen`, Optionen `--arbeiter` und `--email`. |
| `test_phase3_abnahme.py` | neu | 20 Tests. |
| `test_phase2_abnahme.py` | geändert | Zwei Tests an den neuen Apify-Aufrufweg und an die Reserve angepasst. |
| `README.md` | geändert | Parallelität, Abbrechen, Fortsetzen. |

---

## 3. Getroffene Annahmen

| Situation | Entscheidung | Warum |
|---|---|---|
| „Ab `kunden_erledigt` fortsetzen" lässt sich mit sechs Arbeitern nicht wörtlich umsetzen | Fortgesetzt wird anhand der Tabelle `kunde`: wer dort steht, ist erledigt. `kunden_erledigt` bleibt die Fortschrittszahl. | Mit sechs Arbeitern ist der Zähler kein Index mehr. Sind die Kunden 1 bis 6 unterwegs und 3 und 5 zuerst fertig, steht der Zähler auf 2, erledigt sind aber 3 und 5. Ein Wiederaufsetzen „ab 2" würde 3 und 5 doppelt abfragen — `idx_kunde_nr` würde den Lauf abbrechen. Die Tabelle weiss es genau, der Zähler nur ungefähr. |
| Woher kommt die Entscheidung eines bereits erledigten Kunden beim Fortsetzen? | Sie wird aus den gespeicherten Kandidaten **neu hergeleitet**, mit derselben Fachlogik. | Kein Netzzugriff, keine Kosten, kein zweiter Codepfad. Dieselben Daten und dieselbe Funktion ergeben dieselben Zeilen — nachgewiesen durch den zeichenweisen Vergleich mit einem ungestörten Lauf. |
| Ein Absturz zwischen dem Schreiben des Kunden und dem seiner Kandidaten | Beides geht in einer Transaktion. | Sonst stünde nach dem Neustart ein Kunde ohne Kandidaten da und würde als „kein Ergebnis" neu entschieden — also falsch, und still. `test_halb_geschriebener_kunde_kann_nicht_entstehen`. |
| Schreibt ein abgebrochener Lauf die drei Dateien? | Nein. `dateien` ist dann `None`, der Zielordner entsteht gar nicht. | In den Dateien fehlten genau die Kunden, die noch nicht dran waren — die Invariante aus §2 wäre verletzt, ohne dass man es der Datei ansieht. Der Zwischenstand steht in der Datenbank und geht nicht verloren. |
| Ist `ABGEBROCHEN` fortsetzbar? | Nein, der Zustand ist endgültig. Fortgesetzt wird nur `LAEUFT`. | So steht es in §6: die Wiederaufnahme ist für den Absturz gedacht, nicht für den Abbruch. Wer abbricht, will nicht weitermachen. |
| Wie viele Abfragen sind gleichzeitig unterwegs? | Höchstens `arbeiter * 2`, also zwölf. Nachgelegt wird erst, wenn Ergebnisse eingesammelt sind. | Ohne diese Grenze wandern bei 2'500 Kunden alle Abfragen sofort in die Warteschlange. Fertige Ergebnisse lägen dann herum, statt in der Datenbank zu stehen — ein Absturz nähme sie mit. Aufgefallen beim Bau des Absturztests, der zunächst null verarbeitete Kunden hinterliess. |
| Woher kennt die Wiederaufnahme den Pfad der Eingabedatei? | Der Aufrufer gibt ihn an; die Datenbank speichert nach §5 nur den `dateiname`. Die Kommandozeile prüft, dass der Name zum offenen Auftrag passt. | Ein Pfad in der Spalte `dateiname` wäre eine stille Vertragsänderung — und in der Oberfläche stünde später ein Dateipfad statt eines Dateinamens. |
| Parallelität nur beim Holen der Daten | Entscheidung, Datenbank und Fortschritt laufen im sammelnden Thread. | Dort liegt keine Zeit (Millisekunden gegen Sekunden), dafür die Genauigkeit: die Fortschrittszahl stimmt jederzeit, und die SQLite-Verbindung braucht keine Sperre. |
| Der Timeout des Laufs und der des Providers waren beide 90 s | Apify bekommt 90 minus 5 Sekunden Reserve. | Sonst gewinnt immer der Notschalter im Lauf, und der Provider kommt nie dazu, den überzogenen Apify-Lauf abzubrechen. Live beobachtet, Abschnitt 5. |
| Strg+C in der Kommandozeile | Bricht den Lauf ab und nennt den Befehl zum Fortsetzen. | Der Lauf dauert Stunden; ohne sauberen Abbruch bliebe nur, das Fenster zu schliessen — und der Job stünde für immer auf `LAEUFT`. |

---

## 4. Abweichungen von den Vorgaben

Keine. Sechs Arbeiter, ein Job zur Zeit, 90 Sekunden Timeout, kein Retry und die
Zustände aus §6 stammen aus `03_ENTSCHEIDUNGEN.md` C und `02_DATENVERTRAG.md`
§6. Am Schema wurde nichts geändert: keine Spalte ergänzt, keine umbenannt. Die
Fachlogik aus Phase 1 ist unberührt — belegt durch den zeichenweisen Vergleich
in `test_drei_dateien_und_invariante_nach_parallelem_lauf`.

---

## 5. Was gefunden wurde

| Fund | Datei / Stelle | Auswirkung | eingegriffen? |
|---|---|---|---|
| Der Notschalter im Lauf kam dem Provider zuvor | `pipeline.py` / `apify_provider.py` | Beide Fristen standen auf 90 Sekunden, die des Laufs beginnt aber früher. Live beobachtet: der Lauf meldete „keine Antwort innerhalb von 90 Sekunden" und **eine Sekunde später** kam der Provider zurück und brach den Apify-Lauf ab. In dieser Reihenfolge wäre der Apify-Lauf bei jedem echten Timeout verwaist weitergelaufen — auf Kosten des Kontingents. | ja, fünf Sekunden Reserve für den Provider |
| `actor.call()` gibt die Lauf-Nummer erst zurück, wenn es zu spät ist | `apify_provider.py` | Solange der Aufruf läuft, kennt niemand die Nummer, also kann der Abbruch-Knopf ihn nicht erreichen. Gelöst mit `start()` und `wait_for_finish()`. | ja |
| Alle Abfragen wurden sofort in die Warteschlange gelegt | `pipeline.py` | Bei einem Absturz gingen fertige, aber noch nicht eingesammelte Ergebnisse verloren. Im Absturztest waren das bei sechs Arbeitern bis zu zwölf Kunden. | ja, Fenster von `arbeiter * 2` |
| SQLite-Verbindungen sind an ihren Thread gebunden | `db.py` | In Phase 2 als Hinweis notiert, hier eingelöst: der Worker-Thread öffnet seine eigene Verbindung, WAL erlaubt das gleichzeitige Lesen von aussen. | ja |
| Drei einzelne Apify-Läufe brauchten 83 s, 91 s und 87 s | Betrieb | Das Betriebsprotokoll nennt für Batch 3 und 4 rund zwei Stunden bei sechs Arbeitern, also etwa 17 Sekunden je Aufruf. Meine drei Messungen sind Einzelaufrufe mit kaltem Container und mehreren Minuten Abstand; sie sind nicht repräsentativ und werden hier ausdrücklich **nicht** hochgerechnet. Der offene Punkt bleibt: bei einem kalten Start kann ein Aufruf die 90 Sekunden reissen, und der betroffene Kunde landet grundlos in ③. | nein — die 90 Sekunden stehen in `03` C. Vorschlag in Abschnitt 7. |
| `logger_config.py` hat weiterhin keinen Aufrufer | `logger_config.py` | Seit Phase 2 gemeldet, unverändert. | nein — Phase 7 |

---

## 6. Messwerte

### 6.1 Parallelität

60 erfundene Kunden, Datenquelle antwortet nach je 0.3 Sekunden.

| Arbeiter | Dauer | gleichzeitig gemessen | je Kunde |
|---|---|---|---|
| 1 | 18.32 s | 1 | 0.305 s |
| 2 | 9.15 s | 2 | 0.152 s |
| 6 | **3.06 s** | 6 | 0.051 s |

Beschleunigung von einem auf sechs Arbeiter: **Faktor 5.99**. Die Grenze aus
`03_ENTSCHEIDUNGEN.md` C wird eingehalten und nie überschritten: nie waren
sieben Abfragen gleichzeitig unterwegs.

Die drei Ausgabedateien sind bei einem und bei sechs Arbeitern zeichengleich.
Die Reihenfolge in der Ausgabe folgt der Eingabedatei, nicht der Reihenfolge,
in der die Arbeiter fertig werden.

### 6.2 Abbruch

200 Kunden, Datenquelle antwortet erst nach 30 Sekunden, sechs Arbeiter.

| Messung | Wert |
|---|---|
| Zeit vom Abbruch bis der Lauf steht | **0.10 s** (Grenze: 5 s) |
| Status in der Datenbank | `ABGEBROCHEN`, mit `beendet_am` |
| Ausgabedateien | keine, der Zielordner entsteht nicht |
| Über die Kommandozeile mit Strg+C, 200 Kunden | **0.07 s** bis zur Meldung, Rückgabewert 1, Hinweis auf `cli.py fortsetzen` |
| Apify-Läufe, die dabei noch rechnen | werden abgebrochen (`test_abbruch_erreicht_die_datenquelle`, live bestätigt in 6.4) |

### 6.3 Absturz und Wiederaufnahme

20 Kunden, der Prozess wird per `os._exit(9)` getötet — kein Aufräumen.

| Messung | ein Arbeiter | sechs Arbeiter |
|---|---|---|
| Kunden vor dem Absturz in der Datenbank | 4 | 12 |
| Kunden nach der Wiederaufnahme | 20 | 20 |
| verschiedene Kundennummern | 20 | 20 |
| Kunden in zwei Dateien | 0 | 0 |
| Kunden in keiner Datei | 0 | 0 |
| Aufrufe der Datenquelle beim Fortsetzen | 16 | 8 |
| Ausgabedateien nach dem Absturz | keine | keine |

Aufrufe plus bereits Erledigte ergeben in beiden Fällen genau 20: kein Kunde
wurde zweimal geholt, keiner ausgelassen. Dass mit sechs Arbeitern schon zwölf
Kunden gesichert waren, ist das Fenster aus Abschnitt 3 — es begrenzt, wie viel
ein Absturz mitnehmen kann.

Der fortgesetzte Lauf erzeugt Datei für Datei dasselbe wie ein Lauf ohne
Störung — zeichenweise verglichen.

### 6.4 Echter Apify-Lauf mit dem neuen Aufrufweg

Zwei Läufe mit je einem Kunden, erfundene Kundennummer, öffentliches Geschäft
als Suchbegriff. Keine Datei aus `Daten/` beteiligt.

| Beobachtung | Ergebnis |
|---|---|
| `start()` liefert die Lauf-Nummer sofort | ja, in beiden Läufen |
| `wait_for_finish()` kehrt mit einem Status zurück | ja, beide Male `TIMED-OUT` |
| Der überzogene Lauf wird bei Apify abgebrochen | ja, protokolliert mit Lauf-Nummer |
| Entscheid | ③ `NICHT_MOEGLICH (kein Ergebnis)`, ohne Retry — so steht es in `03` C |
| Dauer | 91 s und 87 s |
| Reihenfolge vor der Korrektur | Notschalter des Laufs zuerst, Provider eine Sekunde später |
| Reihenfolge nach der Korrektur | Provider entscheidet und räumt auf, der Notschalter bleibt ungenutzt |

**Was damit nicht belegt ist:** ein **erfolgreicher** Abruf über den neuen
Aufrufweg. Beide Läufe liefen in den Timeout. Der erfolgreiche Weg wurde in
Phase 2 mit `call()` gemessen (6 Treffer, alle 14 Felder befüllt); die
Umwandlung von Apify-Daten in `Candidate` ist seither unverändert und durch
Testfälle abgedeckt. Der Unterschied liegt allein im Starten und Warten.
Vorschlag zum Schliessen dieser Lücke in Abschnitt 7.

---

## 7. Für die nächste Phase

- **Die Laufzeit je Apify-Aufruf ist offen.** Betriebsprotokoll: rund 17
  Sekunden. Meine drei Einzelmessungen: 83, 87 und 91 Sekunden, jeweils mit
  kaltem Container. Nach der Regel aus der Freigabe zu Phase 2 wird daraus
  nichts hochgerechnet. **Empfehlung:** beim ersten echten Batch nach Phase 4
  zehn aufeinanderfolgende Aufrufe messen. Fällt der Median deutlich unter 90
  Sekunden, ist alles gut; liegt der erste Aufruf regelmässig darüber, landet
  der erste Kunde jedes Batches grundlos in ③ und die Frist gehört auf den
  Prüfstand — per Korrekturplan, nicht nebenbei.
- **Damit schliesst sich auch die Lücke aus 6.4:** ein Batch mit zehn Aufrufen
  belegt den erfolgreichen Weg über `start()`/`wait_for_finish()` beiläufig mit.
- **Für Phase 5 (Oberfläche) steht alles bereit:** `Worker.starten()`,
  `abbrechen()`, `fortschritt()` und `offener_lauf()` sind genau die vier
  Funktionen, die die Statusseite braucht. `fortschritt()` liest aus der
  Datenbank, nicht aus dem Gedächtnis — der Stand stimmt deshalb auch nach
  einem Neustart des Programms.
- **Beim Start der Webanwendung** ist `offener_lauf()` aufzurufen. Liefert es
  einen Job, wurde er von einem Absturz unterbrochen und die Oberfläche soll
  das Fortsetzen anbieten (§6). Der Pfad der hochgeladenen Datei muss dafür
  auffindbar sein — die Datenbank speichert nur den Dateinamen. Vorschlag: ein
  fester Ordner für Uploads, Datei unter ihrem Namen abgelegt.
- **`ui_manager.py` prüfen, bevor die Oberfläche entsteht.** Der Prüfer hat in
  der Freigabe zu Phase 2 darauf hingewiesen: beim Löschen von `main.py` sind
  die sechs Arbeiter verschwunden, ohne dass es jemandem auffiel. In
  `ui_manager.py` könnte Ähnliches liegen. Zu finden über
  `git show a17150e~1:ui_manager.py`.
- **Der Abbruch ist endgültig.** Wer ihn drückt, kann nicht fortsetzen. Falls
  die Oberfläche das anders darstellen soll, ist das eine Vertragsfrage zu §6.

---

## 8. Zeit

| Arbeitspaket | grober Aufwand |
|---|---|
| Freigabe und ergänzten Phasenplan einlesen | 0.25 h |
| Parallelität im Lauf, Fenster, Reihenfolge der Ausgabe | 1.25 h |
| Wiederaufnahme, Transaktion, `offener_job` | 1.25 h |
| Abbruch bis in die Datenquelle, Umbau des Apify-Aufrufwegs | 1.0 h |
| `worker.py` | 0.75 h |
| Kommandozeile: Fortschritt, Strg+C, `fortsetzen` | 0.75 h |
| Tests (20 neu, 2 angepasst) | 1.75 h |
| Messungen, zwei echte Apify-Läufe, Strg+C-Probe | 0.75 h |
| Findings | 0.75 h |
| **gesamt** | **≈ 8.5 h** |

Der Absturztest hat am meisten gelehrt: er lief zuerst durch, ohne einen
einzigen verarbeiteten Kunden zu hinterlassen. Das war kein Testfehler, sondern
der Hinweis darauf, dass der Lauf zu weit vorausarbeitet — behoben mit dem
Fenster von zwölf Abfragen.
