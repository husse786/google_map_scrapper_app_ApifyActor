# Findings — Phase 7, Version 1.2

Datum: 04.08.2026
Bearbeitete Phase: 7 — Mail und Härtung, zweite Korrekturrunde nach
`KORREKTURPLAN_PHASE_7_v1.1.md`
Status: fertig

Umfang dieser Runde: **K1 (a und b) und K2**. Sonst nichts.

Testlauf: `venv/bin/python -m pytest` → **297 grün, 1 übersprungen**, fünfmal
hintereinander (Abschnitt 6.1). Verwendete Fassung: **`apify-client` 2.0.0**.

---

## 1. Abnahmekriterien

### Die Punkte des Korrekturplans

| # | Punkt | Status | Beleg |
|---|---|---|---|
| K1 a | Tests versionsfest bauen | grün | `ApifyFehlerFuerDenTest`, eine Unterklasse mit eigenem `__new__`. Gegen `apify-client` 3.1.1 nachgemessen: die alte Konstruktion scheitert dort mit genau dem gemeldeten `TypeError`, die neue läuft und bleibt ein echter `ApifyApiError`. Abschnitt 6.2 |
| K1 b | `requirements.txt` festnageln | grün | Alle zwölf Pakete auf die geprüfte Fassung festgelegt, mit Begründung im Kopf der Datei für die zwei, die Fachlogik tragen. Abgeglichen gegen das `venv`, in dem die fünf Läufe grün sind. Abschnitt 6.3 |
| K2 | `google_provider.fetch_by_id` sagt nichts Falsches mehr | grün | Netzfehler, 5xx und unlesbare Antworten kommen als `QuelleNichtVerfuegbar`; 404 und `NOT_FOUND` bleiben ③. 17 Tests, dazu ein Lauf über 100 Kunden in Abschnitt 6.4 |

### Die vier Kriterien der Phase

Unverändert grün. An Mailversand, Fehlertexten und README wurde in dieser Runde
nichts geändert; die Belege stehen in `FINDINGS_PHASE_7.md` Abschnitt 1.

**Zur Zahl 297 statt der im Korrekturplan genannten 283:** K2 bringt vierzehn
Tests mit (283 + 14 = 297). Der eine übersprungene Test ist der bekannte
Langläufer aus Phase 2 (`Dauert 180 Sekunden. Mit LANGSAME_TESTS=1 ausführen.`),
unverändert seit damals.

---

## 2. Geänderte und neue Dateien

| Datei | neu / geändert | Was | Punkt |
|---|---|---|---|
| `test_phase7_abnahme.py` | geändert | `apify_fehler()` baut den Fehler nicht mehr über `ApifyApiError.__new__`, sondern über die Unterklasse `ApifyFehlerFuerDenTest`. Dazu vierzehn Tests für K2. | K1 a, K2 |
| `requirements.txt` | geändert | Zwölf Pakete mit `==` festgelegt. Kopfkommentar erklärt, warum `apify-client` und `thefuzz` keine reine Technikfrage sind. | K1 b |
| `google_provider.py` | geändert | `fetch_by_id` unterscheidet «Google kennt die Id nicht» von «wir konnten nicht fragen». Vier Meldungstexte, `_pruefen_ob_endgueltig`, `_meldet_nicht_gefunden`. | K2 |
| `modus_b.py` | geändert | `entscheide_kunde` bekommt `erreichbar: bool = True`. Bei `False` derselbe Zustand wie ein leeres Ergebnis, aber ein Grund, der stimmt. | K2 |
| `pipeline.py` | geändert | `Ausgefallen(list)` — eine leere Liste, die sagt, warum sie leer ist. Wird an `modus_b` durchgereicht. | K2 |
| `test_phase6_abnahme.py` | geändert | `test_google_fehler_liefert_nichts_statt_absturz` heisst jetzt `test_google_fehler_ist_kein_geloeschter_kunde` und erwartet die Ausnahme statt `None`. | K2 |
| `agent/findings/FINDINGS_PHASE_7_v1.2.md` | neu | Dieses Dokument. | — |

Nicht angefasst, wie verlangt: die sechs Apify-Fehlerarten, die sieben
Stichwörter, die Grenze von zehn, `mail.py`, `README.md`, `data_cleaner.py`,
die Schwellenwerte aus `03 B`.

