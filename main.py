import threading
import uvicorn
from telegram.ext import Application, MessageHandler, filters

from bot.config import TELEGRAM_TOKEN
from bot.handlers import responder_con_ia
from api.server import app as fastapi_app


def run_fastapi_server():
    """Inicia el servidor FastAPI en un thread separado."""
    print("Iniciando servidor FastAPI en http://0.0.0.0:8000")
    config = uvicorn.Config(fastapi_app, host="0.0.0.0", port=8000, log_level="info")
    server = uvicorn.Server(config)
    server.run()


def main():
    print("=" * 60)
    print("WALL-E Bot v1.1 - Iniciando servicios")
    print("=" * 60)
    
    # Thread para FastAPI Server (en background)
    fastapi_thread = threading.Thread(target=run_fastapi_server, daemon=False)
    fastapi_thread.start()
    
    # Telegram Bot en hilo principal (requiere estar en main thread)
    print("Iniciando Bot de Telegram con Memoria Markdown activa...")
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder_con_ia))
    app.run_polling()


if __name__ == '__main__':
    main()

