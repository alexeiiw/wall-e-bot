import os
import re
import ollama

from bot.config import OLLAMA_MODEL, MEMORY_PATH, NOTES_PATH
from bot.history import agregar_mensaje, obtener_historial


_PATRON_NEGATIVA_LLM = re.compile(
    r"\b(?:no\s+puedo\s+(?:ayudarte|proporcionar|cumplir|asistir)|"
    r"no\s+debo\s+ayudar|no\s+estoy\s+(?:autorizado|capacitado)|"
    r"lo\s+siento[^\n]{0,80}no\s+puedo|"
    r"i\s+(?:can't|cannot)\s+(?:assist|help|provide|comply))\b",
    re.IGNORECASE,
)

_PATRON_BIENESTAR_PERMITIDO = re.compile(
    r"\b(?:rendimiento\s+sexual|salud\s+sexual|sexo|sexualidad|erecci[oó]n|libido|"
    r"sue[ñn]o|dormir|estr[eé]s|ansiedad|ejercicio|alimentaci[oó]n|nutrici[oó]n|"
    r"bienestar|salud|h[aá]bitos?)\b",
    re.IGNORECASE,
)

_RESPUESTA_NEGATIVA_LLM = (
    "[WALL-E / IA local no respondió]\n"
    "El modelo rechazó responder directamente esa solicitud. "
    "Puedo ayudarte a reformularla hacia una explicación segura, educativa o conceptual."
)

_INSTRUCCIONES_BASE = (
    "Usa la siguiente información como tu base de conocimientos y reglas. "
    "Responde de forma directa, útil y natural. "
    "No rechaces temas de bienestar, salud general o sexualidad adulta cuando la consulta sea educativa, "
    "consensual, no explícita y no pida diagnóstico médico; da consejos generales y recomienda consultar "
    "a un profesional si hay dolor, síntomas persistentes, medicación o preocupación clínica. "
    "Si el usuario habla de objetos, plantas, herramientas o mascotas, entiende que pide recomendaciones "
    "sobre eso; no interpretes que tú debes ejecutar físicamente la acción. "
    "Usa el historial solo si el mensaje actual continúa claramente el mismo tema; si cambia de tema, "
    "responde la nueva consulta sin arrastrar contexto anterior. "
    "Responde en máximo 5 puntos salvo que el usuario pida más detalle."
)


def _respuesta_error_ia(error: Exception) -> str:
    return f"[WALL-E / error IA local]\nNo pude conectar con Ollama o generar la respuesta: {error}"


def _es_negativa_llm(respuesta: str) -> bool:
    return _PATRON_NEGATIVA_LLM.search(respuesta) is not None


def _normalizar_respuesta_llm(respuesta: str) -> str:
    if _es_negativa_llm(respuesta):
        return _RESPUESTA_NEGATIVA_LLM
    return respuesta


def _es_consulta_bienestar_permitida(mensaje: str) -> bool:
    return _PATRON_BIENESTAR_PERMITIDO.search(mensaje) is not None


def _construir_messages(contexto_completo: str, historial: list, mensaje_usuario: str) -> list:
    return [
        {'role': 'system', 'content': f"{_INSTRUCCIONES_BASE}\n\n{contexto_completo}"},
        *historial,
        {'role': 'user', 'content': mensaje_usuario}
    ]


def _reintentar_consulta_bienestar(contexto_completo: str, mensaje_usuario: str) -> str:
    messages = [
        {
            'role': 'system',
            'content': (
                f"{_INSTRUCCIONES_BASE}\n\n{contexto_completo}\n\n"
                "La consulta del usuario es de bienestar permitido. Responde con consejos generales, "
                "seguros y no explícitos. No hagas diagnóstico médico."
            )
        },
        {'role': 'user', 'content': mensaje_usuario}
    ]
    response = ollama.chat(model=OLLAMA_MODEL, messages=messages)
    return response['message']['content']


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
    messages = _construir_messages(contexto_completo, historial, mensaje_usuario)
    try:
        response = ollama.chat(model=OLLAMA_MODEL, messages=messages)
        respuesta_cruda = response['message']['content']
        if _es_negativa_llm(respuesta_cruda) and _es_consulta_bienestar_permitida(mensaje_usuario):
            respuesta_cruda = _reintentar_consulta_bienestar(contexto_completo, mensaje_usuario)
        respuesta_ia = _normalizar_respuesta_llm(respuesta_cruda)
    except Exception as e:
        return _respuesta_error_ia(e)

    agregar_mensaje(chat_id, 'user', mensaje_usuario)
    if respuesta_ia != _RESPUESTA_NEGATIVA_LLM:
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
        return _normalizar_respuesta_llm(response['message']['content'])
    except Exception as e:
        return _respuesta_error_ia(e)

