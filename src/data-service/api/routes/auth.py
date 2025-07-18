"""
Authentication routes for the External Data Service.
Incluye validaciones de seguridad robustas.
"""
from datetime import timedelta
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm

from core.auth import (
    authenticate_user,
    create_access_token,
    get_current_active_user,
    User,
    has_scope
)
from core.config import settings
from core.security import (
    InputSanitizer, 
    RateLimiter,
    SecureAPIRequest,
    secure_logger
)
from models.schemas import Token, UserInfo

router = APIRouter()

# Inicializar componentes de seguridad
rate_limiter = RateLimiter()
input_sanitizer = InputSanitizer()

@router.post("/token", response_model=Token)
async def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Dict[str, str]:
    """
    Get an access token con validaciones de seguridad.
    
    Args:
        request: Request object para obtener IP del cliente
        form_data: OAuth2 password request form
        
    Returns:
        Access token
        
    Raises:
        HTTPException: If authentication failed or rate limited
    """
    # Obtener IP del cliente
    client_ip = getattr(request.state, 'client_ip', 'unknown')
    
    # Verificar rate limiting específico para login
    login_key = f"login:{client_ip}"
    if not rate_limiter.is_allowed(login_key, max_requests=5, window_minutes=5):
        secure_logger.safe_log(f"Rate limit exceeded for login from IP: {client_ip}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again later.",
            headers={"Retry-After": "300"}  # 5 minutos
        )
    
    # Sanitizar inputs de login
    username = input_sanitizer.sanitize_string(form_data.username)
    password = form_data.password  # No sanitizar password para no alterar autenticación
    
    # Validar longitud de username
    if len(username) > 50:
        secure_logger.safe_log(f"Username too long from IP: {client_ip}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username too long"
        )
    
    # Validar caracteres peligrosos en username
    if input_sanitizer.detect_injection_attempts(username):
        secure_logger.safe_log(f"Injection attempt in username from IP: {client_ip}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid username format"
        )
    
    # Log intento de login (sin exponer password)
    secure_logger.safe_log(f"Login attempt: username={username} IP={client_ip}")
    
    # Autenticar usuario
    user = authenticate_user(username, password)
    if not user:
        # Log intento fallido
        secure_logger.safe_log(f"Failed login attempt: username={username} IP={client_ip}")
        
        # Incrementar contador de rate limiting
        rate_limiter.increment(login_key)
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Log login exitoso
    secure_logger.safe_log(f"Successful login: username={username} IP={client_ip}")
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    access_token = create_access_token(
        data={"sub": user["username"], "scopes": user["scopes"]},
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserInfo)
async def read_users_me(
    request: Request,
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Get information about the current user con logging de seguridad.
    
    Args:
        request: Request object
        current_user: Current user
        
    Returns:
        User information
    """
    client_ip = getattr(request.state, 'client_ip', 'unknown')
    
    # Verificar rate limiting para consultas de usuario
    user_key = f"user_info:{client_ip}"
    if not rate_limiter.is_allowed(user_key, max_requests=30, window_minutes=1):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please slow down."
        )
    
    # Log acceso a información de usuario
    secure_logger.safe_log(f"User info requested: username={current_user.username} IP={client_ip}")
    
    return {
        "username": current_user.username,
        "scopes": current_user.scopes
    }


@router.get("/status")
async def check_auth_status(
    request: Request,
    current_user: User = Depends(has_scope(["read:all"]))
) -> Dict[str, str]:
    """
    Check authentication status con validaciones de seguridad.
    
    Args:
        request: Request object
        current_user: Current user
        
    Returns:
        Status message
    """
    client_ip = getattr(request.state, 'client_ip', 'unknown')
    
    # Verificar rate limiting para status checks
    status_key = f"auth_status:{client_ip}"
    if not rate_limiter.is_allowed(status_key, max_requests=60, window_minutes=1):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many status checks. Please slow down."
        )
    
    # Log verificación de status
    secure_logger.safe_log(f"Auth status checked: username={current_user.username} IP={client_ip}")
    
    return {"status": "authenticated", "username": current_user.username}


@router.post("/validate")
async def validate_token(
    request: Request,
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Validar token de acceso con información de seguridad.
    
    Args:
        request: Request object
        current_user: Current user
        
    Returns:
        Token validation info
    """
    client_ip = getattr(request.state, 'client_ip', 'unknown')
    
    # Verificar rate limiting para validaciones de token
    validate_key = f"token_validate:{client_ip}"
    if not rate_limiter.is_allowed(validate_key, max_requests=100, window_minutes=1):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many token validations. Please slow down."
        )
    
    # Log validación de token
    secure_logger.safe_log(f"Token validated: username={current_user.username} IP={client_ip}")
    
    return {
        "valid": True,
        "username": current_user.username,
        "scopes": current_user.scopes,
        "client_ip": client_ip,
        "timestamp": rate_limiter._get_current_time()
    }
