# FREIGABE — Phase 3, Version 1.1

Geprüft am 03.08.2026. Branch geklont, Tests selbst ausgeführt, Messungen
unabhängig nachgestellt.

**Ergebnis: freigegeben. Phase 4 kann starten.**

---

## 1. Nachgerechnet

| Prüfung | Ergebnis |
|---|---|
| Fünf vollständige Testläufe | **5 × 114 grün + 1 übersprungen** |
| Langsamer Test mit `LANGSAME_TESTS=1` | selbst ausgeführt: **182.23 s**, bestanden |
| `STANDARD_TIMEOUT_SEKUNDEN` in `pipeline.py` und `apify_provider.py` | 180 |
| Reserve für Apify (`wartezeit = timeout − RESERVE`) | 175, Reihenfolge wie in v1.0 gebaut |
| K1: Sollzahl aus der Tabelle statt aus dem Zähler | im Diff bestätigt, plus zusätzliche Prüfung, dass der Zähler nach dem Fortsetzen wieder stimmt |

---

## 2. Zur Einschränkung des Entwicklers

Er meldet, der rote Test sei lokal in 20 provozierten Abstürzen nicht
reproduzierbar gewesen, und auch fünf Läufe vor der Korrektur seien grün
geblieben.

**Auf meiner Maschine war er in vier von fünf Läufen rot**, sobald die Variante
mit einem Arbeiter vorher lief. Die Fehlermeldungen passten exakt auf die von
ihm selbst beschriebene Lücke:

```
assert 11 == (20 - 8)
assert  6 == (20 - 13)
```

Nach der Korrektur laufen auf derselben Maschine fünf vollständige Durchläufe
sauber durch. Der Fehler war real, die Korrektur wirkt, und seine Analyse der
Ursache war richtig — sie war auf seiner Hardware nur nicht sichtbar.

**Lehre:** Zeitabhängige Tests, die auf einer Maschine grün sind, sind kein
Beleg. Wo Nebenläufigkeit im Spiel ist, gilt ein Kriterium erst als erfüllt,
wenn es an einer vom Aufbau her belegbaren Ursache hängt — nicht wenn es
zufällig durchläuft.

---

## 3. K3 — vom Prüfer nicht nachstellbar

Der erfolgreiche Live-Abruf (80 s, 6 Treffer, 14 von 14 Feldern, Apify-Lauf mit
`SUCCEEDED` beendet) ist **nur durch die Meldung belegt**. Ein Apify-Token
liegt dem Prüfer nicht vor.

Der Beleg ist in sich schlüssig und deckt sich mit K2: Derselbe Suchbegriff lief
zwei Stunden zuvor mit der 90-Sekunden-Frist in den Timeout. Das bestätigt die
Fristerhöhung von der anderen Seite — nicht der neue Aufrufweg war das Problem.

Ab hier trägt die Meldung mehr Gewicht als die Nachprüfung. Die Regel aus dem
Korrekturplan bleibt in Kraft: ein Kriterium gilt erst als grün, wenn der
vollständige Testlauf mehrfach hintereinander grün ist.

---

## 4. Nebenfund, korrekt zurückgestellt

**Python wartet beim Beenden auf abgebrochene Abfragen.** Der Lauf steht sofort
und die Daten sind geschrieben, aber das Schliessen des Programms kann sich um
bis zu 175 Sekunden verzögern.

Richtig erkannt, richtig nicht behoben — lag ausserhalb von K1–K3.

In der Webapp betrifft das den Serverstopp. Für den Nutzer sieht ein Fenster,
das sich drei Minuten nicht schliesst, wie ein Absturz aus. Deshalb ist der
Punkt jetzt **im Phasenplan verankert**, nicht nur vermerkt — dasselbe Muster
wie bei den sechs Workern, die nach dem Löschen von `main.py` unbemerkt
verschwunden waren.

---

## 5. Änderungen am Phasenplan

**Phase 4**, neues Abnahmekriterium:
mindestens zehn aufeinanderfolgende echte Apify-Aufrufe mit Einzelzeiten.
Klärt die offene Frage, warum das Betriebsprotokoll rund 17 Sekunden nennt und
Einzelmessungen rund 85. Die Frist wird nicht eigenmächtig erhöht.

**Phase 5**, Umfang und Abnahmekriterium:
Server lässt sich während eines laufenden Jobs in unter 10 Sekunden beenden;
der Job steht danach als `LAEUFT` in der Datenbank und wird beim nächsten Start
zur Fortsetzung angeboten.

---

## 6. Stand nach drei Phasen

| Phase | Status |
|---|---|
| 1 Kern repariert und entkoppelt | freigegeben |
| 2 Provider und Datenmodell | freigegeben |
| 3 Worker, Parallelität, Wiederaufnahme, Abbruch | **freigegeben (v1.1)** |
| 4 Upload-Validierung | offen |
| 5 Weboberfläche | offen |
| 6 Modus B | offen |
| 7 Mail und Härtung | offen |

Die riskanteste Phase ist durch. Phase 4 ist die wichtigste: dort entscheidet
sich, wie viele Prüffälle überhaupt übrig bleiben — und damit, ob die Prüfmaske
gebaut werden muss.
