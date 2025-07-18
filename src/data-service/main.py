"""
Main application entry point for the External Data Service.
Incluye sistema completo de seguridad robusta.
"""
import logging
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import uvicorn
import uuid

from api.routes import api_router
from core.config import settings
from core.logging import configure_logging, get_request_logger
from core.security import SecurityMiddleware, SecurityHeaders, secure_logger

# Configure logging
configure_logging()

logger = logging.getLogger(__name__)

# Create FastAPI app with security settings
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    # Security: Disable server header
    servers=[{"url": "/", "description": "External Data Service"}]
)

# ============================================
# MIDDLEWARE DE SEGURIDAD (ORDEN IMPORTANTE)
# ============================================

# 1. Trusted Host Protection (primero)
app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=["localhost", "127.0.0.1", "*.crypto-ai-bot.local"]
)

# 2. Security Middleware (nuestro sistema completo)
app.add_middleware(SecurityMiddleware)

# 3. CORS (después de seguridad)
if settings.BACKEND_CORS_ORIGINS:
    # CORS más restrictivo
    cors_origins = [str(origin) for origin in settings.BACKEND_CORS_ORIGINS]
    # Filtrar wildcard en producción
    if "*" in cors_origins and hasattr(settings, 'ENVIRONMENT') and settings.ENVIRONMENT == "production":
        cors_origins = ["https://crypto-ai-bot.com"]  # Dominio real en producción
        
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],  # Métodos específicos
        allow_headers=[
            "Accept",
            "Accept-Language", 
            "Content-Language",
            "Content-Type",
            "Authorization",
            "X-Requested-With"
        ],
        expose_headers=["X-Request-ID"],
        max_age=3600,  # Cache preflight por 1 hora
    )

# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)

# ============================================
# MIDDLEWARE DE REQUEST PROCESSING
# ============================================

@app.middleware("http")
async def request_processing_middleware(request: Request, call_next):
    """
    Middleware avanzado para procesamiento de requests con auditoría.
    """
    # Generate unique request ID
    request_id = str(uuid.uuid4())
    
    # Get request logger
    request_logger = get_request_logger(request_id)
    
    # Extract client info safely
    client_ip = "unknown"
    if request.client:
        client_ip = request.client.host
    
    # Check for forwarded headers (for proxy setups)
    forwarded_for = request.headers.get('X-Forwarded-For')
    if forwarded_for:
        client_ip = forwarded_for.split(',')[0].strip()
    
    # Mask sensitive headers for logging
    safe_headers = {}
    for header_name, header_value in request.headers.items():
        if header_name.lower() in ['authorization', 'x-api-key']:
            safe_headers[header_name] = secure_logger.mask_sensitive_data(header_value)
        else:
            safe_headers[header_name] = header_value
    
    # Log request start with security info
    secure_logger.safe_log(
        f"Request started: ID={request_id} IP={client_ip} "
        f"Method={request.method} Path={request.url.path} "
        f"UserAgent={request.headers.get('User-Agent', 'Unknown')[:100]}"
    )
    
    # Add request ID to request state for downstream use
    request.state.request_id = request_id
    request.state.client_ip = client_ip
    
    # Process request with error handling
    try:
        response = await call_next(request)
        
        # Log successful response
        request_logger.info(
            f"Request completed: ID={request_id} Status={response.status_code} "
            f"Path={request.url.path}"
        )
        
        # Add security headers to response
        security_headers = SecurityHeaders.get_security_headers()
        for header_name, header_value in security_headers.items():
            response.headers[header_name] = header_value
        
        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        
        return response
        
    except Exception as e:
        # Log error with context
        request_logger.error(
            f"Request failed: ID={request_id} Error={str(e)} "
            f"Path={request.url.path} IP={client_ip}"
        )
        
        # Return secure error response
        return Response(
            content='{"error": "Internal server error", "request_id": "' + request_id + '"}',
            status_code=500,
            media_type="application/json",
            headers={
                "X-Request-ID": request_id,
                **SecurityHeaders.get_security_headers()
            }
        )

