# Findings — Phase 8, Version 1.0

Datum: 05.08.2026
Bearbeitete Phase: 8 — Prüfmaske im Browser
Status: fertig

Testlauf: `venv/bin/python -m pytest` → **329 grün, 1 übersprungen**, fünfmal
hintereinander (Abschnitt 6.1). Fassungen unverändert: `apify-client` 2.0.0,
`thefuzz` 0.22.1.

---

## 1. Abnahmekriterien

| # | Kriterium | Status | Beleg |
|---|---|---|---|
| 1 | Alle Prüffälle eines Jobs sind aufrufbar und einzeln entscheidbar | grün | `test_alle_pruefaelle_sind_aufrufbar` vergleicht die Liste mit `pruefaelle_lesen`; `test_jeder_fall_ist_einzeln_entscheidbar` entscheidet jeden einzeln, danach ist nichts mehr offen |
| 2 | Eine Entscheidung ist nach dem Neuladen der Seite noch da | grün | `test_entscheidung_ueberlebt_das_neuladen`; `test_entscheidung_steht_in_der_datenbank` liest sie über eine frische Verbindung, also wie nach einem Neustart |
| 3 | Entschiedene Fälle stehen in `fertig_fuer_erp.csv`, nicht mehr in `zur_pruefung.csv` | grün | `test_entschiedener_fall_wandert_in_die_erp_datei`; gemessen in Abschnitt 6.3 |
| 4 | Die Invariante aus `02_DATENVERTRAG.md` §2 gilt auch nach Entscheidungen | grün | `test_invariante_haelt_nach_jeder_entscheidung` prüft nach **jeder** einzelnen Entscheidung, dass jede `KundenNr` in genau einer der drei Dateien steht |
| 5 | Eine unentschiedene Restmenge bleibt korrekt in ② | grün | `test_unentschiedener_rest_bleibt_in_zwei` und `test_restmenge_behaelt_alle_ihre_treffer` — die übrigen Fälle behalten `qualitaet`, `grund`, `score` und alle ihre Vorschläge |
| 6 | Bedienbar mit Tastatur; 50 Fälle hintereinander ohne Mausgriff entscheidbar | grün | `test_fuenfzig_faelle_ohne_einen_mausgriff`: 50 Entscheidungen in Folge, jede Antwort verweist selbst auf den nächsten offenen Fall. Dazu `test_die_maske_ist_ohne_javascript_bedienbar` und `test_die_zifferntasten_stehen_an_den_knoepfen`. Von Hand im Browser nachgestellt (Abschnitt 6.4) |

### Umfang aus dem Phasenplan

| Punkt | Umgesetzt |
|---|---|
| Liste der Prüffälle eines Jobs, ein Fall pro Zeile, mit Grund | `/pruefung/{job_id}` — KundenNr, Kunde, Grund, Trefferzahl |
| Detailansicht: Kundendaten links, Google-Kandidaten rechts, je mit `score` und `grund` aus `kandidat` | `/pruefung/{job_id}/fall/{kunde_id}`, geprüft von `test_kundendaten_links_treffer_rechts` |
| Ein Klick je Entscheidung: Kandidat wählen, oder «keiner passt» → ③ | jeder Treffer ist ein Absendeknopf; `test_keiner_passt_schickt_den_kunden_nach_drei` |
| Fortschritt sichtbar, Arbeit jederzeit unterbrechbar | Zähler und Balken auf beiden Seiten; `test_fortschritt_ist_sichtbar_und_waechst`, `test_arbeit_kann_unterbrochen_und_fortgesetzt_werden` |
| Entschiedene Fälle fliessen in `fertig_fuer_erp.csv` — **ein** ERP-Import statt zwei | Abschnitt 6.3; die Ergebnisseite führt hin und bietet den alten Weg über das erneute Hochladen nicht mehr an |

---

## 2. Geänderte und neue Dateien

