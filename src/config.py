from dotenv import load_dotenv
import os
from pathlib import Path

load_dotenv()

DATA_DIR = Path("data")

BOT_TOKEN = os.getenv("BOT_TOKEN")

AUTHORIZED_USER = int(os.getenv("AUTHORIZED_USER", "-1")) # Si no se define o se pone -1, va a actuar en modo público
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@localhost.local") #  si no se define, cae en un mail genérico, no recomendada para producción

# Services Manager REST API
URL_API_SERVICE_MANAGER = os.getenv("url_api_service_manager", "").rstrip("/")
TOKEN_SERVICE_MANAGER = os.getenv("token_service_manager", "")


WATCHDOG_FILE = DATA_DIR / "watchdog.json"
