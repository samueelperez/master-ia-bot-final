"""
Configuración de seguridad centralizada para el módulo AI.
Separación clara de responsabilidades de configuración.
"""

import os
import logging
from typing import List

logger = logging.getLogger(__name__)


class SecurityConfig:
    """Configuración de seguridad centralizada."""
    
    # Rate limiting (requests por minuto)
    RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
    RATE_LIMIT_PER_HOUR = int(os.getenv("RATE_LIMIT_PER_HOUR", "1000"))
    RATE_LIMIT_BURST = int(os.getenv("RATE_LIMIT_BURST", "10"))
    
    # Timeouts seguros
    HTTP_TIMEOUT = int(os.getenv("HTTP_TIMEOUT", "15"))
    OPENAI_TIMEOUT = int(os.getenv("OPENAI_TIMEOUT", "30"))
    DATABASE_TIMEOUT = int(os.getenv("DATABASE_TIMEOUT", "10"))
    
    # CORS restrictivo
    ALLOWED_ORIGINS = os.getenv(
        "ALLOWED_ORIGINS", 
        "http://localhost:3000,http://localhost:8080"
    ).split(",")
    
    # API Keys y secretos
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    API_SECRET_KEY = os.getenv("API_SECRET_KEY", "change-me-in-production")
    
    # Hosts permitidos
    ALLOWED_HOSTS = os.getenv(
        "ALLOWED_HOSTS", 
        "localhost,127.0.0.1"
    ).split(",")
    
    # Configuración de logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_DIR = os.getenv("LOG_DIR", "logs")
    
    # Configuración de validación
    MAX_PROMPT_LENGTH = int(os.getenv("MAX_PROMPT_LENGTH", "1000"))
    MAX_SYMBOLS_PER_REQUEST = int(os.getenv("MAX_SYMBOLS_PER_REQUEST", "5"))
    MAX_CONVERSATION_HISTORY = int(os.getenv("MAX_CONVERSATION_HISTORY", "10"))
    
    @classmethod
    def validate_config(cls) -> None:
        """Validar configuración crítica al inicio."""
        errors = []
        warnings = []
        
        # Validaciones críticas (no forzar OPENAI_API_KEY en desarrollo)
        if cls.is_production() and not cls.OPENAI_API_KEY:
            errors.append("OPENAI_API_KEY es requerida en producción")
        elif not cls.OPENAI_API_KEY:
            warnings.append("⚠️ OPENAI_API_KEY no configurada - funcionalidad de IA limitada")
        
        if cls.RATE_LIMIT_PER_MINUTE <= 0:
            errors.append("RATE_LIMIT_PER_MINUTE debe ser mayor a 0")
        
        if cls.HTTP_TIMEOUT <= 0:
            errors.append("HTTP_TIMEOUT debe ser mayor a 0")
        
        # Validaciones de seguridad
        if cls.API_SECRET_KEY == "change-me-in-production":
            if cls.is_production():
                errors.append("API_SECRET_KEY debe cambiarse en producción")
            else:
                warnings.append("⚠️ Usando API_SECRET_KEY por defecto. Cambiar en producción!")
        
        if "*" in cls.ALLOWED_ORIGINS:
            warnings.append("⚠️ CORS permite todos los orígenes - no recomendado para producción")
        
        if "localhost" in cls.ALLOWED_HOSTS and cls.is_production():
            warnings.append("⚠️ localhost permitido en producción")
        
        # Log de errores y warnings
        for warning in warnings:
            logger.warning(warning)
        
        if errors:
            error_msg = "; ".join(errors)
            logger.error(f"Errores de configuración críticos: {error_msg}")
            raise RuntimeError(f"Configuración inválida: {error_msg}")
        
        logger.info("✅ Configuración de seguridad validada correctamente")
    
    @classmethod
    def get_cors_config(cls) -> dict:
        """Obtener configuración CORS."""
        return {
            "allow_origins": cls.ALLOWED_ORIGINS,
            "allow_credentials": True,
            "allow_methods": ["GET", "POST", "PUT", "DELETE"],
            "allow_headers": ["*"],
        }
    
    @classmethod
    def is_production(cls) -> bool:
        """Verificar si estamos en producción."""
        return os.getenv("ENVIRONMENT", "development").lower() == "production"
    
    @classmethod
    def get_log_config(cls) -> dict:
        """Obtener configuración de logging."""
        return {
            "level": cls.LOG_LEVEL,
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "dir": cls.LOG_DIR
        }


class ValidationConfig:
    """Configuración para validación de entrada."""
    
    ALLOWED_SYMBOLS = {
        'BTC', 'ETH', 'ADA', 'DOT', 'SOL', 'MATIC', 'AVAX', 'LINK', 'UNI', 'AAVE',
        'ATOM', 'ALGO', 'XRP', 'LTC', 'BCH', 'ETC', 'XLM', 'VET', 'TRX', 'FIL',
        'THETA', 'XTZ', 'EOS', 'NEO', 'IOTA', 'DASH', 'ZEC', 'XMR', 'QTUM', 'ONT',
        'ICX', 'ZIL', 'BAT', 'ENJ', 'REN', 'KNC', 'USDT', 'USDC', 'BUSD', 'DAI',
        'JASMY'
    }
    
    ALLOWED_TIMEFRAMES = {'1m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '8h', '12h', '1d', '3d', '1w', '1M'}
    
    DANGEROUS_PATTERNS = [
        r'<script.*?>.*?</script>',  # XSS scripts
        r'javascript:',             # JavaScript protocol
        r'on\w+\s*=',              # Event handlers
        r'eval\s*\(',              # eval calls
        r'exec\s*\(',              # exec calls
        r'\bselect\b.*\bfrom\b',   # SQL SELECT
        r'\binsert\b.*\binto\b',   # SQL INSERT
        r'\bupdate\b.*\bset\b',    # SQL UPDATE
        r'\bdelete\b.*\bfrom\b',   # SQL DELETE
        r'\bdrop\b.*\btable\b',    # SQL DROP
        r'\bunion\b.*\bselect\b',  # SQL UNION
        r'\.\./',                  # Path traversal
        r'\|\s*\w+',              # Command injection
        r'&&\s*\w+',              # Command chaining
        # r';\s*\w+',               # Command termination - Desactivado temporalmente
    ]
    
    @classmethod
    def get_symbol_validation_pattern(cls) -> str:
        """Obtener patrón regex para validación de símbolos."""
        return r'^[A-Z]{2,10}$'
    
    @classmethod
    def get_timeframe_validation_pattern(cls) -> str:
        """Obtener patrón regex para validación de timeframes."""
        return r'^(1|5|15|30)m|(1|2|4|6|8|12)h|(1|3)d|1w|1M$'


# Inicializar y validar configuración al importar
SecurityConfig.validate_config()
