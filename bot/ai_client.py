import os
import ollama

from bot.config import OLLAMA_MODEL, MEMORY_PATH, NOTES_PATH
from bot.history import agregar_mensaje, obtener_historial


def cargar_memoria():
    if os.path.exists(MEMORY_PATH):
        with open(MEMORY_PATH, "r", encoding="utf-8") as f:
            return f.read()
    return "Eres un asistente de IA básico."


def cargar_notas():
    if os.path.exists(NOTES_PATH):
        with open(NOTES_PATH, "r", encoding="utf-8") as f:
            return f.read()
    return ""


def generar_respuesta(chat_id: int, mensaje_usuario: str) -> str:
    contexto_memoria = cargar_memoria()
    contexto_notas = cargar_notas()
    
    # Combinar memoria + notas en un único contexto
    contexto_completo = contexto_memoria
    if contexto_notas.strip():
        contexto_completo += "\n\n## Notas e Ideas de Alex\n" + contexto_notas
    
    historial = obtener_historial(chat_id)
    messages = [
        {'role': 'system', 'content': f"Usa la siguiente información como tu base de conocimientos y reglas:\n\n{contexto_completo}"},
        *historial,
        {'role': 'user', 'content': mensaje_usuario}
    ]
    try:
        response = ollama.chat(model=OLLAMA_MODEL, messages=messages)
        respuesta_ia = response['message']['content']
    except Exception as e:
        return f"Error al conectar con la IA local: {e}"

    agregar_mensaje(chat_id, 'user', mensaje_usuario)
    agregar_mensaje(chat_id, 'assistant', respuesta_ia)
    return respuesta_ia


def resumir_texto(instruccion: str, texto: str) -> str:
    """Envía un texto al LLM con una instrucción puntual y devuelve el resumen."""
    messages = [
        {'role': 'system', 'content': 'Eres un asistente que resume información de forma breve y clara.'},
        {'role': 'user', 'content': f"{instruccion}:\n\n{texto}"}
    ]
    try:
        response = ollama.chat(model=OLLAMA_MODEL, messages=messages)
        return response['message']['content']
    except Exception as e:
        return f"Error al conectar con la IA local: {e}"

