# Findings — Phase 7, Version 1.1

Datum: 04.08.2026
Bearbeitete Phase: 7 — Mail und Härtung, Korrekturrunde nach
`KORREKTURPLAN_PHASE_7.md`
Status: fertig

Umfang dieser Runde: **K1 und K2**. Sonst nichts.

Testlauf: `python -m pytest` → **283 grün, 1 übersprungen**, fünfmal
hintereinander (Abschnitt 6.1).

---

## 1. Abnahmekriterien

### Die zwei Punkte des Korrekturplans

| # | Punkt | Status | Beleg |
|---|---|---|---|
| K1 | Unbekannte Apify-Fehler landen nicht mehr stillschweigend in ③ | grün | `apify_provider.py` reicht jeden nicht gelisteten `ApifyApiError` als `QuelleNichtVerfuegbar(endgueltig=False)` weiter. Nachweis mit 2'500 Kunden in Abschnitt 6.2, dazu sechs Tests. |
| K2 | Beschreibung widerspricht dem Verhalten | grün | Der Text von `fetch_by_text` sagt jetzt, was gilt: eine leere Liste heisst «nichts gefunden», ein Fehler von Apify kommt als Ausnahme. `test_beschreibung_passt_zum_verhalten` hält fest, dass die alte Aussage nicht zurückkommt. |

### Die vier Kriterien der Phase

Unverändert grün. An Mailversand, Fehlertexten und README wurde in dieser Runde
nichts geändert; die Belege stehen in `FINDINGS_PHASE_7.md` Abschnitt 1.

---

## 2. Geänderte Dateien

| Datei | Was | Punkt |
|---|---|---|
| `apify_provider.py` | Nach `_pruefen_ob_endgueltig` folgt `raise QuelleNichtVerfuegbar(UNBEKANNTE_MELDUNG, endgueltig=False)` statt `return []`. Neue Meldung mit Handlungsanweisung. Beschreibung von `fetch_by_text` und Kopfkommentar richtiggestellt. | K1, K2 |
| `pipeline.py` | Eine Protokollzeile: die Zwischenmeldung sagte «Der Lauf wurde gestoppt», obwohl er weiterlief. Siehe Abschnitt 5. | K1 |
| `test_phase7_abnahme.py` | Sechs Tests dazu. | K1, K2 |

Nicht angefasst, wie verlangt: die sechs Fehlerarten, die sieben Stichwörter,
die Grenze von zehn, der Pfad `status != 'SUCCEEDED'`, `mail.py`, `README.md`.

---

## 3. Getroffene Annahmen

| Situation | Entscheidung | Warum |
|---|---|---|
| Was steht in der Meldung für einen unbekannten Fehler? | Nur deutscher Text mit Handlungsanweisung. Was Apify wörtlich geschrieben hat, steht ausschliesslich im Protokoll. | Apify schreibt englisch. Diese Meldung landet in `job.fehlermeldung`, also auf der Ergebnisseite und in der Mail — dort gilt seit Phase 5 «keine englische Zeichenkette in der Oberfläche». Der Test prüft, dass «Too many requests» nicht in der Meldung steht. |
| Ist ein unbekannter Fehler endgültig oder vorübergehend? | Vorübergehend. | So im Korrekturplan vorgegeben. Wir wissen nicht, was der Fehler bedeutet — ihn sofort als endgültig zu behandeln, würde einen Lauf bei einem einmaligen Ausrutscher töten. Nach zehn hintereinander ist die Frage beantwortet. |
| Neun Kunden landen vor dem Stopp in ③ | Bleibt so. | Ausdrücklich im Korrekturplan: «Ein einzelner Ausrutscher kostet weiterhin nur einen Kunden.» Der Unterschied zu vorher ist neun statt 2'500 — und der Lauf sagt es, statt sich `FERTIG` zu nennen. |

---

## 4. Abweichungen von den Vorgaben

Keine.

---

## 5. Was gefunden wurde

