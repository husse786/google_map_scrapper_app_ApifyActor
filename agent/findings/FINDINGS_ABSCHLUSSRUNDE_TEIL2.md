# Findings — Abschlussrunde, Teil 2a und Teil 2

Datum: 05.08.2026
Bearbeitete Runde: Abschlussrunde nach `ABSCHLUSSRUNDE.md`, **Teil 2a und Teil 2**
Status: fertig

Reihenfolge wie verlangt: erst Teil 2a (die drei Punkte aus der Abnahme von
Teil 1), danach Teil 2 (die Löschungen).

Testlauf: `venv/bin/python -m pytest` → **383 grün, 1 übersprungen**, fünfmal
hintereinander (Abschnitt 6.1). Fassungen unverändert: `apify-client` 2.0.0,
`thefuzz` 0.22.1.

---

# Teil 2a — die drei Punkte aus der Abnahme

## 1. Abnahmekriterien Teil 2a

| # | Kriterium | Status | Beleg |
|---|---|---|---|
| 1 | `Denner Bremgarten` erscheint nur noch unter «unvollständiger Suchbegriff» | grün | `test_unvollstaendige_zeile_erscheint_nur_einmal`, dazu `test_keine_unvollstaendige_art_wird_als_kostenstelle_gemeldet` für alle vier Arten |
| 2 | `Emil Frey AG, KST 715611 0, 5745 Safenwil` erscheint weiterhin unter «Kostenstelle» | grün | `test_eine_echte_kostenstelle_wird_weiterhin_gemeldet` |
| 3 | Keine Meldung sagt mehr «1 Zeilen» | grün | `test_keine_meldung_sagt_eine_zeilen` über alle drei Hinweismeldungen |
| 4 | Das README beschreibt die Prüfmaske als eigenen Schritt | grün | `test_das_readme_beschreibt_die_pruefmaske_als_eigenen_schritt`, `test_das_readme_sagt_was_die_pruefmaske_tut` |
| 5 | Angepasste Phase-4-Zahlen in den Findings, vorher und nachher | grün | Abschnitt 5a — **die Zahlen haben sich nicht geändert**, und das ist der Befund |

## 2. Geänderte Dateien (Teil 2a)

| Datei | Was |
|---|---|
| `upload_pruefung.py` | `_pruefe_kostenstellen` sieht nur noch vollständige Suchbegriffe an. Singular in beiden Meldungen aus Phase 4. |
| `README.md` | «Der Ablauf, fünf Seiten»; neuer Schritt 5 **Prüfung**; Schritt 4 nennt den Knopf, der hinführt. |
| `test_abschlussrunde_abnahme.py` | 13 Tests für die drei Punkte. |

## 3. Getroffene Annahmen (Teil 2a)

| Situation | Entscheidung | Warum |
|---|---|---|
| Soll auch die **Kategorieprüfung** unvollständige Zeilen überspringen? | Nein. | Der Plan nennt nur die Kostenstellenprüfung, und die Begründung trägt nur dort: Bei `Denner Bremgarten` gibt es kein Strassenfeld, die Aussage ist **falsch**. Der Titelteil dagegen existiert immer — er ist der Text vor dem ersten Komma. «Der Name ist nur eine Branche» bleibt bei `Restaurant` ohne Komma eine wahre Aussage. Eine wahre zweite Aussage zu unterdrücken wäre eine andere Entscheidung als eine falsche zu entfernen. |
| Wo steht die Prüfmaske im README? | Als Schritt **5**, nach «Ergebnis» — nicht zwischen «Lauf» und «Ergebnis», wie der Plan schreibt. | So ist die Anwendung gebaut und seit Phase 8 abgenommen: Der Schrittanzeiger im Seitenkopf lautet *Art wählen · Datei · Lauf · Ergebnis · Prüfung*, und die Maske wird über einen Knopf **auf der Ergebnisseite** erreicht. Ein README, das eine andere Reihenfolge behauptet als der Bildschirm zeigt, führt genau den Nutzer in die Irre, für den es geschrieben ist. Der geforderte Inhalt steht vollständig da. |