| Datei | neu / geändert | Was |
|---|---|---|
| `pruefmaske.py` | **neu** | Entscheiden und Dateien neu schreiben. Kennt keine Datenquelle, keine HTTP-Schicht. |
| `db.py` | geändert | `kunde_lesen`, `pruefaelle_lesen`, `kunde_entscheiden`. Schema **unverändert** — kein neues Feld, keine neue Tabelle. |
| `webapp.py` | geändert | Drei Routen (`/pruefung/{job}`, `.../fall/{kunde}` lesend und schreibend). Die Ergebnisseite reicht den Prüfstand durch. |
| `templates/pruefung_liste.html` | **neu** | Die Liste. |
| `templates/pruefung_fall.html` | **neu** | Der einzelne Fall. |
| `templates/ergebnis.html` | geändert | Verweis auf die Maske statt auf das erneute Hochladen — siehe Abschnitt 5. |
| `templates/grundgeruest.html` | geändert | Fünfter Schritt «Prüfung» im Kopf. |
| `static/stil.css` | geändert | Stile für Liste, Fall und Tastenhinweise. |
| `test_phase8_abnahme.py` | **neu** | 23 Tests, einer je Kriterium und die Ränder. |

Nicht angefasst: `data_cleaner.py`, `pipeline.py`, `modus_b.py`, die Provider,
`02_DATENVERTRAG.md` §5, die Schwellenwerte.

**Keine Migration.** Die Datengrundlage steht seit Phase 2 vollständig in der
Datenbank; §5 nennt sie ausdrücklich als Grundlage für diese Maske. Es entstehen
keine neuen Daten, es wird entschieden, was schon da ist.

---

## 3. Getroffene Annahmen

| Situation | Entscheidung | Warum |
|---|---|---|
| Wann werden die drei Dateien neu geschrieben? | Nach **jeder** einzelnen Entscheidung. | Die Alternative wäre ein Knopf «jetzt speichern» am Ende — und genau den vergisst ein Nutzer ohne IT-Hintergrund, wenn er nach vierzig Fällen aufhört. So stimmen die Dateien in jedem Augenblick. Der Preis ist gemessen und klein: 44 ms je Entscheidung bei 2'500 Kunden (Abschnitt 6.2). |
| Wie entstehen die Dateien neu? | Vollständig aus der Datenbank, nach derselben Regel, nach der der Lauf sie geschrieben hat. | Zeilen zwischen den vorhandenen Dateien hin- und herzuschieben wäre fehleranfälliger und hinge daran, dass die Dateien noch unverändert dastehen. Dass die Regel dasselbe ergibt, ist nicht behauptet, sondern Zeichen für Zeichen geprüft: `test_neu_schreiben_ohne_entscheidung_aendert_nichts`. |
| `aussortiert.csv` beim Neuschreiben | Bleibt unverändert, wird durchgereicht. | Sie lässt sich **nicht** aus der Datenbank herstellen (Abschnitt 5). Sie ist keine der drei Ausgaben und unterliegt der Invariante nicht (§2). |
| Reihenfolge der Zeilen nach dem Neuschreiben | Nach `kunde.id`, also nach Verarbeitung. | Der Lauf schreibt in der Reihenfolge der Eingabedatei; bei sechs Arbeitern ist die Reihenfolge in der Datenbank die der Fertigstellung. Nach der ersten Entscheidung ist die Ausgabe also nach Verarbeitung sortiert. Für den ERP-Import spielt das keine Rolle, die Invariante hängt nicht daran. Die Eingabereihenfolge wäre nur zu halten, indem die Maske die hochgeladene Datei mitliest — eine Kopplung ohne Gegenwert. |
| Was passiert bei einer zweiten Entscheidung zum selben Fall? | Die neue ersetzt die alte. | Wer sich vertippt, soll das ohne Umweg richtigstellen können. `test_eine_entscheidung_laesst_sich_aendern` hält fest, dass danach genau eine Zeile in ① steht und der alte Treffer abgelehnt ist. |
| Prüfen vor Ende des Laufs | Nicht möglich, mit Erklärung. | Vorher steht nicht fest, welche Kunden zur Prüfung gehen, und es gibt keine Dateien, die man richtigstellen könnte. |

---

## 4. Abweichungen von den Vorgaben

