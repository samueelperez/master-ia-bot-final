"""
Servicio para manejar sugerencias de usuarios.
"""

import json
import os
from datetime import datetime
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class SuggestionsService:
    def __init__(self):
        self.suggestions_file = "logs/suggestions.json"
        self._ensure_suggestions_file()
    
    def _ensure_suggestions_file(self):
        """Asegurar que el archivo de sugerencias existe."""
        try:
            if not os.path.exists(self.suggestions_file):
                os.makedirs(os.path.dirname(self.suggestions_file), exist_ok=True)
                with open(self.suggestions_file, 'w', encoding='utf-8') as f:
                    json.dump([], f, ensure_ascii=False, indent=2)
                logger.info(f"Archivo de sugerencias creado: {self.suggestions_file}")
        except Exception as e:
            logger.error(f"Error creando archivo de sugerencias: {e}")
    
    def add_suggestion(self, user_id: str, suggestion_text: str, user_info: Dict[str, Any] = None) -> Dict[str, Any]:
        """Agregar una nueva sugerencia."""
        try:
            # Leer sugerencias existentes
            suggestions = self._read_suggestions()
            
            # Crear nueva sugerencia
            new_suggestion = {
                "id": len(suggestions) + 1,
                "user_id": user_id,
                "suggestion": suggestion_text,
                "timestamp": datetime.now().isoformat(),
                "status": "pending",
                "user_info": user_info or {}
            }
            
            # Agregar a la lista
            suggestions.append(new_suggestion)
            
            # Guardar en archivo
            self._save_suggestions(suggestions)
            
            logger.info(f"Sugerencia agregada por usuario {user_id}: {suggestion_text[:50]}...")
            
            return {
                "status": "success",
                "message": "Sugerencia enviada correctamente",
                "suggestion_id": new_suggestion["id"]
            }
            
        except Exception as e:
            logger.error(f"Error agregando sugerencia: {e}")
            return {
                "status": "error",
                "message": "Error al guardar la sugerencia"
            }
    
    def get_suggestions(self, limit: int = 50, status: str = None) -> List[Dict[str, Any]]:
        """Obtener sugerencias (para administradores)."""
        try:
            suggestions = self._read_suggestions()
            
            # Filtrar por status si se especifica
            if status:
                suggestions = [s for s in suggestions if s.get("status") == status]
            
            # Limitar resultados
            if limit:
                suggestions = suggestions[-limit:]
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Error obteniendo sugerencias: {e}")
            return []
    
    def update_suggestion_status(self, suggestion_id: int, status: str, admin_notes: str = None) -> Dict[str, Any]:
        """Actualizar el status de una sugerencia (para administradores)."""
        try:
            suggestions = self._read_suggestions()
            
            # Buscar la sugerencia
            for suggestion in suggestions:
                if suggestion["id"] == suggestion_id:
                    suggestion["status"] = status
                    if admin_notes:
                        suggestion["admin_notes"] = admin_notes
                    suggestion["updated_at"] = datetime.now().isoformat()
                    
                    # Guardar cambios
                    self._save_suggestions(suggestions)
                    
                    logger.info(f"Status de sugerencia {suggestion_id} actualizado a: {status}")
                    
                    return {
                        "status": "success",
                        "message": f"Status actualizado a: {status}"
                    }
            
            return {
                "status": "error",
                "message": "Sugerencia no encontrada"
            }
            
        except Exception as e:
            logger.error(f"Error actualizando status de sugerencia: {e}")
            return {
                "status": "error",
                "message": "Error al actualizar el status"
            }
    
    def _read_suggestions(self) -> List[Dict[str, Any]]:
        """Leer sugerencias del archivo."""
        try:
            with open(self.suggestions_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []
    
    def _save_suggestions(self, suggestions: List[Dict[str, Any]]):
        """Guardar sugerencias en el archivo."""
        with open(self.suggestions_file, 'w', encoding='utf-8') as f:
            json.dump(suggestions, f, ensure_ascii=False, indent=2)

# Instancia global del servicio
suggestions_service = SuggestionsService() 