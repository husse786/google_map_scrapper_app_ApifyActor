# Findings — Phase 6, Version 1.0

Datum: 04.08.2026
Bearbeitete Phase: 6 — Modus B (placeId)
Status: fertig mit Vorbehalt

Testlauf: `python -m pytest` → **241 grün, 1 übersprungen**, fünfmal
hintereinander (15.45 / 14.12 / 13.81 / 13.71 / 13.79 s). Aufteilung:
8 + 40 + 51 + 20 + 40 + 36 aus den Phasen 1 bis 5, **47 neu**.

Zusätzlich im echten Browser durchgespielt, wie in der Freigabe zu Phase 5
verlangt.

> **Der Vorbehalt:** Es gibt keinen Google-Schlüssel. Alle sieben
> Abnahmekriterien sind erfüllt und belegt, aber **kein einziger echter Aufruf
> an Google** wurde gemacht. Was das heisst und was noch aussteht, steht in
> Abschnitt 5.

---

## 1. Abnahmekriterien

| # | Kriterium | Status | Beleg |
|---|---|---|---|
| 1 | Gültige ID → ① mit `OK (ID)` | grün | `test_gueltige_id_geht_nach_eins`, `test_gueltige_id_mit_passender_position_geht_nach_eins`. Im Browser bestätigt: zwei von vier Kunden landen in ①. |
| 2 | Unbekannte ID → ③ mit `NICHT_MOEGLICH (ID ungueltig)` | grün | `test_unbekannte_id_geht_nach_drei`. Die gesuchte Id steht trotzdem in der Ausgabezeile, damit sie im ERP auffindbar bleibt. Dazu `test_fehlende_id_in_der_eingabe_geht_nach_drei` für die leere Zelle. |
| 3 | `permanentlyClosed` → ② mit verständlichem Grund | grün | `test_dauerhaft_geschlossen_geht_nach_zwei` prüft den Wortlaut: «Google meldet den Betrieb als dauerhaft geschlossen: …» — genau die Formulierung aus `02_DATENVERTRAG.md` §4. |
| 4 | Position 1.4 km entfernt → ②; Position 150 m entfernt → ① | grün | `test_position_1400_meter_entfernt_geht_nach_zwei` (Text enthält «1.4 km»), `test_position_150_meter_entfernt_geht_nach_eins`. Die Grenze selbst in `test_die_grenze_liegt_bei_200_metern` mit fünf Abständen. `test_haversine_rechnet_richtig` prüft die Formel gegen eine bekannte Strecke. |
| 5 | Fehlende `lat`/`lng` → keine Distanzprüfung, kein Prüffall | grün | `test_ohne_position_keine_distanzpruefung` mit vier Varianten (beide leer, eine leer, unlesbar). Auch wenn der Betrieb 150 km entfernt liegt: ohne Vergleichspunkt kein Prüffall. Dazu der Fall, dass Google keinen Standort liefert. |
| 6 | Namensänderung allein löst **keinen** Prüffall aus | grün | `test_namensaenderung_ist_kein_prueffall` (aus Volg wird Spar), `test_auch_eine_andere_adresse_am_selben_ort_ist_kein_prueffall`. |
| 7 | Beide Modi schreiben identisch aufgebaute Ausgabedateien | grün | `test_beide_modi_schreiben_dieselben_spalten` lässt beide Modi laufen und vergleicht die Spaltenlisten gegen `OUTPUT_COLUMNS`. `test_jede_zeile_traegt_score_und_grund` prüft, dass keine Pflichtspalte leer bleibt. |

---

## 2. Geänderte und neue Dateien