## 4. Abweichungen von den Vorgaben (Teil 2a)

| Vorgabe | Abweichung | Warum |
|---|---|---|
| `ABSCHLUSSRUNDE.md` Teil 2a C: «Ein eigener Schritt zwischen „Lauf" und „Ergebnis"» | Der Schritt steht **nach** «Ergebnis». | Siehe Abschnitt 3. Die Anwendung erreicht die Maske von der Ergebnisseite aus; die Reihenfolge im README folgt dem Bildschirm. |

## 5a. Was gefunden wurde (Teil 2a)

| Fund | Auswirkung | eingegriffen? |
|---|---|---|
| **Die Phase-4-Zahlen haben sich nicht geändert.** Der Plan erwartete, dass die Zeilenzahlen in den Phase-4-Tests sich durch das Auflösen der Doppelmeldung verschieben. Kein einziger Phase-4-Test wurde rot. | Alle Suchbegriffe in den Phase-4-Fixtures sind vollständig — `Emil Frey AG, KST 715611 0, 5745 Safenwil`, `Muster AG, KOST 4711, …` und so fort. Die Überschneidung, um die es geht, kam in ihnen schlicht nicht vor. Sie wurde erst durch die neue Prüfung aus Teil 1 sichtbar. | **nein**, nichts anzupassen. Die Zahlen stehen trotzdem in Abschnitt 6.2, vorher und nachher, weil das Kriterium sie verlangt |
| **Der Plan verortet die Prüfmaske anders als die Anwendung.** «zwischen Lauf und Ergebnis» gegen den gebauten Schrittanzeiger *… Ergebnis · Prüfung*. | Beim Schreiben des README aufgefallen. Der Inhalt des Schritts ist derselbe; nur seine Stelle im Ablauf unterscheidet sich. | **ja** — dem Bildschirm gefolgt, in Abschnitt 4 als Abweichung vermerkt |

---

# Teil 2 — toter Code

## 1. Abnahmekriterien Teil 2

| # | Kriterium | Status | Beleg |
|---|---|---|---|
| 1 | Die freigegebenen Dateien sind entfernt | grün | Sieben Stück, Abschnitt 6.3. `test_die_tote_datei_ist_weg` je Datei |
| 2 | Fünf vollständige Läufe | grün | Abschnitt 6.1 |
| 3 | Kein Import zeigt mehr auf eine entfernte Datei | grün | `test_kein_modul_importiert_die_geloeschte_datei` über alle Module des Projekts; zusätzlich alle Einstiegspunkte einmal importiert (Abschnitt 6.4) |
| 4 | `README.md` erwähnt keine entfernte Datei | grün | `test_das_readme_nennt_keine_entfernte_datei` |
| 5 | Unveränderte Testzahl aus Teil 1 | **mit Erklärung** | Sie hat sich geändert, und zwar zwangsläufig — Abschnitt 6.5 |

## 2. Entfernte Dateien

| Datei | Zeilen | Warum |
|---|---|---|
| `data_cleaner.py.bak` | 149 | Sicherungskopie; die Historie liegt in Git |
| `clean_input_data.py` | 42 | Einmalskript mit festem Pfad |
| `csv_processor.py` | 82 | ersetzt durch `pipeline.py` und die Provider |
| `csv_postprocessor.py` | 44 | Spaltenauswahl liegt im Datenvertrag |
| `logger_config.py` | 42 | wurde nur von den beiden darüber importiert |
| `data_preprocessor.py` | 159 | seine Prüfung ist in Teil 1 nachgebaut und durch eigene Tests abgesichert |
| `data_consolidator.py` | 120 | das Aufteilen in Batches war eine Umgehung der alten Anwendung und entfällt |
| **gesamt** | **638** | |

