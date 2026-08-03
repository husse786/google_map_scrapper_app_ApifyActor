# Findings — Phase 4, Version 1.0

Datum: 03.08.2026
Bearbeitete Phase: 4 — Upload-Validierung
Status: fertig

Testlauf: `python -m pytest` → **155 grün, 1 übersprungen**, fünfmal
hintereinander (9.09 / 8.85 / 8.70 / 8.67 / 8.74 s), wie im Korrekturplan zu
Phase 3 festgelegt. Aufteilung: 8 + 40 + 48 + 20 aus den Phasen 1 bis 3,
40 neu.

> **Der wichtigste Befund steht in Abschnitt 6.1 und widerspricht der Annahme,
> auf der diese Phase aufgebaut ist.** Die Kostenstellen-Prüfung, laut
> `03_ENTSCHEIDUNGEN.md` D „der wirkungsvollste Punkt im ganzen Projekt",
> trifft auf den beiden gemessenen Batches **14 und 11 Zeilen** und erklärt
> davon **je einen** der 448 bzw. 512 Prüffälle „keine Strassentreffer".
> Die Zahl 4'288 aus `03` D ist nicht falsch — sie stammt aus den V1-Batches.
> Der ERP-Export hat sich seither geändert.

---

## 1. Abnahmekriterien

| # | Kriterium | Status | Beleg |
|---|---|---|---|
| 1 | `Emil Frey AG, KST 715611 0, 5745 Safenwil` wird als Kostenstelle erkannt | grün | `test_kostenstelle_wird_erkannt`, zusätzlich im vollständigen Bericht in `test_die_drei_beispiele_im_ganzen_bericht`. |
| 2 | `Denner, Hauptstrasse 5, 5620 Bremgarten` wird **nicht** als Kostenstelle erkannt | grün | `test_echte_strasse_wird_nicht_als_kostenstelle_erkannt`, plus zehn weitere Fälle in `test_kostenstellen_erkennung`. |
| 3 | `Boucherie, Rue des Tilleuls 5, 1800 Vevey` wird als reiner Kategorietitel erkannt | grün | `test_kategorietitel_wird_erkannt`. Dazu war eine Abweichung nötig, siehe Abschnitt 4. |
| 4 | Fehlende Pflichtspalte erzeugt eine deutsche Meldung mit Beispielzeile, keinen Stacktrace | grün | `test_fehlende_pflichtspalte_meldet_deutsch`, `test_fehlende_pflichtspalte_wirft_keine_ausnahme`, `test_cli_meldet_fehlende_spalte_ohne_stacktrace`. Geprüft wird auch, dass kein ß und kein englisches Wort im Text steht. |
| 5 | Datei mit 10'001 Zeilen wird abgewiesen | grün | `test_zehntausendeins_zeilen_werden_abgewiesen`; `test_genau_zehntausend_zeilen_sind_erlaubt` zieht die Grenze; `test_zu_grosse_datei_startet_keinen_lauf` zeigt, dass der Lauf gar nicht erst beginnt. |
| 6 | Messung: wie viele Zeilen einer realen Eingabedatei jede der drei Prüfungen trifft, und wie viele Prüffälle dadurch entfallen | grün | Abschnitt 6.1, zwei reale Dateien mit je 2'513 Kunden, verknüpft mit den tatsächlichen Laufergebnissen aus den Phasen 1 bis 3. |
| 7 | Laufzeitmessung: mindestens zehn aufeinanderfolgende echte Apify-Aufrufe mit Einzelzeiten | grün | Abschnitt 6.3. |

---

## 2. Geänderte und neue Dateien

| Datei | neu / geändert | Was |
|---|---|---|
| `upload_pruefung.py` | neu | Die drei Prüfungen aus `03_ENTSCHEIDUNGEN.md` D, die Zeilenobergrenze und der Bericht in Klartext. Ein `Befund` trägt Art, Schwere, Anzahl, Meldung, Beispielzeile und Zeilennummer; ein `Pruefbericht` bündelt sie und weiss, ob der Start möglich ist. |
| `cli.py` | geändert | Neuer Befehl `pruefen`. Vor jedem `lauf` läuft die Prüfung automatisch mit: Hinweise werden gezeigt, eine zu grosse Datei stoppt den Start. |
| `test_phase4_abnahme.py` | neu | 40 Tests. |
| `README.md` | geändert | Schritt 0 „Die Datei vorher prüfen", Modulübersicht. |

