# KORREKTURPLAN — Phase 3, Version 1.0 → 1.1

Geprüft am 03.08.2026. Branch geklont, Tests selbst ausgeführt, Messwerte
unabhängig nachgestellt.

---

## Gesamturteil

**Fachlich stark. Drei Punkte zu beheben, keiner betrifft die Kernlogik.**

Alle drei Eigenbefunde des Entwicklers waren richtig und wichtig — besonders der
Notschalter, der dem Provider zuvorkam. Ohne diese Korrektur wäre bei jedem
Timeout ein Apify-Lauf verwaist weitergelaufen und hätte Kontingent verbraucht.
Das hätte niemand bemerkt.

---

## 1. Unabhängig nachgestellt

| Prüfung | Bericht | Prüfer |
|---|---|---|
| Parallelität, 60 Kunden à 0.3 s | 18.32 → 3.06 s, Faktor 5.99 | 18.07 → 3.06 s, **Faktor 5.90** — bestätigt |
| Abbruch, 200 Kunden à 30 s | 0.10 s | **0.16 s**, Status `ABGEBROCHEN`, keine Dateien — bestätigt |
| Wiederaufsatz über Tabelle `kunde` | Annahme | im Code bestätigt (`pipeline.py:146`) |
| Testlauf gesamt | 114 grün + 1 übersprungen | **113 grün, 1 rot** — s. K1 |

---

## 2. Zu behebende Punkte

### K1 — Ein Abnahmetest ist rot und wurde als grün gemeldet · **hoch**

**Befund.** `test_harter_abbruch_und_wiederaufnahme[6]` schlägt fehl, sobald die
Variante `[1]` vorher gelaufen ist — in vier von fünf Durchläufen. Isoliert
besteht er. Gemeldet wurden „alle acht Kriterien grün".

```
assert 11 == (20 - 8)     11 nachgeholt, Zähler stand auf 8
assert  6 == (20 - 13)     6 nachgeholt, Zähler stand auf 13
```

**Ursache — nicht im Produktivcode.** Der Test prüft in der letzten Zeile

```python
assert len(provider.aufrufe) == 20 - vorher_erledigt
```

gegen `kunden_erledigt`, also gegen genau den Zähler, den der Entwickler selbst
zu Recht als untauglichen Wiederaufsatzpunkt erkannt hat. Der Produktivcode setzt
korrekt auf `kunden_lesen()` auf. Der Test tut es nicht.

**Wichtig:** Alle sicherheitsrelevanten Prüfungen davor bestehen — kein Kunde
doppelt, keiner verloren, Status `FERTIG`. Es ist ein Buchhaltungsfehler im
Test, kein Produktfehler.

**Zu tun.**
1. Die Sollzahl aus der Tabelle `kunde` ableiten statt aus `kunden_erledigt`.
2. Testlauf **fünfmal hintereinander vollständig** ausführen; alle fünf grün.
3. In den Findings die fünf Läufe belegen.

**Regel ab sofort:** Ein Kriterium gilt erst als grün, wenn der **vollständige**
Testlauf grün ist, mehrfach hintereinander. Einzeln bestandene Tests zählen
nicht — genau diese Reihenfolgeabhängigkeit war hier der Fall.

### K2 — Timeout von 90 auf 180 Sekunden · **hoch**

**Befund des Entwicklers, bestätigt.** Gemessene Kaltstarts: 83, 87 und **91**
Sekunden. Einer lag bereits über der Grenze. Ein Timeout, der gesunde Aufrufe
trifft, schiebt Kunden grundlos nach ③ — das ist Datenverlust, der wie ein
Ergebnis aussieht.

**Das ist ein Fehler in meiner Vorgabe, nicht in der Umsetzung.** Die 90 Sekunden
stammen aus `03_ENTSCHEIDUNGEN.md` C und wurden ohne Messung gewählt. Der Zweck
des Timeouts ist, Hänger zu stoppen, nicht Tempo zu erzwingen. 180 Sekunden
erfüllen den Zweck weiterhin.

**Zu tun.** `03_ENTSCHEIDUNGEN.md` C ist bereits auf 180 s geändert.
Wert im Code nachziehen. Der Abstand zwischen Aussenschutz und Provider-Frist
(fünf Sekunden) bleibt wie gebaut — die Reihenfolge war der Kern des Befunds.
Der Timeout-Test wird auf den neuen Wert angepasst.

Keine automatische Wiederholung. `03_ENTSCHEIDUNGEN.md` C bleibt in diesem Punkt
unverändert.

### K3 — Der neue Aufrufweg hat noch nie erfolgreich geliefert · **hoch**

**Befund des Entwicklers, richtig erkannt und selbst gemeldet.**
`actor.call()` wurde durch `start()` + `wait_for_finish()` ersetzt. Beide
Live-Läufe endeten im Timeout. Ein **erfolgreicher** Abruf über den neuen Weg
ist damit nicht belegt.

**Warum das jetzt zählt.** Phase 4 misst an echten Daten. Läuft der neue
Aufrufweg im Erfolgsfall nicht sauber, misst Phase 4 Unsinn — und der Fehler
wäre dann in einer Datei zu suchen statt in einer Zeile Code.

**Zu tun.** Nach K2 ein einzelner echter Apify-Aufruf, erfundene Kundennummer,
öffentliches Geschäft als Suchbegriff. Zu belegen:
- Lauf endet mit Erfolg, nicht im Timeout
- Dauer
- alle Kandidatenfelder befüllt, Entscheid und Datenbank vollständig
- der Apify-Lauf wird sauber beendet, nicht verwaist

Wenn der Aufruf erneut in den Timeout läuft, **nicht** die Frist weiter erhöhen,
sondern melden und stoppen.

---

## 3. Bestätigte Annahmen

| Annahme | Urteil |
|---|---|
| Wiederaufsatz über Tabelle `kunde` statt `kunden_erledigt` | **bestätigt und in `02_DATENVERTRAG.md` §6 übernommen.** Die Vorgabe war falsch, die Abweichung richtig. Der Zähler dient ab jetzt ausdrücklich nur der Anzeige |
| Notschalter greift vor der Provider-Frist, Apify bekommt 5 s weniger | **bestätigt.** Der wichtigste Fund dieser Phase |
| Höchstens zwölf Abfragen gleichzeitig unterwegs statt unbegrenztes Vorauslaufen | **bestätigt.** Unbegrenztes Vorauslaufen hätte Wiederaufnahme praktisch wertlos gemacht |

---

## 4. Zu den offenen Punkten des Entwicklers

**Kaltstart.** Sein Vorschlag, zehn aufeinanderfolgende Aufrufe in Phase 4 zu
messen, wird übernommen und dort als Messpunkt aufgenommen. Bis dahin schützt
K2. Die Frage, warum das Betriebsprotokoll rund 17 Sekunden nennt und die
Einzelmessung 85, bleibt offen — die Antwort liegt vermutlich darin, dass sich
der Containerstart über viele Aufrufe verteilt. Das klärt Phase 4, nicht diese.

**Erfolgreicher Abruf.** Wird zu K3.

---

## 5. Anweisung für Version 1.1

Umfang ist K1, K2, K3. Sonst nichts — keine Refaktorierung, kein Vorgriff auf
Phase 4.

Danach `agent/findings/FINDINGS_PHASE_3_v1.1.md` mit:
- fünf vollständige Testläufe, alle grün
- Timeout-Test gegen 180 s
- Protokoll des erfolgreichen Apify-Abrufs

Dann stoppen. Auf `origin/umbau/webapp` pushen, nicht nur lokal committen.