Ausserdem geändert: `upload_pruefung.py` und `test_abschlussrunde_abnahme.py` —
beide erwähnten `data_preprocessor.py` im Fliesstext als etwas, das dasteht. Die
Sätze sagen jetzt, dass die Datei gelöscht ist und in der Git-Historie liegt.

Verbliebene Module: `apify_provider`, `cli`, `config`, `config.template`,
`data_cleaner`, `db`, `fake_provider`, `google_provider`, `mail`, `modus_b`,
`pipeline`, `place_provider`, `pruefmaske`, `upload_pruefung`, `webapp`,
`worker`.

## 3. Getroffene Annahmen (Teil 2)

| Situation | Entscheidung | Warum |
|---|---|---|
| **`ABSCHLUSSRUNDE.md` widerspricht sich bei `data_preprocessor.py`.** Zeile 79 sagt «erst nach Teil 1 löschen», Zeile 152 verlangt als Abnahmekriterium, die Datei stehe noch da. | **Gelöscht.** | Drei Quellen gegen eine: die Tabelle in Zeile 79, `FREIGABE_ABSCHLUSSRUNDE_TEIL1.md` §5 («Teil 2 löscht sechs Dateien, `data_preprocessor.py` eingeschlossen — seine Prüfung ist jetzt nachgebaut und durch eigene Tests abgesichert») und der ausdrückliche Auftrag dieser Runde. Zeile 152 stammt erkennbar aus der Fassung, in der die Datei noch stehen bleiben sollte, und wurde beim Ergänzen nicht nachgezogen. Ebenso die Zahl «sechs» in Zeile 148 — es sind sieben. |
| Was wird aus den Erwähnungen im Fliesstext? | Umformuliert, nicht gestrichen. | Der Satz «diese Prüfung stand im alten Ablauf in `data_preprocessor.py`» erklärt, woher die Regel kommt — das bleibt wertvoll. Er darf nur nicht auf eine Datei zeigen, als stünde sie noch da. |
| `WORKFLOW_AND_HANDOFF.md` und `docs_old/` nennen die gelöschten Dateien | Nicht angefasst. | Beides sind Dokumente von **vor** dem Umbau (`WORKFLOW_AND_HANDOFF.md` ist auf den 14.04.2026 datiert und beschreibt den alten Drei-Schritt-Ablauf). Das Kriterium nennt ausdrücklich `README.md`. Vorschlag in Abschnitt 7 |

## 4. Abweichungen von den Vorgaben (Teil 2)

| Vorgabe | Abweichung | Warum |
|---|---|---|
| `ABSCHLUSSRUNDE.md` Zeile 152: «`data_preprocessor.py` steht noch da» | Gelöscht | Siehe Abschnitt 3. Widerspruch im Plan; drei neuere Quellen sagen löschen |
| `ABSCHLUSSRUNDE.md` Zeile 148: «Die **sechs** zum Löschen freigegebenen Dateien» | Es sind **sieben** | Die Tabelle listet sieben, alle mit «löschen». Die Zahl stammt aus der Fassung vor der Entscheidung zu `data_consolidator.py` |

## 5b. Was gefunden wurde (Teil 2)

