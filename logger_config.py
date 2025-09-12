# logger_config.py
# Konfiguriert das zentrale Logging-System für die Anwendung.

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Erstelle einen "logs" Ordner, falls er nicht existiert
log_dir = Path(__file__).resolve().parent / "logs"
log_dir.mkdir(exist_ok=True)
log_file = log_dir / "app.log"

def setup_logger():
    """Richtet den zentralen Logger ein."""
    # Logger-Instanz holen
    logger = logging.getLogger("AppLogger")
    logger.setLevel(logging.INFO) # Loggt alles ab dem Level INFO (INFO, WARNING, ERROR, CRITICAL)

    # Verhindern, dass Handler mehrfach hinzugefügt werden
    if logger.hasHandlers():
        logger.handlers.clear()

    # Formatter definieren: Wie soll eine Log-Nachricht aussehen?
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 1. Handler: In die Datei 'app.log' schreiben
    # RotatingFileHandler sorgt dafür, dass die Log-Datei nicht unendlich groß wird.
    file_handler = RotatingFileHandler(log_file, maxBytes=1024*1024*5, backupCount=2, encoding='utf-8')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # 2. Handler: In die Konsole/Terminal schreiben (für direktes Feedback)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    return logger

# Erstelle eine globale Logger-Instanz, die von anderen Modulen importiert werden kann
logger = setup_logger()