Nicht angefasst: `data_cleaner.py`, `pipeline.py`, `worker.py`, `db.py`, die
Provider. Insbesondere wurde `GENERIC_FIRST_WORDS` nicht verändert —
`test_scoring_liste_bleibt_unangetastet` hält das fest.

---

## 3. Getroffene Annahmen

| Situation | Entscheidung | Warum |
|---|---|---|
| Zählweise der Zeilennummer | Kopfzeile ist Zeile 1, der erste Datensatz steht auf Zeile 2. | Der Nutzer sucht die Zeile in Excel. Dort steht sie genau unter dieser Nummer. |
| Die Beispielzeile | Die Zeile so, wie sie in der Datei steht, nicht die von Pandas eingelesene Fassung. | „Beispielzeile **im Original**". Passt die Zeilenzahl der Datei nicht zur Tabelle (mehrzeilige Felder), wird die Zeile aus der Tabelle zusammengesetzt — dann stimmt die Nummer nicht mehr exakt, aber es gibt keinen Absturz. |
| „10'001 Zeilen" — Datenzeilen oder Dateizeilen? | Datenzeilen ohne Kopfzeile. 10'000 sind erlaubt, 10'001 nicht. | `03_ENTSCHEIDUNGEN.md` C spricht von „Zeilen pro Upload"; der Nutzer meint damit Kunden, nicht die Kopfzeile. |
| Anzahl und Beispielzeile bei einer fehlenden Pflichtspalte | Anzahl = alle Zeilen der Datei, Beispielzeile = die Kopfzeile (Zeile 1). | Betroffen ist die ganze Datei, und der Fehler steckt in der Kopfzeile. `03` D verlangt genau dort „wie Zeile 1 aussehen muss". |
| Leeres Strassenfeld | Zählt als Kostenstelle. | `03` D sagt „Strassenteil ohne Buchstabenfolge ≥ 4" — ein leeres Feld erfüllt das. In den beiden gemessenen Dateien kam der Fall nicht vor (Abschnitt 6.1), in den Rohdaten dagegen sehr wohl. |
| Eine fehlende Pflichtspalte blockiert **nicht** | Nur Hinweis, wie die anderen beiden Prüfungen. | `03` D: „Alle warnen, keine blockiert." Konsequenz und Empfehlung in Abschnitt 5. |
| Der Bericht nennt immer Zeilen- und Kundenzahl | Auch wenn nichts gefunden wurde. | Der Phasenplan verlangt „Zeilenzahl melden". Und eine Datei ohne Befund soll das ausdrücklich sagen, nicht schweigen. |
| Zehn Apify-Aufrufe mit echten Kundenzeilen | Von Husey so entschieden. Sechs parallel wie im Betrieb. | Nur so ist die Messung mit den rund 17 Sekunden aus dem Betriebsprotokoll vergleichbar. In diesen Findings stehen ausschliesslich Zeiten und Trefferzahlen. |

---

## 4. Abweichungen von den Vorgaben

| Vorgabe | Abweichung | Warum unvermeidbar |
|---|---|---|
| `03_ENTSCHEIDUNGEN.md` D: „Titel besteht ausschliesslich aus Wörtern der `GENERIC_FIRST_WORDS`-Liste" | Die Prüfung benutzt eine **Obermenge**: `GENERIC_FIRST_WORDS` plus 42 weitere Kategoriewörter, überwiegend französisch und italienisch. | `GENERIC_FIRST_WORDS` enthält nur deutsche Wörter; `boucherie` steht nicht darin. Das Abnahmekriterium verlangt aber ausdrücklich, dass `Boucherie` erkannt wird. Die Liste selbst zu erweitern verbietet `03` B3 — sie steuert die Gewichtung im Scoring, jede Ergänzung würde produktive Ergebnisse verändern. Die Obermenge löst beides: das Scoring bleibt Wort für Wort gleich, die Prüfung beim Hochladen versteht die Westschweiz. Belegt durch `test_scoring_liste_bleibt_unangetastet`. |