| Datei | neu / geändert | Was |
|---|---|---|
| `modus_b.py` | neu | Die Entscheidung nach `03_ENTSCHEIDUNGEN.md` B4: Haversine, 200 Meter, geschlossen, ungültige Id. Kein Scoring. 200 Zeilen. |
| `google_provider.py` | neu | Places API (New), Endpunkt Place Details. Neben `apify_provider.py` das einzige Modul, das Feldnamen einer Datenquelle kennt. |
| `pipeline.py` | geändert | `Lauf` kennt jetzt einen Modus. Modus B holt über die Id statt über den Text und entscheidet über `modus_b`. Der Timeout wurde in `_mit_frist()` herausgezogen, damit beide Wege dieselbe Frist nutzen. |
| `worker.py` | geändert | Modus wird durchgereicht und im Job gespeichert. |
| `upload_pruefung.py` | geändert | Pflichtspalten je Modus; im Modus B entfallen die beiden inhaltlichen Prüfungen. |
| `webapp.py` | geändert | Zweiter Einstieg, Modus wird beim Hochladen mitgeführt, Datenquelle je Modus, Kacheltexte je Modus. |
| `cli.py` | geändert | `--modus A|B`, `--quelle echt` wählt Apify oder Google je nach Modus. |
| `templates/art_waehlen.html`, `templates/datei.html` | geändert | Zweite Kachel entsperrt, Hinweistext je Modus. |
| `config.template.py` | geändert | `GOOGLE_API_KEY`. |
| `test_phase6_abnahme.py` | neu | 47 Tests. |
| `test_phase5_abnahme.py` | geändert | Der Test, der «Modus B ist noch nicht verfügbar» prüfte, prüft jetzt das Gegenteil. |
| `README.md` | geändert | Die beiden Arten erklärt. |

`data_cleaner.py` wurde nicht angefasst — Modus B geht am Scoring vorbei.

---

## 3. Getroffene Annahmen

| Situation | Entscheidung | Warum |
|---|---|---|
| Welchen Wert bekommt `score` im Modus B? | **100** sobald die Id auflöst, **0** wenn nicht. | Der Datenvertrag verlangt einen befüllten Wert in jeder Zeile (§2), aber im Modus B gibt es nichts zu schätzen: die Id **ist** die Identität. 100 heisst hier «der Betrieb ist zweifelsfrei derselbe» — auch bei einem Prüffall, denn der betrifft Öffnung und Standort, nicht die Identität. |
| Geschlossen **und** weit weg | Die Schliessung gewinnt. | `03` B4 nennt sie zuerst, und sie ist die wichtigere Auskunft: ein geschlossener Betrieb muss nicht umgezogen sein, er ist einfach weg. `test_geschlossen_schlaegt_die_entfernung`. |
| Genau 200 Meter Abstand | Zählt noch als «am selben Ort». | `03` B4 sagt «Distanz > 200 m» — grösser, nicht grösser gleich. |
| `temporarilyClosed` | Kein Prüffall. | `03` B4 nennt ausdrücklich nur die dauerhafte Schliessung. Ein Betrieb in den Betriebsferien ist kein Fall für den Sachbearbeiter. |
| `SearchString`, `PLZ`, `Stadt` in der Ausgabe des Modus B | Bleiben leer. | Diese Spalten gibt es in der Eingabe des Modus B nicht. Der **Aufbau** der Datei ist identisch, wie verlangt; der Inhalt kann es nicht sein. |
| Welche Google-Schnittstelle? | Places API (New), `GET /v1/places/{id}` mit Feldmaske. | Die alte Place Details API ist für neue Projekte abgekündigt. Die Feldmaske holt nur die Felder aus dem Datenvertrag — jedes weitere Feld kostet Geld, ohne dass es jemand liest. |
| `cid` im Modus B | Bleibt leer. | Die Places API liefert keine cid. Nur Apify kennt sie. |
| Schreibweise von `location` | Wie bei Apify: `{'lat': 47.35, 'lng': 8.24}`. | «Identisch aufgebaute Ausgabedateien» heisst auch, dass dieselbe Spalte gleich aussieht — sonst stolpert der ERP-Import über den Modus. |
| Timeout für Google | 30 Sekunden statt 180. | Ein Direktabruf über die Id antwortet in Sekundenbruchteilen; 180 Sekunden wären keine Notbremse, sondern eine Einladung zum Hängen. Die 180 aus `03` C sind für den Apify-Actor gemessen, der eine Suche ausführt. **Falls der Prüfer das anders sieht, ist es eine Zeile.** |
| Beim Fortsetzen: welcher Modus? | Der aus dem Job, nicht der des Aufrufers. | Ein Lauf arbeitet weiter, wie er begonnen hat. `test_fortsetzen_uebernimmt_den_modus_aus_dem_job`. |
| Texte der Ergebniskacheln | Je Modus verschieden. | «Mehrere mögliche Treffer — Sie entscheiden» ist im Modus B schlicht falsch: dort gibt es nie mehrere Treffer. Aufgefallen beim Ansehen im Browser. |
| `--quelle apify` heisst jetzt `--quelle echt` | Umbenannt. | Mit zwei echten Datenquellen ist «apify» kein sinnvoller Name mehr für «nicht die Testantworten». Die Wahl fällt jetzt über den Modus. |

