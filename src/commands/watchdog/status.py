from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from services import watchdog_service

COMMAND = "watchdog_status"
DESCRIPTION = "Muestra el estado del watchdog"

async def handler(update, context):
    state = watchdog_service.get_status()

    current_cat = context.user_data.get("current_category", "watchdog")
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Volver al Menú", callback_data=f"menu_{current_cat}")]
    ])

    texto = (
        "📊 *Estado del Watchdog*\n\n"
        f"• *Estado:* {'🟢 ON' if state['enabled'] else '🔴 OFF'}\n"
        f"• *Intervalo:* {state['interval']} segundos"
    )

    await update.effective_message.reply_text(
        texto,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )