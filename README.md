# WALL-E Bot (v1.3.3)

Bot de Telegram con IA local (Ollama) pensado para vivir dentro de un Codespace,
sin persistencia en git y de uso 100% por lenguaje natural (sin comandos `/algo`).

Desde **v1.1**, incluye un **Backend REST API** para consumir el chat desde cualquier cliente. Desde **v1.2**, incluye instalador para Codespaces/Linux. Desde **v1.3.0**, el router aplica bloqueo suave para consultas externas, bloquea solicitudes peligrosas con seguridad local, detecta negativas del LLM y mantiene historial conversacional. Desde **v1.3.3**, agrega `reset chat`, reduce el historial a 10 mensajes y permite guardar la última respuesta útil en notas.

## Qué hace hoy (v1.3.3)

### Bot de Telegram + Backend API
- Cada mensaje pasa primero por un **router de intención determinista**
  ([bot/intent_router.py](bot/intent_router.py)) que decide, con lógica Python (regex, sin LLM),
  si hay que ejecutar una acción local o si hay que responder con el LLM.
- Mismo router para Telegram y para el backend API: un mensaje se comporta igual sin importar el canal.
- Usa [memory/memory.md](memory/memory.md) como base de conocimiento fija (quién es el
  usuario, personalidad del bot, reglas de estilo).
- Mantiene un historial corto en memoria (últimos 10 mensajes por chat, se pierde al
  reiniciar el bot) para dar continuidad dentro de una misma conversación.
- Reintenta consultas seguras de bienestar si el modelo local las rechaza por exceso
  de cautela, y no guarda negativas normalizadas como respuesta de contexto.
