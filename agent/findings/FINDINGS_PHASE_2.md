# Findings — Phase 2, Version 1.0

Datum: 03.08.2026
Bearbeitete Phase: 2 — Provider und Datenmodell
Status: fertig

Branch: `umbau/webapp`, enthält die Freigabe und die §2-Ergänzung aus `main`.
Testlauf: `python -m pytest` → **93 grün, 1 übersprungen** (der 90-Sekunden-Lauf,
siehe Kriterium 4). Aufteilung: 8 + 40 aus Phase 1, 45 + 1 neu.

---

## 1. Abnahmekriterien

| # | Kriterium | Status | Beleg |
|---|---|---|---|
| 1 | Kein Modul ausserhalb von `ApifyProvider` kennt Apify-Feldnamen | grün | `test_kein_modul_kennt_apify_feldnamen`, parametrisiert über alle 13 Projektmodule. Sucht 16 Apify-eigene Namen (`searchStringsArray`, `defaultDatasetId`, `maxCrawledPlacesPerSearch`, `ApifyClient`, `apify_client` …). Gegenprobe `test_apify_provider_kennt_sie_als_einziger` stellt sicher, dass der Test nicht ins Leere greift. Zur Abgrenzung siehe Annahme 1. |
| 2 | Der Lauf aus Phase 1 funktioniert unverändert über `ApifyProvider` | grün | Ein echter Apify-Lauf über einen Kunden, Messwerte in Abschnitt 6.2: 6 Treffer, alle 14 Kandidatenspalten befüllt, Spalten nach §2, Entscheid und Datenbank vollständig. |
| 3 | Derselbe Lauf funktioniert über `FakeProvider` ohne Netzzugriff | grün | `test_lauf_ueber_fakeprovider_ergibt_dasselbe_wie_phase1` vergleicht die drei Ausgabedateien **Zeichen für Zeichen** mit dem Ergebnis von Phase 1. `test_lauf_ueber_fakeprovider_ohne_netzzugriff` sperrt `socket.connect` und `socket.create_connection` und prüft, dass kein einziger Versuch stattfindet. |
| 4 | Timeout nachweisbar: Test mit künstlich verzögertem Provider endet nach ~90 s in ③ | grün | `test_timeout_mit_echten_90_sekunden`: gemessen **90.04 s**, Kunde in ③ mit `NICHT_MOEGLICH (kein Ergebnis)`. Der Test ist im Alltag übersprungen, damit die Suite in 4 s läuft; Befehl in Abschnitt 6.1. Täglich läuft `test_haengender_provider_endet_in_datei_drei` mit 0.3 s statt 90 s, plus `test_timeout_standard_ist_90_sekunden`. |
| 5 | Nach einem Lauf enthält die Datenbank jeden Kandidaten mit `score` und `entscheid` | grün | `test_datenbank_enthaelt_jeden_kandidaten_mit_score_und_entscheid`: 16 Kandidaten der Fixture, alle mit Score, Entscheid aus der Liste `gewaehlt`/`abgelehnt`/`vorgeschlagen` und Klartextgrund. `test_abgelehnte_kandidaten_stehen_ebenfalls_in_der_datenbank` und `test_gewaehlter_kandidat_ist_der_aus_datei_eins` prüfen die Zuordnung. |
| 6 | `idx_kunde_nr` verhindert nachweislich einen doppelten Kunden pro Job | grün | `test_idx_kunde_nr_verhindert_doppelten_kunden`: zweiter Schreibversuch wirft `sqlite3.IntegrityError`, dieselbe Nummer in einem anderen Job bleibt erlaubt. `test_doppelte_kundennummer_in_der_eingabe_bricht_den_lauf_nicht` zeigt, dass der Lauf davor abfängt. |

---

## 2. Geänderte und neue Dateien

