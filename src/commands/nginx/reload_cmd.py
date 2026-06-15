from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from services import nginx_service

COMMAND = "nginx_reload"
DESCRIPTION = "Validar y recargar configuración de Nginx"

async def handler(update, context):
    query = update.callback_query
    
    texto_espera = "🔄 *Verificando archivos y recargando Nginx...*"
    if query:
        await query.answer()
        msg = await query.edit_message_text(texto_espera, parse_mode="Markdown")
    else:
        msg = await update.effective_message.reply_text(texto_espera, parse_mode="Markdown")
        
    exito, resultado = nginx_service.reload_nginx()
    
    current_cat = context.user_data.get("current_category", "nginx")
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Volver al Menú", callback_data=f"menu_{current_cat}")]
    ])
    
    if exito:
        texto_final = f"✅ *¡Nginx Recargado!*\n\n{resultado}"
    else:
        texto_final = f"❌ *Error al recargar Nginx:*\n\n{resultado}\n\n_Ningún cambio fue aplicado para proteger el servidor._"
        
    await msg.edit_text(
        texto_final,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )