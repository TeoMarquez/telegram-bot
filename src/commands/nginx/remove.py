from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ConversationHandler, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from services import nginx_service

COMMAND = "nginx_remove"
DESCRIPTION = "Eliminar un sitio de Nginx"

WAITING_CONFIRM = 0

async def handler(update, context):
    query = update.callback_query
    sites = nginx_service.list_sites()
    
    if not sites:
        texto = "📂 *Nginx:* No hay ningún sitio configurado para eliminar."
        current_cat = context.user_data.get("current_category", "nginx")
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Volver", callback_data=f"menu_{current_cat}")]])
        
        if query:
            await query.answer()
            await query.edit_message_text(texto, reply_markup=keyboard, parse_mode="Markdown")
        else:
            await update.effective_message.reply_text(texto, reply_markup=keyboard, parse_mode="Markdown")
        return ConversationHandler.END

    texto = "🗑️ *Eliminar sitio de Nginx*\n\nEscribí el nombre exacto del archivo:\n\n"
    for site in sites:
        texto += f"• `{site['file']}` (Dominio: {site['domain']})\n"
    texto += "\n❌ O mandá /cancelar para salir."

    if query:
        await query.answer()
        await query.edit_message_text(texto, parse_mode="Markdown")
    else:
        await update.effective_message.reply_text(texto, parse_mode="Markdown")
        
    return WAITING_CONFIRM

async def _receive_filename(update, context):
    site_name = update.message.text.strip()
    
    filename = site_name if site_name.endswith(".conf") else f"{site_name}.conf"
    
    exito = nginx_service.remove_site(filename)
    
    current_cat = context.user_data.get("current_category", "nginx")
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Volver al Menú", callback_data=f"menu_{current_cat}")]
    ])
    
    if exito:
        await update.message.reply_text(
            f"🗑️ Archivo `{filename}` eliminado correctamente.\n\n_Recordá recargar Nginx en producción._",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            f"❌ No se encontró el archivo `{filename}`. Verificá el nombre exacto e intentá de nuevo con /nginx_remove.",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
    return ConversationHandler.END

async def _cancel(update, context):
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
        WAITING_CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, _receive_filename)],
    },
    fallbacks=[CommandHandler("cancelar", _cancel)],
    per_chat=True,
    per_user=True,
)