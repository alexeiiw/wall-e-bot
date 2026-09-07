"""
Autenticación Bearer Token para el API REST.
Valida que el token en el header "Authorization" coincida con BACKEND_SECRET_KEY.
"""

from fastapi import HTTPException, Depends, Header
from typing import Optional
import os


async def verify_bearer_token(authorization: Optional[str] = Header(None)):
    """
    Dependency para validar Bearer token en endpoints protegidos.
    
    Uso:
    @app.post("/api/v1/chat/send")
    async def send_message(request: MessageRequest, token = Depends(verify_bearer_token)):
        ...
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid Authorization header format")
    
    token = authorization.split("Bearer ")[-1]
    backend_key = os.getenv("BACKEND_SECRET_KEY")
    
    if not backend_key:
        raise HTTPException(status_code=500, detail="BACKEND_SECRET_KEY not configured")
    
    if token != backend_key:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    return token


def validate_message_length(message: str, max_length: int = 5000) -> bool:
    """Valida que el mensaje no exceda la longitud máxima."""
    if not message or len(message) > max_length:
        return False
    return True