---

## 4. Abweichungen von den Vorgaben

Keine. Die Werte aus `03_ENTSCHEIDUNGEN.md` B4 — 200 Meter, Haversine, die vier
Fälle und ihre Zuordnung — stehen so im Code. Die Spalten und die
`qualitaet`-Werte `OK (ID)`, `PRUEFUNG (geschlossen)`,
`PRUEFUNG (Standort abweichend)` und `NICHT_MOEGLICH (ID ungueltig)` stammen
wörtlich aus `02_DATENVERTRAG.md` §3.

---

## 5. Was gefunden wurde

| Fund | Auswirkung | eingegriffen? |
|---|---|---|
| **Kein Google-Schlüssel vorhanden.** Weder in `.env` noch in `config.py`. | Der `GoogleProvider` ist gegen aufgezeichnete Antworten geprüft: Umwandlung in `Candidate`, Feldmaske, Schlüssel im Kopf, 404, Netzfehler, leere Id, fehlender Schlüssel. **Nicht geprüft ist, ob eine echte Google-Antwort so aussieht, wie ich sie nachgebildet habe.** Genau dieser Punkt hat in Phase 3 zugeschlagen, als sich der Apify-Aufrufweg änderte. Zu tun steht in Abschnitt 7. | nein — ohne Schlüssel nicht möglich. `aus_konfiguration()` meldet das in Klartext statt mit einem Stacktrace |
| **Die Ergebniskacheln erklärten den falschen Modus.** «Mehrere mögliche Treffer — Sie entscheiden» stand auch nach einem Modus-B-Lauf da, obwohl es dort nie mehrere Treffer gibt. | Aufgefallen beim Ansehen im echten Browser, nicht im Test — dieselbe Lehre wie beim englischen «Choose File» in Phase 5. | ja, Texte je Modus |
| Der Timeout lag zweimal im Code | `_kandidaten_holen` trug die Frist-Schleife inline; für den zweiten Weg hätte ich sie kopieren müssen. Jetzt liegt sie in `_mit_frist()`, beide Wege teilen sie. | ja |
| `03_ENTSCHEIDUNGEN.md` B4 lässt die Reihenfolge offen | Was gilt, wenn ein Betrieb geschlossen **und** umgezogen ist? Die Tabelle nennt beides, ohne Vorrang. | nein — Annahme getroffen und in Abschnitt 3 vermerkt |
| Der Umbauplan nennt eine offene Frage zum Datenschutz | «Gmail-Konto für Firmendaten zulässig? — ICT / Datenschutz, vor Produktivbetrieb Modus B» (`UMBAUPLAN_WEBAPP.md` §8). Diese Frage ist mit dieser Phase nicht beantwortet und blockiert den produktiven Einsatz von Modus B, nicht seinen Bau. | nein — gemeldet |

---

## 6. Messwerte

### 6.1 Modus B im Browser

Vier erfundene Kunden gegen die Fixture als Datenquelle, über die Oberfläche
hochgeladen und gestartet:

| Kunde | Eingabe | Ergebnis |
|---|---|---|
| 900001 | Id bekannt, Position stimmt | ① `OK (ID)`, «Standort stimmt, Abweichung 0 m» |
| 900010 | Id bekannt, **keine** Position | ① `OK (ID)`, «keine Angabe zum Vergleichen» |
| 900005 | Id bekannt, Position 26.7 km entfernt | ② `PRUEFUNG (Standort abweichend)` |
| 900099 | Id unbekannt | ③ `NICHT_MOEGLICH (ID ungueltig)` |

Verteilung auf der Ergebnisseite: **2 / 1 / 1**. Jede Zeile trägt `score` und
einen deutschen Klartextgrund, die Datei beginnt mit dem BOM und trennt mit
Semikolon.

