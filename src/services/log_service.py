from datetime import datetime, date
from pathlib import Path
import threading

LOG_DIR = Path("logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

_lock = threading.Lock()
_current_date = None
_current_file = None


def _get_log_file():
    global _current_date, _current_file

    today = date.today()

    if _current_date != today:
        _current_date = today
        _current_file = LOG_DIR / f"bot-{today}.log"

    return _current_file


def log_event(msg: str):
    file = _get_log_file()

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    line = f"{timestamp} | {msg}\n"

    with _lock:
        with open(file, "a", encoding="utf-8") as f:
            f.write(line)