| Fund | Auswirkung | eingegriffen? |
|---|---|---|
| **Die Zwischenmeldung im Protokoll war falsch.** Beim ersten bis neunten Fehlschlag wurde die Nutzermeldung protokolliert — und die sagt «Der Lauf wurde gestoppt», obwohl er weiterlief. Neun Zeilen «gestoppt» in einem Protokoll, in dem der Lauf weitergeht. | Aufgefallen beim Nachrechnen für Abschnitt 6.2, nicht durch einen Test. Wer das Protokoll liest, um einen Fehler zu suchen, wird in die Irre geführt. | ja: die Zwischenzeile nennt jetzt nur die Tatsache («Abfrage gescheitert, 3 von 10 hintereinander. Dieser Kunde gilt als ohne Ergebnis, der Lauf macht weiter.»), die Nutzermeldung steht nur noch beim tatsächlichen Stopp |
| **Dieselbe Lücke steckt in `google_provider.py`.** `fetch_by_id` liefert `None`, wenn Google nicht erreichbar ist oder mit 500 antwortet — genau wie bei einer unbekannten Id. `modus_b` macht daraus ③ mit dem Text «Zur gespeicherten Google-ID gibt es keinen Eintrag mehr. Der Betrieb wurde bei Google gelöscht oder ersetzt.» | Derselbe Fehlertyp wie K1, mit einem Unterschied: die Meldung ist nicht nur unvollständig, sie ist **falsch**. Bei einem Netzausfall sagt die Anwendung dem Sachbearbeiter, seine Kundendaten seien bei Google gelöscht worden. Betroffen ist nur Modus B, und der steht nach `03 B4` unter Produktivsperre — es kann also gerade niemandem schaden. | **nein** — ausserhalb von K1 und K2. Vorschlag in Abschnitt 7 |
| Zwei Commits landeten während eines Testlaufs im Arbeitsbaum | Die Läufe 3 bis 5 eines ersten Fünferblocks sammelten nur 48 statt 284 Tests ein, weil sich die Dateien unter pytest wegbewegten. Kein Produktbefund; die fünf Läufe in Abschnitt 6.1 sind danach am sauberen Baum wiederholt. | — |

---

## 6. Messwerte

### 6.1 Fünf vollständige Testläufe

| Lauf | Ergebnis | Dauer |
|---|---|---|
| 1 | 283 grün, 1 übersprungen | 14.84 s |
| 2 | 283 grün, 1 übersprungen | 14.37 s |
| 3 | 283 grün, 1 übersprungen | 14.46 s |
| 4 | 283 grün, 1 übersprungen | 14.23 s |
| 5 | 283 grün, 1 übersprungen | 14.34 s |

Sechs Tests sind in dieser Runde dazugekommen (277 → 283).

### 6.2 Der Nachweis aus K1

Ein Provider, der bei jedem Aufruf einen `ApifyApiError` der Art
`rate-limit-exceeded` wirft — eine Art, die **nicht** auf der Liste der sechs
endgültigen Fehler steht. Eingabe: 2'500 Kunden.

| Messung | vor der Korrektur (Stand v1.0) | jetzt |
|---|---|---|
| Aufrufe an Apify | 2'500 | **11** |
| Kunden in der Datenbank | 2'500 | **9**, alle `nicht_moeglich` |
| Zustand des Jobs | `FERTIG` | **`FEHLER`** |
| Ausgabedateien | drei, eine davon mit 2'500 Kunden «nichts gefunden» | **keine** |
| Meldung an den Nutzer | keine | siehe unten |

Der Wortlaut, der in `job.fehlermeldung` steht und damit auf der Ergebnisseite
und in der Mail erscheint:

> Apify hat die Anfragen mehrfach hintereinander mit einem Fehler beantwortet,
> den wir nicht einordnen können. Der Lauf wurde gestoppt, damit keine Kunden
> fälschlich als «nichts gefunden» gelten. Bitte es später noch einmal
> versuchen und den Lauf fortsetzen — die bereits verarbeiteten Kunden bleiben
> erhalten. Was Apify gemeldet hat, steht im Protokoll im Ordner logs.

Die Tests dazu:

