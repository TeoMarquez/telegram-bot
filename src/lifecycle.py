from datetime import datetime
import asyncio

from config import AUTHORIZED_USER
from utils import get_public_ip
from services import watchdog_service
from commands import get_bot_commands

async def notify_startup(app):

    await app.bot.set_my_commands(
            get_bot_commands()
        )

    await app.bot.send_message(
        chat_id=AUTHORIZED_USER,
        text=(
            "🟢 Bot iniciado\n\n"
            f"Hora: {datetime.now():%Y-%m-%d %H:%M:%S}\n"
            f"IP pública: {get_public_ip()}"
        )
    )

    watchdog_service.ensure_state_file()
    
    asyncio.create_task(
        watchdog_service.watchdog_loop(app)
    )