### 6.2 Die Grenze von 200 Metern

Gemessen mit einer Position, die schrittweise nach Norden verschoben wird:

| Abstand | Ergebnis |
|---|---|
| 0 m | ① |
| 199 m | ① |
| 200 m | ① |
| 201 m | ② |
| 5'000 m | ② |
| 1'400 m | ② mit dem Text «1.4 km» |
| 150 m | ① mit dem Text «150 m» |

Die Haversine-Formel gegengeprüft: ein Grad Breite ergibt 111'195 Meter, der
Lehrbuchwert liegt bei rund 111'320 — 0.1 % Abweichung, weil die Formel eine
Kugel annimmt statt eines abgeplatteten Ellipsoids. Bei einer 200-Meter-Grenze
sind das 20 Zentimeter.

### 6.3 Umfang

| | |
|---|---|
| `modus_b.py` | 200 Zeilen |
| `google_provider.py` | 190 Zeilen |
| Änderungen an `pipeline.py` | rund 60 Zeilen, davon die Hälfte der herausgezogene Timeout |
| Tests | 47 neu |

---

## 7. Für die nächste Phase

- **Der eine offene Punkt: ein echter Google-Aufruf.** Sobald ein Schlüssel in
  `.env` steht, genügt ein einziger Kunde:
  `python cli.py lauf <datei.csv> --modus B --quelle echt`.
  Zu belegen wäre dasselbe wie bei Apify in Phase 2 und 3: der Abruf gelingt,
  alle Felder sind befüllt, die Entscheidung stimmt, und `businessStatus`
  kommt so an, wie `modus_b` ihn erwartet. **Ohne diesen Nachweis würde ich
  Modus B nicht produktiv einsetzen** — die Umwandlung ist gegen meine
  Nachbildung geprüft, nicht gegen Google.
- **Vor dem Produktivbetrieb zu klären** (nicht durch mich): ob ein privates
  Gmail-Konto für Firmendaten zulässig ist, und dass für Google eine Kreditkarte
  hinterlegt sein muss — beides steht in `UMBAUPLAN_WEBAPP.md` §8 und ist
  weiterhin offen.
- **Für Phase 7 (Mail):** Modus B dauert Minuten statt Stunden. Die Mail ist
  dort Komfort, im Modus A ist sie der Ablauf. Wer die Texte schreibt, sollte
  das unterscheiden.
- **Für Phase 8 (Prüfmaske):** Modus-B-Prüffälle haben genau **einen**
  Kandidaten und einen klaren Grund — geschlossen oder umgezogen. Die Maske
  braucht dafür keine Kandidatenauswahl, sondern zwei Knöpfe: übernehmen oder
  verwerfen. Das ist ein anderer Fall als die Modus-A-Prüfung mit mehreren
  Treffern, und er ist einfacher.
- **`kunde.place_id`, `lat` und `lng` sind jetzt gefüllt** (§5). Die Prüfmaske
  kann daraus zeigen, wie weit ein Betrieb sich bewegt hat.

---

## 8. Zeit

| Arbeitspaket | grober Aufwand |
|---|---|
| Freigabe und Phase-6-Umfang einlesen | 0.25 h |
| `modus_b.py` mit Haversine und den vier Fällen | 1.0 h |
| `google_provider.py` | 1.0 h |
| Modus durch Lauf, Worker, Prüfung, Oberfläche und Kommandozeile ziehen | 1.5 h |
| Tests (47 neu) | 2.0 h |
| Durchgang im echten Browser | 0.5 h |
| Findings | 0.75 h |
| **gesamt** | **≈ 7 h** |

Die Fachlogik von Modus B ist in einem Nachmittag geschrieben — sie umfasst
vier Regeln. Der Aufwand lag darin, den Modus sauber durch eine Kette zu
ziehen, die für einen einzigen Modus gebaut war, ohne dabei etwas an Modus A
zu verändern. Dass das gelungen ist, zeigen die 194 Tests der früheren Phasen,
die weiterhin grün sind — angefasst wurde davon genau einer, und der prüfte,
dass Modus B noch nicht verfügbar ist.
