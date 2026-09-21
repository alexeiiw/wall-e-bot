from collections import defaultdict, deque

MAX_MENSAJES = 10

# Historial en memoria (se pierde al reiniciar el bot), por chat_id
_historial = defaultdict(lambda: deque(maxlen=MAX_MENSAJES))


def agregar_mensaje(chat_id: int, role: str, content: str):
    _historial[chat_id].append({'role': role, 'content': content})


def obtener_historial(chat_id: int):
    return list(_historial[chat_id])


def limpiar_historial(chat_id: int):
    _historial[chat_id].clear()


def obtener_ultima_respuesta(chat_id: int):
    for mensaje in reversed(_historial[chat_id]):
        if mensaje.get('role') == 'assistant':
            return mensaje.get('content')
    return None
