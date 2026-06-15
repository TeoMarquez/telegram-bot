from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from services import watchdog_service

COMMAND = "watchdog_off"
DESCRIPTION = "Desactiva el watchdog"

async def handler(update, context):
    watchdog_service.set_enabled(False)

    current_cat = context.user_data.get("current_category", "watchdog")
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Volver al Menú", callback_data=f"menu_{current_cat}")]
    ])

    await update.effective_message.reply_text(
        "⛔ *Watchdog desactivado*",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )