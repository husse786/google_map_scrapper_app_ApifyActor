# data_preprocessor.py
# Modul zur Vorverarbeitung der Input-Daten BEVOR sie an die Google Maps API gesendet werden.
#
# Zweck: Prüft die Vollständigkeit des SearchStrings und trennt die Eingabedaten in:
#   - _vollstaendig.csv     → alle 3 Teile vorhanden → bereit für Flow 1 (Crawling)
#   - _unvollstaendig.csv   → mindestens 1 Teil fehlt → zuerst manuell korrigieren
#
# SearchString-Format: "Title, Strasse+Nr, PLZ Stadt"
#   Teil 1: Name/Titel des Geschäfts     (z.B. "Freibad Full")
#   Teil 2: Strasse und Hausnummer        (z.B. "Rheinweg 199")
#   Teil 3: Postleitzahl und Ort          (z.B. "5324 Full-Reuenthal")

import pandas as pd
import logging

logger = logging.getLogger(__name__)


class DataPreprocessor:
    """Prüft die Vollständigkeit der Input-Daten vor dem Crawling."""

    def _analyze_searchstring(self, search_string: str) -> dict:
        """
        Zerlegt den SearchString in seine 3 Teile und prüft deren Vollständigkeit.

        Beispiel vollständig:
            "Freibad Full, Rheinweg 199, 5324 Full-Reuenthal"
            → Teil 1: "Freibad Full"       ✅
            → Teil 2: "Rheinweg 199"       ✅
            → Teil 3: "5324 Full-Reuenthal" ✅

        Beispiel unvollständig:
            "Spar Supermarkt,  , 9642 Ebnat-Kappel"
            → Teil 1: "Spar Supermarkt"     ✅
            → Teil 2: ""                     ❌ (leer)
            → Teil 3: "9642 Ebnat-Kappel"   ✅

        Returns:
            Dict mit den Teilen und einer Bewertung:
            {
                'title': str,           # Teil 1
                'street': str,          # Teil 2
                'plz_city': str,        # Teil 3
                'is_complete': bool,    # True wenn alle 3 Teile vorhanden
                'missing_parts': list   # Liste der fehlenden Teile
            }
        """
        parts = search_string.split(',') if search_string else []
        missing_parts = []

        # Teil 1: Titel/Name
        title = parts[0].strip() if len(parts) >= 1 else ''
        if not title:
            missing_parts.append('Title')

        # Teil 2: Strasse + Hausnummer
        street = parts[1].strip() if len(parts) >= 2 else ''
        if not street:
            missing_parts.append('Strasse')

        # Teil 3: PLZ + Stadt
        plz_city = parts[2].strip() if len(parts) >= 3 else ''
        if not plz_city:
            missing_parts.append('PLZ+Stadt')

        return {
            'title': title,
            'street': street,
            'plz_city': plz_city,
            'is_complete': len(missing_parts) == 0,
            'missing_parts': missing_parts
        }

    def preprocess(self, input_filepath: str) -> dict:
        """
        Hauptmethode: Liest die Input-CSV und teilt sie in vollständige
        und unvollständige Datensätze auf.

        Args:
            input_filepath: Pfad zur Input-CSV-Datei

        Returns:
            Dict mit Dateipfaden:
            {
                'vollstaendig': '/pfad/zur/datei_vollstaendig.csv',
                'unvollstaendig': '/pfad/zur/datei_unvollstaendig.csv',
                'stats': {
                    'total': int,
                    'complete': int,
                    'incomplete': int
                }
            }
        """
        logger.info(f"Starte Vorverarbeitung der Datei: {input_filepath}")

        # CSV laden — alles als String einlesen
        df = pd.read_csv(input_filepath, sep=';', encoding='utf-8-sig', dtype=str).fillna('')

        # Pflichtfelder prüfen
        if 'SearchString' not in df.columns or 'KundenNr' not in df.columns:
            raise ValueError("Die Spalten 'SearchString' und 'KundenNr' werden benötigt.")

        # Leere Zeilen und Spalten ohne Header entfernen
        # (manchmal hat die CSV eine leere letzte Spalte durch abschliessendes Semikolon)
        df = df.loc[:, ~df.columns.str.match(r'^Unnamed')]
        df = df[df['SearchString'].str.strip() != '']

        complete_rows = []      # Vollständige Datensätze → bereit zum Crawlen
        incomplete_rows = []    # Unvollständige Datensätze → zuerst korrigieren

        for _, row in df.iterrows():
            search_string = str(row.get('SearchString', ''))
            kunden_nr = str(row.get('KundenNr', ''))

            # SearchString analysieren
            analysis = self._analyze_searchstring(search_string)

            if analysis['is_complete']:
                # Alle 3 Teile vorhanden → bereit für Crawling
                complete_rows.append(row.to_dict())
                logger.debug(f"KundenNr {kunden_nr}: ✅ vollständig")
            else:
                # Mindestens 1 Teil fehlt → separat speichern
                row_dict = row.to_dict()
                # Fehlende Teile als zusätzliche Spalte hinzufügen (für Übersicht)
                row_dict['fehlende_teile'] = ', '.join(analysis['missing_parts'])
                incomplete_rows.append(row_dict)
                logger.info(f"KundenNr {kunden_nr}: ❌ unvollständig — "
                           f"fehlend: {', '.join(analysis['missing_parts'])}")

        # --- Ergebnisse speichern ---
        base_path = input_filepath.rsplit('.', 1)[0]
        results = {}

        # Vollständige Datensätze → diese Datei geht in Flow 1 (Crawling)
        complete_filepath = f"{base_path}_vollstaendig.csv"
        complete_df = pd.DataFrame(complete_rows)
        complete_df.to_csv(complete_filepath, sep=';', index=False, encoding='utf-8-sig')
        results['vollstaendig'] = complete_filepath
        logger.info(f"Vollständig: {len(complete_rows)} Einträge → {complete_filepath}")

        # Unvollständige Datensätze → diese Datei muss manuell korrigiert werden
        incomplete_filepath = f"{base_path}_unvollstaendig.csv"
        incomplete_df = pd.DataFrame(incomplete_rows)
        incomplete_df.to_csv(incomplete_filepath, sep=';', index=False, encoding='utf-8-sig')
        results['unvollstaendig'] = incomplete_filepath
        logger.info(f"Unvollständig: {len(incomplete_rows)} Einträge → {incomplete_filepath}")

        # Statistik
        results['stats'] = {
            'total': len(df),
            'complete': len(complete_rows),
            'incomplete': len(incomplete_rows)
        }

        logger.info(f"Vorverarbeitung abgeschlossen: "
                    f"{len(complete_rows)}/{len(df)} vollständig, "
                    f"{len(incomplete_rows)}/{len(df)} unvollständig")

        return results