---

## 3. Getroffene Annahmen

| Situation | Entscheidung | Warum |
|---|---|---|
| Welche Fassung von `apify-client` festnageln — 2.0.0 oder die neuere 3.1.1? | **2.0.0**, die Fassung im Projekt-`venv`. | 3.1.1 ist nicht nur beim Testfehler anders. `actor().call()` heisst dort `run_timeout` statt `timeout_secs` und `wait_duration` statt `wait_secs`, und beide erwarten ein `timedelta` statt Sekunden; `wait_for_finish` genauso. Ausserdem liefern beide jetzt `Run`-Objekte statt `dict`. Ein Wechsel wäre ein Umbau von `apify_provider.py` — das ist nicht K1. Festgenagelt wird die Fassung, unter der die Läufe grün sind und unter der die echten Apify-Aufrufe der Phasen 2 bis 4 liefen. Messung in Abschnitt 6.3 |
| Welchen `qualitaet`-Wert bekommt ein Kunde, dessen Abfrage ausgefallen ist? | `NICHT_MOEGLICH (kein Ergebnis)` — der bestehende Wert aus `02_DATENVERTRAG.md` §3, Zeile «API lieferte nichts». | Der Korrekturplan verlangt ausdrücklich keinen neuen Wert und keine Änderung am Datenvertrag. Der Zustand stimmt: die API lieferte nichts. Nur der Grundtext musste die Wahrheit sagen statt «gelöscht». |
| Was heisst ein leerer Datensatz bei HTTP 200? | Vorübergehend, nicht «gelöscht». | Google meldet eine gelöschte Id mit 404 oder `NOT_FOUND`, nicht mit einem leeren 200er. Ein leerer 200er ist unerwartet — und aus etwas Unerwartetem eine Aussage über die Kundendaten zu machen, ist genau der Fehler, den K2 behebt. Im Zweifel Prüfung. |
| Wie verhält sich ein ausgefallener Kunde beim Fortsetzen? | Er bleibt ausgefallen. `_aus_datenbank` liest den damaligen `qualitaet`-Wert zurück. | `_aus_datenbank` ist ein Nachspielen ohne Netzzugriff; es muss dieselbe Entscheidung ergeben wie beim ersten Mal. Sonst würde ein Kunde, der als «nicht geprüft» geschrieben wurde, beim Fortsetzen stillschweigend zu «gelöscht». |

---

## 4. Abweichungen von den Vorgaben

Keine.

Zur Klarstellung bei einem Punkt, der wie eine Abweichung aussehen könnte: Die
Tabelle in K2 nennt «Zeitüberschreitung» als Fall für `QuelleNichtVerfuegbar`.
Das ist erfüllt — `requests.Timeout` ist eine `requests.RequestException` und
läuft in den Netzfall. Der davon getrennte Wächter in `pipeline.py`
(180 Sekunden, gilt für beide Modi) bleibt bei «wie leeres Ergebnis → ③» nach
`03_ENTSCHEIDUNGEN.md C`. Siehe dazu den letzten Fund in Abschnitt 5.

---

## 5. Was gefunden wurde