Die ergänzten Wörter stehen vollständig in `upload_pruefung.py` unter
`ZUSAETZLICHE_KATEGORIE_WOERTER`. Welche davon in der Praxis auslösen, steht in
Abschnitt 6.2 — der Prüfer kann die Liste danach kürzen oder erweitern.

---

## 5. Was gefunden wurde

| Fund | Auswirkung | eingegriffen? |
|---|---|---|
| **Die Kostenstellen-Prüfung greift auf den aktuellen Daten fast nicht.** 14 und 11 Treffer bei je 2'513 Kunden. Von den 448 bzw. 512 Fällen „keine Strassentreffer" geht **je einer** auf eine Kostenstelle zurück. | Die Erwartung aus `03` D („der wirkungsvollste Punkt im ganzen Projekt") trifft für diese Daten nicht zu. Zahlen und Erklärung in Abschnitt 6.1. | nein — die Prüfung ist gebaut wie vorgegeben und richtig. Was fehlt, ist eine Entscheidung des Prüfers über die Folgen |
| **Der Präfix `KST`/`KOST` kommt in echten Daten praktisch nicht vor.** In 10'822 V1-Zeilen zweimal, in 7'626 V2-Zeilen keinmal. Was tatsächlich auslöst, ist die zweite Hälfte der Regel: ein Strassenfeld ohne Buchstabenfolge, also reine Ziffern wie `715611 0`. | Die Regel aus `03` D ist richtig, ihr Beispiel aber untypisch. Wer nur nach `KST` suchte, fände nichts. | nein — die Regel bleibt wie vorgegeben |
| **Die Vorverarbeitung fängt den grössten Teil schon ab.** In `InputData_cleaned_unvollstaendig.csv` sind 85 von 87 Zeilen (97.7%) Kostenstellen-Treffer — leere Strassenfelder, die `data_preprocessor.py` bereits aussortiert. In der Datei, die tatsächlich läuft, bleiben 37 von ursprünglich 122. | Ein Teil der erwarteten Wirkung wird heute schon erzielt, nur an anderer Stelle und ohne Meldung an den Nutzer. | nein — gemeldet |
| **Der wahre Grund für die Prüffälle ist ein anderer.** Klassifikation der 448 bzw. 512 Fälle in Abschnitt 6.2: 58% und 64% „andere Strasse", 19% und 22% „gleiche Strasse, andere Hausnummer". | Das ist kein Eingabefehler, sondern die Grenze des Abgleichs. Keine Upload-Prüfung kann das vorhersagen. | nein — Befund für die Entscheidung über die Prüfmaske |
| **Eine fehlende Pflichtspalte wird nur als Hinweis gemeldet**, weil `03` D das so vorschreibt. Der Lauf startet dann, bricht aber sofort ab: `pipeline.py` verlangt `SearchString`, `PLZ` und `KundenNr`. | Der Nutzer bekommt eine Warnung, drückt Start und sieht dann einen Fehler statt eines Ergebnisses. | nein — `03` D verbietet das Blockieren. **Empfehlung an den Prüfer:** diese eine Prüfung auf blockierend umstellen. Ein Lauf ohne `KundenNr` kann nicht gelingen, da gibt es nichts zu entscheiden |
| Hausnummernbereiche (`31-35`, `31/35`) | Wie in Phase 3 gemeldet, jetzt beziffert: 7 und 8 Fälle, also 1.6% der Prüffälle. Deutlich seltener als befürchtet. | nein — `03` B3 |
| **Apify ist heute rund fünfmal langsamer als zur Zeit von Batch 3 und 4.** 79.5 s je Aufruf gegen rund 17 s laut Betriebsprotokoll, bei gleicher Konfiguration und denselben Kundenzeilen. | Hochgerechnet aus zehn Aufrufen bräuchte ein Batch heute rund 12 Stunden statt zwei. Für die Weboberfläche in Phase 5 heisst das: die Statusseite muss einen halben Arbeitstag überstehen, nicht zwei Stunden. Vermutung und Nachprüfweg in Abschnitt 6.3. | nein — Befund für den Prüfer |

---

## 6. Messwerte

### 6.1 Die drei Prüfungen auf realen Daten