**Eine, und sie braucht eine Entscheidung des Prüfers.**

| Vorgabe | Abweichung | Warum |
|---|---|---|
| `02_DATENVERTRAG.md` §3: «Abschliessende Liste. Keine neuen Werte ohne Korrekturplan.» | Zwei neue Werte: **`OK (geprüft)`** (①) und **`NICHT_MOEGLICH (geprüft)`** (③) | s. unten |

§3 beschreibt, was die **Fachlogik** entscheidet — jeder Wert nennt die Regel,
die gegriffen hat: `OK (Strasse)`, `OK (Score)`, `OK (Dynamisch)`. Beim
Schreiben des Vertrags gab es keine Prüfmaske; ein Wert für «ein Mensch hat
hingesehen» war nicht vorgesehen.

Die drei Auswege ohne neuen Wert habe ich durchgespielt:

| Weg | Was daran falsch ist |
|---|---|
| Einen vorhandenen `OK (…)`-Wert setzen | Die Zeile behauptet dann, eine Regel habe gegriffen. Es hat aber keine gegriffen — deshalb war der Fall ja in ②. |
| `PRUEFUNG (…)` stehen lassen und nur `ergebnis` umstellen | Dann steht in der ERP-Datei eine Zeile, die sich selbst als ungeprüft ausweist. Und §3 ordnet jedem `PRUEFUNG (…)` die Datei ② zu — verletzt wäre die Tabelle so oder so. |
| `NICHT_MOEGLICH (kein Ergebnis)` für «keiner passt» | Das hiesse «die API lieferte nichts». Sie lieferte etwas; ein Mensch hat es verworfen. |

Alle drei lassen eine Zeile über sich selbst etwas Falsches sagen — genau der
Fehler, den Phase 7 in vier Runden ausgeräumt hat. Deshalb zwei neue Werte, im
Muster der vorhandenen, und dieser Eintrag hier.

**Zu entscheiden:** ob §3 um die zwei Werte ergänzt wird. Bis dahin steht die
Begründung als Kommentar an der Stelle im Code, an der sie gesetzt werden
(`pruefmaske.py`).

Nicht abgewichen: `qualitaet` bleibt das einzige neue am Datensatz. Datei,
Spalten, `score` und die Invariante sind unverändert; das Schema aus §5 wurde
nicht ergänzt.

---

## 5. Was gefunden wurde

| Fund | Datei / Stelle | Auswirkung | eingegriffen? |
|---|---|---|---|
| **`aussortiert.csv` lässt sich nicht aus der Datenbank herstellen.** Ihre Zeilen tragen ein eigenes `qualitaet` (`AUSSORTIERT (PLZ)`, `AUSSORTIERT (Strasse)`), und die Tabelle `kandidat` hat keine Spalte dafür. | `02_DATENVERTRAG.md` §5 gegen `data_cleaner.py` | Beim ersten Versuch schrieb die Maske dort die `qualitaet` des **Kunden** hinein und ersetzte damit die Diagnose des Laufs durch «OK (Strasse)». Der Byte-Vergleich hat es gefunden, bevor ein Test es hätte übersehen können. | **ja** — die Datei wird jetzt unverändert durchgereicht. Das Schema zu ergänzen wäre der falsche Weg gewesen: §5 ist wörtlich verbindlich, und die Datei ist Diagnose, keine Ausgabe |
| **Der Text auf der Ergebnisseite beschrieb den Weg, den diese Phase abschafft.** «Geprüfte Zeilen aus *Zur Prüfung* können Sie später wieder hochladen — sie werden dann in die ERP-Datei übernommen.» | `templates/ergebnis.html` | Ein Rückweg über das erneute Hochladen war nie gebaut; der Satz versprach etwas, das es nicht gab. Jetzt gibt es den Rückweg — nur anders. | **ja** — der Satz verweist auf die Maske und nennt den Zweck: eine Datei statt zwei |
| **Der neue Modul steht ohne Zutun unter der Architekturregel aus Phase 2.** `test_kein_modul_kennt_apify_feldnamen` ist über alle `*.py` des Projekts parametrisiert. | `test_phase2_abnahme.py:89` | `pruefmaske.py` wurde automatisch mitgeprüft — daher 306 statt 305 Tests vor der Phase-8-Datei. Kein Eingriff nötig, hier vermerkt, damit die Zahl nachvollziehbar ist. | **nein** — funktioniert wie vorgesehen |
| **Ein Fall mit Anführungszeichen im Grund brach den ersten Testentwurf.** Die Seite maskiert `"` zu `&#34;`, wie sich das gehört. | `test_phase8_abnahme.py` | Der Test verglich den Rohtext und schlug nur im vollständigen Lauf fehl, weil bei sechs Arbeitern eine andere Reihenfolge herauskam. | **ja** — der Test vergleicht jetzt den Text, den der Nutzer liest, und prüft **alle** Fälle statt des ersten |

