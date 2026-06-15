# commands/__init__.py

from telegram.ext import CommandHandler, CallbackQueryHandler
from telegram import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup

from . import network, watchdog

CATEGORIES = [network, watchdog]

COMMAND_MAP = {
    cmd.COMMAND: cmd.handler
    for cat in CATEGORIES
    for cmd in cat.COMMANDS
    if cmd not in getattr(cat, 'CONVERSATION_COMMANDS', [])
}

def get_bot_commands():
    return [
        BotCommand(cat.COMMAND, cat.DESCRIPTION)
        for cat in CATEGORIES
    ]
# En commands/__init__.py

def get_handlers():
    handlers = []
    
    for cat in CATEGORIES:
        conversations = getattr(cat, 'CONVERSATIONS', [])
        for conv in conversations:
            handlers.append(conv)

    for cat in CATEGORIES:
        handlers.append(
            CommandHandler(cat.COMMAND, _make_category_handler(cat))
        )

    for cat in CATEGORIES:
        conv_cmds = getattr(cat, 'CONVERSATION_COMMANDS', [])
        for cmd in cat.COMMANDS:
            if cmd not in conv_cmds:
                handlers.append(
                    CommandHandler(cmd.COMMAND, cmd.handler)
                )

    handlers.append(
        CallbackQueryHandler(_callback_dispatcher)
    )

    return handlers

def _render_menu_keyboard(cat):
    """Función auxiliar para armar la botonera de una categoría."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            f"/{cmd.COMMAND} — {cmd.DESCRIPTION}",
            callback_data=cmd.COMMAND
        )]
        for cmd in cat.COMMANDS
    ])

def _make_category_handler(cat):
    """Manejador cuando alguien escribe el comando principal (ej: /watchdog)."""
    async def handler(update, context):
        await update.effective_message.reply_text(
            f"{cat.CATEGORY}",
            reply_markup=_render_menu_keyboard(cat)
        )
    return handler


class CustomUpdate:
    """Wrapper para interceptar el envío de mensajes y transformarlo en edición."""
    def __init__(self, original_update, query):
        self._update = original_update
        self._query = query

    def __getattr__(self, name):
        if name == "effective_message":
            return CustomMessage(self._update.effective_message, self._query)
        return getattr(self._update, name)


class CustomMessage:
    def __init__(self, original_message, query):
        self._message = original_message
        self._query = query

    async def reply_text(self, text, *args, **kwargs):
        # Forzamos a que edite el mensaje existente en lugar de mandar uno nuevo
        return await self._query.edit_message_text(text, *args, **kwargs)

    def __getattr__(self, name):
        return getattr(self._message, name)


async def _callback_dispatcher(update, context):
    query = update.callback_query
    data = query.data

    if data.startswith("menu_"):
        cat_name = data.replace("menu_", "")
        cat = next((c for c in CATEGORIES if getattr(c, 'COMMAND', '') == cat_name), None)
        if cat:
            await query.answer()
            await query.edit_message_text(
                f"{cat.CATEGORY}",
                reply_markup=_render_menu_keyboard(cat)
            )
            return

    is_conv = any(
        cmd.COMMAND == data 
        for cat in CATEGORIES 
        for cmd in getattr(cat, 'CONVERSATION_COMMANDS', [])
    )
    if is_conv:
        return 

    handler_fn = COMMAND_MAP.get(data)

    if handler_fn:
        await query.answer()
        
        for cat in CATEGORIES:
            if any(cmd.COMMAND == data for cmd in cat.COMMANDS):
                context.user_data["current_category"] = cat.COMMAND
                break
        
        wrapped_update = CustomUpdate(update, query)
        
        await handler_fn(wrapped_update, context)
    else:
        await query.edit_message_text("❌ Comando no encontrado.")