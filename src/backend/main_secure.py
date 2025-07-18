"""
API Backend Securizada para Crypto AI Bot.
Integra autenticación, rate limiting, validación y headers de seguridad.
"""

import os
import logging
import psutil
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, Depends, Query, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager

# Imports de la aplicación
from core.db import SessionLocal
from core.models import Strategy
from services import fetcher, ta_service

# Imports de seguridad
from core.config.security_config import SecurityConfig, APIRequest, IndicatorRequest
from core.security.auth import get_current_user, require_auth
from core.security.middleware import SecurityMiddleware
from core.validation.input_validator import input_validator

# Configuración de logging estructurado
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
    handlers=[
        logging.FileHandler('logs/backend_secure.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Crear directorio de logs si no existe
os.makedirs('logs', exist_ok=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestión del ciclo de vida de la aplicación."""
    logger.info("🚀 Iniciando Backend Securizado")
    logger.info(f"📊 Configuración de seguridad: Rate Limiting {SecurityConfig.RATE_LIMIT_PER_MINUTE}/min")
    yield
    logger.info("🔒 Cerrando Backend Securizado")

# Crear aplicación FastAPI
app = FastAPI(
    title="Crypto AI Bot - Backend Securizado",
    description="API backend con seguridad integral: autenticación, rate limiting, validación y headers de seguridad",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs" if os.getenv("ENABLE_DOCS", "true").lower() == "true" else None,
    redoc_url="/redoc" if os.getenv("ENABLE_DOCS", "true").lower() == "true" else None,
)

# Middleware de hosts confiables (debe ir antes que CORS)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=SecurityConfig.ALLOWED_HOSTS + ["localhost", "127.0.0.1", "*.localhost"]
)

# Configuración CORS restrictiva
app.add_middleware(
    CORSMiddleware,
    allow_origins=SecurityConfig.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
    expose_headers=["X-Request-ID", "X-RateLimit-Remaining-Minute", "X-RateLimit-Reset-Minute"]
)

# Middleware de seguridad principal (debe ir al final)
app.add_middleware(SecurityMiddleware)

def get_db():
    """Dependency para obtener sesión de base de datos."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

# =============================================================================
# ENDPOINTS PÚBLICOS (sin autenticación)
# =============================================================================

@app.get("/health")
async def health():
    """Health check básico."""
    return {
        "status": "ok", 
        "version": "2.0.0",
        "security": "enabled"
    }

@app.get("/health/detailed")
async def health_detailed():
    """Health check detallado con métricas del sistema."""
    try:
        # Métricas del sistema
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            "status": "ok",
            "version": "2.0.0",
            "timestamp": psutil.time.time(),
            "system": {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available_gb": round(memory.available / (1024**3), 2),
                "disk_percent": disk.percent,
                "disk_free_gb": round(disk.free / (1024**3), 2)
            },
            "security": {
                "authentication": "enabled",
                "rate_limiting": "enabled", 
                "input_validation": "enabled",
                "cors_origins": len(SecurityConfig.ALLOWED_ORIGINS)
            }
        }
    except Exception as e:
        logger.error(f"Error en health check detallado: {e}")
        return {
            "status": "partial",
            "version": "2.0.0",
            "error": "Error obteniendo métricas del sistema"
        }

# =============================================================================
# ENDPOINTS PROTEGIDOS (requieren autenticación)
# =============================================================================

@app.get("/db-test")
async def db_test(
    session: Session = Depends(get_db),
    user = Depends(require_auth("db-test"))
):
    """Test de conexión a base de datos (requiere autenticación)."""
    try:
        strategies = session.query(Strategy).all()
        return {
            "status": "connected",
            "count_strategies": len(strategies), 
            "strategies": [s.name for s in strategies],
            "user": user.get("token_hash", "unknown")
        }
    except Exception as e:
        logger.error(f"Database test error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Error de conexión a base de datos"
        )

@app.get("/available-indicators")
async def get_available_indicators(user = Depends(require_auth("indicators-list"))):
    """Obtener indicadores disponibles (requiere autenticación)."""
    try:
        indicators = ta_service.get_available_indicators()
        return {
            "categories": list(indicators.keys()),
            "indicators": indicators,
            "user": user.get("token_hash", "unknown")
        }
    except Exception as e:
        logger.error(f"Error getting available indicators: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error obteniendo indicadores disponibles"
        )

@app.get("/indicator-profiles")
async def get_indicator_profiles(user = Depends(require_auth("indicator-profiles"))):
    """Obtener perfiles de indicadores (requiere autenticación)."""
    try:
        return {
            "profiles": list(ta_service.INDICATOR_PROFILES.keys()),
            "details": ta_service.INDICATOR_PROFILES,
            "user": user.get("token_hash", "unknown")
        }
    except Exception as e:
        logger.error(f"Error getting indicator profiles: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error obteniendo perfiles de indicadores"
        )

@app.get("/indicators")
async def get_indicators(
    symbol: str = Query(..., description="Símbolo de la criptomoneda (ej: BTC-USD)"),
    tf: str = Query(..., description="Timeframe (ej: 1h, 4h, 1d)"),
    limit: int = Query(100, ge=1, le=1000, description="Número de candlesticks a obtener"),
    profile: Optional[str] = Query(None, description="Perfil predefinido de indicadores"),
    categories: Optional[List[str]] = Query(None, description="Lista de categorías de indicadores"),
    user = Depends(require_auth("indicators"))
):
    """Calcular indicadores técnicos (requiere autenticación)."""
    try:
        # Validar parámetros de entrada
        validated_data = input_validator.validate_api_request({
            'symbol': symbol,
            'timeframe': tf,
            'limit': limit,
            'profile': profile,
            'categories': categories
        })
        
        # Obtener datos
        df = fetcher.fetch_ohlcv(
            validated_data['symbol'], 
            validated_data['timeframe'], 
            validated_data['limit']
        )
        
        # Calcular indicadores
        if validated_data.get('profile'):
            ind = ta_service.compute_indicators(df, profile=validated_data['profile'])
        elif validated_data.get('categories'):
            ind = ta_service.compute_indicators(df, categories=validated_data['categories'])
        else:
            ind = ta_service.compute_indicators(df, profile="basic")
            
        return {
            "symbol": validated_data['symbol'], 
            "timeframe": validated_data['timeframe'], 
            "limit": validated_data['limit'],
            "indicators": ind,
            "indicator_count": len(ind) if ind else 0,
            "user": user.get("token_hash", "unknown")
        }
        
    except ValueError as e:
        # Error de validación
        logger.warning(f"Validation error in get_indicators: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error de validación: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error calculating indicators: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error calculando indicadores técnicos"
        )

@app.post("/indicators/custom")
async def get_custom_indicators(
    symbol: str = Query(..., description="Símbolo de la criptomoneda"),
    tf: str = Query(..., description="Timeframe"),
    limit: int = Query(100, ge=1, le=1000, description="Número de candlesticks"),
    request_body: IndicatorRequest = None,
    user = Depends(require_auth("custom-indicators"))
):
    """Calcular indicadores personalizados (requiere autenticación)."""
    try:
        # Validar parámetros base
        validated_data = input_validator.validate_api_request({
            'symbol': symbol,
            'timeframe': tf,
            'limit': limit
        })
        
        # Obtener datos
        df = fetcher.fetch_ohlcv(
            validated_data['symbol'], 
            validated_data['timeframe'], 
            validated_data['limit']
        )
        
        # Calcular indicadores personalizados
        ind = ta_service.compute_indicators(
            df,
            categories=request_body.categories if request_body else None,
            specific_indicators=request_body.specific_indicators if request_body else None,
            profile=request_body.profile if request_body else None
        )
            
        return {
            "symbol": validated_data['symbol'], 
            "timeframe": validated_data['timeframe'], 
            "limit": validated_data['limit'],
            "indicators": ind,
            "indicator_count": len(ind) if ind else 0,
            "request_config": {
                "categories": request_body.categories if request_body else None,
                "specific_indicators": request_body.specific_indicators if request_body else None,
                "profile": request_body.profile if request_body else None
            },
            "user": user.get("token_hash", "unknown")
        }
        
    except ValueError as e:
        logger.warning(f"Validation error in get_custom_indicators: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error de validación: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error calculating custom indicators: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error calculando indicadores personalizados"
        )

@app.get("/strategies")
async def list_strategies(user = Depends(require_auth("strategies"))):
    """Listar estrategias disponibles (requiere autenticación)."""
    try:
        session = SessionLocal()
        rows = session.query(Strategy).all()
        return {
            "strategies": [
                {"id": s.id, "description": s.params.get("description", "")}
                for s in rows
            ],
            "count": len(rows),
            "user": user.get("token_hash", "unknown")
        }
    except Exception as e:
        logger.error(f"Error listing strategies: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error listando estrategias"
        )
    finally:
        session.close()

# =============================================================================
# ENDPOINT DE INFORMACIÓN DE SEGURIDAD
# =============================================================================

@app.get("/security/info")
async def get_security_info():
    """Información sobre las medidas de seguridad implementadas."""
    return {
        "security_features": {
            "authentication": "Bearer Token requerido para endpoints protegidos",
            "rate_limiting": f"{SecurityConfig.RATE_LIMIT_PER_MINUTE} requests/minuto, {SecurityConfig.RATE_LIMIT_PER_HOUR} requests/hora",
            "input_validation": "Validación y sanitización de todos los parámetros",
            "cors_protection": f"CORS restringido a {len(SecurityConfig.ALLOWED_ORIGINS)} orígenes específicos",
            "security_headers": "Headers de seguridad HTTP estándar aplicados",
            "payload_limits": f"Máximo {SecurityConfig.MAX_PAYLOAD_SIZE // 1024} KB por request"
        },
        "endpoints": {
            "public": ["/health", "/health/detailed", "/security/info"],
            "protected": ["/db-test", "/available-indicators", "/indicator-profiles", "/indicators", "/indicators/custom", "/strategies"]
        },
        "rate_limits": {
            "per_minute": SecurityConfig.RATE_LIMIT_PER_MINUTE,
            "per_hour": SecurityConfig.RATE_LIMIT_PER_HOUR,
            "per_day": SecurityConfig.RATE_LIMIT_PER_DAY,
            "burst": SecurityConfig.RATE_LIMIT_BURST
        }
    }

if __name__ == "__main__":
    import uvicorn
    
    logger.info("🚀 Iniciando servidor backend securizado...")
    uvicorn.run(
        "main_secure:app",
        host="0.0.0.0",
        port=int(os.getenv("BACKEND_PORT", "8000")),
        reload=False,  # Deshabilitado en producción por seguridad
        access_log=True,
        log_level="info"
    ) 