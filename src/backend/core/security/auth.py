"""
Sistema de autenticación para el backend.
Implementa autenticación con Bearer tokens.
"""

import logging
from typing import Optional
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import hashlib
import time

from ..config.security_config import SecurityConfig, hash_token

logger = logging.getLogger(__name__)

# Instancia del esquema de autenticación Bearer
security = HTTPBearer()

class TokenValidator:
    """Validador de tokens de autenticación."""
    
    def __init__(self):
        self.failed_attempts = {}
        self.blocked_tokens = set()
    
    def validate_token(self, token: str) -> bool:
        """
        Validar token de autenticación.
        
        Args:
            token: Token a validar
        
        Returns:
            True si el token es válido
        """
        if not token:
            return False
        
        # Verificar si el token está en la lista negra
        if token in self.blocked_tokens:
            logger.warning(f"Token bloqueado intentado: {token[:8]}...")
            return False
        
        # Validar contra API_SECRET_KEY
        expected_hash = hash_token(SecurityConfig.API_SECRET_KEY)
        provided_hash = hash_token(token)
        
        return expected_hash == provided_hash
    
    def record_failed_attempt(self, token: str):
        """Registrar intento fallido de autenticación."""
        current_time = time.time()
        
        if token not in self.failed_attempts:
            self.failed_attempts[token] = []
        
        self.failed_attempts[token].append(current_time)
        
        # Limpiar intentos antiguos (más de 1 hora)
        cutoff_time = current_time - 3600
        self.failed_attempts[token] = [
            attempt for attempt in self.failed_attempts[token] 
            if attempt > cutoff_time
        ]
        
        # Si hay más de 5 intentos fallidos en la última hora, bloquear token
        if len(self.failed_attempts[token]) >= 5:
            self.blocked_tokens.add(token)
            logger.warning(f"Token bloqueado por múltiples intentos fallidos: {token[:8]}...")
    
    def is_token_blocked(self, token: str) -> bool:
        """Verificar si un token está bloqueado."""
        return token in self.blocked_tokens


# Instancia global del validador
token_validator = TokenValidator()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Dependency para validar autenticación en endpoints.
    
    Args:
        credentials: Credenciales HTTP Bearer
    
    Returns:
        Información del usuario autenticado
    
    Raises:
        HTTPException: Si la autenticación falla
    """
    if not credentials:
        logger.warning("Request sin credenciales de autenticación")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales de autenticación requeridas",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    
    # Verificar si el token está bloqueado
    if token_validator.is_token_blocked(token):
        logger.warning(f"Intento de acceso con token bloqueado: {token[:8]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token bloqueado por múltiples intentos fallidos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Validar token
    if not token_validator.validate_token(token):
        # Registrar intento fallido
        token_validator.record_failed_attempt(token)
        logger.warning(f"Token inválido: {token[:8]}...")
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticación inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Token válido - retornar información del usuario
    return {
        "authenticated": True,
        "token_hash": hash_token(token)[:16],
        "auth_time": time.time()
    }


async def get_optional_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    """
    Dependency para autenticación opcional.
    
    Args:
        credentials: Credenciales HTTP Bearer opcionales
    
    Returns:
        Información del usuario si está autenticado, None si no
    """
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None


def require_auth(endpoint_name: str = ""):
    """
    Decorator para requerir autenticación en endpoints específicos.
    
    Args:
        endpoint_name: Nombre del endpoint para logging
    
    Returns:
        Dependency function
    """
    async def auth_dependency(user = Depends(get_current_user)):
        if endpoint_name:
            logger.info(f"Usuario autenticado accediendo a {endpoint_name}")
        return user
    
    return auth_dependency 