Zwei reale Eingabedateien, je 2'513 Kunden. Es sind genau die beiden Batches,
deren Laufergebnisse in den Phasen 1 bis 3 ausgewertet wurden — dadurch lässt
sich nicht nur zählen, wie oft eine Prüfung anschlägt, sondern auch, ob die
betroffenen Kunden am Ende wirklich zum Prüffall wurden.

| Prüfung | batch_3 | batch_4 |
|---|---|---|
| Pflichtspalten fehlen | nein | nein |
| Kostenstelle statt Strasse | **14** (0.6%) | **11** (0.4%) |
| davon leeres Strassenfeld | 0 | 0 |
| Titel ist nur eine Branche | **74** (2.9%) | **22** (0.9%) |
| mindestens eine Prüfung | 87 (3.5%) | 33 (1.3%) |

**Und was wurde daraus im Lauf?**

| | batch_3 | batch_4 |
|---|---|---|
| Kunden mit Kostenstelle, die als „keine Strassentreffer" endeten | **1** von 448 | **1** von 512 |
| Kunden mit Kostenstelle, die trotzdem in ① landeten | 9 | 8 |
| Kunden mit Kostenstelle, die in ③ landeten | 1 | 2 |
| Kunden mit Kategorietitel, die als „mehrere hohe Treffer" endeten | 1 von 36 | 0 von 29 |
| Kunden mit Kategorietitel, die trotzdem in ① landeten | 41 | 14 |
| **Prüffälle, die auf eine der beiden Prüfungen zurückgehen** | **32** von 745 (4.3%) | **9** von 849 (1.1%) |
| **Prüffälle, die bleiben** | **713** (28.4% aller Kunden) | **840** (33.4% aller Kunden) |

Bemerkenswert: von 14 Kunden mit einer Kostenstelle im Strassenfeld landeten
neun trotzdem sauber in ①. Der Strassenabgleich fällt bei ihnen aus, das
Namens-Scoring trägt die Entscheidung allein — und tut das offenbar gut.

**Warum die Zahl 4'288 aus `03` D hier nicht wiederkehrt.** Sie stammt aus den
V1-Batches. Dieselbe Prüfung, angewendet auf die Eingabedateien beider
Generationen:

| Datei | Zeilen | Kostenstelle | Anteil | Kategorietitel | Anteil |
|---|---|---|---|---|---|
| V1 Batch 1 | 99 | 10 | **10.1%** | 7 | 7.1% |
| V1 Batch 2 | 400 | 24 | 6.0% | 60 | 15.0% |
| V1 Batch 3 | 500 | 21 | 4.2% | 41 | 8.2% |
| V1 Batch 4 | 1'000 | 49 | 4.9% | 52 | 5.2% |
| V1 gesamt | 10'822 | 419 | 3.9% | 353 | 3.3% |
| V2 roh | 7'626 | 122 | 1.6% | 102 | 1.3% |
| V2 nach der Vorverarbeitung | 7'539 | 37 | **0.5%** | 101 | 1.3% |
| V2 aussortiert als unvollständig | 87 | 85 | **97.7%** | 1 | 1.1% |

Zwei Dinge zusammen erklären den Unterschied: der ERP-Export ist zwischen V1
und V2 besser geworden (3.9% → 1.6%), und die bestehende Vorverarbeitung nimmt
von dem, was übrig bleibt, nochmals zwei Drittel heraus (1.6% → 0.5%).

### 6.2 Woran die 448 und 512 Prüffälle wirklich liegen

Klassifikation aller Kunden mit `PRUEFUNG (keine Strassentreffer)`, ermittelt
durch Vergleich der gesuchten mit den gefundenen Strassen:

| Muster | batch_3 | batch_4 |
|---|---|---|
| andere Strasse | 258 (57.6%) | 328 (64.1%) |
| andere Strasse, Eingabe ohne Hausnummer | 96 (21.4%) | 62 (12.1%) |
| gleiche Strasse, andere Hausnummer | 86 (19.2%) | 111 (21.7%) |
| gleiche Strasse, Hausnummernbereich (`31-35`) | 7 (1.6%) | 8 (1.6%) |
| Google liefert gar keine Strasse | 0 | 2 (0.4%) |
| **Kostenstelle im Strassenfeld** | **1 (0.2%)** | **1 (0.2%)** |

