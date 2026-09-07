"""
FastAPI server que expone el LLM y funcionalidades del chat privado de WALL-E.
Endpoints:
- GET / -> Info del API
- POST /api/v1/chat/send -> Enviar mensaje y obtener respuesta
- GET /api/v1/chat/history -> Obtener historial de últimos 5 mensajes
"""

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from datetime import datetime
import sys
import os

# Agregar el directorio raíz al path para importar bot/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.intent_router import resolver_mensaje
from bot.history import obtener_historial
from api.auth import verify_bearer_token, validate_message_length


app = FastAPI(
    title="WALL-E Backend API",
    description="API REST para acceder al chat privado con IA local (Ollama)",
    version="1.0.0"
)


class MessageRequest(BaseModel):
    """Modelo de request para enviar mensajes."""
    message: str


class MessageResponse(BaseModel):
    """Modelo de response para respuestas del chat."""
    status: str
    response: str
    timestamp: str
    chat_id: str


class HistoryResponse(BaseModel):
    """Modelo de response para historial."""
    status: str
    history: list


class InfoResponse(BaseModel):
    """Modelo de response para info del API."""
    name: str
    version: str
    status: str
    description: str


@app.get("/", response_model=InfoResponse)
async def root():
    """
    Endpoint raíz que devuelve información del API.
    No requiere autenticación.
    """
    return {
        "name": "WALL-E Backend API",
        "version": "1.0.0",
        "status": "running",
        "description": "API REST para chat privado con IA local"
    }


@app.get("/health")
async def health_check():
    """Health check. No requiere autenticación."""
    return {"status": "ok"}


@app.post("/api/v1/chat/send", response_model=MessageResponse)
async def send_message(request: MessageRequest, token = Depends(verify_bearer_token)):
    """
    Endpoint para enviar un mensaje y obtener respuesta de la IA.
    
    Requiere: Authorization: Bearer <BACKEND_SECRET_KEY>
    
    Args:
        request: { "message": "Tu pregunta aquí" }
        token: Validado automáticamente por verify_bearer_token
    
    Returns:
        { "status": "ok", "response": "Respuesta del bot...", "timestamp": "...", "chat_id": "default" }
    """
    # Validar mensaje
    if not validate_message_length(request.message):
        raise HTTPException(status_code=400, detail="Message too long or empty (max 5000 chars)")
    
    # Usar chat_id fijo "api" para requests desde el backend
    chat_id = 999999  # Chat ID especial para API
    
    try:
        # Enruta el mensaje por el mismo router de intención que usa Telegram
        respuesta = resolver_mensaje(chat_id, request.message)
        
        return {
            "status": "ok",
            "response": respuesta,
            "timestamp": datetime.now().isoformat(),
            "chat_id": "default"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating response: {str(e)}")


@app.get("/api/v1/chat/history", response_model=HistoryResponse)
async def get_history(token = Depends(verify_bearer_token)):
    """
    Endpoint para obtener el historial de últimos 5 mensajes.
    
    Requiere: Authorization: Bearer <BACKEND_SECRET_KEY>
    
    Returns:
        { "status": "ok", "history": [...últimos 5 mensajes...] }
    """
    try:
        # Obtener historial del chat_id especial "api"
        chat_id = 999999
        history = obtener_historial(chat_id)
        
        return {
            "status": "ok",
            "history": history
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving history: {str(e)}")