| Datei | neu / geändert / entfernt | Was |
|---|---|---|
| `place_provider.py` | neu | `Candidate` und das `PlaceProvider`-Protokoll nach §7, dazu die Zuordnung Candidate-Feld → Ausgabespalte. |
| `apify_provider.py` | neu | `ApifyProvider` mit 90-Sekunden-Timeout. Enthält als einziges Modul Apify-Feldnamen und die Actor-Einstellungen. |
| `fake_provider.py` | neu | `FakeProvider` mit festen Antworten aus einer CSV im Format der angereicherten Datei. |
| `db.py` | neu | SQLite-Schema wörtlich nach §5 mit allen drei Indizes, plus Zugriffsschicht: Job anlegen, Zustand setzen, Kunde schreiben, Kandidaten schreiben, Fortschritt lesen und setzen. |
| `pipeline.py` | neu | Ein Lauf: Eingabe → Provider → Entscheidung → Datenbank → drei Ausgabedateien. Timeout gilt für jeden Provider, nicht nur für Apify. |
| `data_cleaner.py` | geändert | Kleiner Umbau, keine neue Fachlogik: `entscheide_kunde()` als öffentlicher Einstieg für einen einzelnen Kunden, `schreibe_ausgabedateien()` und `ausgabeordner_fuer()` als Funktionen. `clean_data()` benutzt jetzt dieselben Bausteine wie der Lauf. |
| `cli.py` | geändert | Zwei Befehle statt einem: `bereinigen` wie bisher, neu `lauf` mit `--quelle fake|apify`. |
| `apify_wrapper.py` | entfernt | Geht in `ApifyProvider` auf. Nichts importierte ihn mehr, seit `main.py` weg ist. |
| `config.template.py` | geändert | `DEFAULT_ACTOR_INPUT` und `FINAL_COLUMNS` entfernt. Die Actor-Einstellungen stehen jetzt in `apify_provider.py`; damit ist auch die in Umbauplan §9 gemeldete Abweichung zwischen Vorlage und `config.py` erledigt. |
| `test_phase2_abnahme.py` | neu | 45 Tests plus einer, der nur auf Anforderung läuft. |
| `README.md` | geändert | Modulübersicht und die zwei CLI-Befehle. |
| `.gitignore` | geändert | `*.sqlite` ergänzt — Laufdatenbanken enthalten echte Kundendaten. |

---

## 3. Getroffene Annahmen

| Situation | Entscheidung | Warum |
|---|---|---|
| Was heisst „Apify-Feldname"? `title`, `street`, `placeId` kommen bei Apify **und** im Datenvertrag §2 vor | Geprüft wird auf Namen, die es **nur** bei Apify gibt (`searchStringsArray`, `defaultDatasetId`, `categoryName`, `totalScore`, …). Die Spaltennamen aus §2 gehören dem Vertrag, nicht der Datenquelle. | Sonst dürfte auch `data_cleaner.py` das Wort `title` nicht kennen — der Vertrag schreibt es aber vor. Der Schutz, den das Kriterium meint, hält: eine zweite Datenquelle liefert `Candidate`, sonst ändert sich nichts. |
| `config.py` liegt nicht im Repository (per `.gitignore`) und enthält lokal noch Apify-Einstellungen | Vom Test ausgenommen. `aus_konfiguration()` liest daraus nur noch Token und Actor-Id. | Die Actor-Einstellungen stehen jetzt in `apify_provider.py`. Der Eintrag `DEFAULT_ACTOR_INPUT` in der lokalen `config.py` ist tot und kann gelöscht werden. |
| Wo gehören die Actor-Einstellungen hin? | Nach `apify_provider.py`, mit den Werten der produktiven `config.py` (`maxCrawledPlacesPerSearch` 6, `scrapeDirectories` True). | Sonst kennt die Konfiguration Apify-Feldnamen. Nebeneffekt: die Abweichung zwischen `config.py` und `config.template.py` aus Umbauplan §9 ist weg. |
| Timeout auf welcher Ebene? | Auf beiden. `ApifyProvider` setzt `timeout_secs` und `wait_secs`; der Lauf schneidet zusätzlich jeden Provider nach derselben Zeit ab. | Der Provider-eigene Timeout hilft nur bei Apify. Das Kriterium verlangt einen Nachweis mit einem *künstlich verzögerten Provider* — der Schutz muss also für jede Datenquelle gelten. |
| Was passiert mit einem Apify-Lauf, der in den Timeout läuft? | Er wird auf Apify abgebrochen (`run.abort()`). | Sonst rechnet er weiter und verbraucht Kontingent, obwohl niemand mehr auf ihn wartet. |
| Parallelität: `03_ENTSCHEIDUNGEN.md` C nennt 6 parallele Worker | Der Lauf arbeitet sequenziell. | Parallelität ohne Abbruch und Wiederaufnahme müsste in Phase 3 komplett neu gebaut werden. Der Umfang von Phase 2 nennt sie nicht, der von Phase 3 heisst „Worker". Siehe Abschnitt 7. |
| Der 90-Sekunden-Nachweis dauert 90 Sekunden | Läuft nur mit `LANGSAME_TESTS=1`, im Alltag übersprungen. Einmal ausgeführt und in Abschnitt 6.1 dokumentiert. | Eine Testsuite, die anderthalb Minuten steht, wird nicht mehr ausgeführt. Ein übersprungener Test ist sichtbar, ein weggelassener nicht. |
| Eine `KundenNr` kommt mehrfach in der Eingabe vor | Die erste Zeile zählt, der Rest wird gezählt und gemeldet (`doppelte_kundennummern`). | Ein Kunde, eine Ausgabezeile (§2). `idx_kunde_nr` bleibt das Netz darunter, greift im Normalbetrieb aber nicht mehr. |
| Verbindung zwischen Ausgabezeile und Kandidat | Interne Spalte `_kandidat_nr` in der Kundengruppe. Sie erreicht die CSV nicht, weil beim Schreiben nur die Vertragsspalten ausgewählt werden. | Ohne sie liesse sich nach der Entscheidung nicht mehr sagen, welcher Kandidat welche Zeile wurde — `placeId` ist nicht zuverlässig gefüllt. |
| `entscheid` für Kandidaten eines Prüffalls | `vorgeschlagen` für alle Zeilen in ② und ③, `gewaehlt` in ①, `abgelehnt` in `aussortiert`. | §5 nennt genau diese drei Werte. In ② hat niemand gewählt, alle Kandidaten stehen zur Auswahl. |
| Kunde ohne jeden Treffer | Kein Eintrag in `kandidat`, nur in `kunde` mit `ergebnis = 'nicht_moeglich'`. | Es gibt keinen Kandidaten, den man speichern könnte. |
| `Lauf` prüft die Invariante selbst | Landet ein Kunde in null oder zwei Hauptdateien, bricht der Lauf ab. | Lieber ein Abbruch als eine halbe Wahrheit in der Datenbank. Die Regel aus §2 ist damit auch zur Laufzeit abgesichert, nicht nur im Test. |
| Standard-Datenbank der CLI | `laeufe.sqlite` im Projektordner, in `.gitignore`. | Sie enthält echte Kundendaten, sobald jemand eine echte Datei laufen lässt. |
| Live-Test gegen Apify | Ein einziger Lauf mit einem erfundenen Suchbegriff auf ein öffentliches Geschäft in Zürich — keine Kundennummer, keine Kundenadresse. | Das Kriterium verlangt den Nachweis, der Phasenplan sieht Apify „nur für einen Test" vor. Ein Kunde ist die kleinste Menge, die ihn erbringt. |

