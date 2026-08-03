# db.py
# Eine SQLite-Datei, Schema wörtlich nach 02_DATENVERTRAG.md §5.
#
# Der Zweck ist Transparenz: nicht nur der gewählte Treffer wird gespeichert,
# sondern jeder Kandidat mit seinem Score und der Entscheidung darüber. Erst
# damit ist nach einem Lauf auswertbar, warum ein Kunde zur Prüfung ging.

import logging
import sqlite3
from datetime import datetime
from pathlib import Path

from place_provider import Candidate

logger = logging.getLogger(__name__)

# Wörtlich aus 02_DATENVERTRAG.md §5. Nicht umbenennen, nicht ergänzen.
SCHEMA = """
CREATE TABLE IF NOT EXISTS job (
  id INTEGER PRIMARY KEY,
  modus TEXT NOT NULL,
  dateiname TEXT NOT NULL,
  status TEXT NOT NULL,
  email TEXT,
  kunden_total INTEGER DEFAULT 0,
  kunden_erledigt INTEGER DEFAULT 0,
  fehlermeldung TEXT,
  erstellt_am TEXT NOT NULL,
  gestartet_am TEXT,
  beendet_am TEXT
);

CREATE TABLE IF NOT EXISTS kunde (
  id INTEGER PRIMARY KEY,
  job_id INTEGER NOT NULL REFERENCES job(id),
  kunden_nr TEXT NOT NULL,
  search_string TEXT, plz TEXT, stadt TEXT,
  place_id TEXT, lat TEXT, lng TEXT,
  ergebnis TEXT,
  qualitaet TEXT,
  grund TEXT,
  verarbeitet_am TEXT
);
CREATE INDEX IF NOT EXISTS idx_kunde_job ON kunde(job_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_kunde_nr ON kunde(job_id, kunden_nr);

CREATE TABLE IF NOT EXISTS kandidat (
  id INTEGER PRIMARY KEY,
  kunde_id INTEGER NOT NULL REFERENCES kunde(id),
  title TEXT, street TEXT, postal_code TEXT, city TEXT, address TEXT,
  place_id TEXT, cid TEXT, location TEXT,
  phone TEXT, phone_unformatted TEXT, website TEXT, opening_hours TEXT,
  permanently_closed TEXT, temporarily_closed TEXT,
  score REAL,
  entscheid TEXT,
  grund TEXT
);
CREATE INDEX IF NOT EXISTS idx_kandidat_kunde ON kandidat(kunde_id);
"""

# 02_DATENVERTRAG.md §6
ZUSTAENDE = ('NEU', 'VALIDIERT', 'LAEUFT', 'FERTIG', 'ABGEBROCHEN', 'FEHLER')

# 02_DATENVERTRAG.md §5, Spalte kandidat.entscheid
ENTSCHEIDE = ('gewaehlt', 'abgelehnt', 'vorgeschlagen')

# 02_DATENVERTRAG.md §5, Spalte kunde.ergebnis
ERGEBNISSE = ('fertig', 'pruefung', 'nicht_moeglich')


def _jetzt() -> str:
    return datetime.now().isoformat(timespec='seconds')


