# main.py
from commands.nginx import ssl_cmd
from telegram.ext import ApplicationBuilder
from config import BOT_TOKEN
from utils import wait_for_internet
from lifecycle import notify_startup
from commands import get_handlers, nginx 

def main():
    wait_for_internet()

    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .post_init(notify_startup)
        .build()
    )

    app.add_handler(ssl_cmd.CALLBACK_HANDLER)
    for handler in get_handlers():
        app.add_handler(handler)

    print("Bot is running...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()