| Fund | Datei / Stelle | Auswirkung | eingegriffen? |
|---|---|---|---|
| **Die alte Testkonstruktion war nicht sporadisch kaputt, sondern versionsabhängig.** In `apify-client` 2.0.0 hat `ApifyApiError` kein eigenes `__new__` und erbt das von `Exception` — der Aufruf ohne Argumente geht durch. Ab 3.1.1 lautet die Signatur `__new__(cls, response, attempt, *, method='GET')`, und derselbe Aufruf scheitert. | `test_phase7_abnahme.py` | Der Nachweis für K1 hing an der Maschine, auf der er lief. Genau wie vom Prüfer beschrieben. | **ja** — K1 a |
| **`requirements.txt` hatte keine einzige Versionsangabe.** Zwölf Pakete, alle offen. | `requirements.txt` | Ein `pip install -r requirements.txt` auf einem neuen Rechner hätte `apify-client` 3.x geholt. Damit wäre nicht nur der Test rot geworden, sondern `apify_provider.py` gar nicht mehr gelaufen: `timeout_secs` und `wait_secs` gibt es dort nicht mehr. | **ja** — K1 b |
| **`fetch_by_id` sagte «gelöscht», wenn nur das Netz weg war.** Bestätigt und behoben. Der Weg: `return None` → `modus_b` → `NICHT_MOEGLICH (ID ungueltig)` → «Der Betrieb wurde bei Google gelöscht oder durch einen neuen Eintrag ersetzt.» | `google_provider.py:123` ff. | Gemessen: 100 Kunden, alle mit dieser falschen Begründung, Lauf meldet `FERTIG`. Abschnitt 6.4. | **ja** — K2 |
| **Google meldet eine unbekannte Id nicht immer als 404.** Manche Fehler kommen als 400 mit `NOT_FOUND` im Rumpf. | `google_provider.py` | Ohne diesen Zweig wäre eine wirklich gelöschte Id als «Störung» durchgegangen und hätte nach zehn Stück den Lauf gestoppt — der umgekehrte Fehler. `_meldet_nicht_gefunden` fängt ihn. | **ja** — gehört zu K2, sonst wäre K2 halb |
| **Der 180-Sekunden-Wächter in `pipeline.py` kann dieselbe falsche Aussage erzeugen.** Läuft `_mit_frist` ab oder wirft der Provider etwas Unerwartetes, kommt `None` zurück, daraus wird eine gewöhnliche leere Liste — und im Modus B damit wieder «gelöscht». | `pipeline.py:439` ff. (`_mit_frist`) | In der Praxis eng: der Google-Abruf hat seine eigene Frist von 30 Sekunden (`03 C`), die vorher greift und korrekt als Netzfehler herauskommt. Der Wächter feuert nur bei einem echten Hänger. | **nein** — der Wächter ist modusübergreifend und steht unter `03_ENTSCHEIDUNGEN.md C` («Verhalten bei Timeout: wie leeres Ergebnis → ③»). `03` schlägt den Korrekturplan. Eine Änderung wäre eine Entscheidung des Prüfers, kein Bugfix. Vorschlag in Abschnitt 7 |

---

## 6. Messwerte

### 6.1 Fünf vollständige Testläufe

Am sauberen Arbeitsbaum, ohne Änderungen zwischen den Läufen.

| Lauf | Ergebnis | Dauer |
|---|---|---|
| 1 | 297 grün, 1 übersprungen | 15.23 s |
| 2 | 297 grün, 1 übersprungen | 14.74 s |
| 3 | 297 grün, 1 übersprungen | 15.16 s |
| 4 | 297 grün, 1 übersprungen | 14.98 s |
| 5 | 297 grün, 1 übersprungen | 14.77 s |

Die drei Tests, die beim Prüfer in allen fünf Läufen rot waren, sind grün:

```
test_unbekannter_apify_fehler_ist_kein_leeres_ergebnis    PASSED
test_unbekannter_apify_fehler_stoppt_den_lauf_nach_zehn   PASSED
test_bekannte_arten_stoppen_weiterhin_sofort              PASSED
```

### 6.2 K1 a — der Nachweis hängt nicht mehr an der Fassung

Gemessen in einer eigenen Umgebung mit `apify-client` **3.1.1**, also der
Fassung, unter der der Prüfer die roten Tests hatte:

| Konstruktion | unter 3.1.1 |
|---|---|
| `ApifyApiError.__new__(ApifyApiError)` — Stand v1.1 | `TypeError: ApifyApiError.__new__() missing 2 required positional arguments: 'response' and 'attempt'` |
| `ApifyFehlerFuerDenTest(...)` — Stand v1.2 | läuft. `isinstance(fehler, ApifyApiError)` ist `True`, `type` und `message` sind gesetzt |

Der Typ bleibt echt — das war die Bedingung, weil `fetch_by_text` genau auf
`ApifyApiError` fängt. Die Unterklasse überschreibt nur `__new__` und umgeht
damit die Pflichtargumente, ohne die Vererbung anzutasten.

### 6.3 K1 b — die festgelegten Fassungen

Abgeglichen gegen das `venv`, in dem die fünf Läufe aus 6.1 grün sind. Alle
zwölf stimmen mit `requirements.txt` überein.

