# WALL-E Backend API

## Descripción

API REST que expone el chat privado con IA local (Ollama) del bot WALL-E. Permite enviar mensajes y obtener respuestas desde cualquier cliente, no solo desde Telegram.

## Autenticación

Todos los endpoints (excepto `/` y `/health`) requieren autenticación Bearer Token:

```
Authorization: Bearer <BACKEND_SECRET_KEY>
```

El token se define en el archivo `.env`:
```env
BACKEND_SECRET_KEY=tu_cadena_secreta_aqui
```

## Endpoints

### `GET /`

Información del API.

**Autenticación:** No requerida

**Response:**
```json
{
  "name": "WALL-E Backend API",
  "version": "1.0.0",
  "status": "running",
  "description": "API REST para chat privado con IA local"
}
```

---

### `GET /health`

Health check del servidor.

**Autenticación:** No requerida

**Response:**
```json
{
  "status": "ok"
}
```

---

### `POST /api/v1/chat/send`

Envía un mensaje y obtiene la respuesta de la IA.

**Autenticación:** Requerida

**Headers:**
```
Authorization: Bearer <BACKEND_SECRET_KEY>
Content-Type: application/json
```

**Body:**
```json
{
  "message": "Tu pregunta o mensaje aquí"
}
```

**Response (200):**
```json
{
  "status": "ok",
  "response": "Respuesta del bot...",
  "timestamp": "2026-08-30T15:30:00.123456",
  "chat_id": "default"
}
```

**Errors:**
- `400 Bad Request`: Mensaje vacío o > 5000 caracteres
- `401 Unauthorized`: Token inválido
- `500 Internal Server Error`: Error al generar respuesta

---

### `GET /api/v1/chat/history`

Obtiene el historial de últimos 5 mensajes.

**Autenticación:** Requerida

**Headers:**
```
Authorization: Bearer <BACKEND_SECRET_KEY>
```

**Response (200):**
```json
{
  "status": "ok",
  "history": [
    {
      "role": "user",
      "content": "Primer mensaje"
    },
    {
      "role": "assistant",
      "content": "Respuesta del bot"
    }
  ]
}
```

**Errors:**
- `401 Unauthorized`: Token inválido
- `500 Internal Server Error`: Error al recuperar historial

---

## Ejemplos de Uso

### Curl

#### GET /
```bash
curl http://localhost:8000/
```

#### POST /api/v1/chat/send
```bash
curl -X POST http://localhost:8000/api/v1/chat/send \
  -H "Authorization: Bearer abc123xyz789def456" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hola, ¿cómo estás?"}'
```

#### GET /api/v1/chat/history
```bash
curl http://localhost:8000/api/v1/chat/history \
  -H "Authorization: Bearer abc123xyz789def456"
```

---

### Python

```python
import requests
import json

BASE_URL = "http://localhost:8000"
TOKEN = "abc123xyz789def456"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

# Enviar mensaje
response = requests.post(
    f"{BASE_URL}/api/v1/chat/send",
    json={"message": "¿Qué es machine learning?"},
    headers=headers
)

print(response.json())

# Obtener historial
response = requests.get(
    f"{BASE_URL}/api/v1/chat/history",
    headers=headers
)

print(response.json())
```

---

### JavaScript (Fetch)

```javascript
const BASE_URL = "http://localhost:8000";
const TOKEN = "abc123xyz789def456";

const headers = {
    "Authorization": `Bearer ${TOKEN}`,
    "Content-Type": "application/json"
};

// Enviar mensaje
fetch(`${BASE_URL}/api/v1/chat/send`, {
    method: "POST",
    headers: headers,
    body: JSON.stringify({ message: "Hola" })
})
.then(res => res.json())
.then(data => console.log(data));

// Obtener historial
fetch(`${BASE_URL}/api/v1/chat/history`, {
    method: "GET",
    headers: headers
})
.then(res => res.json())
.then(data => console.log(data));
```

---

## Notas Importantes

1. **Chat ID único**: Todos los requests desde la API usan el mismo `chat_id` (999999 internamente), por lo que comparten el mismo historial de 5 últimos mensajes.

2. **Contexto de memoria**: Cada respuesta tiene acceso a:
   - Contexto en `memory/memory.md` (quién es el usuario, personalidad del bot)
   - Contexto en `notas/notas_e_ideas.md` (notas e ideas anotadas)
   - Últimos 5 mensajes del historial

3. **Límite de mensajes**: Máximo 5000 caracteres por mensaje. Mensajes más largos serán rechazados.

4. **Token compartido**: La misma cadena `BACKEND_SECRET_KEY` se usa para todos los clientes. Para múltiples usuarios en producción, considera implementar API Keys por usuario.
