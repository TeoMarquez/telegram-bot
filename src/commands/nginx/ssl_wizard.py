from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, CallbackQueryHandler
from services import nginx_service

COMMAND = "nginx_ssl"
DESCRIPTION = "Generar certificado SSL para un sitio de Nginx"
SELECTING_SITE = 0

async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    sites = nginx_service.get_uncertified_sites()
    current_cat = context.user_data.get("current_category", "nginx")
    
    back_keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Volver", callback_data=f"menu_{current_cat}")]])
    
    if not sites:
        texto = "✨ *Nginx SSL:* Todos tus sitios activos ya tienen el certificado SSL instalado."
        if query:
            await query.answer()
            await query.edit_message_text(texto, reply_markup=back_keyboard, parse_mode="Markdown")
        else:
            await update.effective_message.reply_text(texto, reply_markup=back_keyboard, parse_mode="Markdown")
        return ConversationHandler.END

    keyboard = []
    for site in sites:
        keyboard.append([InlineKeyboardButton(f"🔒 {site['domain']} ({site['file']})", callback_data=site['domain'])])
    
    keyboard.append([InlineKeyboardButton("❌ Cancelar", callback_data="cancel_ssl")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    texto = "🛡️ *Asistente de Certificación SSL*\n\nSeleccioná el dominio que querés certificar con Let's Encrypt:"

    if query:
        await query.answer()
        await query.edit_message_text(texto, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await update.effective_message.reply_text(texto, reply_markup=reply_markup, parse_mode="Markdown")
        
    return SELECTING_SITE

async def process_ssl_generation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    domain = query.data
    current_cat = context.user_data.get("current_category", "nginx")
    back_keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Volver al Menú", callback_data=f"menu_{current_cat}")]])
    
    if domain == "cancel_ssl":
        await query.edit_message_text("❌ Operación cancelada.", reply_markup=back_keyboard)
        return ConversationHandler.END
    
    await query.edit_message_text(f"⏳ Solicitando certificado SSL para `{domain}`...\nEsto puede tardar unos segundos.", parse_mode="Markdown")
    
    success_ssl, msg_ssl = nginx_service.generate_ssl(domain)
    
    if not success_ssl:
        await query.message.reply_text(
            f"❌ *Error de Certificación:*\n\n{msg_ssl}", 
            reply_markup=back_keyboard, 
            parse_mode="Markdown"
        )
        return ConversationHandler.END
        
    success_reload, msg_reload = nginx_service.reload_nginx()
    
    if success_reload:
        await query.message.reply_text(
            f"✅ *¡Éxito total!*\n\n{msg_ssl}\n\nNginx se recargó correctamente.", 
            reply_markup=back_keyboard, 
            parse_mode="Markdown"
        )
    else:
        await query.message.reply_text(
            f"⚠️ *SSL generado pero Nginx falló al recargar:*\n\n{msg_reload}", 
            reply_markup=back_keyboard, 
            parse_mode="Markdown"
        )
        
    return ConversationHandler.END

async def _cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    current_cat = context.user_data.get("current_category", "nginx")
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Volver al Menú", callback_data=f"menu_{current_cat}")]])
    await update.effective_message.reply_text("❌ Operación cancelada.", reply_markup=keyboard)
    return ConversationHandler.END

CONVERSATION = ConversationHandler(
    entry_points=[
        CommandHandler(COMMAND, handler),
        CallbackQueryHandler(handler, pattern=f"^{COMMAND}$")
    ],
    states={
        SELECTING_SITE: [CallbackQueryHandler(process_ssl_generation)]
    },
    fallbacks=[CommandHandler("cancelar", _cancel)],
    per_message=False
)