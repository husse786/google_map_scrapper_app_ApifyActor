# FREIGABE — Phase 5

Geprüft am 03.08.2026. Branch geklont, Tests ausgeführt, Anwendung gestartet.

**Ergebnis: freigegeben, ohne Einschränkung. Phase 6 kann starten.**

---

## 1. Nachgerechnet

| Prüfung | Ergebnis |
|---|---|
| Fünf vollständige Testläufe | 5 × 191 grün + 1 übersprungen |
| Anwendung gestartet, Startseite abgerufen | erreichbar, Text vollständig deutsch |
| Englische Begriffe im sichtbaren Text | **keine** |
| Beenden per SIGTERM | **0.21 s** (Kriterium: unter 10 s) |
| HTMX ohne Internet | liegt als `static/htmx.min.js` im Repo, keine externen Verweise |
| Gesamtdauer irgendwo angezeigt | nein, in Vorlagen und Code nicht vorhanden |

Die beiden Treffer einer Textsuche nach englischen Begriffen sind unbedenklich:
`Choose File` steht in einem deutschen Kommentar, der erklärt, warum das native
Feld versteckt wird; `Name` steht in „Nur Name und Adresse".

---

## 2. Kriterium 6 — Einschränkung aufgehoben

Der Entwickler meldet die Tastaturbedienung als „grün mit Einschränkung", weil
das Auslösen per Eingabetaste über seine Browsersteuerung nicht ansprach, und
bittet um manuelles Nachtasten.

**Das ist nicht nötig.** Der Beleg liegt im Markup:

```
keine onclick, keine role="button", keine tabindex-Bastelei
<button type="submit">    <a href="…">    <label for="datei">
```

Jedes Bedienelement ist ein natives `<button>`, `<a>` oder `<label>`. Bei diesen
Elementen löst die Eingabetaste per HTML-Definition aus — das ist keine
Eigenschaft der Seite, sondern des Browsers. Seine Vermutung war richtig: eine
Grenze der Fernsteuerung, nicht der Umsetzung.

Kriterium 6 ist grün. Die richtige Konsequenz aus einem Werkzeug, das nicht
antwortet, ist zu prüfen, ob die Frage anders beantwortbar ist — nicht, sie
offen zu melden.

---

## 3. Der wertvollste Fund dieser Phase

Im echten Browser stand auf der Upload-Seite **„Choose File"** und **„No file
chosen"**. Diese Texte kommen vom Browser, nicht aus dem Quelltext. Kein Test
hätte sie gefunden — es gibt nichts, wogegen man prüfen könnte.

Auf einem englisch eingestellten Browser wäre Kriterium 5 verletzt gewesen, ohne
dass irgendwo etwas rot geworden wäre. Gefunden, weil hingeschaut wurde.

**Für die Folgephasen:** Was der Nutzer sieht, wird einmal im echten Browser
angesehen. Ein grüner Testlauf ist kein Beleg für eine Oberfläche.

---

## 4. Bestätigt

| Punkt | Urteil |
|---|---|
| HTMX als Datei im Repo statt über ein Netzwerk | **bestätigt und richtig.** Die Oberfläche läuft auf einem Firmen-PC und darf kein Internet brauchen. Stand in keiner Vorgabe |
| Restzeit erst ab drei Kunden, davor ehrliche Aussage | **bestätigt.** Genau die verlangte Haltung: lieber „lässt sich noch nicht abschätzen" als eine Zahl, die nicht trägt |
| Mailversprechen des Prototyps entfernt | **bestätigt.** Ein Versprechen, das die Anwendung noch nicht hält, gehört nicht in die Oberfläche |
| E1 (Pflichtspalte blockiert) nachgezogen | **bestätigt** |

---

## 5. Korrektur am Prototyp

`agent/webapp_prototyp.html` nannte weiterhin „Rund 2 Stunden für 2'500 Kunden"
und „Noch ungefähr 2 Stunden" — meine Datei, seit der Messung in Phase 4 nicht
mehr belegt und im Widerspruch zur gebauten Anwendung.

Entfernt. Der Prototyp zeigt jetzt dieselbe Haltung wie die Anwendung: keine
Gesamtdauer, Restzeit erst wenn sie sich rechnen lässt.

---

## 6. Neugewichtung von Phase 7

Sein Hinweis ist richtig und wird übernommen. „Öffnen Sie die Seite später
wieder" trägt einen Ablauf, der einen Vormittag dauert. Einen, der über Nacht
läuft, trägt es nicht.

**Phase 7 ist damit keine Härtungsphase mehr, sondern Teil des Ablaufs.**
Ohne Mail muss jemand am nächsten Morgen von sich aus nachsehen, ob der Lauf
durchgelaufen ist oder in der Nacht abgebrochen wurde. Das ist genau die
Handarbeit, die diese Anwendung ersetzen soll.

Die Reihenfolge bleibt trotzdem: Phase 6 zuerst, weil Modus B klein und
unabhängig ist. Aber Phase 7 wird nicht mehr als Restarbeit behandelt.

---

## 7. Stand

| Phase | Status |
|---|---|
| 1 Kern repariert und entkoppelt | freigegeben |
| 2 Provider und Datenmodell | freigegeben |
| 3 Worker, Parallelität, Wiederaufnahme | freigegeben (v1.1) |
| 4 Upload-Validierung und Messung | freigegeben |
| 5 Weboberfläche | **freigegeben** |
| 6 Modus B | offen |
| 7 Mail und Härtung | offen, neu gewichtet |
| 8 Prüfmaske | offen |

Die Anwendung ist ab jetzt vollständig im Browser bedienbar: Datei hochladen,
Lauf verfolgen, Ergebnisse herunterladen, nach einem Neustart fortsetzen.