Vier von fünf Prüffällen entstehen, weil Google einen Betrieb an einer anderen
Adresse führt als das ERP — nicht weil die Eingabe fehlerhaft wäre. Das ist vor
dem Lauf nicht erkennbar.

**Welche Kategoriewörter tatsächlich auslösen** (batch_3, häufigste):
`metzgerei` 25, `boucherie` 8, `epicerie` 7, `lebensmittelgeschaeft` 6,
`boulangerie patisserie` 6, `alimentation` 5, `restaurant post` 2, `kiosk` 2.
Die französischen Wörter aus der Erweiterung (Abschnitt 4) machen rund ein
Drittel der Treffer aus; ohne sie wäre das Abnahmekriterium 3 nicht erfüllbar
und ein Teil der Westschweizer Fälle unsichtbar.

### 6.3 Laufzeit von zehn echten Apify-Aufrufen

Zehn echte Kundenzeilen aus batch_3, sechs Arbeiter, ein Lauf. Nur Zeiten und
Trefferzahlen — keine Kundendaten.

| Nr | Start nach | Dauer | Treffer |
|---|---|---|---|
| 1 | 0.0 s | 63.6 s | 1 |
| 2 | 0.0 s | 64.8 s | 1 |
| 3 | 0.0 s | 75.1 s | 0 |
| 4 | 0.0 s | 79.8 s | 1 |
| 5 | 0.0 s | 84.7 s | 3 |
| 6 | 0.0 s | 91.2 s | 6 |
| 8 | 63.6 s | 79.2 s | 6 |
| 7 | 64.8 s | 70.3 s | 1 |
| 10 | 75.1 s | 99.4 s | 5 |
| 9 | 79.8 s | 81.1 s | 1 |

| Messung | Wert |
|---|---|
| kürzester Aufruf | 63.6 s |
| Median | **79.5 s** |
| längster Aufruf | 99.4 s |
| Aufrufe über 180 s | **0** |
| Gesamtzeit für 10 Kunden | 174.5 s |
| **je Kunde** | **17.5 s** |
| Status | `FERTIG`, 10 von 10 |

**Der Kaltstart ist als Erklärung erledigt — die Frage dahinter ist grösser
geworden.**

*Was geklärt ist.* Es gibt keinen Kaltstart. Der erste Aufruf war mit 63.6
Sekunden der **schnellste** von allen zehn. Die 83, 87 und 91 Sekunden aus
Phase 3 waren keine Anlaufzeit, sondern die normale Streuung: sie liegt heute
zwischen 64 und 99 Sekunden, Median 80.

*Was nicht aufgeht.* Die beiden Zahlen messen tatsächlich Verschiedenes — aber
sie versöhnen sich trotzdem nicht:

| | damals (Betriebsprotokoll) | heute (gemessen) | Faktor |
|---|---|---|---|
| Wanduhr je Kunde, 6 Arbeiter | 2.9 s | **17.5 s** | 6.1× |
| daraus je Aufruf | ~17 s | **79.5 s** | 4.6× |

Das Betriebsprotokoll nennt für Batch 3 und 4 „6 workers, ~2 hrs each" bei
2'513 Kunden. Das sind 2.9 Sekunden Wartezeit je Kunde, also rund 17 Sekunden
je einzelnem Aufruf. Heute braucht derselbe Actor mit derselben Konfiguration
auf denselben Kundenzeilen **rund 80 Sekunden je Aufruf**. Hochgerechnet aus
diesen zehn Aufrufen — und nur daraus — bräuchte ein Batch über 2'513 Kunden
heute **rund 12 Stunden statt zwei**.

*Was ich nicht weiss.* Woran das liegt, ist von hier aus nicht feststellbar.
Die naheliegendste Vermutung: Apify begrenzt die gleichzeitig laufenden Actors
über den Arbeitsspeicher des Kontos. Reicht der nicht für sechs Läufe, warten
die überzähligen in der Warteschlange — und diese Wartezeit steckt in der
gemessenen Dauer, weil sie zwischen `start()` und `wait_for_finish()` liegt.
Nachprüfbar allein in der Apify-Konsole: Speichergrenze des Kontos gegen den
Bedarf eines Laufs, und die dort ausgewiesene reine Laufzeit gegen meine
gemessene. **Befund für den Prüfer, keine eigenmächtige Änderung.**