| Fund | Auswirkung | eingegriffen? |
|---|---|---|
| **Kein einziges lebendes Modul importierte eine der sieben Dateien.** Die einzigen Importe waren `csv_processor.py` und `csv_postprocessor.py`, die beide `logger_config` holten — alle drei sind jetzt weg. | Die Löschung war folgenlos, wie erwartet. Belegt statt angenommen: ein Test über alle Module, plus ein Import aller Einstiegspunkte. | **ja** — Teil 2 |
| **`WORKFLOW_AND_HANDOFF.md` beschreibt weiterhin den alten Drei-Schritt-Ablauf** mit `data_preprocessor.py`, `apify_wrapper.py`, `csv_processor.py` und `data_consolidator.py`. Stand 14.04.2026, also von vor dem Umbau. | Wer die Datei findet, liest eine Anleitung für eine Anwendung, die es nicht mehr gibt — und die Hälfte der genannten Dateien existiert nicht mehr. Dasselbe gilt für `docs_old/`. | **nein** — ausserhalb des Umfangs, das Kriterium nennt nur `README.md`. Vorschlag in Abschnitt 7 |
| **Mein erster Löschtest war falsch parametrisiert.** `data_cleaner.py.bak` auf den Modulnamen zurückgeführt ergibt `data_cleaner` — ein Modul, das weiterlebt und von sechs Dateien importiert wird. | Der Test behauptete, niemand dürfe `data_cleaner` importieren, und fiel sofort um. Gefunden vom eigenen Testlauf, nicht vom Prüfer. Die Sicherungskopie war ohnehin nie importierbar; für sie genügt der Existenztest. | **ja** — die Importprüfung läuft jetzt nur über die sechs echten Module |

## 6. Messwerte

### 6.1 Fünf vollständige Testläufe

| Lauf | Ergebnis | Dauer |
|---|---|---|
| 1 | 383 grün, 1 übersprungen | 25.03 s |
| 2 | 383 grün, 1 übersprungen | 24.20 s |
| 3 | 383 grün, 1 übersprungen | 24.15 s |
| 4 | 383 grün, 1 übersprungen | 24.11 s |
| 5 | 383 grün, 1 übersprungen | 23.94 s |

### 6.2 Die Zahlen zur Doppelmeldung, vorher und nachher

Eine Datei mit sieben Zeilen, je eine pro Art:

| Befund | vorher (Teil 1) | jetzt (Teil 2a) |
|---|---|---|
| unvollständiger Suchbegriff | 4 | 4 |
| Kostenstelle | **4** | **1** |
| Kategoriename | 1 | 1 |
| Summe der gemeldeten Zeilen | **9** bei 6 betroffenen Zeilen | **6** bei 6 betroffenen Zeilen |

Die drei zu viel waren dreimal dieselbe falsche Aussage. Jede Zeile erscheint
jetzt unter genau einem Befund — festgehalten von
`test_jede_zeile_erscheint_unter_genau_einem_befund`.

**Die Phase-4-Tests:** unverändert, alle 40 grün, keine Zahl angepasst. Ihre
Fixtures enthalten ausschliesslich vollständige Suchbegriffe; die Überschneidung
kam dort nicht vor.

### 6.3 Der Bericht, den der Nutzer liest

Dieselbe Datei mit sieben Zeilen, nach Teil 2a:

```
7 Kunden (7 Zeilen)

4 Zeilen haben keinen vollständigen Suchbegriff. Erwartet werden drei durch
Komma getrennte Teile: Name, Strasse mit Hausnummer, PLZ mit Ort.
Beispiel Zeile 2: «Denner Bremgarten;5620;M;900001»

1 Zeile hat im Strassenfeld keinen Strassennamen, sondern zum Beispiel eine
Kostenstelle. Ohne Strasse findet die Suche die Adresse nicht.
Beispiel Zeile 6: «Emil Frey AG, KST 715611 0, 5745 Safenwil;5620;M;900005»

1 Zeile trägt als Namen nur eine Branche statt eines Firmennamens. Die Suche
findet dann viele gleich gute Treffer und kann nicht entscheiden.
Beispiel Zeile 7: «Boucherie, Rue des Tilleuls 5, 1800 Vevey;5620;M;900006»

Der Lauf kann trotzdem gestartet werden. Die genannten Zeilen landen
voraussichtlich in der Datei «zur Prüfung».
```

Drei Befunde, drei verschiedene Zeilen als Beispiel, kein «1 Zeilen».

### 6.4 Nach dem Löschen

