from bot.config import MEMORY_PATH


def guardar_memoria(dato: str) -> str:
    """Agrega una línea nueva al archivo de memoria persistente del bot."""
    with open(MEMORY_PATH, "a", encoding="utf-8") as f:
        f.write(f"\n- {dato}")
    return f"Guardado en memoria: {dato}"