---

## 4. Abweichungen von den Vorgaben

Keine. Schema, Spalten, Zustände, Entscheide, Ergebniswerte und der Timeout von
90 Sekunden stammen wörtlich aus `02_DATENVERTRAG.md` §5/§6/§7 und
`03_ENTSCHEIDUNGEN.md` C. Die Fachlogik aus Phase 1 wurde nicht angefasst: der
Beweis dafür ist der zeichengenaue Vergleich der Ausgabedateien (Kriterium 3).

Nicht gebaut, weil ausserhalb des Umfangs: Web, Worker, Wiederaufnahme,
Abbruch, Google, Mailversand, Prüfmaske.

---

## 5. Was im Bestandscode gefunden wurde

| Fund | Datei / Stelle | Auswirkung | eingegriffen? |
|---|---|---|---|
| `config.py`: „TODO: Timeout für Apify Actor-Runs (noch nicht implementiert) — der apify-client erlaubt timeout nicht direkt in actor.call()" | `config.py`, Kommentar | Die Annahme ist falsch. `ActorClient.call()` kennt `timeout_secs` und `wait_secs` (apify-client 2.0.0). Der Timeout hat schlicht gefehlt. | ja, beide Werte werden gesetzt |
| `ACTOR_TIMEOUT_MS = 120000` in `config.py` | `config.py` | Wurde nirgends gelesen und widerspricht mit 120 s dem Wert 90 s aus `03_ENTSCHEIDUNGEN.md` C. | nein — `config.py` gehört nicht zum Repository. Kann lokal gelöscht werden. |
| `apify_wrapper.py` gab bei jedem Fehler `[]` zurück, ohne den Lauf zu markieren | `apify_wrapper.py` | Ein Kontingentfehler war von „nichts gefunden" nicht unterscheidbar. Bleibt vorerst so (kein Retry, ③), wird in Phase 7 zum Fehlertext. | nein — Phase 7 |
| `logger_config.py` wird von keinem Modul mehr gebraucht | `logger_config.py` | Nach dem Wegfall von `apify_wrapper.py` importiert es niemand mehr. Die Datei konfiguriert ohnehin einen Logger, den keiner benutzt (Findings Phase 1). | nein — Aufräumen gehört zu Phase 7 |
| `csv_processor.py`, `csv_postprocessor.py` sind ohne Aufrufer | Projektwurzel | Der Lauf schreibt direkt; das Zwischenformat `_angereicherte_daten.csv` entfällt. Laut Umbauplan §2 sollen beide bleiben. | nein — nur gemeldet |
| Hausnummernbereiche treffen nie | `data_cleaner._street_matches` | Beim Apify-Lauf lieferte Google Adressen der Form „31-35" und „31/35 1 OG". Gesucht war eine einzelne Nummer, also kein Strassentreffer → ②. Korrekt nach `03` B3, aber in Einkaufszentren und Passagen ein systematischer Prüffall. | nein — `03` B3 verbietet Änderungen an der Hausnummernlogik. Zahlenmässig bewerten in Phase 4. |
| Ein Provider läuft in einem eigenen Thread, die SQLite-Verbindung nicht | `pipeline.py`, `db.py` | Fiel beim Schreiben eines Tests auf: SQLite-Verbindungen sind an ihren Thread gebunden. Im Lauf harmlos, weil nur der Hauptthread schreibt. Für Phase 3 relevant. | nein — Hinweis in Abschnitt 7 |

