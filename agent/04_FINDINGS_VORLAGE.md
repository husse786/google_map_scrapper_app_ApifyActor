# 04 — FINDINGS-VORLAGE

Nach jeder Phase eine Datei: `FINDINGS_PHASE_1.md`, `FINDINGS_PHASE_2.md`, …
Bei Korrekturrunden: `FINDINGS_PHASE_1_v1.1.md`.

**Findings werden committet und sind öffentlich lesbar.** Keine echten
Kundennamen, Adressen, Kundennummern oder placeId. Fixture-Daten (900001–900010)
sind erfunden und dürfen vollständig zitiert werden. Regeln: `05_TESTDATEN.md`.

Diese Datei ist die einzige Grundlage, auf der der Prüfer arbeitet. Was nicht
darin steht, existiert für ihn nicht. Kurz und faktisch — keine Zusammenfassung
dessen, was ohnehin im Plan steht.

---

```markdown
# Findings — Phase N, Version 1.0

Datum:
Bearbeitete Phase:
Status: fertig | fertig mit Vorbehalt | blockiert

---

## 1. Abnahmekriterien

Jedes Kriterium aus dem Phasenplan, wörtlich, mit Ergebnis.

| # | Kriterium | Status | Beleg |
|---|---|---|---|
| 1 | ... | grün / rot | Testname, Befehl oder Messwert |

Rot ist erlaubt, solange es hier steht. Verschwiegen ist es nicht erlaubt.

---

## 2. Geänderte und neue Dateien

| Datei | neu / geändert / entfernt | Was |
|---|---|---|

---

## 3. Getroffene Annahmen

Alles, was kein Dokument abgedeckt hat und wo du selbst entschieden hast.
Der Prüfer korrigiert hier, nicht im Code.

| Situation | Deine Entscheidung | Warum |
|---|---|---|

---

## 4. Abweichungen von den Vorgaben

Nur, wenn du von `03_ENTSCHEIDUNGEN.md` oder `02_DATENVERTRAG.md` abgewichen bist.
Normalerweise leer.

| Vorgabe | Abweichung | Warum unvermeidbar |
|---|---|---|

---

## 5. Was du im Bestandscode gefunden hast

Fehler, Ungereimtheiten, tote Pfade — auch wenn sie nicht zur Phase gehörten.
Nicht selbst beheben, wenn sie ausserhalb des Umfangs liegen. Nur melden.

| Fund | Datei / Stelle | Auswirkung | eingegriffen? |
|---|---|---|---|

---

## 6. Messwerte

Nur wenn die Phase eine Messung verlangt (Phase 1: Vergleichslauf,
Phase 4: Trefferzahlen der Validierung).

Vorher/Nachher als Tabelle, plus eine Zeile je Kunde, der die Kategorie
gewechselt hat, mit Begründung.

---

## 7. Für die nächste Phase

Was die nächste Phase wissen muss und im Plan nicht steht.
Offene Enden, bewusst liegengelassene Stellen, Stolperfallen.

---

## 8. Zeit

Grober Aufwand pro Arbeitspaket. Dient der Planung der Folgephasen,
nicht der Bewertung.
```

---

## Was der Prüfer zurückgibt

`KORREKTURPLAN_PHASE_N.md` mit derselben Nummerierung wie deine Findings:

| Punkt | Bezug | Was zu tun ist | Warum |
|---|---|---|---|

Danach baust du Version 1.1 und schreibst neue Findings. So lange, bis alle
Abnahmekriterien grün sind und der Prüfer freigibt.

---

## Häufigste Gründe für eine Korrekturrunde

Vermeidbar, wenn du beim Bauen darauf achtest:

- Ein Kunde landet in zwei Ausgabedateien oder in keiner
- `grund` enthält Fachsprache statt Klartext („Stage 4 failed")
- `score` fehlt in einer der Ausgabedateien
- Ein Schwellenwert wurde „naheliegender" gewählt als in `03_ENTSCHEIDUNGEN.md`
- Eine Abstraktion wurde gebaut, die niemand verlangt hat
- Englische Zeichenketten in der Oberfläche
- Abnahmekriterium als erfüllt gemeldet ohne Beleg
- Echte Kundendaten im Bericht oder im Repository
