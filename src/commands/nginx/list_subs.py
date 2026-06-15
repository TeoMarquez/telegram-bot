from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from services import nginx_service

COMMAND = "nginx_list"
DESCRIPTION = "Listar sitios activos"

async def handler(update, context):
    sites = nginx_service.list_sites()
    
    if not sites:
        texto = "📂 *Nginx:* No se encontraron sitios configurados."
    else:
        texto = "⚙️ *Servicios expuestos en Nginx:*\n\n"
        for site in sites:
            texto += f"🌐 `{site['domain']}`\n   └─ _Archivo:_ `{site['file']}.conf`\n\n"
            
    current_cat = context.user_data.get("current_category", "nginx")
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Volver al Menú", callback_data=f"menu_{current_cat}")]
    ])
    
    await update.effective_message.reply_text(
        texto,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )