"""
Router de intención: evalúa cada mensaje con lógica determinista (regex) antes
de recurrir al LLM. Es el único punto de entrada usado por Telegram y por el
backend API, para garantizar el mismo comportamiento en ambos canales.

Ver README.md -> "Cómo agregar un nuevo comando" antes de tocar este archivo.
"""

import re
from dataclasses import dataclass
from typing import Optional

from bot.memory_trigger import (
    detectar_dato_a_recordar,
    detectar_nota_a_anotar,
    detectar_solicitud_listar_notas,
)
from bot.tools import guardar_memoria
from bot.notes import guardar_nota, cargar_notas, buscar_notas
from bot.ai_client import generar_respuesta, resumir_texto
from bot.config import OLLAMA_MODEL

# Cantidad máxima de resultados de SEARCH_NOTES que se responden directo,
# sin pasar por el LLM. Por encima de este número, se resumen con LLM.
UMBRAL_RESULTADOS_BUSQUEDA = 3

_PATRON_RESUMIR = re.compile(
    r"(?:resum[ií]me|hazme un resumen de|resumen de)\s+mis\s+(?:notas|ideas)",
    re.IGNORECASE
)

_PATRON_BUSCAR = re.compile(
    r"(?:busca(?:r)?|revisa)\s+(?:en\s+)?mis\s+notas\s+(?:sobre|de|acerca de)?\s*(.+)"
    r"|qu[eé]\s+tengo\s+sobre\s+(.+)",
    re.IGNORECASE
)

_PATRON_AYUDA = re.compile(
    r"\bwall[y-]?e?\b.*(?:qu[eé]\s+(?:puedes|pod[eé]s|sabes)\s+hacer|ay[uú]dame|\bayuda\b)",
    re.IGNORECASE
)

_PATRON_FUERA_DE_ALCANCE = re.compile(
    r"\b(?:clima|pron[oó]stico|temperatura|noticias?|[uú]ltima\s+hora|"
    r"d[oó]lar|cotizaci[oó]n|precio\s+actual|en\s+tiempo\s+real)\b",
    re.IGNORECASE
)

_PATRON_HERRAMIENTA_EXTERNA = re.compile(
    r"\b(?:busca\s+en\s+internet|buscar\s+en\s+internet|googlea|consulta\s+(?:web|internet)|"
    r"(?:consulta|revisa|abre|sincroniza)\s+(?:mi\s+)?(?:calendario|agenda|correo|email)|"
    r"(?:llama|consulta|usa)\s+(?:una\s+)?api)\b",
    re.IGNORECASE
)

_SALUDOS_SIMPLES = {
    "hola",
    "buenas",
    "buen dia",
    "buen día",
    "buenos dias",
    "buenas tardes",
    "buenas noches",
    "hey",
}

_CONFIRMACIONES_SIMPLES = {
    "ok",
    "okay",
    "si",
    "sí",
    "dale",
    "va",
    "listo",
    "perfecto",
    "gracias",
    "muchas gracias",
}

_RESPUESTA_FUERA_DE_ALCANCE = (
    "No tengo acceso a datos externos o en tiempo real desde aquí. "
    "Puedo ayudarte con tus notas, memoria y tareas personales guardadas."
)

_RESPUESTA_HERRAMIENTA_EXTERNA = (
    "Todavía no tengo integrada esa herramienta externa. "
    "Puedo trabajar con tu memoria y tus notas locales."
)

# Lista de comandos disponibles, para el breef de ayuda. Se va sumando una
# fila cada vez que se agrega un comando nuevo (ver README -> "Comandos actuales").
COMANDOS_DISPONIBLES = [
    ("Recordar algo", "Decime 'recuerda que...' y lo guardo en memoria permanente."),
    ("Anotar una nota", "Decime 'anota que...' y lo guardo en tus notas."),
    ("Resumir tus notas", "Decime 'resumime mis notas' y te doy un resumen con IA."),
    ("Buscar en tus notas", "Decime 'busca en mis notas sobre...' y te muestro lo que encuentre."),
    ("Listar tus notas", "Decime 'mis notas' o 'qué notas tengo' y te las muestro."),
    ("Charlar conmigo", "Si la consulta aporta contexto o contenido, te respondo usando el LLM."),
    ("Fuera de alcance", "Clima, noticias o datos en tiempo real se responden sin gastar LLM."),
]


