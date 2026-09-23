# Findings — Korrekturrunde 1 (vor dem Produktivbetrieb), Version 1.0

Datum: 23.09.2026
Bearbeitet: Runde 1 aus der Vorab-Prüfung für den Produktivbetrieb — nur
Punkte ohne Fachentscheidung. Die Fachlogik (`data_cleaner.py`, `modus_b.py`,
`pipeline.py`) ist **nicht angefasst**.
Status: fertig

---

## 1. Kriterien dieser Runde

Jeder Punkt wurde vorher an einer Kopie des Repos nachgestellt (erfundene
Daten und Fixture) und ist jetzt durch einen Test belegt.

| # | Befund vorher | Status | Beleg |
|---|---|---|---|
| 1 | Zwei Uploads mit gleichem Dateinamen teilen einen Ergebnisordner. Job 1 lieferte nach Job 2 dessen Kunden; ein Prüfentscheid in Job 1 überschrieb `fertig_fuer_erp.csv` von Job 2 (900006/900010 → 900001–900005). Ein neuer Upload überschrieb auch die Eingabe eines offenen Jobs | grün | `test_gleicher_dateiname_ueberschreibt_keinen_anderen_auftrag`, `test_pruefentscheid_schreibt_nur_in_den_eigenen_auftrag`, `test_neuer_upload_ueberschreibt_nicht_die_eingabe_eines_offenen_auftrags` |
| 3 | Apify-Lauf mit Status ≠ `SUCCEEDED` (z. B. `TIMED-OUT` nach 175 s) galt als «nichts gefunden». Alle 30 Kunden in ③, Job `FERTIG`, der Zähler für zehn Fehlschläge griff nie | grün | `test_unvollendeter_apify_lauf_ist_ein_fehlschlag` (4 Status), `test_lauf_mit_lauter_zeitueberschreitungen_endet_nicht_als_fertig`; Gegenprobe `test_erfolgreicher_leerer_lauf_bleibt_nichts_gefunden` |
| 4 | `python webapp.py` (README, täglicher Gebrauch) startete im Probebetrieb mit leeren Antworten: alle Kunden in ③, «Fertig», kein Hinweis | grün | `test_start_ohne_angaben_ist_echter_betrieb`, `test_probebetrieb_ohne_antwortdatei_startet_nicht`, `test_probebetrieb_steht_auf_jeder_seite` |
| 6 | Doppelklick auf «Auftrag fortsetzen»: zwei Worker am selben Job, 12 von 40 Kunden doppelt abgefragt, Ende mit `UNIQUE constraint failed …` auf der Ergebnisseite | grün | `test_doppelklick_auf_fortsetzen_fragt_niemanden_doppelt_ab` (40 Abfragen für 40 Kunden, `FERTIG`), `test_worker_weist_zweites_fortsetzen_desselben_auftrags_ab` |
| — | Doppelte/leere `KundenNr` fielen im Web ohne Hinweis aus allen drei Dateien | grün | `test_upload_warnt_vor_doppelten_und_leeren_kundennummern` |
| — | Fehlende `config.py`/`.env`: Fehlerseite sprach von einem laufenden Auftrag, obwohl keiner lief | grün | `test_fehlende_zugangsdaten_sagen_was_fehlt` (2 Fälle) |
| — | CLI: gestoppter Lauf endete mit `TypeError`-Stacktrace; nach Strg+C empfahl sie `fortsetzen`, das nicht geht | grün | `test_cli_gestoppter_lauf_ohne_stacktrace` |
| — | Prüfmaske: gehaltene Zifferntaste konnte den nächsten Fall mitentscheiden | grün | `test_pruefmaske_ignoriert_gehaltene_tasten` |
| — | Lesefehler beim Upload nannte «CSV» statt «CSV UTF-8» | grün | `test_upload_fehler_nennt_csv_utf8` |
| — | Wächter: Fachlogik unverändert | grün | `test_algorithmus_unveraendert_auf_der_fixture` — die zehn Fixture-Kunden landen wie in `05_TESTDATEN.md` |

Testlauf: **411 grün**, 1 übersprungen (vorher 383 + 1). Kein Test entfernt.

---

## 2. Geänderte und neue Dateien

