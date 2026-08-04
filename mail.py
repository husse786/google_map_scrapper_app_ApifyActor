# mail.py
# Bescheid geben, wenn ein Lauf zu Ende ist.
#
# Ein Lauf über 2'500 Kunden dauert Stunden — bei der in Phase 4 gemessenen
# Geschwindigkeit möglicherweise über Nacht. Ohne Mail müsste jemand am
# nächsten Morgen von sich aus nachsehen, ob er durchgelaufen ist oder um drei
# Uhr abgebrochen wurde. Genau diese Handarbeit soll die Anwendung ersparen.
#
# Fehlt die SMTP-Konfiguration, wird das protokolliert und sonst nichts. Ein
# Lauf darf nie daran scheitern, dass niemand eine Mail einrichten wollte.

import logging
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from pathlib import Path

logger = logging.getLogger(__name__)

BETREFF_JE_STATUS = {
    'FERTIG': 'fertig',
    'ABGEBROCHEN': 'abgebrochen',
    'FEHLER': 'gestoppt',
}


@dataclass
class SmtpKonfiguration:
    """Was zum Versenden nötig ist. Ohne `server` wird nicht versendet."""

    server: str = ''
    port: int = 25
    benutzer: str = ''
    passwort: str = ''
    absender: str = ''
    tls: bool = True

    @property
    def vollstaendig(self) -> bool:
        return bool(self.server and self.absender)


def aus_konfiguration() -> SmtpKonfiguration:
    """
    Liest die SMTP-Angaben aus config.py.

    Fehlt die Datei oder fehlen Einträge, kommt eine leere Konfiguration
    zurück — kein Fehler. Ob versendet wird, entscheidet `vollstaendig`.
    """
    try:
        import config
    except Exception:
        return SmtpKonfiguration()

    return SmtpKonfiguration(
        server=str(getattr(config, 'SMTP_SERVER', '') or ''),
        port=int(getattr(config, 'SMTP_PORT', 25) or 25),
        benutzer=str(getattr(config, 'SMTP_BENUTZER', '') or ''),
        passwort=str(getattr(config, 'SMTP_PASSWORT', '') or ''),
        absender=str(getattr(config, 'SMTP_ABSENDER', '') or ''),
        tls=bool(getattr(config, 'SMTP_TLS', True)),
    )


# ==========================================================================
# Die Nachricht
# ==========================================================================

def betreff(job: dict) -> str:
    """
    Nennt Dateiname und Ergebnis — beides muss in der Übersicht sichtbar sein.

    Bewusst ohne Gedankenstrich: ein Sonderzeichen im Betreff zwingt jedes
    Mailprogramm zur Umkodierung, und in der Übersicht steht dann mitten im
    Betreff ein Zeichensalat. Ein schlichter Bindestrich bleibt lesbar.
    """
    ergebnis = BETREFF_JE_STATUS.get(job.get('status'), str(job.get('status')))
    return f'Kundendaten anreichern: {job.get("dateiname", "")} - {ergebnis}'


def nachricht(job: dict, dateien: dict = None) -> str:
    """Der Text der Mail. Deutsch, kurz, mit dem nächsten Schritt am Schluss."""
    status = job.get('status')
    dateiname = job.get('dateiname', '')
    erledigt = job.get('kunden_erledigt') or 0
    total = job.get('kunden_total') or 0

    zeilen = []
    if status == 'FERTIG':
        zeilen.append(f'Der Lauf zur Datei «{dateiname}» ist fertig.')
        zeilen.append('')
        zeilen.append(f'{_zahl(total)} Kunden verarbeitet.')
        if dateien:
            zeilen.append('')
            zeilen.append('Die drei Dateien liegen bereit:')
            for beschriftung, pfad in dateien.items():
                zeilen.append(f'  {beschriftung}: {Path(pfad).name}')
            zeilen.append('')
            zeilen.append(f'Ordner: {Path(next(iter(dateien.values()))).parent}')
        zeilen.append('')
        zeilen.append('Zum Herunterladen die Anwendung im Browser öffnen.')

    elif status == 'ABGEBROCHEN':
        zeilen.append(f'Der Lauf zur Datei «{dateiname}» wurde abgebrochen.')
        zeilen.append('')
        zeilen.append(f'{_zahl(erledigt)} von {_zahl(total)} Kunden waren fertig. '
                      f'Sie sind gespeichert und gehen nicht verloren.')
        zeilen.append('')
        zeilen.append('Es wurden keine Ergebnisdateien geschrieben, weil der Lauf '
                      'unvollständig ist.')

    else:  # FEHLER
        zeilen.append(f'Der Lauf zur Datei «{dateiname}» musste gestoppt werden.')
        zeilen.append('')
        meldung = job.get('fehlermeldung')
        if meldung:
            zeilen.append(str(meldung))
            zeilen.append('')
        zeilen.append(f'{_zahl(erledigt)} von {_zahl(total)} Kunden waren fertig. '
                      f'Sie sind gespeichert.')
        zeilen.append('')
        zeilen.append('Wenn die Ursache behoben ist, bietet die Anwendung beim '
                      'nächsten Start an, den Lauf fortzusetzen. Es wird kein '
                      'Kunde doppelt gesucht.')

    zeilen.append('')
    zeilen.append('—')
    zeilen.append('Diese Nachricht wurde automatisch verschickt.')
    return '\n'.join(zeilen)


def _zahl(wert: int) -> str:
    return f'{wert:,}'.replace(',', "'")


# ==========================================================================
# Versand
# ==========================================================================

def sende_abschlussmail(job: dict, dateien: dict = None,
                        konfiguration: SmtpKonfiguration = None) -> bool:
    """
    Verschickt die Nachricht zum Ende eines Laufs.

    Liefert True, wenn sie draussen ist. Alles andere — keine Adresse, keine
    SMTP-Angaben, Server nicht erreichbar — wird protokolliert und mit False
    beantwortet. Diese Funktion wirft nichts: sie darf einen fertigen Lauf
    nicht nachträglich zu einem Fehler machen.
    """
    empfaenger = (job.get('email') or '').strip()
    if not empfaenger:
        logger.info(f'Job {job.get("id")}: keine Adresse hinterlegt, keine Mail.')
        return False

    konfiguration = konfiguration or aus_konfiguration()
    if not konfiguration.vollstaendig:
        logger.info(
            f'Job {job.get("id")}: keine SMTP-Konfiguration hinterlegt. '
            f'Es wäre eine Mail an {empfaenger} gegangen, Betreff '
            f'«{betreff(job)}».')
        return False

    post = EmailMessage()
    post['Subject'] = betreff(job)
    post['From'] = konfiguration.absender
    post['To'] = empfaenger
    post.set_content(nachricht(job, dateien))

    try:
        with smtplib.SMTP(konfiguration.server, konfiguration.port,
                          timeout=30) as verbindung:
            if konfiguration.tls:
                verbindung.starttls()
            if konfiguration.benutzer:
                verbindung.login(konfiguration.benutzer, konfiguration.passwort)
            verbindung.send_message(post)
    except Exception as fehler:
        logger.error(f'Mail an {empfaenger} liess sich nicht versenden: {fehler}')
        return False

    logger.info(f'Mail an {empfaenger} verschickt: {betreff(job)}')
    return True
