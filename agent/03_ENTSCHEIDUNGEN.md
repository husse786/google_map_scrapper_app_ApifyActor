# 03 — ENTSCHEIDUNGEN

Bereits getroffen. Nicht neu bewerten, nicht „verbessern", nicht abweichen.
Höchste Priorität aller Dokumente.

Wer etwas hier ändern will, schreibt es in die Findings — und baut es trotzdem
erst einmal wie hier beschrieben.

---

## A — Technik

| Frage | Entscheidung | Warum nicht anders |
|---|---|---|
| Sprache | Python 3.11+ | 80% der Fachlogik existiert bereits und ist erprobt |
| Web | FastAPI | Upload, Status, Download — mehr wird nicht gebraucht |
| Oberfläche | Jinja2 + HTMX | kein npm, kein Build, kein React |
| Datenbank | SQLite, eine Datei | ein Nutzer, ein Job |
| Hintergrund | `threading.Thread` + Status in SQLite | kein Celery, kein Redis |
| Fuzzy-Matching | `thefuzz` | Wechsel würde alle Schwellenwerte entwerten |
| Tests | `pytest` | — |
| Betrieb | `uvicorn`, Port 8000 | — |

Weitere Bibliotheken darfst du frei wählen und in den Findings vermerken.

---

## B — Fachliche Schwellenwerte

### B1 · Strassenvergleich

**`fuzz.partial_ratio` wird ersetzt durch `fuzz.ratio`, Schwelle ≥ 90.**

Der heutige Code nutzt `partial_ratio > 90`. Das prüft Teilstrings und lässt
falsche Strassen durch. Gemessen an echten Fällen:

| Input | Google | `ratio` | `partial_ratio` | soll |
|---|---|---|---|---|
| Dorfstrasse | Oberdorfstrasse | 85 | **100** | ablehnen |
| Rainweg | Rebrainweg | 82 | **100** | ablehnen |
| Bahnhofstrasse | Bahnhofplatz | 62 | 76 | ablehnen |
| Seetalstrasse | Lenzburgerstrasse | 60 | 73 | ablehnen |
| Hundwilerhöhe | Hundwillerhöche | **93** | 89 | annehmen |
| St. Bernhardstrasse | St.Bernhardstrasse | 97 | 94 | annehmen |
| Wohlerstrasse | Wohlerstr. | 100 | 100 | annehmen |

`ratio` trennt sauber: höchster Ablehner 85, tiefster Annehmer 93.
Schwelle 90 liegt in der Lücke, mit Abstand nach beiden Seiten.
`partial_ratio` trennt gar nicht.

Hausnummern-Logik bleibt unverändert: sind **beide** vorhanden, müssen sie
exakt gleich sein. Fehlt eine, genügt der Strassenname.

### B2 · Einzeltreffer (heutige Stufe 3)

Heute wird ein einzelner Überlebender **ungeprüft** akzeptiert. Ein
Namens-Mindestscore allein wäre falsch, weil Rebranding (Volg → Spar an
derselben Adresse) auf 0 fällt und trotzdem korrekt ist.

**Regel: Ein Einzeltreffer geht nur nach ① wenn mindestens eine Bedingung gilt.**

```
(1) Namensscore >= 60
ODER
(2) Strasse UND Hausnummer stimmen exakt überein
```

Sonst → ② mit `PRUEFUNG (Einzeltreffer unsicher)`.

Bedingung (2) fängt Rebranding: gleiche Adresse, neuer Name → bleibt akzeptiert.
Bedingung (1) fängt Fälle, in denen Google keine Hausnummer liefert.

### B3 · Unverändert übernehmen

Diese Werte sind produktiv erprobt. Nicht anfassen.