class Datenbank:
    """Zugriffsschicht: Job anlegen, Kunde schreiben, Kandidaten schreiben, Fortschritt."""

    def __init__(self, pfad: str = ':memory:'):
        self.pfad = str(pfad)
        if self.pfad != ':memory:':
            Path(self.pfad).parent.mkdir(parents=True, exist_ok=True)
        self.verbindung = sqlite3.connect(self.pfad)
        self.verbindung.row_factory = sqlite3.Row
        self.verbindung.execute('PRAGMA foreign_keys = ON')
        self.verbindung.executescript(SCHEMA)
        self.verbindung.commit()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.schliessen()

    def schliessen(self) -> None:
        self.verbindung.close()

    # ------------------------------------------------------------------
    # Job
    # ------------------------------------------------------------------

    def job_anlegen(self, modus: str, dateiname: str, kunden_total: int = 0,
                    email: str = None) -> int:
        if modus not in ('A', 'B'):
            raise ValueError(f'Unbekannter Modus "{modus}", erlaubt sind A und B.')
        cursor = self.verbindung.execute(
            'INSERT INTO job (modus, dateiname, status, email, kunden_total, '
            'kunden_erledigt, erstellt_am) VALUES (?, ?, ?, ?, ?, 0, ?)',
            (modus, dateiname, 'NEU', email, kunden_total, _jetzt()))
        self.verbindung.commit()
        return cursor.lastrowid

    def status_setzen(self, job_id: int, status: str, fehlermeldung: str = None) -> None:
        """Setzt den Zustand nach 02_DATENVERTRAG.md §6 und stempelt die Zeiten."""
        if status not in ZUSTAENDE:
            raise ValueError(f'Unbekannter Zustand "{status}".')

        felder = ['status = ?']
        werte = [status]
        if status == 'LAEUFT':
            felder.append('gestartet_am = ?')
            werte.append(_jetzt())
        if status in ('FERTIG', 'ABGEBROCHEN', 'FEHLER'):
            felder.append('beendet_am = ?')
            werte.append(_jetzt())
        felder.append('fehlermeldung = ?')
        werte.append(fehlermeldung)
        werte.append(job_id)

        self.verbindung.execute(
            f'UPDATE job SET {", ".join(felder)} WHERE id = ?', werte)
        self.verbindung.commit()

    def job_lesen(self, job_id: int) -> dict:
        zeile = self.verbindung.execute(
            'SELECT * FROM job WHERE id = ?', (job_id,)).fetchone()
        return dict(zeile) if zeile else None

    # ------------------------------------------------------------------
    # Fortschritt
    # ------------------------------------------------------------------

    def fortschritt_setzen(self, job_id: int, kunden_erledigt: int) -> None:
        """Wird nach jedem Kunden aufgerufen (02_DATENVERTRAG.md §6)."""
        self.verbindung.execute(
            'UPDATE job SET kunden_erledigt = ? WHERE id = ?', (kunden_erledigt, job_id))
        self.verbindung.commit()

    def fortschritt_lesen(self, job_id: int) -> dict:
        zeile = self.verbindung.execute(
            'SELECT status, kunden_total, kunden_erledigt, fehlermeldung '
            'FROM job WHERE id = ?', (job_id,)).fetchone()
        return dict(zeile) if zeile else None

    # ------------------------------------------------------------------
    # Kunde
    # ------------------------------------------------------------------

    def kunde_schreiben(self, job_id: int, kunden_nr: str, search_string: str = '',
                        plz: str = '', stadt: str = '', place_id: str = '',
                        lat: str = '', lng: str = '', ergebnis: str = None,
                        qualitaet: str = None, grund: str = None) -> int:
        """
        Legt einen Kunden an. Ein zweiter Kunde mit derselben Nummer im selben
        Job wird von `idx_kunde_nr` abgewiesen (sqlite3.IntegrityError).
        """
        if ergebnis is not None and ergebnis not in ERGEBNISSE:
            raise ValueError(f'Unbekanntes Ergebnis "{ergebnis}".')
        cursor = self.verbindung.execute(
            'INSERT INTO kunde (job_id, kunden_nr, search_string, plz, stadt, '
            'place_id, lat, lng, ergebnis, qualitaet, grund, verarbeitet_am) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (job_id, str(kunden_nr), search_string, plz, stadt, place_id, lat, lng,
             ergebnis, qualitaet, grund, _jetzt()))
        self.verbindung.commit()
        return cursor.lastrowid

    def kunden_lesen(self, job_id: int) -> list:
        return [dict(z) for z in self.verbindung.execute(
            'SELECT * FROM kunde WHERE job_id = ? ORDER BY id', (job_id,))]

    # ------------------------------------------------------------------
    # Kandidaten
    # ------------------------------------------------------------------

    def kandidaten_schreiben(self, kunde_id: int, eintraege: list) -> int:
        """
        Schreibt die Kandidaten eines Kunden.

        `eintraege` ist eine Liste von (Candidate, score, entscheid, grund).
        Jeder Kandidat wird gespeichert, auch der abgelehnte — das ist der
        Grund, warum es die Tabelle überhaupt gibt.
        """
        zeilen = []
        for kandidat, score, entscheid, grund in eintraege:
            if not isinstance(kandidat, Candidate):
                raise TypeError('kandidaten_schreiben erwartet Candidate-Objekte.')
            if entscheid not in ENTSCHEIDE:
                raise ValueError(f'Unbekannter Entscheid "{entscheid}".')
            zeilen.append((
                kunde_id, kandidat.title, kandidat.street, kandidat.postal_code,
                kandidat.city, kandidat.address, kandidat.place_id, kandidat.cid,
                kandidat.location, kandidat.phone, kandidat.phone_unformatted,
                kandidat.website, kandidat.opening_hours, kandidat.permanently_closed,
                kandidat.temporarily_closed, float(score), entscheid, grund))

        self.verbindung.executemany(
            'INSERT INTO kandidat (kunde_id, title, street, postal_code, city, '
            'address, place_id, cid, location, phone, phone_unformatted, website, '
            'opening_hours, permanently_closed, temporarily_closed, score, '
            'entscheid, grund) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '
            '?, ?, ?, ?)', zeilen)
        self.verbindung.commit()
        return len(zeilen)

    def kandidaten_lesen(self, kunde_id: int) -> list:
        return [dict(z) for z in self.verbindung.execute(
            'SELECT * FROM kandidat WHERE kunde_id = ? ORDER BY id', (kunde_id,))]

    def kandidaten_zaehlen(self, job_id: int) -> int:
        zeile = self.verbindung.execute(
            'SELECT COUNT(*) AS anzahl FROM kandidat WHERE kunde_id IN '
            '(SELECT id FROM kunde WHERE job_id = ?)', (job_id,)).fetchone()
        return zeile['anzahl']
