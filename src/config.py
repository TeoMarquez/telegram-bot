from dotenv import load_dotenv
import os
from pathlib import Path

load_dotenv()

DATA_DIR = Path("data")

BOT_TOKEN = os.getenv("BOT_TOKEN")
AUTHORIZED_USER = int(os.getenv("AUTHORIZED_USER"))

WATCHDOG_FILE = DATA_DIR / "watchdog.json"