---

## 6. Messwerte

### 6.1 Timeout

| Messung | Wert |
|---|---|
| Vorgabe `03_ENTSCHEIDUNGEN.md` C | 90 Sekunden |
| Gemessen, Provider antwortet nie (`test_timeout_mit_echten_90_sekunden`) | **90.04 s**, danach ③ `NICHT_MOEGLICH (kein Ergebnis)` |
| Wiederholungen des Aufrufs | 0 — ein Aufruf je Kunde, wie in `03` C festgelegt |
| Laufzeit der Testsuite ohne diesen Test | 4 s |

Reproduzieren:

```bash
LANGSAME_TESTS=1 python -m pytest test_phase2_abnahme.py::test_timeout_mit_echten_90_sekunden -q --durations=1
```

### 6.2 Echter Apify-Lauf

Ein Kunde, erfundene Kundennummer, öffentliches Geschäft in Zürich als
Suchbegriff. Keine Datei aus `Daten/` beteiligt.

| Messung | Wert |
|---|---|
| Dauer des Laufs, ein Kunde | **83 s** |
| Treffer von Apify | 6 |
| Kandidatenspalten befüllt | 14 von 14, bei allen 6 Treffern |
| Spalten der Ausgabedatei | stimmen mit `OUTPUT_COLUMNS` überein |
| Entscheid | ② `PRUEFUNG (keine Strassentreffer)` — gesucht war Hausnummer 32, Google liefert „31-35" |
| In der Datenbank | 1 Job (`FERTIG`), 1 Kunde (`pruefung`), 6 Kandidaten mit Score zwischen 20.0 und 100.0, alle `vorgeschlagen` |
| Verschachtelte Felder | `location` als `{'lat': …, 'lng': …}`, `openingHours` als Liste von Tagesangaben — identisch zur bisherigen Schreibweise |

**83 Sekunden bei 90 Sekunden Grenze.** Das ist knapp. Bei 2'500 Kunden
sequenziell wären das rund 58 Stunden — die zwei Stunden aus dem Umbauplan
setzen die sechs parallelen Worker aus `03` C voraus. Siehe Abschnitt 7.

### 6.3 Gleichheit mit Phase 1

| Prüfung | Ergebnis |
|---|---|
| `fertig_fuer_erp.csv` über Provider gegen Phase 1 | zeichengleich |
| `zur_pruefung.csv` | zeichengleich |
| `nicht_moeglich.csv` | zeichengleich |
| Verteilung Fixture | ① 6 · ② 3 · ③ 1 — wie in Phase 1 |
| Netzzugriffe im Lauf über `FakeProvider` | 0 (gemessen, nicht angenommen) |

### 6.4 Datenbank nach dem Fixture-Lauf

