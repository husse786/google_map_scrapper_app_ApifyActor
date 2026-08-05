# ABSCHLUSSRUNDE

Nach Phase 8. Zwei Teile: eine Rückentwicklung schliessen, dann aufräumen.

Der zweite Teil ist der harmlosere. Der erste ist der Grund, warum diese Runde
nicht einfach ein `git rm` ist.

---

## Teil 1 — Rückentwicklung: unvollständige Suchbegriffe

### Befund

`upload_pruefung.py` prüft **nicht**, ob ein `SearchString` alle drei Teile hat.

```
'Denner, Hauptstrasse 5, 5620 Bremgarten'  →  Strasse = 'Hauptstrasse 5'
'Denner Bremgarten'                        →  Strasse = ''        keine Meldung
'Denner, 5620 Bremgarten'                  →  Strasse = '5620 Bremgarten'
```

Im alten Ablauf hat `data_preprocessor.py` genau das getan: Es teilte die
Eingabe in `_vollstaendig.csv` und `_unvollstaendig.csv` und liess nur die
vollständigen Zeilen zur Suche. Die unvollständigen wurden zuerst von Hand
korrigiert.

Diese Prüfung ist beim Umbau verschwunden. Die betroffenen Zeilen gehen jetzt
zu Apify, verbrauchen Kontingent und landen in ② mit „keine Strassentreffer" —
obwohl vor dem Start erkennbar gewesen wäre, dass sie nicht funktionieren
können.

`02_DATENVERTRAG.md` §1 sagt es bereits: *„`SearchString` hat drei
kommagetrennte Teile … Fehlt einer, ist die Zeile unvollständig."* Die
Validierung setzt das nicht um.

**Dasselbe Muster wie die sechs Worker**, die mit `main.py` verschwanden: eine
Funktion, die beim Ersetzen einer Datei still wegfiel, weil niemand fragte, was
in der Datei ausser dem Offensichtlichen noch steckte.

### Zu tun

Vierte Prüfung in `upload_pruefung.py`, Modus A. Sie **warnt**, blockiert nicht
— wie die Kostenstellen- und die Kategorieprüfung, und aus demselben Grund: Der
Nutzer soll entscheiden.

Die Meldung nennt Anzahl, Zeilennummer und Beispielzeile im Original, etwa:

> 87 Zeilen haben keinen vollständigen Suchbegriff. Erwartet werden drei durch
> Komma getrennte Teile: Name, Strasse mit Hausnummer, PLZ mit Ort.
> Beispiel Zeile 412: `Denner Bremgarten` — hier fehlen Strasse und PLZ.
> Diese Kunden landen voraussichtlich in *Zur Prüfung*.

Wie viele Teile fehlen, ist für die Meldung nicht nötig; die Beispielzeile zeigt es.

### Abnahmekriterien

- [ ] `Denner, Hauptstrasse 5, 5620 Bremgarten` löst **nicht** aus
- [ ] `Denner Bremgarten` löst aus
- [ ] `Denner, 5620 Bremgarten` löst aus
- [ ] Leerer `SearchString` löst aus
- [ ] Modus B ist unberührt — dort gibt es keinen `SearchString`
- [ ] Die Prüfung warnt und blockiert nicht
- [ ] Fünf vollständige Läufe

---

## Teil 2 — Toter Code

Sieben Dateien, nicht fünf. Zwei davon brauchen eine Entscheidung des
Auftraggebers, nicht des Entwicklers.

| Datei | Von wem aufgerufen | Entscheidung |
|---|---|---|
| `data_cleaner.py.bak` | niemand | **löschen** — die Historie liegt in Git |
| `clean_input_data.py` | niemand | **löschen** — Einmalskript mit festem Pfad |
| `csv_processor.py` | niemand | **löschen** — ersetzt durch `pipeline.py` und die Provider |
| `csv_postprocessor.py` | niemand | **löschen** — Spaltenauswahl liegt jetzt im Datenvertrag |
| `logger_config.py` | nur die beiden darüber | **löschen** — fällt mit ihnen |
| `data_preprocessor.py` | niemand | **erst nach Teil 1 löschen.** Seine Prüfung wird dort nachgebaut. Vorher bleibt es als Referenz stehen |
| `data_consolidator.py` | niemand | **nicht löschen, siehe unten** |

### `data_consolidator.py` — Frage an den Auftraggeber

Das Modul führte die Ergebnisse mehrerer Batches zusammen. Die Webapp kennt nur
einzelne Aufträge; ein Zusammenführen gibt es nicht.

Ob das fehlt, hängt an einer Frage, die der Entwickler nicht beantworten kann:
**Wird weiterhin in Batches zu 2'513 gearbeitet, oder geht künftig die ganze
Datei in einem Auftrag durch?**

Die Zeilengrenze liegt bei 10'000 (`03 C`), der Gesamtbestand bei rund 7'539
Kunden. Ein Auftrag würde also reichen — dann ist das Modul überflüssig. Wird
weiter in Batches gearbeitet, fehlt die Funktion in der Webapp.

**Bis zur Antwort bleibt die Datei stehen.** Nicht löschen, nicht einbauen.

### Abnahmekriterien Teil 2

- [ ] Die fünf zum Löschen freigegebenen Dateien sind entfernt
- [ ] Fünf vollständige Läufe, unveränderte Testzahl aus Teil 1
- [ ] Kein Import zeigt mehr auf eine entfernte Datei
- [ ] `README.md` erwähnt keine entfernte Datei
- [ ] `data_preprocessor.py` und `data_consolidator.py` stehen noch da, mit je
      einem Kommentar am Kopf, warum

---

## Reihenfolge

Teil 1 zuerst, vollständig und abgenommen. Erst danach Teil 2 — sonst wird die
Referenz für die nachzubauende Prüfung gelöscht, bevor sie nachgebaut ist.

Findings in `agent/findings/FINDINGS_ABSCHLUSSRUNDE.md`, beide Teile getrennt.