| Wert | Bleibt |
|---|---|
| Score-Schwelle für „hoher Treffer" | `80` |
| Dynamischer Abstand Platz 1 zu 2 | `30` |
| Gewichtung Markenname | 70% erstes Wort / 30% Gesamttitel |
| Gewichtung generisches Wort | 30% erstes Wort / 70% Gesamttitel |
| Liste `GENERIC_FIRST_WORDS` | wie heute |
| Liste `LEGAL_SUFFIXES` | wie heute |
| PLZ-Vergleich | exakt; fehlt eine Seite, durchlassen |
| `token_set_ratio` für Gesamttitel | bleibt |

Die bekannte Schwäche von `token_set_ratio` bei Kurzkürzeln (`bp`, `LS`, `DLZ`)
ist **nicht** Teil dieses Umbaus. Nicht anfassen.

### B4 · Modus B — Plausibilitätsprüfung

**Sperre für den Produktivbetrieb.** Modus B darf erst mit echten Kundendaten
laufen, wenn ein Live-Abruf gegen die echte Google-API dokumentiert ist. Bis
dahin ist nur belegt, dass der Code gegen **nachgebildete** Antworten richtig
arbeitet — nicht, dass eine echte Google-Antwort so aussieht. Dieselbe Lücke
schlug in Phase 3 zu, als sich der Apify-Aufrufweg änderte.

Ebenfalls offen und ausserhalb der Entwicklung: Zulässigkeit eines privaten
Gmail-Kontos für Firmendaten, und die Kreditkartenhinterlegung bei Google
(`UMBAUPLAN_WEBAPP.md` §8). Beides blockiert den Betrieb, nicht den Bau.

| Fall | Ergebnis |
|---|---|
| `permanentlyClosed` = wahr | ② `PRUEFUNG (geschlossen)` |
| Distanz zu gespeicherter Position **> 200 m** | ② `PRUEFUNG (Standort abweichend)` |
| `lat`/`lng` fehlen in der Eingabe | keine Distanzprüfung, kein Prüffall |
| placeId liefert nichts | ③ `NICHT_MOEGLICH (ID ungueltig)` |
| Name hat sich geändert | ① — Rebranding ist normal, **kein** Prüffall |
| `temporarilyClosed` = wahr | ① — vorübergehend geschlossen heisst, der Betrieb besteht weiter. Die Spalte `temporarilyClosed` führt die Information ins ERP mit |
| geschlossen **und** Standort abweichend | ② `PRUEFUNG (geschlossen)` — geschlossen schlägt Entfernung, es ist die handlungsrelevantere Aussage |
| Entfernung genau 200 m | ① — der Vertrag sagt „> 200 m" |

Distanz per Haversine. 200 m trennt „anderes Gebäude" von GPS-Ungenauigkeit
und Eingangs-versus-Gebäudemitte.

---

## C — Betriebsgrenzen

| Grenze | Wert | Zweck |
|---|---|---|
| Timeout pro API-Aufruf | **180 Sekunden** | fehlt heute völlig; hängender Lauf blockiert unbegrenzt. Von 90 s heraufgesetzt: gemessene Kaltstarts lagen bei 83, 87 und **91** Sekunden — 90 s hätte gesunde Aufrufe fälschlich nach ③ geschoben. Der Timeout soll Hänger stoppen, nicht Tempo erzwingen |
| Timeout Google Place Details | **30 Sekunden** | (Ergänzt nach Phase 6.) Ein Direktabruf über die ID ist kein Actor, der eine Suche fährt — er antwortet in Sekundenbruchteilen. 180 s wären hier kein Schutz, sondern eine Blockade |
| Verhalten bei Timeout | **wie ein Netzfehler**, zählt zu den zehn hintereinander | (Geändert nach Phase 7 v1.2.) Ursprünglich stand hier „wie leeres Ergebnis → ③". Das war falsch, aus demselben Grund wie K1 und K2: **eine Zeitüberschreitung ist keine Antwort.** In Modus B wird daraus die Aussage, der Kunde sei bei Google gelöscht — das stimmt nicht. Ein einzelner Ausrutscher kostet weiterhin einen Kunden; hängt die Quelle systematisch, stoppt der Lauf nach zehn statt 2'500 Zeilen in ③ zu schreiben |
| Retry nach Timeout | **keiner** | unverändert. Der Zähler ersetzt keine Wiederholung |
| Parallele Worker (Apify) | **6** | produktiv getestet, stabil |
| Maximale Zeilen pro Upload | **10'000** | Schutz vor versehentlichem Kontingentverbrauch |
| Automatische Wiederholung | **keine** | verdreifacht Laufzeit und Kosten; dafür gibt es Datei ③ |
| Gleichzeitige Jobs | **1** | zweiter Start wird abgewiesen mit Hinweis auf laufenden Job |

