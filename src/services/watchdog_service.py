# services/watchdog_service.py

import asyncio

from config import (
    AUTHORIZED_USER,
    WATCHDOG_FILE
)

from utils import get_uptime
import psutil
import json

STATE_FILE = WATCHDOG_FILE

def load_state():

    with open(STATE_FILE) as f:
        return json.load(f)
    
def save_state(data):

    with open(STATE_FILE, "w") as f:
        json.dump(
            data,
            f,
            indent=4
        )

def ensure_state_file():

    STATE_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    if not STATE_FILE.exists():

        save_state({
            "enabled": True,
            "interval": 3600
        })

def get_interval():

    return load_state()["interval"]

def set_interval(seconds):

    state = load_state()

    state["interval"] = seconds

    save_state(state)

def is_enabled():

    return load_state()["enabled"]

def set_enabled(value):

    state = load_state()

    state["enabled"] = value

    save_state(state)

def get_status():
    state = load_state()

    return {
        "enabled": state["enabled"],
        "interval": state["interval"]
    }

async def watchdog_loop(app):
    while True:
        try:
            if is_enabled() and AUTHORIZED_USER != -1:
                ram = psutil.virtual_memory()
                cpu = psutil.cpu_percent()

                await app.bot.send_message(
                    chat_id=AUTHORIZED_USER,
                    text=(
                        "🟢 Watchdog\n\n"
                        f"Uptime: {get_uptime()}\n"
                        f"RAM: {ram.percent}%\n"
                        f"CPU: {cpu}%\n"
                        f"Disponible: {ram.available // 1024 // 1024} MB"
                    )
                )
        except Exception as e:
            print(f"Watchdog error: {e}")

        await asyncio.sleep(get_interval())