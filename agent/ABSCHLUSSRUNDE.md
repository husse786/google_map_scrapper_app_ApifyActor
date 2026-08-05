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
| `data_consolidator.py` | niemand | **löschen** — Entscheidung des Auftraggebers, s. unten |

### `data_consolidator.py` — beantwortet, wird gelöscht

Das Modul führte die Ergebnisse mehrerer Batches zusammen. Der Auftraggeber hat
die Herkunft geklärt: Er teilte eine Liste von rund 7'000 Kunden **von Hand in
Excel** in fünf bis sechs Dateien auf, liess sie einzeln laufen und stand danach
vor fünf mal drei Ausgabedateien, die so niemandem zu geben waren. Das Modul
führte sie wieder zusammen.

Das Aufteilen war eine Notlösung für die alte Anwendung: kein sichtbarer
Fortschritt, kein Fortsetzen nach einem Abbruch, also kleinere Häppchen. Beides
gibt es jetzt — die Zeilengrenze liegt bei 10'000 (`03 C`), der Gesamtbestand
bei rund 7'539, und ein unterbrochener Lauf setzt fort (Phase 3).

Damit entfällt der Anlass. **Löschen.** Sollte das Zusammenführen je wieder
gebraucht werden, liegt es in der Git-Historie. Etwas stehen zu lassen „für den
Fall" schliesst `03 E` aus.

---

## Teil 2a — drei Punkte aus der Abnahme von Teil 1

Vor den Löschungen. Alle drei betreffen, was der Nutzer liest.

### A — Doppelmeldung auflösen

Drei der vier Arten unvollständiger Zeilen werden zusätzlich als „Kostenstelle
im Strassenfeld" gemeldet. Bei `Denner Bremgarten` **gibt es kein Strassenfeld**
— die Aussage ist nicht ungenau, sie ist falsch.

Die Kostenstellenprüfung prüft künftig nur Zeilen, deren Suchbegriff vollständig
ist. Die Vollständigkeitsprüfung kommt zuerst; wer dort gemeldet wurde,
erscheint nicht ein zweites Mal unter einem falschen Etikett.

Die Zeilenzahlen in den Phase-4-Tests ändern sich dadurch. Das ist richtig so —
sie hielten ein Verhalten fest, das eine falsche Aussage enthielt. Die Anpassung
gehört in die Findings, mit den Zahlen vorher und nachher.

### B — «1 Zeilen haben»

Die beiden Meldungen aus Phase 4 bilden den Singular nicht. Die neue Prüfung tut
es bereits (`upload_pruefung.py:360`). Dieselbe Form für die beiden alten.

### C — README kennt die Prüfmaske nicht

Schritt 4 endet beim Herunterladen. Dass Prüffälle im Browser entschieden
werden, steht nirgends — Phase 8 wurde mit dieser Lücke abgenommen, das ist ein
Versäumnis des Prüfers.

Ein eigener Schritt zwischen „Lauf" und „Ergebnis": was die Prüfmaske ist, wie
man sie erreicht, dass mit den Tasten `1`–`9` und `0` entschieden wird, und dass
entschiedene Fälle in die ERP-Datei wandern. In der Sprache der übrigen
Schritte — für jemanden ohne Vorkenntnisse.

### Abnahmekriterien Teil 2a

- [ ] `Denner Bremgarten` erscheint nur noch unter „unvollständiger Suchbegriff"
- [ ] `Emil Frey AG, KST 715611 0, 5745 Safenwil` erscheint weiterhin unter
      „Kostenstelle" — die Zeile ist vollständig, nur der Inhalt taugt nicht
- [ ] Keine Meldung sagt mehr «1 Zeilen»
- [ ] Das README beschreibt die Prüfmaske als eigenen Schritt
- [ ] Angepasste Phase-4-Zahlen in den Findings, vorher und nachher

---

### Abnahmekriterien Teil 2

- [ ] Die sechs zum Löschen freigegebenen Dateien sind entfernt
- [ ] Fünf vollständige Läufe, unveränderte Testzahl aus Teil 1
- [ ] Kein Import zeigt mehr auf eine entfernte Datei
- [ ] `README.md` erwähnt keine entfernte Datei
- [ ] `data_preprocessor.py` steht noch da, mit einem Kommentar am Kopf, warum

---

## Reihenfolge

Teil 1 ist abgenommen. Jetzt **Teil 2a**, dann **Teil 2**. In dieser Reihenfolge:
Teil 2 löscht `data_preprocessor.py`, und bis Teil 2a durch ist, bleibt die
Referenz nützlich.

Findings in `agent/findings/FINDINGS_ABSCHLUSSRUNDE_TEIL2.md`, beide Teile
getrennt.
