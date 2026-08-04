# KORREKTURPLAN — Phase 7, Version 1.1 → 1.2

Geprüft am 03.08.2026.

---

## Gesamturteil

**K1 ist im Produktivcode richtig gelöst. Der Nachweis dafür hält nicht stand.**

Die drei Tests, die K1 belegen sollen, fallen bei mir in **allen fünf Läufen**
durch. Nicht sporadisch, nicht reihenfolgeabhängig — immer.

```
FAILED test_unbekannter_apify_fehler_ist_kein_leeres_ergebnis
FAILED test_unbekannter_apify_fehler_stoppt_den_lauf_nach_zehn
FAILED test_bekannte_arten_stoppen_weiterhin_sofort

ApifyApiError.__new__() missing 2 required positional arguments:
'response' and 'attempt'
```

---

## 1. Nachgerechnet

| Prüfung | Ergebnis |
|---|---|
| K1 im Produktivcode | **richtig** — `raise QuelleNichtVerfuegbar(…, endgueltig=False)` statt `return []` |
| K2 Beschreibung berichtigt | bestätigt |
| Fünf vollständige Testläufe | 5 × **280 grün, 3 rot** |
| Zwischenmeldung im Protokoll | berichtigt |
| `google_provider.fetch_by_id` hat dieselbe Lücke | **bestätigt** — s. K2 |

Der Fehler steckt nicht in der Logik, sondern in der Testkonstruktion:

```python
fehler = ApifyApiError.__new__(ApifyApiError)
```

In `apify-client` 3.1.1 lautet die Signatur
`__new__(cls, response, attempt, *, method='GET')` — der Aufruf ohne Argumente
scheitert. Auf der Maschine des Entwicklers ist eine ältere Fassung installiert,
dort geht es durch.

---

## 2. Zu behebende Punkte

### K1 — Der Nachweis hängt an einer Bibliotheksversion · **hoch**

**Zwei Teile, beide nötig.**

**a) Tests versionsfest bauen.** Der Typ muss echt bleiben, weil `fetch_by_text`
genau darauf fängt. Eine Unterklasse mit eigenem `__new__` erfüllt beides und
funktioniert auch in 3.1.1 — geprüft:

```python
class _TestFehler(ApifyApiError):
    def __new__(cls, *a, **k):
        return Exception.__new__(cls)
    def __init__(self, art, text):
        Exception.__init__(self, text)
        self.type = art
        self.message = text
```

**b) `requirements.txt` festnageln.** Aktuell steht dort keine einzige
Versionsangabe. Das ist bei diesem Projekt kein Schönheitsfehler:

Die gesamte K1-Logik hängt an `fehler.type` und `fehler.message` — Innereien
einer fremden Bibliothek. Benennt eine künftige Fassung sie um, greifen die
sechs bekannten Fehlerarten nicht mehr, und **der Fehler aus Phase 7 ist
zurück**: erschöpftes Kontingent sieht wieder aus wie „nichts gefunden".
Genau der Fehler, dessen Behebung diese Phase ausmacht.

Mindestens `apify-client` und `thefuzz` auf die geprüften Fassungen festlegen
(`thefuzz`, weil alle Schwellenwerte aus `03 B` an dessen Verhalten hängen).
Die geprüfte Fassung ist die, unter der die fünf Läufe grün sind — in den
Findings nennen.

**Zu belegen:** Fünf vollständige Läufe, alle 283 grün, plus die verwendete
Fassung von `apify-client`.

### K2 — `google_provider.fetch_by_id` sagt dem Sachbearbeiter etwas Falsches · **hoch**

**Sein Befund, bestätigt.** Bei `requests.RequestException` wird `None`
zurückgegeben. Der Aufrufer macht daraus `NICHT_MOEGLICH (ID ungueltig)` — die
Anwendung teilt dem Sachbearbeiter also mit, sein Kunde sei bei Google gelöscht
worden, obwohl nur das Netz weg war.

**Das ist schlimmer als der Apify-Fall.** Dort war die Aussage unvollständig,
hier ist sie falsch. Der Sachbearbeiter würde einen intakten Datensatz aus dem
ERP nehmen.

Der Entwickler hat richtig gehandelt, es zu melden statt eigenmächtig zu
beheben — es lag ausserhalb von K1 und K2.

**Zu tun.** Dieselbe Form wie bei Apify:

| Fall | Verhalten |
|---|---|
| HTTP 404 / Google meldet `NOT_FOUND` | weiterhin ③ `NICHT_MOEGLICH (ID ungueltig)` — das ist die Wahrheit |
| Netzfehler, Zeitüberschreitung, HTTP 5xx | `QuelleNichtVerfuegbar(…, endgueltig=False)` — zählt zu den zehn |
| Schlüssel fehlt, ungültig, Kontingent erschöpft, Rechte fehlen | `QuelleNichtVerfuegbar` endgültig, mit deutscher Handlungsanweisung |

Kein neuer `qualitaet`-Wert, keine Änderung an `02_DATENVERTRAG.md` §3.

**Warum trotz Produktivsperre jetzt:** Der Zusammenhang liegt offen, der Eingriff
ist derselbe wie eben, und eine bekannt falsche Aussage an den Nutzer wird nicht
terminiert, sondern behoben.

---

## 3. Bestätigt

| Punkt | Urteil |
|---|---|
| K1 im Produktivcode | **richtig gelöst.** 2'500 Aufrufe → 11, `FERTIG` → `FEHLER`, drei Dateien → keine |
| Neun Kunden vor dem Stopp bleiben so | **bestätigt.** Der Korrekturplan sagt ausdrücklich, ein Ausrutscher darf einen Kunden kosten. Neun statt 2'500, und der Lauf sagt es |
| Zwischenmeldung „Der Lauf wurde gestoppt", während er weiterlief | **bestätigt behoben.** Gehört zur Meldung, die K1 verlangt hat |
| Selbstkorrektur beim Branch, offen berichtet | **richtig.** Fehler benannt, bereinigt, gemeldet — genau so |

---

## 4. Zur Kenntnis für den Auftraggeber

`origin/main` steht auf `eb75e26` und enthält damit die K1/K2-Codeänderungen,
aber nicht die Findings dazu. Die beiden Commits `b7fb414` und `eb75e26`
stammen nicht vom Entwickler dieser Runde.

Kein Schaden — der Arbeitsbranch enthält alles. Aber `main` trägt jetzt
Änderungen, die noch nicht freigegeben sind. Vor dem nächsten Merge einmal
nachsehen, was dort steht.

---

## 5. Anweisung für Version 1.2

Umfang ist K1 (a und b) und K2. Sonst nichts.

Danach `agent/findings/FINDINGS_PHASE_7_v1.2.md` mit fünf vollständigen Läufen,
der verwendeten Fassung von `apify-client`, und dem Nachweis für K2.
Dann stoppen.
