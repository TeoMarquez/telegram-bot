from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler
from services import nginx_service

async def _callback_handler(update, context):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    domain = data.replace("ssl_gen_", "")
    
    if not domain or domain == data:
        await query.edit_message_text("❌ No se pudo determinar un dominio válido para certificar.")
        return

    await query.edit_message_text(
        f"⏳ *Solicitando certificado SSL para `{domain}`...*\n"
        f"Esto puede demorar unos segundos mientras Let's Encrypt valida el dominio.",
        parse_mode="Markdown"
    )
    
    exito_ssl, resultado_ssl = nginx_service.generate_ssl(domain)
    
    current_cat = context.user_data.get("current_category", "nginx")
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Volver al Menú", callback_data=f"menu_{current_cat}")]
    ])
    
    if exito_ssl:
        exito_reload, msg_reload = nginx_service.reload_nginx()
        if exito_reload:
            texto_final = f"🔒 *¡HTTPS Activo!*\n\n{resultado_ssl}\n\nNginx se recargó correctamente."
        else:
            texto_final = f"⚠️ *SSL generado pero Nginx falló al recargar:*\n\n{msg_reload}"
    else:
        texto_final = f"❌ *Error de Certificación:*\n\n{resultado_ssl}\n\n_Asegurate de que el dominio apunte correctamente a la IP pública de la Mini-PC antes de generar el SSL._"
        
    await query.edit_message_text(
        texto_final,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

CALLBACK_HANDLER = CallbackQueryHandler(_callback_handler, pattern="^ssl_gen_")