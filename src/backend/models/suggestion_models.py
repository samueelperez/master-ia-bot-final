"""
Modelos Pydantic para las sugerencias de usuarios.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

class SuggestionRequest(BaseModel):
    """Modelo para solicitud de nueva sugerencia."""
    suggestion: str = Field(..., min_length=1, max_length=1000, description="Texto de la sugerencia")
    user_info: Optional[Dict[str, Any]] = Field(default=None, description="Información adicional del usuario")

class SuggestionResponse(BaseModel):
    """Modelo para respuesta de sugerencia."""
    status: str = Field(..., description="Status de la operación")
    message: str = Field(..., description="Mensaje de respuesta")
    suggestion_id: Optional[int] = Field(None, description="ID de la sugerencia creada")

class SuggestionItem(BaseModel):
    """Modelo para un item de sugerencia."""
    id: int = Field(..., description="ID único de la sugerencia")
    user_id: str = Field(..., description="ID del usuario que envió la sugerencia")
    suggestion: str = Field(..., description="Texto de la sugerencia")
    timestamp: str = Field(..., description="Timestamp de creación")
    status: str = Field(..., description="Status de la sugerencia")
    user_info: Dict[str, Any] = Field(default_factory=dict, description="Información del usuario")
    admin_notes: Optional[str] = Field(None, description="Notas del administrador")
    updated_at: Optional[str] = Field(None, description="Timestamp de última actualización")

class SuggestionListResponse(BaseModel):
    """Modelo para lista de sugerencias."""
    suggestions: list[SuggestionItem] = Field(..., description="Lista de sugerencias")
    total: int = Field(..., description="Total de sugerencias")
    limit: int = Field(..., description="Límite aplicado")

class SuggestionStatusUpdate(BaseModel):
    """Modelo para actualización de status de sugerencia."""
    status: str = Field(..., description="Nuevo status de la sugerencia")
    admin_notes: Optional[str] = Field(None, description="Notas del administrador") 