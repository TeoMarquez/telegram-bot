# lifecycle.py
from datetime import datetime
import asyncio

from config import AUTHORIZED_USER
from utils import get_public_ip
from services import watchdog_service, heartbeat_service, log_service
from commands import get_bot_commands

async def notify_startup(app):

    log_service.log_event("BOT_START")

    await app.bot.set_my_commands(get_bot_commands())

    if AUTHORIZED_USER != -1:
        try:
            await app.bot.send_message(
                chat_id=AUTHORIZED_USER,
                text=(
                    "🟢 Bot iniciado\n\n"
                    f"Hora: {datetime.now():%Y-%m-%d %H:%M:%S}\n"
                    f"IP pública: {get_public_ip()}"
                )
            )
        except Exception as e:
            log_service.log_event(f"STARTUP_ERROR | {e}")

    watchdog_service.ensure_state_file()

    asyncio.create_task(heartbeat_service.heartbeat_loop())
    asyncio.create_task(watchdog_service.watchdog_loop(app))