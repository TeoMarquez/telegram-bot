from telegram.ext import ConversationHandler, MessageHandler, filters, CommandHandler, CallbackQueryHandler
from services import watchdog_service

COMMAND = "watchdog_setinterval"
DESCRIPTION = "Configura el intervalo del watchdog"

MIN_INTERVAL = 3
MAX_INTERVAL = 60 * 60 * 24 * 7

WAITING_INTERVAL = 0

async def handler(update, context):
    print(">>> handler called")
    
    # Detectamos si viene de un botón (callback_query) o de texto directo
    query = update.callback_query
    
    texto_mensaje = (
        "⏱ ¿Cada cuántos segundos querés que corra el watchdog?\n"
        f"Mínimo: {MIN_INTERVAL}s — Máximo: {MAX_INTERVAL}s\n\n"
        "Mandá /cancelar para salir."
    )

    if query:
        # Si vino de un botón, respondemos al click y editamos el mensaje existente
        await query.answer()
        await query.edit_message_text(texto_mensaje)
    else:
        # Si escribieron el comando, mandamos un mensaje nuevo
        await update.effective_message.reply_text(texto_mensaje)
        
    return WAITING_INTERVAL

async def _receive_interval(update, context):
    print("STATE HIT:", context.chat_data)
    print("TEXT:", update.message.text)

    text = update.message.text.strip()

    try:
        interval = int(text)
    except ValueError:
        await update.message.reply_text(
            "❌ Eso no es un número válido. Mandá un entero o /cancelar."
        )
        return WAITING_INTERVAL

    if interval < MIN_INTERVAL:
        await update.message.reply_text(
            f"❌ El mínimo es {MIN_INTERVAL} segundos. Intentá de nuevo o /cancelar."
        )
        return WAITING_INTERVAL

    if interval > MAX_INTERVAL:
        await update.message.reply_text(
            f"❌ El máximo es {MAX_INTERVAL} segundos (1 semana). Intentá de nuevo o /cancelar."
        )
        return WAITING_INTERVAL

    watchdog_service.set_interval(interval)

    await update.message.reply_text(
        f"✅ Intervalo establecido en {interval} segundos."
    )
    return ConversationHandler.END


async def _cancel(update, context):
    await update.effective_message.reply_text("❌ Operación cancelada.")
    return ConversationHandler.END


CONVERSATION = ConversationHandler(
    entry_points=[
        CommandHandler(COMMAND, handler),
        CallbackQueryHandler(handler, pattern=f"^{COMMAND}$")
    ],
    states={
        WAITING_INTERVAL: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, _receive_interval)
        ]
    },
    fallbacks=[CommandHandler("cancelar", _cancel)],
    per_chat=True,
    per_user=True,
)