| Paket | Fassung | warum diese |
|---|---|---|
| `apify-client` | **2.0.0** | trägt Fachlogik: die Fehlerbehandlung liest `fehler.type` und `fehler.message` |
| `thefuzz` | **0.22.1** | trägt Fachlogik: die Schwellenwerte 90 / 80 / 60 aus `03 B` sind an dieses Verhalten gemessen |
| `python-Levenshtein` | 0.27.1 | Rechenkern von `thefuzz` |
| `pandas` | 2.3.2 | |
| `requests` | 2.32.5 | |
| `python-dotenv` | 1.2.1 | |
| `fastapi` | 0.141.1 | |
| `uvicorn` | 0.52.1 | |
| `jinja2` | 3.1.6 | |
| `python-multipart` | 0.0.32 | |
| `pytest` | 9.1.1 | |
| `httpx` | 0.28.1 | |

Was ein Sprung auf `apify-client` 3.1.1 kosten würde — gemessen, nicht
vermutet:

| Aufruf | 2.0.0 | 3.1.1 |
|---|---|---|
| `actor().call(...)` | `timeout_secs: int`, `wait_secs: int` | `run_timeout: timedelta`, `wait_duration: timedelta` |
| `run().wait_for_finish(...)` | `wait_secs: int` | `wait_duration: timedelta` |
| Rückgabe beider | `dict` oder `None` | `Run` oder `None` |

`apify_provider.py` ruft beide mit den alten Namen auf (Zeilen 189 und 201).
Unter 3.1.1 stiege der Lauf mit einem `TypeError` aus, bevor überhaupt eine
Anfrage rausgeht.

### 6.4 K2 — der Nachweis

Ein Lauf über **100 Kunden** im Modus B, Google nicht erreichbar
(`requests.RequestException` bei jedem Aufruf). Fixture-Nummern, keine echten
Kunden.

| Messung | vorher (Stand v1.1) | jetzt |
|---|---|---|
| Aufrufe an Google | 100 | **11** |
| Zustand des Jobs | `FERTIG` | **`FEHLER`** |
| Kunden in der Datenbank | 100 | **9** |
| davon mit dem Grund «gelöscht» | **100** | **0** |
| Ausgabedateien | vier, darin 100 Kunden in ③ | **keine** |
| Meldung an den Nutzer | keine | siehe unten |

Der Grund, den der Sachbearbeiter vorher gelesen hätte:

> Zur gespeicherten Google-ID gibt es keinen Eintrag mehr. Der Betrieb wurde
> bei Google gelöscht oder durch einen neuen Eintrag ersetzt.

Hundertmal, über intakte Kunden, weil das Netz weg war.

Der Grund, der jetzt bei den neun Kunden steht:

> Die Abfrage bei Google ist fehlgeschlagen; dieser Betrieb wurde nicht
> geprüft. Ob der Eintrag noch besteht, ist damit offen — bitte den Kunden
> später noch einmal auffrischen.

Und die Meldung, die in `job.fehlermeldung` landet und damit auf der
Ergebnisseite und in der Mail erscheint:

> Google ist nicht erreichbar. Meistens liegt es an der Internetverbindung
> dieses Rechners. Bitte die Verbindung prüfen und den Lauf danach fortsetzen —
> die bereits verarbeiteten Kunden bleiben erhalten.

### 6.5 Was `fetch_by_id` jetzt wann tut

| Fall | Verhalten | Test |
|---|---|---|
| HTTP 404 | `None` → ③ `NICHT_MOEGLICH (ID ungueltig)`, «gelöscht oder ersetzt» | `test_unbekannte_id_bleibt_ein_geloeschter_eintrag` |
| HTTP 400 mit `NOT_FOUND` im Rumpf | dasselbe | `test_not_found_im_rumpf_zaehlt_auch` |
| Netzfehler, Zeitüberschreitung | `QuelleNichtVerfuegbar`, **nicht** endgültig | `test_netzfehler_ist_kein_geloeschter_kunde` |
| HTTP 500, 502, 503, 504 | `QuelleNichtVerfuegbar`, **nicht** endgültig | `test_stoerung_bei_google_ist_voruebergehend` |
| HTTP 401, 403, 429 | `QuelleNichtVerfuegbar`, **endgültig** — Lauf stoppt sofort | `test_schluessel_und_kontingent_stoppen_sofort` |
| Antwort ist kein JSON | `QuelleNichtVerfuegbar`, nicht endgültig | `test_unlesbare_antwort_ist_voruebergehend` |
| HTTP 200 mit leerem Datensatz | `QuelleNichtVerfuegbar`, nicht endgültig | `test_leerer_datensatz_ist_kein_geloeschter_kunde` |
| Leere Id in der Eingabe | `None`, ohne Abruf — unverändert | `test_google_leere_id_fragt_gar_nicht_erst` |