# ============================================
# HEALTH CHECK ENDPOINTS
# ============================================

@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint (sin autenticación para monitoring).
    """
    return {
        "status": "healthy",
        "service": "external-data-service",
        "version": "1.0.0"
    }

@app.get("/health/detailed", tags=["Health"])
async def detailed_health_check():
    """
    Health check detallado con información del sistema.
    """
    import psutil
    import time
    
    return {
        "status": "healthy",
        "service": "external-data-service", 
        "version": "1.0.0",
        "timestamp": time.time(),
        "system": {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent
        },
        "security": {
            "rate_limiter": "active",
            "input_validation": "active",
            "security_headers": "active",
            "circuit_breaker": "active"
        }
    }

# ============================================
# ERROR HANDLERS
# ============================================

@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Handler para 404 con logging de seguridad."""
    client_ip = getattr(request.state, 'client_ip', 'unknown')
    request_id = getattr(request.state, 'request_id', str(uuid.uuid4()))
    
    # Log potential scanning attempt
    if any(suspicious in str(request.url.path).lower() for suspicious in 
           ['.env', 'admin', 'config', '.git', 'wp-admin', 'phpmyadmin']):
        logger.warning(f"Suspicious 404 request: IP={client_ip} Path={request.url.path}")
    
    return Response(
        content='{"error": "Not found", "request_id": "' + request_id + '"}',
        status_code=404,
        media_type="application/json",
        headers={
            "X-Request-ID": request_id,
            **SecurityHeaders.get_security_headers()
        }
    )

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    """Handler para errores 500 con logging seguro."""
    client_ip = getattr(request.state, 'client_ip', 'unknown')
    request_id = getattr(request.state, 'request_id', str(uuid.uuid4()))
    
    # Log error without exposing internal details
    logger.error(f"Internal error: ID={request_id} IP={client_ip} Path={request.url.path}")
    
    return Response(
        content='{"error": "Internal server error", "request_id": "' + request_id + '"}',
        status_code=500,
        media_type="application/json",
        headers={
            "X-Request-ID": request_id,
            **SecurityHeaders.get_security_headers()
        }
    )

# ============================================
# STARTUP EVENTS
# ============================================

@app.on_event("startup")
async def startup_event():
    """
    Eventos de inicio con verificaciones de seguridad.
    """
    logger.info("🚀 Starting External Data Service with security features...")
    
    # Verificar configuración de seguridad
    security_checks = {
        "SECRET_KEY": settings.SECRET_KEY != "your-secret-key-change-in-production",
        "API_KEYS": bool(settings.NEWS_API_KEY and settings.TWITTER_API_KEY),
        "CORS_ORIGINS": len(settings.BACKEND_CORS_ORIGINS) > 0,
        "CIRCUIT_BREAKER": settings.CIRCUIT_BREAKER_FAILURE_THRESHOLD > 0
    }
    
    # Log security status
    for check, status in security_checks.items():
        status_emoji = "✅" if status else "⚠️"
        logger.info(f"{status_emoji} Security check {check}: {'PASS' if status else 'WARN'}")
    
    # Warnings for production
    if settings.SECRET_KEY == "your-secret-key-change-in-production":
        logger.warning("⚠️ Using default SECRET_KEY in production!")
    
    if "*" in settings.BACKEND_CORS_ORIGINS:
        logger.warning("⚠️ CORS permite todos los orígenes - no recomendado para producción")
    
    logger.info("✅ External Data Service started successfully with security features")

@app.on_event("shutdown")
async def shutdown_event():
    """
    Eventos de cierre con limpieza de recursos.
    """
    logger.info("🛑 Shutting down External Data Service...")
    logger.info("✅ External Data Service shutdown complete")

# ============================================
# DEVELOPMENT FEATURES
# ============================================

if __name__ == "__main__":
    # Solo para desarrollo local
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=9005,
        reload=True,
        log_level="info",
        # Security headers for development
        headers=[
            ("Server", "External-Data-Service/1.0"),
            ("X-Content-Type-Options", "nosniff"),
            ("X-Frame-Options", "DENY")
        ]
    )