| Datei | neu / geändert | Was |
|---|---|---|
| `worker.py` | geändert | `starten(..., ablage=)` verschiebt die Eingabe nach `auftrag_<Nummer>/`; `_LAUFENDE_JOBS` verhindert zwei Threads am selben Job |
| `webapp.py` | geändert | Upload zuerst in `uploads/eingang/`; `eingabedatei(job)` und `ergebnisordner(job)` hängen am Job, mit Rückfall auf den alten Ort; Start ohne Angaben = echt; Probebetrieb-Hinweis; Seite «Die Zugangsdaten fehlen»; Doppelklick auf Starten/Fortsetzen führt zum laufenden Auftrag |
| `apify_provider.py` | geändert | Status ≠ `SUCCEEDED`, fehlende Lauf-Nummer, unlesbarer Datensatz → `QuelleNichtVerfuegbar(endgueltig=False)`; nicht aufgebauter Client → endgültig. Nach Abbruch durch den Nutzer weiterhin leere Liste |
| `upload_pruefung.py` | geändert | Hinweise `kundennr_leer`, `kundennr_doppelt` (warnen, blockieren nicht) |
| `cli.py` | geändert | `FEHLER` und `ABGEBROCHEN` ehrlich gemeldet, Zahl aus der Datenbank; «CSV UTF-8» |
| `templates/grundgeruest.html` | geändert | Hinweis «Probebetrieb» |
| `templates/pruefung_fall.html` | geändert | `event.repeat` wird ignoriert |
| `README.md` | geändert | Start = echter Betrieb, Windows-Befehle, `SMTP_TLS`, CSV-UTF-8, Kundennummern, Excel/`cid`, Port-Freigabe beschränken, Ordner je Auftrag |
| `test_phase2_abnahme.py` | geändert | ein Test drückte das alte Verhalten aus (Status `RUNNING` → leere Liste); jetzt: Abbruch bei Apify **und** Fehlschlag |
| `test_phase8_abnahme.py` | geändert | Hilfsfunktion `ordner_von` sucht den Ordner über den Job |
| `test_korrekturrunde1_abnahme.py` | neu | 28 Tests dieser Runde |

---

## 3. Getroffene Annahmen

| Situation | Entscheidung | Warum |
|---|---|---|
| Wo der Ordner je Auftrag liegt | `uploads/auftrag_<Nummer>/<datei>.csv`, Ergebnis daneben in `<datei>_ergebnis/` | Datenvertrag §2 («Ordner neben der Eingabedatei») bleibt wörtlich erfüllt; kein neues DB-Feld nötig (§5 bleibt unverändert) |
| Alte Jobs ohne eigenen Ordner | Rückfall auf `uploads/<datei>` | Bestehende Ergebnisse bleiben herunterladbar |
| Leere/doppelte Kundennummer | Warnung, keine Abweisung | `03 D`: nur Pflichtspalte und Zeilenobergrenze blockieren |
| `--quelle fake` ohne `--antworten` | Start verweigert | Ein Probebetrieb ohne Antworten erzeugt nur ③ — kein sinnvoller Zustand |
| Nicht aufgebauter Apify-Client | endgültiger Fehler | Jeder weitere Kunde schlüge genauso fehl |

---

## 4. Abweichungen von den Vorgaben

| Vorgabe | Abweichung | Warum |
|---|---|---|
| `KORREKTURPLAN_PHASE_7.md` §2: «Nicht anfassen: … der Pfad `status != 'SUCCEEDED'`» | angefasst | Geschrieben **vor** der Änderung von `03 C` in Phase 7 v1.2 («eine Zeitüberschreitung ist keine Antwort»). Da der Provider nach 175 s vor der 180-s-Frist des Laufs entscheidet, griff die neue Regel für Apify nie. `03` schlägt den Korrekturplan. Bitte bestätigen |

---

## 5. Gefunden, nicht behoben (Runde 2 — braucht Entscheidung)

| Fund | Stelle | Auswirkung |
|---|---|---|
| Einzeltreffer an **anderer** Strasse geht nach ① (`OK (Einzeltreffer)`), sobald der Name ≥ 60 ist; der Grund erwähnt die Strasse nicht. Zwei solche Treffer gehen dagegen nach ② | `data_cleaner.py` `_decide_single_hit`, Regel `03 B2` | mögliche falsche Adresse in ① — Änderung der Regel `03 B2` nötig |
| «Fortsetzen» nur nach Absturz (`LAEUFT`), nicht nach `FEHLER`/`ABGEBROCHEN` — Ergebnisseite, Mail, README und Meldungstexte versprechen es. «Lauf abbrechen» ohne Rückfrage | `db.py` `offener_job`, `02 §6` | Nach aufgebrauchtem Guthaben muss der ganze Lauf neu (und neu bezahlt) laufen |
| `scrapeContacts: True` kostet, aber keine E-Mail-/Social-Spalte erreicht die Ausgabe | `apify_provider.py` | Kosten und Laufzeit ohne Nutzen — Entscheidung Auftraggeber |
| Öffentliches Repo: Kundenname des Auftraggebers in `WORKFLOW_AND_HANDOFF.md`; `Emil Frey AG, KST 715611 0, 5745 Safenwil` wirkt wie ein echter ERP-Datensatz | Doku, Tests | `05_TESTDATEN.md` — Husey entscheidet |

---

## 7. Für die nächste Runde

- Offen beim Auftraggeber (aus `FREIGABE_PHASE_4.md`, nicht mehr in der
  Schlussliste): Speichergrenze des Apify-Kontos prüfen — Laufzeit sonst rund
  12 Stunden je 2'513 Kunden.
- Nach Runde 2: Pilotlauf mit rund 100 echten Kunden, Stichprobe aus ① von Hand.

---

## 8. Zeit

Nachstellen 1 h, Umsetzung und Tests 2 h.
