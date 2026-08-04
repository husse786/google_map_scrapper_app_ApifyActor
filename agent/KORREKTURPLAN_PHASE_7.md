# KORREKTURPLAN — Phase 7, Version 1.0 → 1.1

Geprüft am 03.08.2026.

---

## Gesamturteil

**Der wichtigste Fund des ganzen Umbaus — aber nur zu zwei Dritteln behoben.**

Fünf vollständige Testläufe, 277 grün. README sauber, kein Tkinter-Rest.
Die Analyse des Fehlers ist richtig, die Umsetzung lässt einen Weg offen, auf
dem derselbe Fehler weiterhin auftreten kann.

---

## 1. Nachgerechnet

| Prüfung | Ergebnis |
|---|---|
| Fünf vollständige Testläufe | 5 × 277 grün + 1 übersprungen |
| Fehler bestand vor Phase 7 | bestätigt — Stand Phase 6 gab `except ApifyApiError` ein leeres Ergebnis zurück |
| Sechs endgültige Fehlerarten mit deutscher Handlungsanweisung | vorhanden, plus sieben Stichwörter als Netz |
| Netzfehler zählen bis 10 hintereinander | `MAX_FEHLSCHLAEGE_HINTEREINANDER = 10` in `pipeline.py` |
| README ohne Reste der Tkinter-Anwendung | bestätigt |
| Toter Code | bestätigt und **zusammenhängender als gemeldet** — s. Abschnitt 4 |

---

## 2. Zu behebende Punkte

### K1 — Unbekannte Apify-Fehler landen weiterhin stillschweigend in ③ · **hoch**

**Befund.** `apify_provider.py`:

```python
except ApifyApiError as fehler:
    _pruefen_ob_endgueltig(fehler)
    return []
```

`_pruefen_ob_endgueltig` wirft nur bei den sechs bekannten Arten oder wenn eines
der sieben Stichwörter im Text steht. **Jeder andere Apify-Fehler fällt durch
und wird zum leeren Ergebnis** — der Kunde landet in ③, der Lauf macht weiter.

Der Zähler für aufeinanderfolgende Fehlschläge greift hier nicht, weil kein
Fehler weitergereicht wird. Ein systematisches Problem mit einer Fehlerart, die
nicht auf der Liste steht, schreibt weiterhin 2'500 Kunden nach ③ und nennt den
Lauf `FERTIG`.

**Der Kern des Arguments:** Ein `ApifyApiError` ist **nie** „nichts gefunden".
Nichts gefunden heisst `SUCCEEDED` mit leerem Datensatz — dieser Pfad existiert
bereits und bleibt unberührt. Ein API-Fehler bedeutet, dass die Frage nicht
beantwortet wurde. Das ist kein Ergebnis.

**Zu tun.** Nach `_pruefen_ob_endgueltig` nicht `return []`, sondern als
vorübergehender Fehlschlag weiterreichen:

```python
raise QuelleNichtVerfuegbar(<deutsche Meldung>, endgueltig=False) from fehler
```

Damit gilt: bekannte Arten stoppen sofort mit Erklärung, unbekannte stoppen nach
zehn hintereinander. Ein einzelner Ausrutscher kostet weiterhin nur einen Kunden.

Nicht anfassen: die sechs Fehlerarten, die sieben Stichwörter, die Grenze von
zehn, und der Pfad `status != 'SUCCEEDED'`.

**Zu belegen:** Ein Test mit einem Provider, der einen `ApifyApiError` einer
nicht gelisteten Art wirft — der Lauf endet nach zehn Kunden mit `FEHLER`, nicht
mit `FERTIG` und 2'500 Zeilen in ③.

### K2 — Beschreibung widerspricht dem Verhalten · niedrig

Die Beschreibung von `fetch_by_text` sagt weiterhin, ein leeres Ergebnis komme
auch dann, wenn „Apify einen Fehler meldet", und der Aufrufer behandle alle
drei Fälle gleich. Seit Phase 7 stimmt das nicht mehr, nach K1 noch weniger.

Wer das liest, baut den Fehler beim nächsten Mal wieder ein.

---

## 3. Bestätigt

| Punkt | Urteil |
|---|---|
| Der Fehler selbst | **der wertvollste Fund des Umbaus.** Ein Lauf, der sich `FERTIG` nennt und 2'500 Kunden fälschlich nach ③ schreibt, ist schlimmer als ein Absturz — er sieht wie ein Ergebnis aus |
| Sechs Fehlerarten mit Handlungsanweisung, verarbeitete Kunden bleiben, Lauf fortsetzbar | bestätigt |
| Netzfehler bis 10 hintereinander | bestätigt |
| Gedankenstrich im Betreff (`=?utf-8?b?4oCU?=`) | **bestätigt.** Wieder ein Fund, den nur der echte Versand zeigt. Ein Ersatzserver hätte das Objekt durchgereicht |
| `FEHLER` heisst in der Oberfläche „Gestoppt" | **bestätigt.** „Abgebrochen" für zwei verschiedene Dinge schickt den Nutzer auf die falsche Fährte |
| README neu geschrieben | bestätigt, mit vier Tests gegen einen Rückfall |

---

## 4. Toter Code — Vorschlag angenommen, mit Ergänzung

Seine Einschätzung, im Rahmen einer Mail-Phase sei der falsche Zeitpunkt, ist
richtig. Eine kurze Runde nach Phase 8, mit einer Entscheidung je Datei.

**Ergänzung:** `logger_config.py` wird nur noch von `csv_processor.py` und
`csv_postprocessor.py` importiert — also ausschliesslich von totem Code. Die
vier Dateien hängen zusammen und werden gemeinsam entschieden, nicht einzeln.
`data_cleaner.py.bak` und `clean_input_data.py` haben gar keine Verwendung mehr.

---

## 5. Offene Punkte beim Auftraggeber

Beide ausserhalb der Entwicklung, beide blockieren den Betrieb, nicht den Bau:

- **SMTP-Freigabe durch ICT.** Bis dahin läuft alles ohne Mail und protokolliert,
  was es verschickt hätte.
- **Der Versand ist gegen einen lokalen Server geprüft, nicht gegen ein
  Firmen-Relais** mit Anmeldung und Zertifikat. Kleinere Lücke als bei Google,
  aber dieselbe Art. Sobald das Relais steht: ein echter Versand, dokumentiert.

Die Produktivsperre für Modus B aus `03 B4` bleibt bestehen.

---

## 6. Anweisung für Version 1.1

Umfang ist K1 und K2. Sonst nichts.

Danach `agent/findings/FINDINGS_PHASE_7_v1.1.md` mit dem Nachweis aus K1 und
fünf vollständigen Testläufen. Dann stoppen.