Die Gegenprobe im ganzen Lauf: `test_geloeschte_id_bleibt_im_lauf_ein_ergebnis`
— eine wirklich unbekannte Id ergibt weiterhin `FERTIG`, eine Zeile in ③,
`NICHT_MOEGLICH (ID ungueltig)`, Grund mit «gelöscht». K2 hat den Normalfall
nicht mitgenommen.

Alle acht Meldungstexte sind deutsch, in Schweizer Schreibweise, mit einer
Handlungsanweisung und ohne englisches Zitat von Google. Geprüft in den Tests
(`'ß' not in …`, `'Bitte' in …`).

---

## 7. Für die nächste Phase

- **Der 180-Sekunden-Wächter, letzter Fund in Abschnitt 5.** Er ist der einzige
  verbliebene Weg, auf dem ein nicht geprüfter Kunde im Modus B als «gelöscht»
  herauskommen kann. Ich habe ihn nicht angefasst, weil `03 C` ihn ausdrücklich
  regelt und `03` Vorrang hat. Wenn der Prüfer es anders will, ist der Eingriff
  klein: `_mit_frist` müsste unterscheiden, ob `None` von einem erfolgreichen
  Abruf kommt oder von einem Fehlschlag, und im zweiten Fall `Ausgefallen()`
  liefern — der Weg dahin steht seit dieser Runde.
- **`apify-client` bleibt auf 2.0.0 stehen.** Ein Sprung auf 3.x ist kein
  `pip install`, sondern ein Umbau von `apify_provider.py`: zwei Aufrufe mit
  neuen Parameternamen und `timedelta` statt Sekunden, dazu `Run`-Objekte statt
  `dict`. Messung in 6.3. Eigene Runde, wenn er kommen soll.
- **Phase 8 ist die letzte.** Danach ist der Rückweg von Datei ② geschlossen.
- **Der Aufräumvorschlag steht weiterhin:** `logger_config.py`,
  `csv_processor.py`, `csv_postprocessor.py`, `clean_input_data.py`,
  `data_cleaner.py.bak`. Eine Runde nach Phase 8, eine Entscheidung je Datei.
- **Unverändert beim Auftraggeber:** SMTP-Freigabe durch die ICT, ein echter
  Versand über das Firmen-Relais, und der Live-Abruf für Modus B.
- **Zur Kenntnis genommen:** `origin/main` steht auf `eb75e26` und trägt
  Änderungen, die noch nicht freigegeben sind (Abschnitt 4 des Korrekturplans).
  Ich habe `main` nicht angefasst; diese Runde liegt vollständig auf
  `umbau/webapp`.

---

## 8. Zeit

| Arbeitspaket | grober Aufwand |
|---|---|
| Korrekturplan einlesen, Stand sichten | 0.25 h |
| K1 a: Unterklasse, Gegenprobe unter 3.1.1 | 0.5 h |
| K1 b: zwölf Fassungen ermitteln und festnageln, 3.1.1 nachmessen | 0.5 h |
| K2: `google_provider`, `modus_b`, `pipeline` | 1.0 h |
| Tests (14 neu, 1 umgestellt) | 0.75 h |
| Nachweis mit 100 Kunden, fünf Testläufe | 0.5 h |
| Findings | 0.5 h |
| **gesamt** | **≈ 4.0 h** |

Der Aufwand steckte diesmal weniger im Code als im Nachmessen. Der Prüfer hatte
recht, dass der Nachweis an einer Bibliotheksfassung hing — und beim Nachmessen
stellte sich heraus, dass dieselbe Fassung nicht nur den Test trägt, sondern den
ganzen Apify-Zugriff. Ohne K1 b wäre der nächste frische Rechner mit einem
`TypeError` in `apify_provider.py` gestartet.
