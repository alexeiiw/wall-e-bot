from telegram import Update
from telegram.ext import ContextTypes

from bot.intent_router import resolver_mensaje


async def responder_con_ia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mensaje_usuario = update.message.text
    chat_id = update.effective_chat.id

    await context.bot.send_chat_action(chat_id=chat_id, action="typing")
    respuesta = resolver_mensaje(chat_id, mensaje_usuario)
    await update.message.reply_text(respuesta)

