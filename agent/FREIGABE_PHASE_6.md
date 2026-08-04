# FREIGABE — Phase 6

Geprüft am 03.08.2026.

**Ergebnis: für den Bau freigegeben. Für den Produktivbetrieb gesperrt,
bis ein Live-Abruf vorliegt. Phase 7 kann starten.**

---

## 1. Nachgerechnet

| Prüfung | Ergebnis |
|---|---|
| Fünf vollständige Testläufe | 5 × 241 grün + 1 übersprungen |
| `data_cleaner.py` angetastet? | nein — Modus B geht am Scoring vorbei |

Die sieben Grenzfälle habe ich selbst durchgespielt, gegen `modus_b.py`:

| Fall | Ergebnis |
|---|---|
| ID gültig, gleiche Position | ① `OK (ID)` |
| dauerhaft geschlossen | ② `PRUEFUNG (geschlossen)` |
| geschlossen **und** 17 km entfernt | ② `PRUEFUNG (geschlossen)` |
| vorübergehend geschlossen | ① `OK (ID)` |
| 17 km entfernt | ② `PRUEFUNG (Standort abweichend)` |
| keine Koordinaten im Input | ① `OK (ID)` |
| kein Treffer | ③ `NICHT_MOEGLICH (ID ungueltig)` |

Alle `qualitaet`-Werte stammen aus der abschliessenden Liste in
`02_DATENVERTRAG.md` §3. Die 200-m-Referenz misst 200.4 m — Haversine korrekt.

---

## 2. Vier Annahmen, alle bestätigt und festgeschrieben

| Annahme | Urteil |
|---|---|
| Geschlossen schlägt Entfernung | **bestätigt.** Die handlungsrelevantere Aussage gewinnt. Ein geschlossener Betrieb 17 km weiter ist zuerst geschlossen |
| Genau 200 m gilt noch als „am selben Ort" | **bestätigt.** Der Vertrag sagt „> 200 m" |
| `temporarilyClosed` ist kein Prüffall | **bestätigt.** Vorübergehend geschlossen heisst, der Betrieb besteht weiter. Die Spalte führt die Information ohnehin ins ERP mit |
| Google bekommt 30 s statt 180 s | **bestätigt.** Ein Direktabruf über die ID ist kein Actor, der eine Suche fährt. 180 s wären hier keine Absicherung, sondern eine Blockade |

Alle vier stehen jetzt in `03_ENTSCHEIDUNGEN.md` B4 und C. Sie sind damit keine
Annahmen mehr, sondern Vorgaben.

---

## 3. Der Vorbehalt ist richtig gesetzt

Der Entwickler meldet „fertig mit Vorbehalt", weil kein Google-Schlüssel vorliegt.
Der `GoogleProvider` ist gegen aufgezeichnete Antworten geprüft — Feldmaske,
Umwandlung, 404, Netzfehler, fehlender Schlüssel. Nicht geprüft ist, ob eine
echte Google-Antwort so aussieht wie die Nachbildung.

**Seine Parallele zu Phase 3 trifft genau.** Dort war der Apify-Aufrufweg von
`call()` auf `start()` + `wait_for_finish()` gewechselt; erst zwei Live-Läufe
zeigten, was daran hängt. Eine Nachbildung prüft die eigene Annahme, nicht die
Wirklichkeit.

**Konsequenz — als Sperre in `03 B4` festgeschrieben:** Modus B läuft nicht mit
echten Kundendaten, bevor ein Live-Abruf dokumentiert ist.

```bash
python cli.py lauf <datei.csv> --modus B --quelle echt
```

Ein Kunde genügt. Zu belegen: Abruf erfolgreich, Dauer, alle Felder befüllt,
Datenbank vollständig.

**Das ist keine Aufgabe für den Entwickler.** Er hat keinen Schlüssel. Es hängt
an drei Dingen, die seit `UMBAUPLAN_WEBAPP.md` §8 offen sind und beim
Auftraggeber liegen: Google Places aufschalten, Kreditkartenhinterlegung, und
die Frage, ob ein privates Gmail-Konto für Firmendaten zulässig ist.

Der Bau ist davon nicht blockiert. Phase 7 kann sofort starten.

---

## 4. Zweiter Fund durch Hinschauen

Nach einem Modus-B-Lauf erklärten die Ergebniskacheln weiterhin „Mehrere
mögliche Treffer — Sie entscheiden". In Modus B gibt es nie mehrere Treffer.

Kein Test hätte das gefunden — der Text war korrektes Deutsch an der falschen
Stelle. Zweite Phase in Folge, in der das Hinschauen im echten Browser etwas
findet, das die Testsuite nicht sieht. Die Regel aus der Phase-5-Freigabe
bewährt sich.

---

## 5. Stand

| Phase | Status |
|---|---|
| 1–5 | freigegeben |
| 6 Modus B | **freigegeben, Produktivsperre bis Live-Abruf** |
| 7 Mail und Härtung | offen, neu gewichtet |
| 8 Prüfmaske | offen |

Zwei Phasen bleiben. Phase 7 trägt den Ablauf bei langen Läufen, Phase 8
schliesst den Rückweg von Datei ②.
