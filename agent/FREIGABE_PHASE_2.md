# FREIGABE — Phase 2

Geprüft am 03.08.2026. Branch `umbau/webapp` geklont, Tests selbst ausgeführt,
Ausgaben selbst verglichen.

**Ergebnis: freigegeben. Keine Korrekturrunde. Phase 3 kann starten.**

---

## 1. Nachgerechnete Kriterien

| Kriterium | Ergebnis |
|---|---|
| Kein Modul ausserhalb `apify_provider.py` kennt Apify-Feldnamen | bestätigt |
| Lauf über `ApifyProvider` wie Phase 1 | bestätigt |
| Lauf über `FakeProvider` ohne Netz | bestätigt |
| Timeout ~90 s → ③, kein Retry | selbst ausgeführt: 90.85 s |
| Datenbank enthält jeden Kandidaten mit `score` und `entscheid` | 16 Kandidaten, 0 ohne Score, 0 ohne Entscheid |
| `idx_kunde_nr` verhindert doppelten Kunden | vorhanden und wirksam |
| `pytest` | 93 grün, 1 übersprungen (der 90-Sekunden-Test, separat ausgeführt) |
| Datenbankschema gegen `02_DATENVERTRAG.md` §5 | kein fehlendes Feld, kein zusätzliches, alle drei Indizes |
| Ausgaben Provider-Weg vs. `clean_data` | **zeichengleich** in allen drei Dateien, selbst verglichen |

Der gemeinsame Einstieg `entscheide_kunde()` ist die richtige Lösung: eine
Fachlogik, zwei Aufrufer. Die Zeichengleichheit belegt, dass an den
Entscheidungen aus Phase 1 nichts verrutscht ist.

---

## 2. Bestätigte Annahmen des Entwicklers

### Parallelität gehört in Phase 3 — Entwickler bestätigt, Prüfer korrigiert sich

Der Prüfer hatte in der Vorprüfung verlangt, die sechs Worker in Phase 2
nachzuziehen. **Diese Forderung wird zurückgenommen.**

Begründung des Prüfers war, Phase 3 sei ohne Parallelität nicht prüfbar. Das
ist falsch: Phase 3 wird gegen den `FakeProvider` getestet, der sofort
antwortet. Die reale Laufzeit berührt kein Abnahmekriterium von Phase 3.
Parallelität gehört dorthin, wo das Ausführungsmodell entsteht.

**Aber:** Sie stand nirgends im Phasenplan. Genau deshalb konnte sie unbemerkt
verschwinden (s. Abschnitt 3). `01_PHASENPLAN.md` Phase 3 wurde deshalb um
Umfang und vier Abnahmekriterien ergänzt.

### Übrige Annahmen

| Annahme | Urteil |
|---|---|
| `FakeProvider` liest Antworten aus einer angereicherten CSV | bestätigt — deckungsgleich mit dem realen Datenfluss |
| Timeout auf zwei Ebenen (`timeout_secs` im Provider + Abschneiden im Lauf) | bestätigt — der Provider allein schützt nicht vor einem hängenden Client |
| 90-Sekunden-Test standardmässig übersprungen, per `LANGSAME_TESTS=1` aktiv | bestätigt — vom Prüfer selbst ausgeführt und bestanden |

---

## 3. Befund des Prüfers: die sechs Worker sind seit Phase 1 weg

Im Altcode lagen sie in `main.py`:

```
main.py:235   with ThreadPoolExecutor(max_workers=6) as executor:
```

`main.py` wurde in Phase 1 gelöscht — vom Prüfer freigegeben, ohne dass der
Verlust auffiel. Weder Entwickler noch Prüfer haben es bemerkt.

Referenzimplementierung: `git show a17150e~1:main.py`.

**Lehre für die weiteren Phasen:** Beim Entfernen von Altcode wird nicht nur
gefragt, ob die Datei ersetzt ist, sondern welche Mechanismen darin lagen.
`ui_manager.py` ist entsprechend zu prüfen, bevor Phase 5 die Oberfläche baut.

---

## 4. Korrektur einer Zahl aus den Findings

Die Findings rechnen aus **einer** Messung von 83 Sekunden auf 58 Stunden für
2'513 Kunden hoch. Das Betriebsprotokoll widerspricht:

> `WORKFLOW_AND_HANDOFF.md` Zeile 396: *(6 workers: ~2 hours for 2,513 customers)*
> Zeile 452: *Batch 3 & 4 ran smoothly (6 workers, ~2 hrs each, no timeouts)*

Zwei Stunden bei sechs Workern entspricht rund **17 Sekunden pro Kunde**, nicht
83. Die Differenz geht vermutlich auf den Kaltstart des Apify-Containers beim
ersten Aufruf zurück, der sich über viele Aufrufe verteilt.

**Regel ab sofort:** Aus einer einzelnen Messung wird nicht auf einen Batch
hochgerechnet. Laufzeitaussagen brauchen mindestens zehn aufeinanderfolgende
Aufrufe oder einen Beleg aus dem Betriebsprotokoll.

Der gemessene Wert selbst ist wertvoll und bleibt in den Findings — nur die
Hochrechnung wird gestrichen.

---

## 5. Zwei Nebenfunde, beide richtig

**Das TODO in `config.py` stimmt nicht.** `actor.call()` kennt `timeout_secs`
und `wait_secs`. Die Annahme, Apify erlaube keinen Timeout, war seit Beginn
falsch und hat den fehlenden Timeout jahrelang gerechtfertigt.

**Hausnummernbereiche bei Einkaufszentren** (`31-35` gegen eine einzelne
Hausnummer) erzeugen systematisch Prüffälle. Richtig eingeordnet: Die
Hausnummernlogik bleibt nach `03_ENTSCHEIDUNGEN.md` B3 unangetastet, der Fall
gehört in die **Messung von Phase 4** — dort wird entschieden, ob er häufig
genug ist, um eine Regeländerung zu rechtfertigen.

---

## 6. Änderung am Phasenplan

`01_PHASENPLAN.md`, Phase 3, ergänzt um:

- Umfang: sechs parallele Worker mit Verweis auf die Referenz in `main.py:235`
- vier Abnahmekriterien: Parallelität nachgewiesen, Abbruch und Wiederaufnahme
  **mit** aktiver Parallelität, Timeout weiterhin je Aufruf

---

Phase 3 startet nach dem aktualisierten `01_PHASENPLAN.md`.
