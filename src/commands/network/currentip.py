# commands/network/currentip.py
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from utils import get_public_ip

COMMAND = "currentip"
DESCRIPTION = "Muestra la IP pública"

async def handler(update, context):
    ip = get_public_ip()
    
    current_cat = context.user_data.get("current_category", "network")
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Volver al Menú", callback_data=f"menu_{current_cat}")]
    ])
    
    await update.effective_message.reply_text(
        f"🌐 *IP pública:* `{ip}`",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )