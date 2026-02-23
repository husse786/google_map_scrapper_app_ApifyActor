# data_cleaner.py
# Modul zur qualitativen Bereinigung und Deduplizierung von Google Maps Ergebnissen.
#
# Zweck: Nimmt die angereicherten Daten (1 Kunde → mehrere Google-Ergebnisse)
#         und entscheidet automatisch, welches Ergebnis das richtige ist.
#
# Ausgabe: 4 Dateien
#   - _eindeutig.csv       → automatisch zugeordnete, korrekte Treffer
#   - _zur_pruefung.csv    → mehrdeutige Fälle für manuelle Prüfung
#   - _aussortiert.csv     → klar falsche Ergebnisse
#   - _erneut_crawlen.csv  → leere API-Ergebnisse, die nochmals abgefragt werden sollen

import pandas as pd
from thefuzz import fuzz
import logging
import re

logger = logging.getLogger(__name__)


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
        
        Prinzip: Nur ablehnen wenn sicher falsch. Im Zweifel durchlassen → Title Scoring entscheidet.
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

        # Schritt 1: Strassenname muss immer ungefähr übereinstimmen (>90% Ähnlichkeit)
        name_match = fuzz.partial_ratio(input_name, google_name) > 90

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
        parts = search_string.split(',')
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
        
        Leere Ergebnisse werden separat gespeichert, damit sie nochmals
        über Flow 1 (Anreicherung) abgefragt werden können.
        """
        key_fields = ['title', 'address', 'street', 'placeId']
        for field in key_fields:
            if str(row.get(field, '')).strip() != '':
                return False
        return True

    # ==========================================================================
    # HAUPTMETHODE: Bereinigung
    # ==========================================================================

    def clean_data(self, input_filepath: str) -> dict:
        """
        Hauptmethode zur Bereinigung der angereicherten Daten.
        
        Ablauf für jeden Kunden (KundenNr-Gruppe):
        
        1. Leere Ergebnisse erkennen     → _erneut_crawlen.csv
        2. PLZ-Filter                     → falsche PLZ aussortieren
        3. Einzelergebnis-Check           → direkt eindeutig wenn nur 1 Treffer
        4. Weiche: Strasse vorhanden?
           JA  → Szenario B: Strassenabgleich, dann Title-Scoring
           NEIN → Szenario A: Nur Title-Scoring
        5. Title-Scoring mit Schwellenwerten:
           Score ≥ 80         → eindeutig (fester Schwellenwert)
           Abstand ≥ 30       → eindeutig (dynamischer Schwellenwert)
           Sonst              → zur manuellen Prüfung
        
        Returns:
            Dict mit Dateipfaden: {'eindeutig': '...', 'zur_pruefung': '...',
                                   'aussortiert': '...', 'erneut_crawlen': '...'}
        """
        logger.info(f"Starte Bereinigung der Datei: {input_filepath}")

        # CSV laden — alles als String einlesen, damit keine Daten verfälscht werden
        df = pd.read_csv(input_filepath, sep=';', encoding='utf-8-sig', dtype=str).fillna('')

        if 'KundenNr' not in df.columns:
            raise ValueError("Die Spalte 'KundenNr' wurde nicht gefunden.")

        # Ergebnis-Listen für die 4 Ausgabedateien
        unique_results = []     # Automatisch zugeordnete korrekte Treffer
        review_results = []     # Mehrdeutige Fälle für manuelle Prüfung
        rejected_results = []   # Klar falsche Ergebnisse
        recrawl_results = []    # Leere Ergebnisse zum nochmaligen Abfragen

        # Daten nach KundenNr gruppieren — jede Gruppe = 1 Kunde mit N Google-Ergebnissen
        grouped = df.groupby('KundenNr')
        total_groups = len(grouped)
        logger.info(f"Verarbeite {total_groups} Kundengruppen...")

        for kunden_nr, group in grouped:
            # Stammdaten des Kunden aus der ersten Zeile der Gruppe lesen
            search_string = group.iloc[0].get('SearchString', '')
            input_plz = str(group.iloc[0].get('PLZ', '')).strip()
            input_stadt = str(group.iloc[0].get('Stadt', '')).strip()

            # ==================================================================
            # SCHRITT 1: Leere Ergebnisse erkennen und für Re-Crawl separieren
            # ==================================================================
            empty_mask = group.apply(lambda row: self._is_empty_result(row), axis=1)
            empty_rows = group[empty_mask]
            filled_rows = group[~empty_mask]

            # Leere Ergebnisse → Re-Crawl-Datei (im Input-Format für Flow 1)
            if not empty_rows.empty:
                logger.info(f"KundenNr {kunden_nr}: {len(empty_rows)} leere Ergebnisse → erneut crawlen")
                for _, row in empty_rows.iterrows():
                    recrawl_results.append({
                        'SearchString': search_string,
                        'PLZ': input_plz,
                        'Stadt': input_stadt,
                        'KundenNr': kunden_nr
                    })

            # Wenn ALLE Ergebnisse leer sind → Kunde ist fertig (kommt in Re-Crawl)
            if filled_rows.empty:
                continue

            # Ab hier nur noch mit gefüllten Ergebnissen weiterarbeiten
            group = filled_rows

            # ==================================================================
            # SCHRITT 2: PLZ-Filter — Ergebnisse aus falscher Postleitzahl entfernen
            # ==================================================================
            plz_mask = group.apply(lambda row: self._plz_matches(row, input_plz), axis=1)
            plz_matches = group[plz_mask]
            plz_mismatches = group[~plz_mask]

            # Falsche PLZ → aussortieren
            if not plz_mismatches.empty:
                logger.debug(f"KundenNr {kunden_nr}: {len(plz_mismatches)} Ergebnisse "
                             f"mit falscher PLZ aussortiert")
                for _, row in plz_mismatches.iterrows():
                    row_dict = row.to_dict()
                    row_dict['qualitaet'] = 'AUSSORTIERT (PLZ)'
                    rejected_results.append(row_dict)

            # Wenn nach PLZ-Filter nichts übrig bleibt → manuelle Prüfung
            if plz_matches.empty:
                logger.info(f"KundenNr {kunden_nr}: Keine PLZ-Treffer, zur Prüfung.")
                for _, row in group.iterrows():
                    row_dict = row.to_dict()
                    row_dict['qualitaet'] = 'ZUR_PRUEFUNG (keine PLZ-Treffer)'
                    review_results.append(row_dict)
                continue

            # Ab hier nur noch mit PLZ-gefilterten Ergebnissen weiterarbeiten
            group = plz_matches

            # ==================================================================
            # SCHRITT 3: Einzelergebnis → automatisch eindeutig
            # ==================================================================
            if len(group) == 1:
                row_dict = group.iloc[0].to_dict()
                row_dict['qualitaet'] = 'OK'
                unique_results.append(row_dict)
                continue

            # ==================================================================
            # SCHRITT 4: Die "Weiche" — Strassenabgleich oder direkt Scoring?
            # ==================================================================
            street_to_find = self._has_street_in_searchstring(search_string)
            processing_group = group  # Standard: alle Ergebnisse gehen ins Scoring

            if street_to_find:
                # --- SZENARIO B: Strasse im Suchbegriff vorhanden ---
                # Zuerst Strasse abgleichen, dann nur passende Ergebnisse scoren
                norm_street_to_find = self._normalize_text(street_to_find)
                logger.debug(f"KundenNr {kunden_nr}: Szenario B (Strasse: '{street_to_find}')")

                # Jedes Google-Ergebnis gegen die erwartete Strasse prüfen
                street_matches_mask = group['street'].apply(
                    lambda x: self._street_matches(street_to_find, str(x))
                    if norm_street_to_find else False
                )
                street_matches = group[street_matches_mask]
                street_mismatches = group[~street_matches_mask]

                # Strassen-Fehlschläge → aussortieren
                if not street_mismatches.empty:
                    for _, row in street_mismatches.iterrows():
                        row_dict = row.to_dict()
                        row_dict['qualitaet'] = 'AUSSORTIERT (Strasse)'
                        rejected_results.append(row_dict)

                if len(street_matches) == 0:
                    # Keine einzige Strasse passt → alle zur manuellen Prüfung
                    logger.info(f"KundenNr {kunden_nr}: Keine Strassentreffer, zur Prüfung.")
                    for _, row in group.iterrows():
                        row_dict = row.to_dict()
                        row_dict['qualitaet'] = 'ZUR_PRUEFUNG (keine Strassentreffer)'
                        review_results.append(row_dict)
                    continue
                elif len(street_matches) == 1:
                    # Genau 1 Strassentreffer → eindeutig
                    row_dict = street_matches.iloc[0].to_dict()
                    row_dict['qualitaet'] = 'OK (Strasse)'
                    unique_results.append(row_dict)
                    continue
                else:
                    # Mehrere Strassentreffer → Title-Scoring entscheidet
                    processing_group = street_matches
            else:
                # --- SZENARIO A: Keine Strasse im Suchbegriff ---
                # Alle Ergebnisse gehen direkt ins Title-Scoring
                logger.debug(f"KundenNr {kunden_nr}: Szenario A (keine Strasse)")

            # ==================================================================
            # SCHRITT 5: Title-Scoring — Name des Suchbegriffs vs Google-Titel
            # ==================================================================
            scored_group = self._calculate_scores(processing_group)

            # Ergebnisse aufteilen: hoher Score (≥80) vs niedriger Score (<80)
            high_confidence_hits = scored_group[scored_group['score'] >= 80]
            low_confidence_hits = scored_group[scored_group['score'] < 80]

            if not high_confidence_hits.empty:
                if len(high_confidence_hits) == 1:
                    # --- GENAU 1 Treffer über 80 → eindeutig ---
                    row_dict = high_confidence_hits.iloc[0].to_dict()
                    row_dict['qualitaet'] = 'OK (Score)'
                    unique_results.append(row_dict)
                    # Alles unter 80 in derselben Gruppe → aussortieren
                    for _, row in low_confidence_hits.iterrows():
                        row_dict = row.to_dict()
                        row_dict['qualitaet'] = 'AUSSORTIERT (Score)'
                        rejected_results.append(row_dict)
                else:
                    # --- MEHRERE Treffer über 80 → mehrdeutig → manuelle Prüfung ---
                    # Beispiel: 2 SPAR-Filialen in derselben PLZ, beide scoren hoch.
                    # Algorithmus kann nicht entscheiden welche richtig ist.
                    logger.info(f"KundenNr {kunden_nr}: {len(high_confidence_hits)} Treffer "
                                f"über 80 → zur Prüfung (mehrdeutig)")
                    for _, row in high_confidence_hits.iterrows():
                        row_dict = row.to_dict()
                        row_dict['qualitaet'] = 'ZUR_PRUEFUNG (mehrere hohe Treffer)'
                        review_results.append(row_dict)
                    for _, row in low_confidence_hits.iterrows():
                        row_dict = row.to_dict()
                        row_dict['qualitaet'] = 'AUSSORTIERT (Score)'
                        rejected_results.append(row_dict)
            else:
                # --- DYNAMISCHER SCHWELLENWERT: Kein Score über 80 ---
                # Prüfen ob der Abstand zwischen Platz 1 und Platz 2 gross genug ist
                sorted_low_hits = low_confidence_hits.sort_values('score', ascending=False)

                if len(sorted_low_hits) >= 2:
                    score_1 = float(sorted_low_hits.iloc[0]['score'])  # Bester Score
                    score_2 = float(sorted_low_hits.iloc[1]['score'])  # Zweitbester Score

                    if score_1 - score_2 >= self.dynamic_gap_threshold:
                        # Abstand gross genug → Bester Treffer ist wahrscheinlich korrekt
                        best_hit = sorted_low_hits.iloc[0].to_dict()
                        best_hit['qualitaet'] = 'OK (Dynamisch)'
                        unique_results.append(best_hit)

                        # Rest aussortieren
                        for _, row in sorted_low_hits.iloc[1:].iterrows():
                            row_dict = row.to_dict()
                            row_dict['qualitaet'] = 'AUSSORTIERT (Dynamisch)'
                            rejected_results.append(row_dict)

                        logger.info(f"KundenNr {kunden_nr}: Dynamischer Treffer "
                                    f"(Score {score_1:.0f} vs {score_2:.0f})")
                    else:
                        # Abstand zu klein → nicht unterscheidbar → manuelle Prüfung
                        for _, row in sorted_low_hits.iterrows():
                            row_dict = row.to_dict()
                            row_dict['qualitaet'] = 'ZUR_PRUEFUNG (kein klarer Treffer)'
                            review_results.append(row_dict)
                else:
                    # Nur 1 Ergebnis mit niedrigem Score → manuelle Prüfung
                    for _, row in sorted_low_hits.iterrows():
                        row_dict = row.to_dict()
                        row_dict['qualitaet'] = 'ZUR_PRUEFUNG (niedriger Score)'
                        review_results.append(row_dict)

        # ==================================================================
        # ERGEBNISSE SPEICHERN
        # ==================================================================
        base_path = input_filepath.rsplit('.', 1)[0]

        results = {}

        # Die 3 Hauptdateien speichern
        for name, data in [('eindeutig', unique_results),
                           ('zur_pruefung', review_results),
                           ('aussortiert', rejected_results)]:
            filepath = f"{base_path}_{name}.csv"
            out_df = pd.DataFrame(data)
            # Interne Score-Spalte entfernen — gehört nicht in die Ausgabe
            if 'score' in out_df.columns:
                out_df = out_df.drop(columns=['score'])
            out_df.to_csv(filepath, sep=';', index=False, encoding='utf-8-sig')
            results[name] = filepath
            logger.info(f"{name}: {len(data)} Einträge → {filepath}")

        # Die 4. Datei: Kunden mit leeren API-Ergebnissen zum nochmaligen Crawlen
        # Format: Gleich wie die Original-Inputdatei → kann direkt in Flow 1 verwendet werden
        if recrawl_results:
            recrawl_filepath = f"{base_path}_erneut_crawlen.csv"
            recrawl_df = pd.DataFrame(recrawl_results)
            # Deduplizieren: Gleicher Kunde mit mehreren leeren Zeilen → nur 1 Eintrag
            recrawl_df = recrawl_df.drop_duplicates(subset=['KundenNr'])
            recrawl_df.to_csv(recrawl_filepath, sep=';', index=False, encoding='utf-8-sig')
            results['erneut_crawlen'] = recrawl_filepath
            logger.info(f"erneut_crawlen: {len(recrawl_df)} Einträge → {recrawl_filepath}")
        else:
            logger.info("Keine leeren Ergebnisse — keine Re-Crawl-Datei nötig.")

        return results