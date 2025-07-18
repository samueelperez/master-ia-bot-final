"""
Configuración de seguridad centralizada para el módulo Backend.
Incluye validación de entrada, rate limiting y configuraciones seguras.
"""

import os
import logging
from typing import List, Dict, Set, Optional
from pydantic import BaseModel, Field, validator
import hashlib
import secrets

# Configurar logging
logger = logging.getLogger(__name__)

class SecurityConfig:
    """Configuración principal de seguridad para el backend."""
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE = int(os.getenv("BACKEND_RATE_LIMIT_PER_MINUTE", "60"))
    RATE_LIMIT_PER_HOUR = int(os.getenv("BACKEND_RATE_LIMIT_PER_HOUR", "1000"))
    RATE_LIMIT_PER_DAY = int(os.getenv("BACKEND_RATE_LIMIT_PER_DAY", "10000"))
    RATE_LIMIT_BURST = int(os.getenv("BACKEND_RATE_LIMIT_BURST", "10"))
    
    # Timeouts
    HTTP_TIMEOUT = int(os.getenv("BACKEND_HTTP_TIMEOUT", "30"))
    DB_TIMEOUT = int(os.getenv("BACKEND_DB_TIMEOUT", "10"))
    CCXT_TIMEOUT = int(os.getenv("BACKEND_CCXT_TIMEOUT", "15"))
    
    # CORS y Orígenes
    ALLOWED_ORIGINS = os.getenv(
        "BACKEND_ALLOWED_ORIGINS", 
        "http://localhost:3000,http://127.0.0.1:3000"
    ).split(",")
    ALLOWED_HOSTS = os.getenv(
        "BACKEND_ALLOWED_HOSTS",
        "localhost,127.0.0.1"
    ).split(",")
    
    # Autenticación
    API_SECRET_KEY = os.getenv("BACKEND_API_SECRET_KEY", None)
    if not API_SECRET_KEY:
        API_SECRET_KEY = secrets.token_urlsafe(32)
        logger.warning("⚠️ Usando API_SECRET_KEY generada. Configurar BACKEND_API_SECRET_KEY en producción!")
    
    # Límites de datos
    MAX_LIMIT_OHLCV = int(os.getenv("BACKEND_MAX_LIMIT_OHLCV", "1000"))
    MAX_INDICATORS_PER_REQUEST = int(os.getenv("BACKEND_MAX_INDICATORS_PER_REQUEST", "50"))
    MAX_PAYLOAD_SIZE = int(os.getenv("BACKEND_MAX_PAYLOAD_SIZE", "1048576"))  # 1MB
    
    # Exchange configuración
    DEFAULT_EXCHANGE = os.getenv("BACKEND_DEFAULT_EXCHANGE", "binance")
    EXCHANGE_SANDBOX = os.getenv("BACKEND_EXCHANGE_SANDBOX", "false").lower() == "true"
    
    # Símbolos permitidos (definidos directamente para evitar circular imports)
    ALLOWED_SYMBOLS: Set[str] = {
        'BTC', 'ETH', 'BNB', 'ADA', 'SOL', 'XRP', 'DOT', 'DOGE', 'AVAX', 'SHIB',
        'MATIC', 'UNI', 'ATOM', 'LTC', 'LINK', 'BCH', 'XLM', 'ALGO', 'VET', 'FIL',
        'TRX', 'ETC', 'THETA', 'XMR', 'CAKE', 'AAVE', 'GRT', 'MKR', 'COMP', 'SUSHI',
        'YFI', 'SNX', 'CRV', 'BAL', 'REN', 'KNC', 'ZRX', 'BAND', 'STORJ', 'ENJ'
    }
    
    @classmethod
    def validate_config(cls):
        """Validar configuración de seguridad."""
        try:
            # Verificar que los valores críticos estén configurados
            if cls.RATE_LIMIT_PER_MINUTE <= 0:
                raise ValueError("RATE_LIMIT_PER_MINUTE debe ser mayor que 0")
            
            if cls.HTTP_TIMEOUT <= 0:
                raise ValueError("HTTP_TIMEOUT debe ser mayor que 0")
            
            if not cls.ALLOWED_ORIGINS:
                raise ValueError("ALLOWED_ORIGINS no puede estar vacío")
            
            # Verificar que API_SECRET_KEY sea suficientemente segura
            if len(cls.API_SECRET_KEY) < 32:
                logger.warning("⚠️ API_SECRET_KEY muy corta - usar al menos 32 caracteres")
            
            logger.info("✅ Configuración de seguridad validada correctamente")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error validando configuración: {e}")
            raise


