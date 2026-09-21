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
from bot.history import limpiar_historial, obtener_ultima_respuesta

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

_PATRON_RESET_CHAT = re.compile(
    r"\b(?:reset\s+chat|limpia\s+(?:el\s+)?(?:chat|contexto|conversaci[oó]n)|"
    r"borra\s+(?:el\s+)?(?:chat|contexto|historial)|empecemos\s+de\s+cero|"
    r"olvida\s+(?:esta\s+)?conversaci[oó]n)\b",
    re.IGNORECASE
)

_PATRON_GUARDAR_ULTIMA_RESPUESTA = re.compile(
    r"\b(?:guarda|guardar|anota|anotar)\s+(?:esta\s+)?(?:respuesta|lo\s+[uú]ltimo|eso)"
    r"|\b(?:eso\s+me\s+interesa|gu[aá]rdalo|an[oó]talo)\b",
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

_PATRON_SOLICITUD_PELIGROSA = re.compile(
    r"\b(?:"
    r"(?:fabricar|hacer|construir|crear|armar|preparar)\s+(?:una\s+)?(?:bomba|explosivo|arma)|"
    r"bomba\s+(?:nuclear|casera|molotov)|explosivos?|armas?\s+(?:quimicas|biologicas|nucleares)|"
    r"(?:hackear|robar|extraer)\s+(?:credenciales|contraseñas|passwords|tokens)|"
    r"malware|ransomware|keylogger|phishing|evadir\s+seguridad|bypass\s+seguridad"
    r")\b",
    re.IGNORECASE,
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
    "Si la pregunta se puede responder de forma conceptual o general, responderé sin inventar datos actuales."
)

_RESPUESTA_HERRAMIENTA_EXTERNA = (
    "Todavía no tengo integrada esa herramienta externa. "
    "Puedo ayudarte con criterios, pasos o alternativas sin simular que usé esa herramienta."
)

_RESPUESTA_SOLICITUD_PELIGROSA = (
    "[WALL-E / seguridad local]\n"
    "No puedo ayudar con instrucciones para fabricar armas, causar daño, robar credenciales, "
    "crear malware o evadir sistemas de seguridad. Sí puedo ayudarte con una explicación segura, "
    "histórica, ética, defensiva o educativa del tema."
)

_PREFIJOS_RESPUESTA_NO_GUARDABLE = (
    "[WALL-E / error IA local]",
    "[WALL-E / IA local no respondió]",
    "[WALL-E / seguridad local]",
)

# Lista de comandos disponibles, para el breef de ayuda. Se va sumando una
# fila cada vez que se agrega un comando nuevo (ver README -> "Comandos actuales").
COMANDOS_DISPONIBLES = [
    ("Recordar algo", "Decime 'recuerda que...' y lo guardo en memoria permanente."),
    ("Anotar una nota", "Decime 'anota que...' y lo guardo en tus notas."),
    ("Resumir tus notas", "Decime 'resumime mis notas' y te doy un resumen con IA."),
    ("Buscar en tus notas", "Decime 'busca en mis notas sobre...' y te muestro lo que encuentre."),
    ("Listar tus notas", "Decime 'mis notas' o 'qué notas tengo' y te las muestro."),
    ("Guardar última respuesta", "Decime 'guarda esta respuesta' y la guardo en tus notas."),
    ("Reset chat", "Decime 'reset chat' para limpiar el contexto temporal de esta conversación."),
    ("Charlar conmigo", "Si la consulta aporta contexto o contenido, te respondo usando el LLM."),
    ("Seguridad local", "Solicitudes peligrosas se bloquean antes de llegar al LLM."),
    ("Bloqueo suave", "Clima, noticias, web o herramientas externas pueden recibir explicación general con advertencia."),
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


def _preparar_respuesta_para_nota(respuesta: str) -> str:
    texto = re.sub(r"\s+", " ", respuesta).strip()
    if len(texto) > 1200:
        texto = texto[:1200].rstrip() + "..."
    return texto


def _es_respuesta_guardable(respuesta: str) -> bool:
    texto = respuesta.strip()
    return bool(texto) and not texto.startswith(_PREFIJOS_RESPUESTA_NO_GUARDABLE)


@dataclass
class IntentResult:
    intent: str
    payload: Optional[str] = None
    needs_llm: bool = False
    confidence: float = 1.0


def route_intent(mensaje: str) -> IntentResult:
    """Clasifica el mensaje en una intención. Prioridad: primer patrón que matchee."""
    if _PATRON_RESET_CHAT.search(mensaje):
        return IntentResult("RESET_CHAT")

    if _PATRON_GUARDAR_ULTIMA_RESPUESTA.search(mensaje):
        return IntentResult("SAVE_LAST_RESPONSE")

    if _es_mensaje_trivial(mensaje):
        return IntentResult("TRIVIAL", payload=_respuesta_trivial(mensaje))

    if _PATRON_AYUDA.search(mensaje):
        return IntentResult("HELP")

    if _PATRON_SOLICITUD_PELIGROSA.search(mensaje):
        return IntentResult("SAFETY_DANGEROUS_REQUEST", payload=_RESPUESTA_SOLICITUD_PELIGROSA)

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

    if resultado.intent == "RESET_CHAT":
        limpiar_historial(chat_id)
        return "Listo, limpié el contexto temporal de esta conversación. La memoria permanente y tus notas no se tocaron."

    if resultado.intent == "SAVE_LAST_RESPONSE":
        ultima_respuesta = obtener_ultima_respuesta(chat_id)
        if not ultima_respuesta:
            return "No encontré una respuesta anterior para guardar."
        if not _es_respuesta_guardable(ultima_respuesta):
            return "No guardé la última respuesta porque era un error, rechazo o bloqueo local."
        nota = _preparar_respuesta_para_nota(ultima_respuesta)
        guardar_nota(f"Respuesta guardada: {nota}")
        return "Listo, guardé la última respuesta en tus notas."

    if resultado.intent == "TRIVIAL":
        return resultado.payload

    if resultado.intent == "SAFETY_DANGEROUS_REQUEST":
        return resultado.payload

    if resultado.intent in {"OUT_OF_SCOPE", "NEEDS_EXTERNAL_TOOL"}:
        respuesta = generar_respuesta(
            chat_id,
            (
                f"{resultado.payload}\n\n"
                f"Pregunta original del usuario: {mensaje}\n\n"
                "Responde de forma útil solo si puedes hacerlo sin datos en tiempo real, "
                "sin afirmar que consultaste internet, correo, calendario, APIs u otras herramientas externas. "
                "Si hace falta información actual o acceso externo, dilo con claridad y ofrece una alternativa práctica."
            )
        )
        return f"[WALL-E / proxy local + IA local]\n{respuesta}"

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
