from collections import defaultdict, deque

MAX_MENSAJES = 5

# Historial en memoria (se pierde al reiniciar el bot), por chat_id
_historial = defaultdict(lambda: deque(maxlen=MAX_MENSAJES))


def agregar_mensaje(chat_id: int, role: str, content: str):
    _historial[chat_id].append({'role': role, 'content': content})


def obtener_historial(chat_id: int):
    return list(_historial[chat_id])