---

## 6. Messwerte

### 6.1 Fünf vollständige Testläufe

| Lauf | Ergebnis | Dauer |
|---|---|---|
| 1 | 329 grün, 1 übersprungen | 24.01 s |
| 2 | 329 grün, 1 übersprungen | 23.88 s |
| 3 | 329 grün, 1 übersprungen | 23.40 s |
| 4 | 329 grün, 1 übersprungen | 24.00 s |
| 5 | 329 grün, 1 übersprungen | 24.11 s |

Die Zahl im Einzelnen: 306 vor dieser Phase, plus 1 (`pruefmaske.py` fällt unter
die Architekturprüfung aus Phase 2), plus 23 neue — 330 gesammelt, davon einer
übersprungen (der 180-Sekunden-Langläufer aus Phase 2, von dieser Phase nicht
berührt).

### 6.2 Was eine Entscheidung kostet

Gemessen an der Grösse aus Phase 4: 2'500 Kunden, davon 840 Prüffälle.
Erfundene Kundennummern.

| Messung | Wert |
|---|---|
| Eine Entscheidung samt Neuschreiben aller Dateien, Mittel aus 50 | **44 ms** |
| davon die langsamste | 55 ms |
| Hochgerechnet auf alle 840 Fälle | 37 s reine Rechenzeit über die ganze Sitzung |

44 ms je Tastendruck sind nicht wahrnehmbar. Damit trägt die Entscheidung aus
Abschnitt 3, nach jeder Entscheidung zu schreiben statt am Ende.

### 6.3 Der Weg eines Falls durch die Dateien

Ein Lauf über die Fixture (10 Kunden, davon 3 zur Prüfung), zwei Entscheidungen
im Browser: bei `900009` der erste Treffer, bei `900002` «keiner passt».

| Kunde | vorher | jetzt | `qualitaet` | `score` |
|---|---|---|---|---|
| `900009` | ② `zur_pruefung`, 2 Zeilen | **① `fertig_fuer_erp`, 1 Zeile** | `OK (geprüft)` | 100.0 — der gemessene Wert des gewählten Treffers |
| `900002` | ② `zur_pruefung`, 3 Zeilen | **③ `nicht_moeglich`, 1 Zeile** | `NICHT_MOEGLICH (geprüft)` | 0.0 |
| `900007` | ② `zur_pruefung`, 2 Zeilen | ② unverändert, 2 Zeilen | `PRUEFUNG (mehrere hohe Treffer)` | 88.0 / 87.1 |

Der Grund, der bei `900009` in der ERP-Datei steht:

> Von Hand geprüft und ausgewählt: Muster Kiosk, Wohlerstrasse 18, 5610
> Beispielwil.

Und bei `900002` in ③:

> Von Hand geprüft: keiner der gefundenen Treffer gehört zu diesem Kunden.

Deutsch, ein Satz, nennt Werte statt Regeln (§4), Schweizer Schreibweise. Nach
beiden Entscheidungen: 7 + 1 + 2 Kunden, jeder in genau einer Datei.

### 6.4 Tastatur, von Hand nachgestellt

Im Browser mit dem laufenden Server: auf dem Fall `900009` die Taste `1` —
der Fall ist entschieden, und ohne einen weiteren Handgriff steht `900002` da,
der Zähler auf «1 von 3 entschieden, 2 noch offen». Dort die Taste `0` — der
Kunde geht nach ③.

