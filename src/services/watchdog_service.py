# services/watchdog_service.py
from config import AUTHORIZED_USER, WATCHDOG_FILE
from state import heartbeat
from services import log_event
from utils import get_uptime

import asyncio
import psutil
import json
import time

STATE_FILE = WATCHDOG_FILE
LOG_INTERVAL = 10
_last_log = {"t": 0}

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
            if not heartbeat.is_alive(120):
                log_event("WATCHDOG_FAIL | heartbeat timeout")
                print("[WATCHDOG] Bot congelado → restart")
                raise SystemExit(1)

            now = time.time()
            ram = psutil.virtual_memory()
            cpu = psutil.cpu_percent()
            
            if now - _last_log["t"] >= LOG_INTERVAL:
                log_event(
                    f"WATCHDOG_OK | CPU={cpu}% RAM={ram.percent}% UPTIME={get_uptime()}"
                )
                _last_log["t"] = now
            await app.bot.get_me()


            if is_enabled() and AUTHORIZED_USER != -1:
                


                await app.bot.send_message(
                    chat_id=AUTHORIZED_USER,
                    text=(
                        "🟢 Watchdog\n\n"
                        f"Uptime: {get_uptime()}\n"
                        f"RAM: {ram.percent}%\n"
                        f"CPU: {cpu}%"
                    )
                )

        except Exception as e:
            log_event(f"WATCHDOG_ERROR | {e}")
            print(f"[WATCHDOG] error: {e}")
            raise SystemExit(1)

        await asyncio.sleep(get_interval())