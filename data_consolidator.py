# data_consolidator.py
# Schritt 3: Zusammenführen — konsolidiert _eindeutig und _zur_pruefung
# aus allen batch_*-Ordnern in eine einzige Ausgabedatei pro Typ.

import csv
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

EINDEUTIG_SUFFIX    = "_optimierte_daten_eindeutig.csv"
ZUR_PRUEFUNG_SUFFIX = "_optimierte_daten_zur_pruefung.csv"


class DataConsolidator:
    """Findet alle batch_*-Ordner und führt deren Ausgabedateien zusammen."""

    def consolidate(self, base_dir: str) -> dict:
        """
        Scannt base_dir nach batch_*-Ordnern, merged _eindeutig und _zur_pruefung.

        Returns:
            {
                'eindeutig':     str (Pfad zur Ausgabedatei),
                'zur_pruefung':  str (Pfad zur Ausgabedatei),
                'output_dir':    str (Pfad zum Ausgabeordner),
                'batches_found': list[int],
                'stats': {
                    'eindeutig_rows':    int,
                    'zur_pruefung_rows': int,
                    'eindeutig_unique_customers':    int,
                    'zur_pruefung_unique_customers': int,
                }
            }
        """
        base_path = Path(base_dir)

        # Alle batch_*-Ordner finden und nach Nummer sortieren
        batch_dirs = sorted(
            [d for d in base_path.iterdir() if d.is_dir() and re.match(r'^batch_\d+$', d.name)],
            key=lambda d: int(re.search(r'\d+', d.name).group())
        )

        if not batch_dirs:
            raise ValueError(f"Keine batch_*-Ordner gefunden in: {base_dir}")

        batch_numbers = [int(re.search(r'\d+', d.name).group()) for d in batch_dirs]
        logger.info(f"Gefundene Batch-Ordner: {batch_numbers}")

        # Nur Batches zählen, die tatsächlich Ausgabedateien haben
        batches_with_data = [
            n for n, d in zip(batch_numbers, batch_dirs)
            if any(d.glob(f"*{EINDEUTIG_SUFFIX}"))
        ]
        if not batches_with_data:
            raise ValueError("Keine Batches mit Ausgabedateien gefunden.")
        logger.info(f"Batches mit Daten: {batches_with_data}")

        # Ausgabeordner benennen nach erstem und letztem Batch mit Daten
        out_folder_name = f"consolidated_batch_{batches_with_data[0]}_{batches_with_data[-1]}"
        output_dir = base_path / out_folder_name
        output_dir.mkdir(exist_ok=True)
        logger.info(f"Ausgabeordner: {out_folder_name}")

        eindeutig_out    = output_dir / f"eindeutig_batch_{batches_with_data[0]}_{batches_with_data[-1]}.csv"
        zur_pruefung_out = output_dir / f"zur_pruefung_batch_{batches_with_data[0]}_{batches_with_data[-1]}.csv"

        eindeutig_stats    = self._merge_files(batch_dirs, EINDEUTIG_SUFFIX,    eindeutig_out)
        zur_pruefung_stats = self._merge_files(batch_dirs, ZUR_PRUEFUNG_SUFFIX, zur_pruefung_out)

        return {
            'eindeutig':     str(eindeutig_out),
            'zur_pruefung':  str(zur_pruefung_out),
            'output_dir':    str(output_dir),
            'batches_found': batches_with_data,
            'stats': {
                'eindeutig_rows':                eindeutig_stats['rows'],
                'zur_pruefung_rows':             zur_pruefung_stats['rows'],
                'eindeutig_unique_customers':    eindeutig_stats['unique_customers'],
                'zur_pruefung_unique_customers': zur_pruefung_stats['unique_customers'],
            }
        }

    def _merge_files(self, batch_dirs: list, suffix: str, output_path: Path) -> dict:
        """Merged alle Dateien mit gegebenem Suffix aus den batch-Ordnern."""
        header_written = False
        total_rows = 0
        unique_customers = set()

        with open(output_path, 'w', newline='', encoding='utf-8-sig') as out_file:
            writer = None

            for batch_dir in batch_dirs:
                # Erste Datei im Ordner finden, die mit dem Suffix endet
                matching = list(batch_dir.glob(f"*{suffix}"))
                if not matching:
                    logger.warning(f"  Keine Datei mit Suffix '{suffix}' in {batch_dir.name} — übersprungen.")
                    continue

                source_file = matching[0]
                logger.info(f"  Lese: {batch_dir.name}/{source_file.name}")

                with open(source_file, 'r', newline='', encoding='utf-8-sig') as in_file:
                    reader = csv.DictReader(in_file, delimiter=';')

                    if not header_written:
                        writer = csv.DictWriter(out_file, fieldnames=reader.fieldnames, delimiter=';')
                        writer.writeheader()
                        header_written = True

                    for row in reader:
                        writer.writerow(row)
                        total_rows += 1
                        kunden_nr = row.get('KundenNr', '').strip()
                        if kunden_nr:
                            unique_customers.add(kunden_nr)

        logger.info(f"  → {total_rows} Zeilen, {len(unique_customers)} eindeutige Kunden geschrieben nach {output_path.name}")
        return {'rows': total_rows, 'unique_customers': len(unique_customers)}