| Prüfung | Ergebnis |
|---|---|
| Einstiegspunkte importierbar | `webapp`, `cli`, `pipeline`, `upload_pruefung`, `pruefmaske`, `data_cleaner`, `worker`, `mail`, `db` — alle |
| `python cli.py --help` | läuft |
| Import auf eine entfernte Datei in einem `*.py` des Projekts | keiner |
| `README.md` nennt eine entfernte Datei | nein |
| Zeilen entfernt | **638** |

### 6.5 Zur Testzahl

Das Kriterium verlangt «unveränderte Testzahl aus Teil 1». Sie hat sich
geändert, und zwar aus zwei Richtungen:

| | Tests |
|---|---|
| Ende Teil 1 | 363 |
| − Phase-2-Prüfung über alle Module (6 Module weniger) | −6 |
| + Teil 2a | +13 |
| + Teil 2 | +14 |
| **jetzt** | **384** (383 grün, 1 übersprungen) |

Die sechs verlorenen sind kein Verlust an Prüfung:
`test_kein_modul_kennt_apify_feldnamen` ist über jede `*.py` des Projekts
parametrisiert und schrumpft zwangsläufig, wenn Module verschwinden. Sie prüfte
sechs Dateien, die es nicht mehr gibt — 53 Tests in Phase 2 vorher, 47 jetzt,
14 statt 20 Module. Kein bestehender Test wurde entfernt oder abgeschwächt.

---

## 7. Für die nächste Runde

- **`WORKFLOW_AND_HANDOFF.md` und `docs_old/`** beschreiben den Ablauf vor dem
  Umbau und nennen Dateien, die es nicht mehr gibt. Entweder löschen, oder mit
  einem Satz am Kopf als historisch kennzeichnen. Ausserhalb des Umfangs dieser
  Runde, aber der letzte Ort im Repository, an dem eine überholte Anleitung
  steht.
- **`agent/UMBAUPLAN_WEBAPP.md` §2** führt `csv_processor.py`,
  `csv_postprocessor.py`, `data_preprocessor.py` und `data_consolidator.py`
  weiterhin als «bleibt». Das ist durch diese Runde überholt; die Findings der
  Phasen 2 und 7 hatten den Widerspruch schon gemeldet.
- **Der Widerspruch in `ABSCHLUSSRUNDE.md`** (Zeilen 148 und 152 gegen die
  Tabelle) sollte bereinigt werden, damit die Abnahme dieser Runde nicht an
  einem Kriterium hängt, das die Runde selbst überholt hat.
- **Unverändert beim Auftraggeber:** SMTP-Freigabe durch die ICT und ein echter
  Versand über das Firmen-Relais; Google Places aufschalten und ein Live-Abruf
  für Modus B (`03 B4` — die Produktivsperre steht weiterhin); die
  Zulässigkeit eines privaten Gmail-Kontos für Firmendaten; Batch 5.

---

## 8. Zeit

| Arbeitspaket | grober Aufwand |
|---|---|
| Abnahme und ergänzten Plan lesen, Widerspruch klären | 0.25 h |
| Teil 2a A: Doppelmeldung auflösen | 0.25 h |
| Teil 2a B: Singular in beiden Meldungen | 0.25 h |
| Teil 2a C: README, Schritt Prüfung | 0.5 h |
| Teil 2: Löschen, Fliesstext nachziehen, Wächtertests | 0.5 h |
| 27 Tests, Messungen | 0.75 h |
| Fünf Testläufe | 0.25 h |
| Findings | 0.5 h |
| **gesamt** | **≈ 3.25 h** |

Das Löschen selbst war ein `git rm`. Bemerkenswert war, was **nicht** eintrat:
Die Phase-4-Zahlen, deren Anpassung der Plan erwartete, blieben unverändert —
die Überschneidung kam in ihren Fixtures nie vor. Sie wurde erst sichtbar, als
Teil 1 die vierte Prüfung dazustellte.
