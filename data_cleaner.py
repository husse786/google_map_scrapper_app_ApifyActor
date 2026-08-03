# data_cleaner.py
# Modul zur qualitativen Bereinigung und Deduplizierung von Google Maps Ergebnissen.
#
# Zweck: Nimmt die angereicherten Daten (1 Kunde → mehrere Google-Ergebnisse)
#         und entscheidet automatisch, welches Ergebnis das richtige ist.
#
# Ausgabe (02_DATENVERTRAG.md §2): drei Hauptdateien plus eine Diagnosedatei
#   - fertig_fuer_erp.csv  ①  automatisch akzeptiert, direkt importierbar
#   - zur_pruefung.csv     ②  unklar, ein Mensch entscheidet
#   - nicht_moeglich.csv   ③  kein verwertbares Ergebnis
#   - aussortiert.csv         Diagnose: verworfene Kandidaten, keine der drei
#
# Invariante: Jede KundenNr aus der Eingabe steht in genau einer der drei
# Hauptdateien — nie in zweien, nie in keiner. Die Diagnosedatei zaehlt nicht mit.

import logging
import re
from pathlib import Path

import pandas as pd
from thefuzz import fuzz

logger = logging.getLogger(__name__)

# Spalten der drei Ausgabedateien, in dieser Reihenfolge (02_DATENVERTRAG.md §2).
# qualitaet, score und grund sind Pflicht und werden nie verworfen.
OUTPUT_COLUMNS = [
    'KundenNr', 'SearchString', 'PLZ', 'Stadt',
    'title', 'address', 'street', 'postalCode', 'city',
    'openingHours', 'phone', 'phoneUnformatted', 'website',
    'permanentlyClosed', 'temporarilyClosed', 'cid', 'placeId', 'location',
    'qualitaet', 'score', 'grund',
]

# Dateinamen der Ausgabe. Identisch in beiden Modi (02_DATENVERTRAG.md §2).
OUTPUT_FILES = {
    'fertig_fuer_erp': 'fertig_fuer_erp.csv',
    'zur_pruefung': 'zur_pruefung.csv',
    'nicht_moeglich': 'nicht_moeglich.csv',
    'aussortiert': 'aussortiert.csv',
}


