from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ConversationHandler, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from services import nginx_service

COMMAND = "nginx_add"
DESCRIPTION = "Añadir nuevo sitio a Nginx"

WAITING_NAME, WAITING_DOMAIN, WAITING_PORT = range(3)

async def handler(update, context):
    query = update.callback_query
    texto = (
        "📝 *Añadir sitio a Nginx*\n\n"
        "Escribí el **nombre interno** para el archivo (ej: `miapp`):\n"
        "❌ _Podés enviar /cancelar en cualquier momento para salir._"
    )
    
    if query:
        await query.answer()
        await query.edit_message_text(texto, parse_mode="Markdown")
    else:
        await update.effective_message.reply_text(texto, parse_mode="Markdown")
        
    return WAITING_NAME

async def _receive_name(update, context):
    name = update.message.text.strip().lower().replace(" ", "_")
    
    sitios_activos = nginx_service.list_sites()
    if any(s['file'] == name for s in sitios_activos):
        await update.message.reply_text(
            f"⚠️ *Nombre en uso:*\n"
            f"Ya existe un archivo de configuración llamado `{name}.conf`.\n\n"
            "Por favor, elegí un **nombre diferente** (o tirá /cancelar):",
            parse_mode="Markdown"
        )
        return WAITING_NAME

    context.user_data["new_site_name"] = name
    base_domain = nginx_service.get_base_domain()
    
    texto_dominio = (
        f"🌐 Nombre guardado: `{name}`\n\n"
        "Ahora mandá el **dominio o subdominio**.\n"
        f"💡 _Si escribís solo una palabra, se autocompletará usando tu dominio base:_ `tu_palabra.{base_domain}`\n\n"
        "Mandá el dominio o subdominio:"
    )
    
    await update.message.reply_text(texto_dominio, parse_mode="Markdown")
    return WAITING_DOMAIN

async def _receive_domain(update, context):
    domain = update.message.text.strip().lower()
    
    if "." not in domain:
        base_domain = nginx_service.get_base_domain()
        domain = f"{domain}.{base_domain}"
        
    context.user_data["new_site_domain"] = domain
    
    await update.message.reply_text(
        f"📍 Dominio final configurado: `{domain}`\n\nPor último, mandá el **puerto local** interno (ej: `3000` o `8080`):",
        parse_mode="Markdown"
    )
    return WAITING_PORT

async def _receive_port(update, context):
    port_str = update.message.text.strip()
    
    if not port_str.isdigit():
        await update.message.reply_text("❌ El puerto debe ser un número entero. Intentá de nuevo:")
        return WAITING_PORT
        
    sitio_ocupante = nginx_service.is_port_in_use(port_str)
    if sitio_ocupante:
        await update.message.reply_text(
            f"⚠️ *Puerto en conflicto:*\n"
            f"El puerto `{port_str}` ya está siendo usado por el sitio: `{sitio_ocupante}`.\n\n"
            "Por favor, mandá un **puerto diferente** (o tirá /cancelar):",
            parse_mode="Markdown"
        )
        return WAITING_PORT

    name = context.user_data.get("new_site_name")
    domain = context.user_data.get("new_site_domain")
    
    exito = nginx_service.add_site(name, domain, port_str)
    
    current_cat = context.user_data.get("current_category", "nginx")
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Volver al Menú", callback_data=f"menu_{current_cat}")]
    ])
    
    if exito:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔒 Generar SSL (HTTPS)", callback_data=f"ssl_gen_{domain}")],
            [InlineKeyboardButton("⬅️ Volver al Menú", callback_data=f"menu_{current_cat}")]
        ])
        
        await update.message.reply_text(
            f"✅ *Sitio creado con éxito!*\n\n"
            f"• **Archivo:** `{name}.conf`\n"
            f"• **Dominio:** `{domain}`\n"
            f"• **Puerto:** `http://127.0.0.1:{port_str}`\n\n"
            f"¿Querés certificar el dominio con HTTPS ahora mismo?",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
    else:
        await update.message.reply_text(
            "❌ Hubo un error al intentar escribir el archivo de configuración.",
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
        CallbackQueryHandler(handler, pattern=f"^{COMMAND}$")
    ],
    states={
        WAITING_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, _receive_name)],
        WAITING_DOMAIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, _receive_domain)],
        WAITING_PORT: [MessageHandler(filters.TEXT & ~filters.COMMAND, _receive_port)],
    },
    fallbacks=[CommandHandler("cancelar", _cancel)],
    per_chat=True,
    per_user=True,
)