def generar_ayuda() -> str:
    """Breef de presentación: qué puede hacer WALL-E hoy y con qué LLM."""
    lineas = [f"- {nombre}: {descripcion}" for nombre, descripcion in COMANDOS_DISPONIBLES]
    return (
        f"Soy WALL-E. Ahora mismo tengo instalado el modelo '{OLLAMA_MODEL}', "
        f"así que puedo:\n" + "\n".join(lineas) +
        "\n\nEsta lista crece a medida que se agregan nuevos comandos."
    )


def _normalizar_mensaje(mensaje: str) -> str:
    texto = mensaje.strip().lower()
    texto = re.sub(r"[¡!¿?.,;:]+", "", texto)
    texto = re.sub(r"\s+", " ", texto)
    return texto


def _es_mensaje_trivial(mensaje: str) -> bool:
    texto = _normalizar_mensaje(mensaje)
    return texto in _SALUDOS_SIMPLES or texto in _CONFIRMACIONES_SIMPLES


def _respuesta_trivial(mensaje: str) -> str:
    texto = _normalizar_mensaje(mensaje)
    if texto in _SALUDOS_SIMPLES:
        return "Hola. Puedo ayudarte con tus notas, memoria o ideas."
    return "Perfecto."


@dataclass
class IntentResult:
    intent: str
    payload: Optional[str] = None
    needs_llm: bool = False
    confidence: float = 1.0


def route_intent(mensaje: str) -> IntentResult:
    """Clasifica el mensaje en una intención. Prioridad: primer patrón que matchee."""
    if _es_mensaje_trivial(mensaje):
        return IntentResult("TRIVIAL", payload=_respuesta_trivial(mensaje))

    if _PATRON_AYUDA.search(mensaje):
        return IntentResult("HELP")

    dato = detectar_dato_a_recordar(mensaje)
    if dato:
        return IntentResult("SAVE_MEMORY", payload=dato)

    nota = detectar_nota_a_anotar(mensaje)
    if nota:
        return IntentResult("SAVE_NOTE", payload=nota)

    if _PATRON_RESUMIR.search(mensaje):
        return IntentResult("SUMMARIZE_NOTES", needs_llm=True)

    match_buscar = _PATRON_BUSCAR.search(mensaje)
    if match_buscar:
        query = next(group for group in match_buscar.groups() if group)
        return IntentResult("SEARCH_NOTES", payload=query.strip())

    if detectar_solicitud_listar_notas(mensaje):
        return IntentResult("LIST_NOTES")

    if _PATRON_HERRAMIENTA_EXTERNA.search(mensaje):
        return IntentResult("NEEDS_EXTERNAL_TOOL", payload=_RESPUESTA_HERRAMIENTA_EXTERNA)

    if _PATRON_FUERA_DE_ALCANCE.search(mensaje):
        return IntentResult("OUT_OF_SCOPE", payload=_RESPUESTA_FUERA_DE_ALCANCE)

    return IntentResult("CHAT", payload=mensaje, needs_llm=True)


def resolver_mensaje(chat_id: int, mensaje: str) -> str:
    """Punto único de entrada: clasifica el mensaje y devuelve la respuesta final.
    Usado por igual desde Telegram y desde el backend API."""
    resultado = route_intent(mensaje)

    if resultado.intent == "HELP":
        return generar_ayuda()

    if resultado.intent in {"TRIVIAL", "OUT_OF_SCOPE", "NEEDS_EXTERNAL_TOOL"}:
        return resultado.payload

    if resultado.intent == "SAVE_MEMORY":
        guardar_memoria(resultado.payload)
        return f"Listo, lo voy a recordar: {resultado.payload}"

    if resultado.intent == "SAVE_NOTE":
        guardar_nota(resultado.payload)
        return f"Anotado: {resultado.payload}"

    if resultado.intent == "LIST_NOTES":
        return cargar_notas()

    if resultado.intent == "SEARCH_NOTES":
        resultados = buscar_notas(resultado.payload)
        if not resultados:
            return f"No encontré notas relacionadas con '{resultado.payload}'."
        if len(resultados) <= UMBRAL_RESULTADOS_BUSQUEDA:
            return "Encontré esto en tus notas:\n" + "\n".join(resultados)
        return resumir_texto(
            f"Resume estos resultados de búsqueda sobre '{resultado.payload}'",
            "\n".join(resultados)
        )

    if resultado.intent == "SUMMARIZE_NOTES":
        return resumir_texto("Resume estas notas en pocos puntos claros", cargar_notas())

    # CHAT: conversación normal, va al LLM con memoria + notas + historial
    return generar_respuesta(chat_id, mensaje)