class DataCleaner:
    """Bereinigt und dedupliziert die angereicherten Google Maps Daten."""

    # Generische Kategorie-Wörter, die keinen Markennamen darstellen.
    # Wenn das erste Wort eines Suchbegriffs generisch ist (z.B. "Restaurant"),
    # wird beim Scoring der Gesamtvergleich stärker gewichtet als der Erst-Wort-Vergleich.
    # Beispiel: "Restaurant Waldegg" → "Restaurant" ist generisch, also zählt
    #           der volle Titel-Vergleich mehr als nur "Restaurant" vs "Restaurant".
    GENERIC_FIRST_WORDS = {
        'restaurant', 'metzgerei', 'kiosk', 'hotel', 'cafe', 'baeckerei',
        'gasthof', 'gasthaus', 'berggasthaus', 'pension', 'bar', 'bistro', 'pizzeria',
        'garage', 'apotheke', 'drogerie', 'coiffeur', 'salon', 'praxis', 'laden',
        'shop', 'markt', 'zentrum', 'haus', 'stiftung', 'verein', 'genossenschaft',
        'tankstelle', 'station', 'post', 'filiale', 'freibad', 'badi', 'hallenbad',
        'schwimmbad', 'camping', 'sportanlage', 'turnhalle'
    }

    # Rechtsform-Suffixe, die vor dem Scoring aus beiden Texten entfernt werden.
    # Damit wird z.B. "Volg Detailhandels AG" zu "Volg" und kann besser
    # mit dem Google-Titel "Volg" verglichen werden.
    LEGAL_SUFFIXES = r'\b(ag|gmbh|kg|sa|sarl|sàrl|inc|ltd|co|ohg|eg|se|mbh|lkg|detailhandels)\b'

    # Feste Schwellenwerte aus 03_ENTSCHEIDUNGEN.md B1/B2/B3.
    HIGH_SCORE_THRESHOLD = 80       # B3: Score, ab dem ein Treffer als "hoch" gilt
    STREET_NAME_THRESHOLD = 90      # B1: fuzz.ratio-Schwelle fuer den Strassennamen
    SINGLE_HIT_NAME_THRESHOLD = 60  # B2: Namensscore, ab dem ein Einzeltreffer reicht

    def __init__(self, dynamic_gap_threshold=30):
        """
        Initialisiert den DataCleaner.

        Args:
            dynamic_gap_threshold: Mindestabstand zwischen dem besten und zweitbesten Score,
                                   damit der beste Treffer als "dynamisch eindeutig" gilt.
                                   Standard: 30 Punkte Unterschied.
        """
        self.dynamic_gap_threshold = dynamic_gap_threshold

    # ==========================================================================
    # HILFSMETHODEN: Textnormalisierung
    # ==========================================================================

    def _normalize_text(self, text: str) -> str:
        """
        Normalisiert einen Text für den Vergleich.
        Ändert NICHT die Originaldaten — nur die interne Vergleichskopie.

        Schritte:
        1. Kleinbuchstaben
        2. Umlaute auflösen (ä→ae, ö→oe, ü→ue)
        3. Französische Akzente entfernen (é→e, è→e, à→a)
        4. Strassenabkürzungen ausschreiben (Str.→Strasse, G.→Gasse)
        5. Bindestriche und Schrägstriche durch Leerzeichen ersetzen
        6. Mehrfache Leerzeichen zusammenfassen
        """
        if not text:
            return ''
        text = str(text).lower().strip()
        # Umlaute → Doppelvokal
        text = text.replace('ä', 'ae').replace('ö', 'oe').replace('ü', 'ue')
        # Französische Akzente entfernen (für Westschweiz)
        text = text.replace('é', 'e').replace('è', 'e').replace('ê', 'e')
        text = text.replace('à', 'a').replace('â', 'a')
        # Schweizer Strassenabkürzungen ausschreiben
        text = text.replace('str.', 'strasse').replace('str ', 'strasse ')
        text = text.replace('g.', 'gasse')
        text = text.replace('pl.', 'platz')
        # Bindestriche und Schrägstriche → Leerzeichen (z.B. "Denner-Satellit" → "Denner Satellit")
        text = text.replace('-', ' ').replace('/', ' ')
        # Mehrfache Leerzeichen zu einem zusammenfassen
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def _normalize_plz(self, plz_value: str) -> str:
        """
        Normalisiert PLZ-Werte für den Vergleich.
        Entfernt '.0' Suffix, das entsteht wenn Pandas Zahlen als Float liest.
        Beispiel: "5703.0" → "5703"
        """
        plz = str(plz_value).strip()
        if plz.endswith('.0'):
            plz = plz[:-2]
        return plz

    def _strip_legal_suffixes(self, text: str) -> str:
        """
        Entfernt Rechtsform-Suffixe aus einem bereits normalisierten Text.
        Beispiel: "volg detailhandels ag" → "volg"
        """
        cleaned = re.sub(self.LEGAL_SUFFIXES, '', text)
        return re.sub(r'\s+', ' ', cleaned).strip()

    # ==========================================================================
    # HILFSMETHODEN: Strassenvergleich
    # ==========================================================================

    def _extract_house_number(self, street_text: str) -> str:
        """
        Extrahiert die Hausnummer aus einem normalisierten Strassentext.
        Sucht nach der letzten Zahl (ggf. mit Buchstabe, z.B. "12a").

        Beispiele:
            "seetalstrasse 60"  → "60"
            "bahnhofstrasse 12a" → "12a"
            "dorfstrasse"        → "" (keine Hausnummer)
        """
        numbers = re.findall(r'\d+\s*[a-zA-Z]?', street_text)
        return numbers[-1].strip() if numbers else ''

    def _extract_street_name(self, street_text: str) -> str:
        """
        Extrahiert den reinen Strassennamen ohne Hausnummer.

        Beispiele:
            "seetalstrasse 60"  → "seetalstrasse"
            "dorfstrasse 19"    → "dorfstrasse"
            "dorfstrasse"       → "dorfstrasse"
        """
        name = re.sub(r'\d+\s*[a-zA-Z]?\s*$', '', street_text).strip()
        return name

    def _street_matches(self, input_street: str, google_street: str) -> bool:
        """
        Vergleicht eine Input-Strasse mit einer Google-Strasse.
        Berücksichtigt Hausnummern intelligent:

        Regeln:
        ┌─────────────────────────┬──────────────────────┬──────────────────────────────┐
        │ Input                   │ Google               │ Ergebnis                     │
        ├─────────────────────────┼──────────────────────┼──────────────────────────────┤
        │ Seetalstrasse 60        │ Seetalstrasse 60     │ ✅ Match (Name + Nr stimmen)  │
        │ Seetalstrasse 60        │ Seetalstrasse 119    │ ❌ Reject (Nr unterschiedlich) │
        │ Seetalstrasse 60        │ Seetalstrasse        │ ✅ Match (Google hat keine Nr) │
        │ Seetalstrasse           │ Seetalstrasse 60     │ ✅ Match (Input hat keine Nr)  │
        │ Seetalstrasse           │ Hauptstrasse 60      │ ❌ Reject (Name unterschiedlich)│
        │ Seetalstrasse           │ Seetalstrasse        │ ✅ Match                       │
        └─────────────────────────┴──────────────────────┴──────────────────────────────┘

        Der Strassenname wird mit fuzz.ratio >= 90 verglichen (03_ENTSCHEIDUNGEN.md B1).
        Das frühere fuzz.partial_ratio hat Teilstrings akzeptiert und damit falsche
        Strassen durchgelassen ("Dorfstrasse" = "Oberdorfstrasse").
        """
        norm_input = self._normalize_text(input_street)
        norm_google = self._normalize_text(google_street)

        # Leere Strassen können nicht verglichen werden
        if not norm_input or not norm_google:
            return False

        # Strassenname und Hausnummer separat extrahieren
        input_number = self._extract_house_number(norm_input)
        google_number = self._extract_house_number(norm_google)
        input_name = self._extract_street_name(norm_input)
        google_name = self._extract_street_name(norm_google)

        # Schritt 1: Strassenname muss immer ungefähr übereinstimmen (fuzz.ratio >= 90)
        name_match = fuzz.ratio(input_name, google_name) >= self.STREET_NAME_THRESHOLD

        # Strassenname stimmt nicht → sofort ablehnen
        if not name_match:
            return False

        # Schritt 2: Hausnummer-Logik
        # Wenn beide eine Hausnummer haben, müssen diese übereinstimmen
        if input_number and google_number:
            return input_number == google_number

        # In allen anderen Fällen (einer oder keiner hat eine Nummer)
        # reicht der Strassenname-Match aus
        return True

    def _street_and_number_exact(self, input_street: str, google_street: str) -> bool:
        """
        Prüft, ob Strassenname UND Hausnummer exakt übereinstimmen.

        Zweite Bedingung der Einzeltreffer-Regel (03_ENTSCHEIDUNGEN.md B2). Sie
        fängt Rebranding ab: gleiche Adresse, neuer Name (Volg → Spar) bleibt in ①.

        Strenger als _street_matches: der Name muss nach der Normalisierung
        zeichengleich sein, und beide Seiten müssen eine Hausnummer tragen.
        """
        norm_input = self._normalize_text(input_street)
        norm_google = self._normalize_text(google_street)
        if not norm_input or not norm_google:
            return False

        input_number = self._extract_house_number(norm_input)
        google_number = self._extract_house_number(norm_google)
        if not input_number or not google_number:
            return False

        if input_number != google_number:
            return False

        return self._extract_street_name(norm_input) == self._extract_street_name(norm_google)

    # ==========================================================================
    # HILFSMETHODEN: Scoring
    # ==========================================================================

    def _get_scoring_weights(self, first_word: str) -> tuple:
        """
        Bestimmt die Gewichtung für das Title-Scoring basierend auf dem ersten Wort.

        Markenname (z.B. "Denner", "Coop", "Migros"):
            → 70% Erst-Wort-Vergleich, 30% Gesamtvergleich
            → Das erste Wort ist der stärkste Indikator

        Generisches Wort (z.B. "Restaurant", "Metzgerei", "Kiosk"):
            → 30% Erst-Wort-Vergleich, 70% Gesamtvergleich
            → Das erste Wort sagt wenig aus, der Gesamtname ist wichtiger
        """
        if first_word in self.GENERIC_FIRST_WORDS:
            return (0.30, 0.70)
        else:
            return (0.70, 0.30)

    def _calculate_scores(self, group: pd.DataFrame) -> pd.DataFrame:
        """
        Berechnet den gewichteten Ähnlichkeitsscore für jede Zeile in einer Kundengruppe.

        Vergleicht den Suchbegriff (SearchString) mit jedem Google-Titel.

        Score-Berechnung:
            1. Erst-Wort-Score: Wie ähnlich ist das erste Wort des Suchbegriffs
               zum ersten Wort des Google-Titels? (fuzz.ratio)
            2. Gesamt-Score: Wie ähnlich ist der gesamte Suchbegriff zum gesamten
               Google-Titel? (fuzz.token_set_ratio — reihenfolge-unabhängig)
            3. Gewichteter Score = (Gewicht₁ × Erst-Wort) + (Gewicht₂ × Gesamt)

        Gibt die Gruppe mit einer neuen 'score' Spalte zurück.

        Der Score haengt nur vom Suchbegriff des Kunden und vom jeweiligen Titel ab,
        nicht von den uebrigen Zeilen der Gruppe. Er wird deshalb einmal fuer alle
        Kandidaten berechnet und danach nur noch gelesen — jede Ausgabezeile traegt
        ihn (02_DATENVERTRAG.md §2).
        """
        if group.empty:
            return group

        # Den Namensteil aus dem SearchString extrahieren (alles vor dem ersten Komma)
        # Beispiel: "Denner-Satellit, Hauptstrasse 5, 5620" → "Denner-Satellit"
        search_name = group.iloc[0].get('SearchString', '')
        search_name_part = search_name.split(',')[0].strip() if search_name else ''

        # Normalisieren und Rechtsformen entfernen für fairen Vergleich
        norm_search_name = self._normalize_text(search_name_part)
        norm_search_name = self._strip_legal_suffixes(norm_search_name)

        # Erstes Wort extrahieren und Gewichtung bestimmen
        search_words = norm_search_name.split()
        search_first_word = search_words[0] if search_words else ''
        first_word_weight, full_title_weight = self._get_scoring_weights(search_first_word)

        logger.debug(f"Scoring '{search_name_part}' | first_word='{search_first_word}' | "
                     f"weights=({first_word_weight:.0%}/{full_title_weight:.0%}) | "
                     f"generic={'YES' if first_word_weight == 0.30 else 'NO'}")

        # Score für jedes Google-Ergebnis berechnen
        scores = []
        for _, row in group.iterrows():
            google_title = str(row.get('title', ''))
            norm_google_title = self._normalize_text(google_title)
            norm_google_title = self._strip_legal_suffixes(norm_google_title)

            # Erstes Wort des Google-Titels extrahieren
            google_words = norm_google_title.split()
            google_first_word = google_words[0] if google_words else ''

            # Erst-Wort-Vergleich: exakter Zeichenvergleich (fuzz.ratio)
            # "denner" vs "denner" → 100, "denner" vs "spar" → niedrig
            if search_first_word and google_first_word:
                core_score = fuzz.ratio(search_first_word, google_first_word)
            else:
                core_score = 0

            # Gesamtvergleich: reihenfolge-unabhängig (fuzz.token_set_ratio)
            # "denner satellit" vs "satellit denner bremgarten" → hoch
            full_score = fuzz.token_set_ratio(norm_search_name, norm_google_title)

            # Gewichteter Gesamtscore
            weighted_score = (first_word_weight * core_score) + (full_title_weight * full_score)

            logger.debug(f"  vs '{google_title}' | core={core_score} full={full_score} "
                         f"weighted={weighted_score:.1f}")

            scores.append(round(weighted_score, 2))

        # Score-Spalte zur Gruppe hinzufügen (Kopie, um SettingWithCopyWarning zu vermeiden)
        group = group.copy()
        group['score'] = scores
        return group

    # ==========================================================================
    # HILFSMETHODEN: Datenprüfung
    # ==========================================================================

    def _has_street_in_searchstring(self, search_string: str) -> str:
        """
        Prüft, ob der SearchString eine Strasse enthält (2. Komma-separierter Teil).

        Beispiele:
            "Denner, Hauptstrasse 5, 5620" → "Hauptstrasse 5" (Strasse vorhanden)
            "Denner,  , 5620"              → "" (keine Strasse)
            "Denner, 5620"                 → "" (nur Zahl, keine Strasse)

        Returns: Den Strassenteil als String, oder '' wenn keine Strasse vorhanden.
        """
        parts = str(search_string).split(',')
        if len(parts) >= 2:
            street_part = parts[1].strip()
            # Sicherstellen, dass es nicht nur eine Zahl ist (z.B. PLZ-Fragment)
            if street_part and not street_part.isdigit():
                return street_part
        return ''

    def _plz_matches(self, row: pd.Series, input_plz: str) -> bool:
        """
        Prüft ob die Postleitzahl des Google-Ergebnisses mit der erwarteten PLZ übereinstimmt.

        Wenn eine der beiden PLZ fehlt, wird nicht gefiltert (Benefit of Doubt).
        So gehen keine Ergebnisse verloren, nur weil Google keine PLZ zurückgegeben hat.
        """
        google_plz = self._normalize_plz(row.get('postalCode', ''))
        input_plz_clean = self._normalize_plz(input_plz)
        # Wenn eine PLZ fehlt, nicht filtern → durchlassen
        if not google_plz or not input_plz_clean:
            return True
        return google_plz == input_plz_clean

    def _is_empty_result(self, row: pd.Series) -> bool:
        """
        Prüft ob ein API-Ergebnis leer ist (die Google Maps API hat nichts gefunden).

        Ein Ergebnis gilt als leer wenn ALLE dieser Felder leer sind:
        title, address, street, placeId
        """
        key_fields = ['title', 'address', 'street', 'placeId']
        for field in key_fields:
            if str(row.get(field, '')).strip() != '':
                return False
        return True

    # ==========================================================================
    # HILFSMETHODEN: Klartextgründe (02_DATENVERTRAG.md §4)
    # ==========================================================================

    @staticmethod
    def _fmt_score(score) -> str:
        """Formatiert einen Score für den Klartextgrund: 93.75 → '94'."""
        try:
            return f"{float(score):.0f}"
        except (TypeError, ValueError):
            return '0'

    @staticmethod
    def _aufzaehlung(werte, max_anzahl: int = 4) -> str:
        """
        Baut eine deutsche Aufzählung aus einer Werteliste, ohne Wiederholungen.

        ['Wohlerstrasse 18', 'Wohlerstrasse 55'] → 'Wohlerstrasse 18 und Wohlerstrasse 55'
        Mehr als max_anzahl Werte werden gekürzt: '..., A, B und 3 weitere'
        """
        eindeutig = [w for w in dict.fromkeys(str(w).strip() for w in werte) if w]
        if not eindeutig:
            return ''
        if len(eindeutig) > max_anzahl:
            rest = len(eindeutig) - max_anzahl
            return ', '.join(eindeutig[:max_anzahl]) + f' und {rest} weitere'
        if len(eindeutig) == 1:
            return eindeutig[0]
        return ', '.join(eindeutig[:-1]) + ' und ' + eindeutig[-1]

    # ==========================================================================
    # HILFSMETHODEN: Ausgabezeilen
    # ==========================================================================

    @staticmethod
    def _make_row(source, qualitaet: str, score, grund: str) -> dict:
        """Baut eine Ausgabezeile aus einer Kandidatenzeile plus Entscheid."""
        row = dict(source)
        row['qualitaet'] = qualitaet
        row['score'] = round(float(score), 2)
        row['grund'] = grund
        return row

    # ==========================================================================
    # HAUPTMETHODE: Bereinigung
    # ==========================================================================

    def clean_data(self, input_filepath: str, output_dir: str = None) -> dict:
        """
        Hauptmethode zur Bereinigung der angereicherten Daten.

        Ablauf für jeden Kunden (KundenNr-Gruppe):

        0. Suchbegriff vorhanden?          → sonst ③ (Eingabe unbrauchbar)
        1. Leere Ergebnisse erkennen       → alle leer: ③ (kein Ergebnis)
        2. Score für jeden Kandidaten berechnen
        3. PLZ-Filter                      → kein Treffer: ② (keine PLZ-Treffer)
        4. Einzeltreffer prüfen            → Regel B2 entscheidet ① oder ②
        5. Weiche: Strasse vorhanden?
           JA  → Szenario B: Strassenabgleich, dann Title-Scoring
           NEIN → Szenario A: Nur Title-Scoring
        6. Title-Scoring mit Schwellenwerten:
           genau 1 Score ≥ 80  → ① OK (Score)
           mehrere ≥ 80        → ② mehrere hohe Treffer
           Abstand ≥ 30        → ① OK (Dynamisch)
           sonst               → ② kein klarer Treffer

        Args:
            input_filepath: angereicherte CSV (Semikolon, utf-8-sig)
            output_dir:     Zielordner. Fehlt er, wird neben der Eingabedatei
                            ein Ordner "<dateiname>_ergebnis" angelegt.

        Returns:
            Dict mit Dateipfaden: {'fertig_fuer_erp': '...', 'zur_pruefung': '...',
                                   'nicht_moeglich': '...', 'aussortiert': '...'}
        """
        logger.info(f"Starte Bereinigung der Datei: {input_filepath}")

        # CSV laden — alles als String einlesen, damit keine Daten verfälscht werden
        df = pd.read_csv(input_filepath, sep=';', encoding='utf-8-sig', dtype=str).fillna('')

        if 'KundenNr' not in df.columns:
            raise ValueError("Die Spalte 'KundenNr' wurde nicht gefunden.")

        # Ergebnis-Listen für die drei Ausgabedateien plus Diagnose
        fertig = []          # ① automatisch akzeptiert
        pruefung = []        # ② Mensch entscheidet
        nicht_moeglich = []  # ③ kein verwertbares Ergebnis
        aussortiert = []     # Diagnose: verworfene Kandidaten

        # Daten nach KundenNr gruppieren — jede Gruppe = 1 Kunde mit N Google-Ergebnissen
        grouped = df.groupby('KundenNr', sort=False)
        logger.info(f"Verarbeite {len(grouped)} Kundengruppen...")

        for kunden_nr, group in grouped:
            self._process_customer(str(kunden_nr), group,
                                   fertig, pruefung, nicht_moeglich, aussortiert)

        # ==================================================================
        # ERGEBNISSE SPEICHERN
        # ==================================================================
        if output_dir:
            target = Path(output_dir)
        else:
            quelle = Path(input_filepath)
            target = quelle.parent / f"{quelle.stem}_ergebnis"
        target.mkdir(parents=True, exist_ok=True)

        results = {}
        for key, data in [('fertig_fuer_erp', fertig),
                          ('zur_pruefung', pruefung),
                          ('nicht_moeglich', nicht_moeglich),
                          ('aussortiert', aussortiert)]:
            filepath = target / OUTPUT_FILES[key]
            out_df = pd.DataFrame(data, columns=OUTPUT_COLUMNS).fillna('')
            out_df.to_csv(filepath, sep=';', index=False, encoding='utf-8-sig')
            results[key] = str(filepath)
            kunden = out_df['KundenNr'].nunique() if not out_df.empty else 0
            logger.info(f"{key}: {kunden} Kunden, {len(out_df)} Zeilen → {filepath}")

        return results

    # ==========================================================================
    # Ein Kunde, eine Entscheidung
    # ==========================================================================

    def _process_customer(self, kunden_nr, group, fertig, pruefung,
                          nicht_moeglich, aussortiert):
        """
        Entscheidet für genau einen Kunden und haengt das Ergebnis an die Listen an.

        Jeder Kunde verlaesst diese Methode ueber genau einen der drei Wege
        fertig / pruefung / nicht_moeglich. Eintraege in aussortiert sind reine
        Diagnose und werden nur geschrieben, wenn der Kunde anderweitig entschieden
        wurde — nie zusaetzlich zu einem Prueffall aus derselben Zeilengruppe.
        """
        stamm = group.iloc[0]
        search_string = str(stamm.get('SearchString', '')).strip()
        input_plz = str(stamm.get('PLZ', '')).strip()

        # ==================================================================
        # SCHRITT 0: Ohne Suchbegriff ist keine Entscheidung möglich
        # ==================================================================
        if not search_string:
            nicht_moeglich.append(self._make_row(
                stamm.to_dict(), 'NICHT_MOEGLICH (Eingabe unbrauchbar)', 0,
                'Im Suchbegriff steht nichts. Ohne Name und Adresse ist keine Suche möglich.'))
            return

        # ==================================================================
        # SCHRITT 1: Leere Ergebnisse erkennen
        # ==================================================================
        empty_mask = group.apply(self._is_empty_result, axis=1)
        empty_rows = group[empty_mask]
        filled_rows = group[~empty_mask]

        if filled_rows.empty:
            # Die Suche hat für diesen Kunden gar nichts geliefert → ③
            logger.info(f"KundenNr {kunden_nr}: kein Ergebnis der Suche.")
            nicht_moeglich.append(self._make_row(
                stamm.to_dict(), 'NICHT_MOEGLICH (kein Ergebnis)', 0,
                f'Die Suche nach "{search_string}" lieferte keinen einzigen Treffer.'))
            return

        # Einzelne leere Zeilen neben echten Treffern sind nur Rauschen → Diagnose
        for _, row in empty_rows.iterrows():
            aussortiert.append(self._make_row(
                row.to_dict(), 'AUSSORTIERT (leeres Ergebnis)', 0,
                'Leere Antwort der Suche; für diesen Kunden gibt es andere Treffer.'))

        # ==================================================================
        # SCHRITT 2: Score für jeden Kandidaten — wird nie mehr verworfen
        # ==================================================================
        scored = self._calculate_scores(filled_rows)

        # ==================================================================
        # SCHRITT 3: PLZ-Filter — Ergebnisse aus falscher Postleitzahl entfernen
        # ==================================================================
        plz_mask = scored.apply(lambda row: self._plz_matches(row, input_plz), axis=1)
        plz_matches = scored[plz_mask]
        plz_mismatches = scored[~plz_mask]

        if plz_matches.empty:
            # Keine einzige passende PLZ → alle Kandidaten zur Prüfung.
            # Sie werden NICHT zusätzlich aussortiert (Invariante, Fehler B1).
            logger.info(f"KundenNr {kunden_nr}: keine PLZ-Treffer, zur Prüfung.")
            gefunden = self._aufzaehlung(
                self._normalize_plz(r.get('postalCode', '')) for _, r in scored.iterrows())
            grund = (f'Gesucht Postleitzahl {input_plz}, '
                     f'gefunden {gefunden or "keine Angabe"}.')
            for _, row in scored.iterrows():
                pruefung.append(self._make_row(
                    row.to_dict(), 'PRUEFUNG (keine PLZ-Treffer)', row['score'], grund))
            return

        for _, row in plz_mismatches.iterrows():
            aussortiert.append(self._make_row(
                row.to_dict(), 'AUSSORTIERT (PLZ)', row['score'],
                f'Postleitzahl {self._normalize_plz(row.get("postalCode", ""))} '
                f'statt {input_plz}.'))

        group = plz_matches
        street_to_find = self._has_street_in_searchstring(search_string)

        # ==================================================================
        # SCHRITT 4: Einzeltreffer prüfen (03_ENTSCHEIDUNGEN.md B2)
        # ==================================================================
        if len(group) == 1:
            self._decide_single_hit(kunden_nr, group.iloc[0], street_to_find,
                                    fertig, pruefung)
            return

        # ==================================================================
        # SCHRITT 5: Die "Weiche" — Strassenabgleich oder direkt Scoring?
        # ==================================================================
        processing_group = group  # Standard: alle Ergebnisse gehen ins Scoring

        if street_to_find:
            # --- SZENARIO B: Strasse im Suchbegriff vorhanden ---
            logger.debug(f"KundenNr {kunden_nr}: Szenario B (Strasse: '{street_to_find}')")

            street_spalte = group['street'] if 'street' in group.columns \
                else pd.Series([''] * len(group), index=group.index)
            street_mask = street_spalte.apply(
                lambda x: self._street_matches(street_to_find, str(x)))
            street_matches = group[street_mask]
            street_mismatches = group[~street_mask]

            if len(street_matches) == 0:
                # Keine einzige Strasse passt → alle zur Prüfung.
                # Sie werden NICHT zusätzlich aussortiert (Fehler B1).
                logger.info(f"KundenNr {kunden_nr}: keine Strassentreffer, zur Prüfung.")
                gefunden = self._aufzaehlung(str(r.get('street', ''))
                                             for _, r in group.iterrows())
                grund = (f'Gesucht {street_to_find}, '
                         f'gefunden {gefunden or "keine Strassenangabe"}.')
                for _, row in group.iterrows():
                    pruefung.append(self._make_row(
                        row.to_dict(), 'PRUEFUNG (keine Strassentreffer)',
                        row['score'], grund))
                return

            # Ab hier gibt es mindestens einen Strassentreffer — erst jetzt
            # duerfen die Fehlschlaege in die Diagnosedatei.
            for _, row in street_mismatches.iterrows():
                aussortiert.append(self._make_row(
                    row.to_dict(), 'AUSSORTIERT (Strasse)', row['score'],
                    f'Gesucht {street_to_find}, dieser Treffer liegt an '
                    f'{row.get("street", "") or "unbekannter Adresse"}.'))

            if len(street_matches) == 1:
                # Genau 1 Strassentreffer → eindeutig
                row = street_matches.iloc[0]
                fertig.append(self._make_row(
                    row.to_dict(), 'OK (Strasse)', row['score'],
                    f'Nur ein Treffer liegt an der gesuchten Adresse {street_to_find}: '
                    f'"{row.get("title", "")}", {row.get("street", "")}. '
                    f'Namensähnlichkeit {self._fmt_score(row["score"])} von 100.'))
                return

            # Mehrere Strassentreffer → Title-Scoring entscheidet
            processing_group = street_matches
        else:
            # --- SZENARIO A: Keine Strasse im Suchbegriff ---
            logger.debug(f"KundenNr {kunden_nr}: Szenario A (keine Strasse)")

        # ==================================================================
        # SCHRITT 6: Title-Scoring — Name des Suchbegriffs vs Google-Titel
        # ==================================================================
        self._decide_by_score(kunden_nr, processing_group, fertig, pruefung, aussortiert)

    # ==========================================================================
    # SCHRITT 4: Einzeltreffer-Regel B2
    # ==========================================================================

    def _decide_single_hit(self, kunden_nr, row, street_to_find, fertig, pruefung):
        """
        Ein einziger Kandidat hat den PLZ-Filter überlebt.

        Nach ① nur, wenn mindestens eine Bedingung gilt (03_ENTSCHEIDUNGEN.md B2):
            (1) Namensscore >= 60
            (2) Strasse UND Hausnummer stimmen exakt überein
        Sonst → ② PRUEFUNG (Einzeltreffer unsicher).
        """
        score = float(row['score'])
        titel = str(row.get('title', ''))
        google_street = str(row.get('street', ''))
        score_text = self._fmt_score(score)

        name_reicht = score >= self.SINGLE_HIT_NAME_THRESHOLD
        adresse_exakt = bool(street_to_find) and self._street_and_number_exact(
            street_to_find, google_street)

        if name_reicht:
            fertig.append(self._make_row(
                row.to_dict(), 'OK (Einzeltreffer)', score,
                f'Ein einziger Treffer übrig: "{titel}", '
                f'Namensähnlichkeit {score_text} von 100.'))
            return

        if adresse_exakt:
            # Rebranding: gleiche Adresse, neuer Name (Volg → Spar)
            fertig.append(self._make_row(
                row.to_dict(), 'OK (Einzeltreffer)', score,
                f'Ein einziger Treffer übrig: "{titel}" an der gesuchten Adresse '
                f'{street_to_find}. Der Name weicht ab (Ähnlichkeit {score_text} von 100), '
                f'Strasse und Hausnummer stimmen exakt.'))
            return

        logger.info(f"KundenNr {kunden_nr}: Einzeltreffer unsicher (Score {score_text}).")
        if street_to_find:
            grund = (f'Nur ein Treffer: "{titel}" an {google_street or "unbekannter Adresse"}. '
                     f'Der Name ist nur zu {score_text} von 100 ähnlich und die Adresse '
                     f'stimmt nicht genau mit {street_to_find} überein.')
        else:
            grund = (f'Nur ein Treffer: "{titel}". Der Name ist nur zu {score_text} von 100 '
                     f'ähnlich und im Suchbegriff steht keine Strasse zum Abgleich.')
        pruefung.append(self._make_row(
            row.to_dict(), 'PRUEFUNG (Einzeltreffer unsicher)', score, grund))

    # ==========================================================================
    # SCHRITT 6: Entscheid über den Namensscore
    # ==========================================================================

    def _decide_by_score(self, kunden_nr, scored_group, fertig, pruefung, aussortiert):
        """
        Entscheidet eine Gruppe von mindestens zwei Kandidaten über den Score.

        Schwellenwerte unverändert aus 03_ENTSCHEIDUNGEN.md B3:
        fester Wert 80, dynamischer Abstand 30.
        """
        ranked = scored_group.sort_values('score', ascending=False)
        high = ranked[ranked['score'] >= self.HIGH_SCORE_THRESHOLD]
        low = ranked[ranked['score'] < self.HIGH_SCORE_THRESHOLD]

        if len(high) == 1:
            # --- GENAU 1 Treffer über 80 → eindeutig ---
            row = high.iloc[0]
            fertig.append(self._make_row(
                row.to_dict(), 'OK (Score)', row['score'],
                f'Bester Treffer "{row.get("title", "")}" erreicht '
                f'{self._fmt_score(row["score"])} von 100, alle anderen bleiben unter 80.'))
            for _, other in low.iterrows():
                aussortiert.append(self._make_row(
                    other.to_dict(), 'AUSSORTIERT (Score)', other['score'],
                    f'"{other.get("title", "")}" erreicht nur '
                    f'{self._fmt_score(other["score"])} von 100.'))
            return

        if len(high) > 1:
            # --- MEHRERE Treffer über 80 → mehrdeutig → manuelle Prüfung ---
            # Beispiel: 2 SPAR-Filialen in derselben PLZ, beide scoren hoch.
            logger.info(f"KundenNr {kunden_nr}: {len(high)} Treffer über 80 → zur Prüfung.")
            erster, zweiter = high.iloc[0], high.iloc[1]
            grund = (f'Mehrere Treffer gleich gut: "{erster.get("title", "")}" '
                     f'({self._fmt_score(erster["score"])}) und "{zweiter.get("title", "")}" '
                     f'({self._fmt_score(zweiter["score"])}).')
            if len(high) > 2:
                grund = (f'{len(high)} Treffer erreichen mindestens 80 Punkte, darunter '
                         f'"{erster.get("title", "")}" ({self._fmt_score(erster["score"])}) '
                         f'und "{zweiter.get("title", "")}" '
                         f'({self._fmt_score(zweiter["score"])}).')
            for _, row in high.iterrows():
                pruefung.append(self._make_row(
                    row.to_dict(), 'PRUEFUNG (mehrere hohe Treffer)', row['score'], grund))
            for _, row in low.iterrows():
                aussortiert.append(self._make_row(
                    row.to_dict(), 'AUSSORTIERT (Score)', row['score'],
                    f'"{row.get("title", "")}" erreicht nur '
                    f'{self._fmt_score(row["score"])} von 100.'))
            return

        # --- DYNAMISCHER SCHWELLENWERT: Kein Score über 80 ---
        if len(ranked) == 1:
            # Kann über die Weiche nicht entstehen; Absicherung gegen künftige Aufrufer.
            row = ranked.iloc[0]
            pruefung.append(self._make_row(
                row.to_dict(), 'PRUEFUNG (kein klarer Treffer)', row['score'],
                f'Einziger Treffer "{row.get("title", "")}" erreicht nur '
                f'{self._fmt_score(row["score"])} von 100.'))
            return

        erster = ranked.iloc[0]
        zweiter = ranked.iloc[1]
        score_1 = float(erster['score'])
        score_2 = float(zweiter['score'])
        abstand = score_1 - score_2

        if abstand >= self.dynamic_gap_threshold:
            # Abstand gross genug → bester Treffer ist wahrscheinlich korrekt
            logger.info(f"KundenNr {kunden_nr}: dynamischer Treffer "
                        f"(Score {score_1:.0f} vs {score_2:.0f}).")
            fertig.append(self._make_row(
                erster.to_dict(), 'OK (Dynamisch)', score_1,
                f'"{erster.get("title", "")}" liegt mit '
                f'{self._fmt_score(score_1)} von 100 klar vor dem nächsten Treffer '
                f'"{zweiter.get("title", "")}" ({self._fmt_score(score_2)}).'))
            for _, row in ranked.iloc[1:].iterrows():
                aussortiert.append(self._make_row(
                    row.to_dict(), 'AUSSORTIERT (Dynamisch)', row['score'],
                    f'"{row.get("title", "")}" ({self._fmt_score(row["score"])}) liegt klar '
                    f'hinter dem besten Treffer "{erster.get("title", "")}" '
                    f'({self._fmt_score(score_1)}).'))
            return

        # Abstand zu klein → nicht unterscheidbar → manuelle Prüfung
        grund = (f'Kein Treffer erreicht 80 Punkte: bester "{erster.get("title", "")}" '
                 f'({self._fmt_score(score_1)}), zweiter "{zweiter.get("title", "")}" '
                 f'({self._fmt_score(score_2)}), Abstand nur {self._fmt_score(abstand)}.')
        for _, row in ranked.iterrows():
            pruefung.append(self._make_row(
                row.to_dict(), 'PRUEFUNG (kein klarer Treffer)', row['score'], grund))