class ValidationConfig:
    """Configuración para validación de entrada."""
    
    # Símbolos permitidos para trading
    ALLOWED_SYMBOLS: Set[str] = {
        'BTC', 'ETH', 'BNB', 'ADA', 'SOL', 'XRP', 'DOT', 'DOGE', 'AVAX', 'SHIB',
        'MATIC', 'UNI', 'ATOM', 'LTC', 'LINK', 'BCH', 'XLM', 'ALGO', 'VET', 'FIL',
        'TRX', 'ETC', 'THETA', 'XMR', 'CAKE', 'AAVE', 'GRT', 'MKR', 'COMP', 'SUSHI',
        'YFI', 'SNX', 'CRV', 'BAL', 'REN', 'KNC', 'ZRX', 'BAND', 'STORJ', 'ENJ'
    }
    
    # Timeframes permitidos
    ALLOWED_TIMEFRAMES: Set[str] = {
        '1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '8h', '12h', '1d', '3d', '1w', '1M'
    }
    
    # Categorías de indicadores válidas
    ALLOWED_INDICATOR_CATEGORIES: Set[str] = {
        'trend', 'momentum', 'volatility', 'volume', 'support_resistance', 'patterns'
    }
    
    # Perfiles de indicadores válidos
    ALLOWED_INDICATOR_PROFILES: Set[str] = {
        'basic', 'intermediate', 'advanced'
    }
    
    # Patrones peligrosos para detectar inyección
    DANGEROUS_PATTERNS = [
        r'<script[^>]*>.*?</script>',  # XSS
        r'javascript:',  # JavaScript injection
        r'on\w+\s*=',  # Event handlers
        r'expression\s*\(',  # CSS expression
        r'import\s+',  # Python imports
        r'exec\s*\(',  # Code execution
        r'eval\s*\(',  # Eval injection
        r'__.*__',  # Python magic methods
        r'\.\./',  # Path traversal
        r'[\'"]\s*;\s*\w+',  # SQL injection patterns
        r'UNION\s+SELECT',  # SQL UNION
        r'DROP\s+TABLE'  # SQL DROP
    ]


class APIRequest(BaseModel):
    """Modelo base para requests de API con validación."""
    
    symbol: str = Field(..., min_length=2, max_length=10)
    timeframe: str = Field(..., min_length=2, max_length=3)
    limit: int = Field(default=100, ge=1, le=1000)
    
    @validator('symbol')
    def validate_symbol(cls, v):
        """Validar símbolo de criptomoneda."""
        symbol_upper = v.upper().replace('-USD', '').replace('/USDT', '').replace('-USDT', '')
        
        if symbol_upper not in ValidationConfig.ALLOWED_SYMBOLS:
            raise ValueError(f"Símbolo no permitido: {v}. Símbolos válidos: {', '.join(sorted(ValidationConfig.ALLOWED_SYMBOLS))}")
        
        return symbol_upper
    
    @validator('timeframe')
    def validate_timeframe(cls, v):
        """Validar timeframe."""
        if v not in ValidationConfig.ALLOWED_TIMEFRAMES:
            raise ValueError(f"Timeframe no permitido: {v}. Timeframes válidos: {', '.join(sorted(ValidationConfig.ALLOWED_TIMEFRAMES))}")
        
        return v
    
    @validator('limit')
    def validate_limit(cls, v):
        """Validar límite de datos."""
        max_limit = SecurityConfig.MAX_LIMIT_OHLCV
        if v > max_limit:
            raise ValueError(f"Límite excedido: {v}. Máximo permitido: {max_limit}")
        
        return v


