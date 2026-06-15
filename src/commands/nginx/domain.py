from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ConversationHandler, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from services import nginx_service

COMMAND = "nginx_domain"
DESCRIPTION = "Ver o configurar el dominio base del servidor"

WAITING_NEW_DOMAIN = 0

async def handler(update, context):
    query = update.callback_query
    domain = nginx_service.get_base_domain()
    
    texto = (
        "🌐 *Configuración de Dominio*\n\n"
        f"El dominio base actual es: `{domain}`\n\n"
        "💡 _Este dominio se usa para autocompletar los subdominios de Nginx de forma automática._"
    )
    
    current_cat = context.user_data.get("current_category", "nginx")
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ Cambiar Dominio", callback_data="nginx_domain_edit")],
        [InlineKeyboardButton("⬅️ Volver al Menú", callback_data=f"menu_{current_cat}")]
    ])
    
    if query:
        await query.answer()
        await query.edit_message_text(texto, reply_markup=keyboard, parse_mode="Markdown")
    else:
        await update.effective_message.reply_text(texto, reply_markup=keyboard, parse_mode="Markdown")
        
    return ConversationHandler.END 

async def _start_edit(update, context):
    query = update.callback_query
    await query.answer()
    
    texto = (
        "✏️ *Modificar Dominio Base*\n\n"
        "Escribí el nuevo dominio raíz para este servidor (ej: `minipc.duckdns.arg` o `api.local`):\n\n"
        "Mandá /cancelar para salir."
    )
    
    await query.edit_message_text(texto, parse_mode="Markdown")
    return WAITING_NEW_DOMAIN

async def _receive_domain(update, context):
    new_domain = update.message.text.strip().lower()
    
    exito = nginx_service.set_base_domain(new_domain)
    
    current_cat = context.user_data.get("current_category", "nginx")
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Volver al Menú", callback_data=f"menu_{current_cat}")]
    ])
    
    if exito:
        await update.message.reply_text(
            f"✅ *Dominio actualizado!*\n\nEl nuevo dominio base es: `{new_domain}`",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            "❌ Hubo un error crítico al intentar guardar el dominio en el archivo de configuración.",
            reply_markup=keyboard
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
        CallbackQueryHandler(handler, pattern=f"^{COMMAND}$"),
        CallbackQueryHandler(_start_edit, pattern="^nginx_domain_edit$") 
    ],
    states={
        WAITING_NEW_DOMAIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, _receive_domain)],
    },
    fallbacks=[CommandHandler("cancelar", _cancel)],
    per_chat=True,
    per_user=True,
)