Die Zifferntasten sind nur eine Abkürzung: Jeder Treffer ist ein echter
Absendeknopf in einem gewöhnlichen Formular, also gehen `Tab` und `Enter`
genauso. Fiele das Skript aus, bliebe die Maske vollständig bedienbar —
`test_die_maske_ist_ohne_javascript_bedienbar` hält fest, dass kein einziges
`onclick` in der Seite steht.

### 6.5 Die Gegenprobe zur Behauptung «es ändert sich nichts»

Die Maske schreibt die Dateien aus der Datenbank neu. Wäre diese Regel auch nur
in einer Spalte anders als die des Laufs, würde die **erste** Entscheidung still
alle übrigen Zeilen verändern.

`test_neu_schreiben_ohne_entscheidung_aendert_nichts` vergleicht deshalb nach
einem Lauf ohne eine einzige Entscheidung alle vier Dateien Zeichen für
Zeichen. Der Test hat den Fund aus Abschnitt 5 (`aussortiert.csv`) gefunden,
bevor er als Test überhaupt fertig war.

Dass die Abnahmetests greifen, ist zusätzlich gegengeprüft: mit
ausgebautem Neuschreiben fallen sieben von ihnen um, darunter alle zu
Kriterium 3.

---

## 7. Für die nächste Phase

- **Die zwei neuen `qualitaet`-Werte** aus Abschnitt 4 brauchen eine
  Entscheidung: entweder `02_DATENVERTRAG.md` §3 wird ergänzt, oder der Prüfer
  nennt einen Weg, den ich nicht gesehen habe.
- **Die Aufräumrunde** ist jetzt dran: `logger_config.py`,
  `clean_input_data.py`, `csv_processor.py`, `csv_postprocessor.py` und
  `data_cleaner.py.bak` — eine Entscheidung je Datei.
- **Modus B in der Maske.** Die Maske ist modusunabhängig gebaut und zeigt bei
  einem Modus-B-Kunden dessen Google-ID statt des Suchbegriffs. Geprüft ist sie
  bislang nur an Modus-A-Fällen, weil Modus B unter der Produktivsperre aus
  `03 B4` steht. Wenn die Sperre fällt, gehört ein Prüffall aus Modus B
  (`PRUEFUNG (geschlossen)`, `PRUEFUNG (Standort abweichend)`) einmal durch die
  Maske gefahren.
- **Die Reihenfolge der Ausgabezeilen** ändert sich mit der ersten Entscheidung
  von Eingabe- auf Verarbeitungsreihenfolge (Abschnitt 3). Falls das ERP daran
  hängt, ist es jetzt zu sagen.
- **Unverändert beim Auftraggeber:** SMTP-Freigabe durch die ICT und ein echter
  Versand über das Firmen-Relais; Google Places aufschalten und ein Live-Abruf
  für Modus B; die Zulässigkeit eines privaten Gmail-Kontos für Firmendaten.

---

## 8. Zeit

| Arbeitspaket | grober Aufwand |
|---|---|
| Phasenplan, Datenvertrag und Bestand lesen | 0.5 h |
| Entwurf: was eine Entscheidung im Datenmodell bedeutet | 0.5 h |
| `pruefmaske.py` und die drei Datenbankmethoden | 1.0 h |
| Routen, zwei Vorlagen, Stile | 1.25 h |
| 23 Tests | 1.25 h |
| Messungen, Gegenprobe, Bedienung im Browser | 0.75 h |
| Findings | 0.5 h |
| **gesamt** | **≈ 5.75 h** |

Der Aufwand lag nicht in der Oberfläche, sondern in der Frage, wie die drei
Dateien nach einer Entscheidung entstehen, ohne dass sich dabei etwas anderes
mitverändert. Die Antwort — aus der Datenbank neu, und das Zeichen für Zeichen
gegen den Lauf geprüft — hat die Diagnosedatei als Sonderfall zutage gefördert,
bevor sie hätte schaden können.