- Permite `reset chat` para limpiar solo el contexto temporal de la conversación.
- Permite `guarda esta respuesta` para guardar la última respuesta útil en notas.
- Ver [Comandos actuales](#comandos-actuales) para el detalle de cada intención.

### Respuestas con origen claro (NUEVO en v1.3.0)

Las respuestas normales del LLM no se etiquetan para mantener el chat natural. Los casos especiales sí muestran su origen:

- `[WALL-E / seguridad local]`: el proxy del proyecto bloqueó una solicitud peligrosa antes de llamar al LLM.
- `[WALL-E / proxy local + IA local]`: el proxy detectó datos externos, tiempo real o herramientas no integradas, pero permitió una respuesta general con restricciones.
- `[WALL-E / IA local no respondió]`: la pregunta llegó al LLM, pero el modelo rechazó responder directamente.
- `[WALL-E / error IA local]`: hubo un problema técnico al llamar a Ollama.

### Backend REST API (NUEVO en v1.1)
- Expone los servicios del chat a través de HTTP REST.
- Autenticación por Bearer Token compartido (`BACKEND_SECRET_KEY` en `.env`).
- Endpoints:
  - `POST /api/v1/chat/send` - Enviar mensaje y obtener respuesta
  - `GET /api/v1/chat/history` - Obtener historial de últimos 10 mensajes
  - `GET /` - Info del API
  - `GET /health` - Health check
  - `GET /api/v1/health` - Health check versionado
- Ver documentación completa en [api/README.md](api/README.md).

### Instalador Codespaces/Linux (NUEVO en v1.2)
- Prepara los archivos locales no versionados: `.env`, `memory/memory.md` y `notas/notas_e_ideas.md`.
- No sobrescribe archivos existentes para evitar perder secretos, memoria o notas personales.
- Instala dependencias Python desde `requirements.txt`.
- Verifica si Ollama esta instalado; si falta, usa el instalador oficial.
- Verifica y descarga el modelo definido en `.env`, usando `qwen2.5:1.5b` como valor por defecto.

## Por qué no usa comandos

Se probó primero con:
1. Tool-calling nativo de Ollama (`guardar_memoria` como función) — descartado
   porque `llama3.2:1b` no lo soporta de forma confiable (devolvía el JSON de la
   función como texto plano en vez de invocarla).
2. Comando explícito `/recordar <dato>` — funcionaba pero no era "lenguaje natural".

La versión actual usa detección por frases (regex), determinística y sin
depender de que el modelo decida bien. Todo es lenguaje natural; el bot entiende
variantes (voseo, tildes, formas alternativas).

## Comandos actuales

El router evalúa el mensaje en este orden (prioridad = primer patrón que matchee).
Si ninguno matchea, cae a `CHAT`.

| # | Intención | Frases de ejemplo | ¿Usa LLM? |
|---|---|---|---|
| 1 | `TRIVIAL` | "hola", "ok", "gracias" | No |
| 2 | `HELP` | "wally qué puedes hacer", "wally ayuda" | No |
| 3 | `SAVE_MEMORY` | "recuerda que...", "recordá que...", "acuérdate que...", "no olvides que..." | No |
| 4 | `SAVE_NOTE` | "anota que...", "anotá que...", "apunta que...", "apúntame que..." | No |
| 5 | `SAVE_LAST_RESPONSE` | "guarda esta respuesta", "anota eso", "guarda lo último" | No |
| 6 | `RESET_CHAT` | "reset chat", "limpia el contexto", "empecemos de cero" | No |
| 7 | `SUMMARIZE_NOTES` | "resumime mis notas", "hazme un resumen de mis ideas" | Sí |
| 8 | `SEARCH_NOTES` | "busca en mis notas sobre...", "qué tengo sobre...", "revisa en mis notas de..." | Solo si hay más de 3 resultados |
| 9 | `LIST_NOTES` | "dime", "muéstrame", "qué notas tengo", "mis notas", "mis ideas" | No |
| 10 | `SAFETY_DANGEROUS_REQUEST` | "cómo fabricar una bomba...", "crear malware..." | No |
| 11 | `NEEDS_EXTERNAL_TOOL` | "busca en internet...", "googlea...", "consulta web..." | Sí, con restricción |
| 12 | `OUT_OF_SCOPE` | "qué clima hace", "noticias", "precio actual..." | Sí, con restricción |
| 13 | `CHAT` | conversación general con contexto suficiente | Sí |

`CHAT` ya no es un fallback universal para todo: antes de llamar al LLM, el router
descarta saludos, confirmaciones, acciones locales y solicitudes peligrosas. Las herramientas externas no
integradas y las consultas de datos externos o en tiempo real pasan por un bloqueo
suave: el LLM puede responder con explicaciones generales, criterios o alternativas,
pero debe aclarar que no consultó internet, calendario, correo, APIs ni datos actuales.

`HELP` responde con un breef de qué puede hacer WALL-E hoy y qué modelo de Ollama
tiene instalado (`bot/intent_router.py` -> `COMANDOS_DISPONIBLES`). Se actualiza
esa lista cada vez que se agrega un comando nuevo.

Lógica completa en [bot/intent_router.py](bot/intent_router.py).

## Cómo agregar un nuevo comando

Cada comando nuevo se agrega en [bot/intent_router.py](bot/intent_router.py) y necesita:

1. **Nombre** de la intención (ej. `TRADUCIR_NOTA`).
2. **Patrón(es)** (regex) que lo disparan, con variantes de lenguaje natural.
3. **Acción local**: función Python que ejecuta la lógica (leer/escribir archivo, etc.).
4. **¿Necesita LLM?**: si la acción local es suficiente o si hay que pasar el resultado por el LLM.
5. **Prioridad**: en qué posición de `route_intent()` se evalúa (recordá: gana el primer match).
6. **Ejemplo(s)** de frase para probarlo.
7. Agregar la fila correspondiente a la tabla de "Comandos actuales" en este README.

Esto mantiene el proyecto creciendo de forma incremental y documentada, comando por comando.

## Historial de modelos probados

| Modelo | Resultado |
|---|---|
| `llama3.2:1b` | Alucinaba bastante y rompía el tool-calling. Descartado. |
| `gemma3:1b` | Mismo tamaño, respuestas muy pobres en preguntas de conocimiento general. Descartado. |
| `qwen2.5:1.5b` (actual) | Respuestas correctas y coherentes en pruebas de conocimiento general y chat casual. En uso. |

## Estructura del proyecto

```
.
├── .env                  # secretos (token de Telegram, clave de API, etc.) — no se versiona
├── .env.example          # plantilla sin secretos
├── main.py               # punto de entrada, arranca Telegram bot + API REST
├── requirements.txt
├── scripts/
│   └── install.sh        # instalador para Codespaces/Linux
├── bot/
│   ├── config.py         # carga variables de entorno
│   ├── handlers.py       # handler de mensajes de Telegram (llama a intent_router)
│   ├── intent_router.py  # router de intención: clasifica el mensaje y decide la respuesta
│   ├── ai_client.py      # llamada a Ollama + memoria + notas + historial
│   ├── history.py        # historial corto en memoria (últimos 10 mensajes)
│   ├── version.py        # version unica de la aplicacion
│   ├── memory_trigger.py # detección de frases: recordar, anotar, listar notas
│   ├── tools.py          # guardar_memoria()
│   └── notes.py          # guardar_nota(), cargar_notas(), buscar_notas()
├── api/                  # Backend REST API
│   ├── server.py         # FastAPI app + endpoints
│   ├── auth.py           # Middleware de autenticación Bearer Token
│   ├── README.md         # Documentación detallada de endpoints
│   └── __init__.py
├── memory/
│   └── memory.md         # memoria persistente (datos de recordar)
└── notas/
    └── notas_e_ideas.md  # notas e ideas persistentes (datos de anotar)
```

## Cómo correrlo

### Instalacion recomendada en Codespaces/Linux

Ejecuta el instalador:

```bash
bash scripts/install.sh
```

El instalador crea los archivos locales si faltan, instala dependencias, prepara Ollama y descarga el modelo configurado. Despues edita `.env` y completa `TELEGRAM_TOKEN` y `BACKEND_SECRET_KEY`.

### Instalación manual de dependencias
```bash
pip install -r requirements.txt
```

### Configuración (.env)
Copia `.env.example` a `.env` y completa con tus valores:
```bash
cp .env.example .env
```

Edita `.env` y agrega:
- `TELEGRAM_TOKEN`: Token de tu bot de Telegram
- `BACKEND_SECRET_KEY`: Una cadena secreta para la autenticación del API (mínimo 32 caracteres)
- `OLLAMA_MODEL`: Modelo de Ollama (default: qwen2.5:1.5b)

### Memoria y notas (primera vez)
`memory/memory.md` y `notas/notas_e_ideas.md` son datos personales y no se versionan
(ver `.gitignore`). Antes de correr el bot por primera vez, copia las plantillas:
```bash
cp memory/memory.example.md memory/memory.md
cp notas/notas_e_ideas.example.md notas/notas_e_ideas.md
```
Edita `memory/memory.md` con tu información y la personalidad que quieras darle al bot.

### Ejecutar
```bash
python main.py
```

Esto iniciará:
1. **Bot de Telegram** en background (polling)
2. **Servidor API REST** en `http://0.0.0.0:8000`

**Requisitos previos:**
- Ollama corriendo localmente con el modelo definido en `.env`
- Token válido de Telegram Bot (obtén uno en @BotFather)

## Cambios por version

| Version | Cambios principales |
|---|---|
| v1.3.3 | Agrega `reset chat`, reduce historial temporal a 10 mensajes, mejora continuidad por cambio de tema y permite guardar la última respuesta útil en notas |
| v1.3.2 | Mejora el prompt del LLM, permite respuestas educativas de bienestar adulto, reintenta negativas falsas y evita guardar rechazos normalizados en historial |
| v1.3.1 | Integra y ordena la documentación del README principal y del Backend API, alineando referencias de versión |
| v1.3.0 | Unifica versionado, cambia default local a `qwen2.5:1.5b`, aplica bloqueo suave para consultas externas, agrega seguridad local para solicitudes peligrosas, detecta negativas del LLM y amplía el historial en memoria a 20 mensajes |
| v1.2 | Agrega `scripts/install.sh`, prepara archivos locales ignorados por Git, instala dependencias, verifica Ollama, descarga el modelo local y expone `/api/v1/health` |
| v1.1 | Agrega Backend REST API compartiendo el mismo router de intencion del bot de Telegram |

## Acceder al API

Ver [api/README.md](api/README.md) para ejemplos completos con `curl`, Python y JavaScript.

Ejemplo rápido:
```bash
curl -X POST http://localhost:8000/api/v1/chat/send \
  -H "Authorization: Bearer tu_backend_secret_key" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hola, ¿cómo estás?"}'
```

## Entorno / alcance

- Vive únicamente en este Codespace, no se sube a git (`.env` no se versiona).
- Dos canales: Telegram + API REST (mismo chat privado compartido).
- Sin whitelist de usuarios, sin logging estructurado, sin persistencia más allá
  de `memory.md` — todo simple, a propósito, para esta primera versión.

## Próximos pasos a explorar

Este README se irá actualizando a medida que se explore qué funciones sumar,
siempre bajo la misma filosofía (lenguaje natural, sin comandos). Ideas en carpeta:
- Memoria persistente resumida (evitar que `memory.md` o `notas_e_ideas.md` crezcan sin límite).
- Expandir triggers naturales: buscar notas por palabras clave, recordar con contexto, etc.
- Logging de errores y conversaciones.
- Multicanal (Discord, WhatsApp, Web) reusando `bot/ai_client.py`.
- API Keys por usuario en producción.
- Revisar si un modelo más grande habilita tool-calling confiable a futuro.