| Test | Was er festhält |
|---|---|
| `test_unbekannter_apify_fehler_ist_kein_leeres_ergebnis` | Der Aufruf wirft `QuelleNichtVerfuegbar`, `endgueltig=False`, deutsche Meldung ohne Apifys englischen Text |
| `test_unbekannter_apify_fehler_stoppt_den_lauf_nach_zehn` | 2'500 Kunden, 11 Aufrufe, `FEHLER`, keine Dateien |
| `test_ein_einzelner_unbekannter_fehler_kostet_nur_einen_kunden` | Drei Ausrutscher am Anfang: der Lauf kommt durch, die drei liegen in ③ |
| `test_bekannte_arten_stoppen_weiterhin_sofort` | Die sechs Arten aus Phase 7 bleiben endgültig |
| `test_kein_treffer_bleibt_ein_ergebnis` | Gegenprobe: `SUCCEEDED` mit leerem Datensatz liefert weiterhin eine leere Liste |
| `test_beschreibung_passt_zum_verhalten` | K2: die alte, falsche Aussage kommt nicht zurück |

### 6.3 Die Grenzen bleiben, wo sie waren

| Fall | Verhalten |
|---|---|
| Bekannte endgültige Art (Kontingent, Token, Rechte, Actor) | Lauf stoppt beim ersten Auftreten |
| Netzfehler | vorübergehend, Stopp nach zehn hintereinander |
| **Unbekannter Apify-Fehler** | **neu: vorübergehend, Stopp nach zehn hintereinander** |
| Timeout | leeres Ergebnis, Kunde nach ③ — unverändert |
| `SUCCEEDED` mit leerem Datensatz | leeres Ergebnis, Kunde nach ③ — unverändert |

---

## 7. Für die nächste Phase

- **Der Zwilling von K1 in `google_provider.py`.** `fetch_by_id` gibt `None`
  zurück, egal ob die Id unbekannt ist oder Google nicht antwortet. Der
  Sachbearbeiter liest dann «Der Betrieb wurde bei Google gelöscht oder
  ersetzt» — bei einem Netzausfall eine falsche Aussage über seine Daten.
  Dieselbe Behandlung wie in K1 wäre naheliegend: Id unbekannt (404) bleibt ③,
  alles andere wird `QuelleNichtVerfuegbar`. Ich habe es nicht angefasst, weil
  der Umfang dieser Runde K1 und K2 war. Modus B steht ohnehin unter
  Produktivsperre — der richtige Zeitpunkt ist, wenn diese Sperre fällt.
- **Phase 8 ist die letzte.** Danach ist der Rückweg von Datei ② geschlossen.
- **Der Aufräumvorschlag steht weiterhin:** `logger_config.py`,
  `csv_processor.py`, `csv_postprocessor.py`, `clean_input_data.py`,
  `data_cleaner.py.bak` — vier davon hängen zusammen, wie der Prüfer ergänzt
  hat. Eine Runde nach Phase 8, eine Entscheidung je Datei.
- **Unverändert beim Auftraggeber:** SMTP-Freigabe durch die ICT, ein echter
  Versand über das Firmen-Relais, und der Live-Abruf für Modus B.

---

## 8. Zeit

| Arbeitspaket | grober Aufwand |
|---|---|
| Korrekturplan einlesen | 0.25 h |
| K1: unbekannte Fehler weiterreichen, Meldung formulieren | 0.5 h |
| K2: Beschreibung und Kopfkommentar | 0.25 h |
| Tests (6 neu) | 0.75 h |
| Nachweis mit 2'500 Kunden, fünf Testläufe | 0.5 h |
| Findings | 0.5 h |
| **gesamt** | **≈ 2.75 h** |

Die Korrektur selbst war eine Zeile. Der Wert steckt in der Frage dahinter, und
die hat sich beim Nachrechnen gleich noch zweimal gestellt: einmal im
Protokoll, das neun Mal «gestoppt» schrieb, während der Lauf weiterlief, und
einmal in `google_provider.py`, wo derselbe Fehler noch steht.