class IndicatorRequest(APIRequest):
    """Request para indicadores técnicos con validación adicional."""
    
    categories: Optional[List[str]] = Field(None, max_items=10)
    specific_indicators: Optional[Dict[str, List[str]]] = Field(None)
    profile: Optional[str] = Field(None, min_length=3, max_length=20)
    
    @validator('categories')
    def validate_categories(cls, v):
        """Validar categorías de indicadores."""
        if v is None:
            return v
        
        for category in v:
            if category not in ValidationConfig.ALLOWED_INDICATOR_CATEGORIES:
                raise ValueError(f"Categoría no válida: {category}")
        
        return v
    
    @validator('profile')
    def validate_profile(cls, v):
        """Validar perfil de indicadores."""
        if v is None:
            return v
        
        if v not in ValidationConfig.ALLOWED_INDICATOR_PROFILES:
            raise ValueError(f"Perfil no válido: {v}")
        
        return v
    
    @validator('specific_indicators')
    def validate_specific_indicators(cls, v):
        """Validar indicadores específicos."""
        if v is None:
            return v
        
        max_indicators = SecurityConfig.MAX_INDICATORS_PER_REQUEST
        total_indicators = sum(len(indicators) for indicators in v.values())
        
        if total_indicators > max_indicators:
            raise ValueError(f"Demasiados indicadores: {total_indicators}. Máximo: {max_indicators}")
        
        return v


class SecurityHeaders:
    """Headers de seguridad HTTP estándar."""
    
    # Headers como atributos de clase para fácil acceso
    X_CONTENT_TYPE_OPTIONS = "nosniff"
    X_FRAME_OPTIONS = "DENY"
    X_XSS_PROTECTION = "1; mode=block"
    STRICT_TRANSPORT_SECURITY = "max-age=31536000; includeSubDomains"
    CONTENT_SECURITY_POLICY = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
    REFERRER_POLICY = "strict-origin-when-cross-origin"
    PERMISSIONS_POLICY = "geolocation=(), microphone=(), camera=()"
    X_PERMITTED_CROSS_DOMAIN_POLICIES = "none"
    CACHE_CONTROL = "no-store, no-cache, must-revalidate, max-age=0"
    
    @staticmethod
    def get_security_headers() -> Dict[str, str]:
        """Obtener headers de seguridad recomendados."""
        return {
            "X-Content-Type-Options": SecurityHeaders.X_CONTENT_TYPE_OPTIONS,
            "X-Frame-Options": SecurityHeaders.X_FRAME_OPTIONS,
            "X-XSS-Protection": SecurityHeaders.X_XSS_PROTECTION,
            "Strict-Transport-Security": SecurityHeaders.STRICT_TRANSPORT_SECURITY,
            "Content-Security-Policy": SecurityHeaders.CONTENT_SECURITY_POLICY,
            "Referrer-Policy": SecurityHeaders.REFERRER_POLICY,
            "Permissions-Policy": SecurityHeaders.PERMISSIONS_POLICY,
            "X-Permitted-Cross-Domain-Policies": SecurityHeaders.X_PERMITTED_CROSS_DOMAIN_POLICIES,
            "Cache-Control": SecurityHeaders.CACHE_CONTROL
        }


def hash_token(token: str) -> str:
    """Hash seguro de tokens para verificación."""
    return hashlib.sha256(token.encode()).hexdigest()


def generate_api_key() -> str:
    """Generar API key segura."""
    return secrets.token_urlsafe(32)


# Inicializar configuración al importar
try:
    SecurityConfig.validate_config()
except Exception as e:
    logger.error(f"Error inicializando configuración de seguridad: {e}")
    raise 