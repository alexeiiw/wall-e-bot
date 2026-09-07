import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:1b")
MEMORY_PATH = os.getenv("MEMORY_PATH", "memory/memory.md")
NOTES_PATH = os.getenv("NOTES_PATH", "notas/notas_e_ideas.md")
BACKEND_SECRET_KEY = os.getenv("BACKEND_SECRET_KEY")

if not TELEGRAM_TOKEN:
    raise RuntimeError("TELEGRAM_TOKEN no está definido. Configuralo en el archivo .env")

if not BACKEND_SECRET_KEY:
    raise RuntimeError("BACKEND_SECRET_KEY no está definido. Configuralo en el archivo .env")