| Tabelle | Inhalt |
|---|---|
| `job` | 1 Zeile, `FERTIG`, `kunden_total` 10, `kunden_erledigt` 10 |
| `kunde` | 10 Zeilen, jede mit `ergebnis`, `qualitaet`, `grund`, `verarbeitet_am` |
| `kandidat` | 16 Zeilen — jeder Treffer der Fixture, mit Score, Entscheid und Grund |
| `kunden_erledigt` im Verlauf | 0, 1, 2 … 9 vor dem jeweiligen Kunden; nach jedem Kunden geschrieben, nicht am Ende |

---

## 7. Für die nächste Phase

- **Parallelität ist offen und gehört in Phase 3.** Der Lauf arbeitet
  sequenziell; ein Apify-Aufruf dauert gemessen 83 Sekunden. Erst die sechs
  Worker aus `03_ENTSCHEIDUNGEN.md` C bringen die Laufzeit in die Nähe der zwei
  Stunden aus dem Umbauplan. Der Einstiegspunkt ist die Schleife in
  `Lauf.ausfuehren`; `_einen_kunden` ist bereits so geschnitten, dass er je
  Kunde unabhängig ist.
- **SQLite und Threads.** Eine Verbindung gehört dem Thread, der sie geöffnet
  hat. Beim Worker in Phase 3 muss die Verbindung im Worker-Thread entstehen
  oder mit `check_same_thread=False` plus Sperre arbeiten. Heute nicht nötig,
  weil nur der Hauptthread schreibt.
- **Wiederaufnahme braucht nichts Neues am Schema.** `job.kunden_erledigt` wird
  nach jedem Kunden geschrieben, `idx_kunde_nr` verhindert, dass ein Kunde beim
  Fortsetzen doppelt entsteht. Was fehlt, ist allein die Logik „ab welchem
  Kunden weiter" — die Kunden werden in Reihenfolge der Eingabedatei
  abgearbeitet, `kunden_erledigt` ist damit zugleich der Index.
- **Der Abbruch muss zwei Dinge treffen:** die Schleife im Lauf und den
  laufenden Apify-Aufruf. Für das Zweite gibt es `ApifyProvider._lauf_abbrechen`
  bereits, heute nur für den Timeout-Fall.
- **`FakeProvider` ist die Grundlage der Phasen 3 bis 5.** Antwortdatei ist
  `agent/testdaten/fixture_optimierte_daten.csv`; für längere Läufe genügt jede
  angereicherte CSV im selben Format.
- **Für Phase 4 vorgemerkt:** Adressen mit Hausnummernbereichen („31-35",
  „31/35 1 OG") erzeugen systematisch Prüffälle. Beim einzigen echten
  Apify-Lauf traf das sofort zu. Zahlenmässig bewerten, wenn die
  Upload-Validierung gemessen wird.
- **Modus B ist im Schema vorgesehen, aber leer.** `kunde.place_id`, `lat`,
  `lng` schreibt der Lauf im Modus A nicht. `FakeProvider.fetch_by_id`
  funktioniert bereits, `ApifyProvider.fetch_by_id` wirft bewusst
  `NotImplementedError`.

---

## 8. Zeit

| Arbeitspaket | grober Aufwand |
|---|---|
| Freigabe und Vertragsänderung einlesen, Branches zusammenführen | 0.25 h |
| `Candidate` und Provider-Schnittstelle | 0.5 h |
| `ApifyProvider` inklusive Timeout und Abbruch | 1.0 h |
| `FakeProvider` | 0.5 h |
| `db.py` mit Schema und Zugriffsschicht | 1.0 h |
| `pipeline.py` und der kleine Umbau an `data_cleaner.py` | 1.5 h |
| `cli.py` um den Befehl `lauf` erweitert | 0.5 h |
| Tests (45 neu) | 1.5 h |
| Echter Apify-Lauf und Timeout-Nachweis | 0.5 h |
| Findings | 0.75 h |
| **gesamt** | **≈ 8 h** |

Der Aufwand lag nicht im Provider, sondern in der Frage, wie der Lauf **exakt**
dieselben Dateien erzeugt wie die Bereinigung aus Phase 1. Die Antwort war der
gemeinsame Einstieg `entscheide_kunde()`: eine Fachlogik, zwei Aufrufer. Der
zeichengenaue Vergleich war danach beim ersten Versuch grün — er ist der Beleg
dafür, dass Phase 2 die Entscheidungen aus Phase 1 nicht angefasst hat.