---

## D — Upload-Validierung (Phase 4)

Diese drei Prüfungen sind Pflicht.

**Fehlende Pflichtspalte blockiert den Start.** (Geändert nach Phase 4.) Ohne
`SearchString`, `PLZ` oder `KundenNr` kann der Lauf nicht arbeiten — er würde
sofort abbrechen. Eine Warnung, die der Nutzer wegklicken kann, führt hier nur
in eine Sackgasse.

Die anderen beiden Prüfungen **warnen**, blockieren nicht. Der Nutzer
entscheidet, ob er trotzdem läuft.

| Prüfung | Auslöser | Meldung nennt |
|---|---|---|
| Pflichtspalten | Spalte fehlt | welche, und wie Zeile 1 aussehen muss |
| Kostenstelle statt Strasse | Strassenteil ohne Buchstabenfolge ≥ 4, oder beginnt mit `KST`/`KOST` | Anzahl + Beispielzeile im Original |
| Titel ist nur Kategorie | Titel besteht ausschliesslich aus Wörtern der `GENERIC_FIRST_WORDS`-Liste | Anzahl + Beispielzeile |

**Diese Einschätzung war falsch und ist durch Messung widerlegt.** (Phase 4.)

Ursprünglich stand hier, das sei der wirkungsvollste Punkt im Projekt — 4'288
von 5'188 Prüfzeilen seien Kostenstellen. Die Messung an zwei realen Batches
ergab **14 und 11 betroffene Zeilen**, von denen je eine als „keine
Strassentreffer" endete.

Zwei Gründe: der ERP-Export ist besser geworden (3.9% → 1.6%), und die
bestehende Vorverarbeitung entfernt von dem Rest nochmals zwei Drittel.

Die Prüfungen bleiben — sie kosten nichts und schaden nicht. Sie sind aber
**kein Hebel**. Die Prüffälle entstehen zu 58–64% durch „andere Strasse" und zu
19–22% durch „gleiche Strasse, andere Hausnummer". Das ist die Grenze des
Abgleichs, kein Eingabefehler, und vor dem Lauf nicht erkennbar.

**Die Liste der Kategoriewörter** (77 Einträge, mehrsprachig) ist geprüft und
freigegeben. Sie löst nur aus, wenn der Titel ausschliesslich aus
Kategoriewörtern besteht — „Bar Rouge" und „Cafe Federal" lösen nicht aus.
Änderungen an der Liste nur über einen Korrekturplan.

---

## E — Was bewusst nicht gebaut wird

Nicht bauen, auch nicht „vorbereitend", auch nicht als Schnittstelle:

- Login, Benutzerverwaltung, Rollen, Mandanten
- Job-Warteschlange mit Prioritäten, Redis, Celery
- WebSockets — Statusseite pollt alle 5 Sekunden
- React, Vue, npm, Build-Pipeline
- Docker (kommt frühestens beim Serverumzug)
- ~~Prüfmaske im Browser~~ — **wird gebaut**, als Phase 8.
  Grund ist der Ablauf: Datei ② hat keinen Rückweg, der Nutzer hätte zwei
  ERP-Importe statt einem. Das gilt unabhängig von der Fallzahl.
  Die Messung aus Phase 4 (713 und 840 Prüffälle je Batch, nicht durch bessere
  Eingabeprüfung verkleinerbar) bestimmt nur, dass sie früh statt spät kommt.
- Automatische Wiederholung fehlgeschlagener Aufrufe
- Mehrsprachigkeit