*Zur Frist von 180 Sekunden.* Der längste Aufruf brauchte 99.4 s, also 55% der
Frist. Kein einziger kam in die Nähe. Mit den alten 90 Sekunden — von denen der
Provider 85 bekommen hätte — wären **zwei von zehn** Kunden fälschlich in ③
gelandet. Die Erhöhung aus dem Korrekturplan war notwendig, nicht vorsorglich.

---

## 7. Für die nächste Phase

- **Die Frage, für die Phase 4 gebaut wurde, ist beantwortet — anders als
  erwartet.** Nach der Upload-Prüfung bleiben **713 und 840 Prüffälle**, also
  28% und 33% aller Kunden. Die Prüfung nimmt davon 4.3% und 1.1% vorweg. Die
  Entscheidung über die Prüfmaske, die laut `03` E „zurückgestellt, bis nach
  Phase 4 messbar" war, lässt sich damit treffen — aber nicht so, wie der Plan
  es sich gedacht hat: die Zahl bleibt hoch, weil ihre Ursache nicht in der
  Eingabedatei liegt.
- **Zweiter Befund, der eine Entscheidung braucht:** Apify liefert heute mit
  rund 80 Sekunden je Aufruf statt der historischen 17. Ein Batch dauert damit
  hochgerechnet 12 Stunden statt zwei. Vor Phase 5 zu klären, weil die
  Statusseite dann einen ganzen Arbeitstag begleiten muss — und weil Huseys PC
  in Stufe 1 des Betriebs so lange laufen müsste (`UMBAUPLAN_WEBAPP.md` §10).
  Erster Blick: Speichergrenze des Apify-Kontos.
- **Eine Entscheidung des Prüfers wird gebraucht:** soll eine fehlende
  Pflichtspalte blockieren? Heute warnt sie nur, so wie `03` D es vorschreibt,
  und der Lauf scheitert danach sofort. Betrifft Phase 5 unmittelbar.
- **Die Liste der Kategoriewörter gehört überprüft.** Sie ist meine
  Zusammenstellung, nicht die des Auftraggebers. Welche Wörter auf realen Daten
  auslösen, steht in Abschnitt 6.2 — kürzen oder erweitern ist eine
  Fachentscheidung, keine technische.
- **Für Phase 5:** `pruefe_datei()` liefert einen `Pruefbericht` mit fertigen
  deutschen Meldungen und `start_moeglich`. Die Upload-Seite braucht darüber
  hinaus nichts zu wissen; `Pruefbericht.als_text()` ist die Kommandozeilen-
  Fassung, für HTML sind die Felder einzeln abrufbar.
- **Nicht gebaut, weil ausserhalb des Umfangs:** die Prüfung meldet nichts über
  doppelte Kundennummern (das tut der Lauf) und korrigiert nichts. Sie liest
  die Datei und sagt, was sie sieht.

---

## 8. Zeit

| Arbeitspaket | grober Aufwand |
|---|---|
| Freigabe, ergänzten Phasenplan und `03` D einlesen | 0.25 h |
| `upload_pruefung.py` | 1.25 h |
| Kommandozeile: Befehl `pruefen`, Prüfung vor dem Lauf | 0.5 h |
| Tests (40 neu) | 1.25 h |
| Messung der drei Prüfungen, Verknüpfung mit den Laufergebnissen | 1.0 h |
| Ursachenanalyse der Prüffälle und V1/V2-Vergleich | 0.75 h |
| Laufzeitmessung mit zehn echten Aufrufen | 0.5 h |
| Findings | 1.0 h |
| **gesamt** | **≈ 6.5 h** |

Der Code war in einem Nachmittag geschrieben. Die Zeit ging in die Messung —
und die hat die Grundannahme der Phase widerlegt. Das ist der eigentliche
Ertrag: ohne diese Zahlen wäre in Phase 5 eine Prüfmaske gebaut oder
weggelassen worden, ohne dass jemand wusste, wovon er redet.
