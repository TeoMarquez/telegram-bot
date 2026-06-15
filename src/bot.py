# main.py

from telegram.ext import ApplicationBuilder
from config import BOT_TOKEN
from utils import wait_for_internet
from lifecycle import notify_startup
from commands import get_handlers 

def main():
    wait_for_internet()

    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .post_init(notify_startup)
        .build()
    )

    for handler in get_handlers():
        app.add_handler(handler)

    print("Bot is running...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()