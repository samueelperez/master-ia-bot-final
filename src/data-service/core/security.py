"""
Sistema completo de seguridad para validación robusta de dependencias externas.
Implementa protecciones contra múltiples vectores de ataque y vulnerabilidades.
"""

import re
import hashlib
import secrets
import logging
import time
import json
from typing import Dict, List, Any, Optional, Union, Callable
from datetime import datetime, timedelta
from urllib.parse import urlparse
import ipaddress

from fastapi import HTTPException, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
import httpx
from pydantic import BaseModel, validator, ValidationError

from core.config import settings

logger = logging.getLogger(__name__)

# ============================================
# MODELOS DE VALIDACIÓN ROBUSTA
# ============================================

class SecureAPIRequest(BaseModel):
    """Modelo base para validación segura de requests a APIs externas."""
    
    symbol: Optional[str] = None
    timeframe: Optional[str] = None
    limit: Optional[int] = None
    
    @validator('symbol')
    def validate_symbol(cls, v):
        """Validar símbolo de criptomoneda."""
        if v is None:
            return v
        
        # Verificar formato básico
        if not re.match(r'^[A-Z0-9]{2,10}$', v.upper()):
            raise ValueError("Símbolo debe contener solo letras/números mayúsculas, 2-10 caracteres")
        
        # Lista blanca de símbolos conocidos
        known_symbols = {
            'BTC', 'ETH', 'BNB', 'XRP', 'ADA', 'SOL', 'DOT', 'DOGE', 
            'AVAX', 'SHIB', 'MATIC', 'LTC', 'UNI', 'LINK', 'ATOM',
            'XLM', 'BCH', 'ALGO', 'ICP', 'VET', 'FIL', 'TRX', 'MANA',
            'SAND', 'AXS', 'THETA', 'HBAR', 'EOS', 'AAVE', 'MKR',
            'COMP', 'YFI', 'SNX', 'CRV', 'BAL', 'ZEC', 'DASH', 'NEO'
        }
        
        if v.upper() not in known_symbols:
            logger.warning(f"Símbolo no reconocido: {v}")
            # Permitir pero registrar para análisis
        
        return v.upper()
    
    @validator('timeframe')
    def validate_timeframe(cls, v):
        """Validar timeframe."""
        if v is None:
            return v
        
        valid_timeframes = {'1m', '5m', '15m', '30m', '1h', '4h', '1d', '1w', '1M'}
        if v not in valid_timeframes:
            raise ValueError(f"Timeframe inválido. Válidos: {valid_timeframes}")
        
        return v
    
    @validator('limit')
    def validate_limit(cls, v):
        """Validar límite de resultados."""
        if v is None:
            return v
        
        if not isinstance(v, int):
            raise ValueError("Límite debe ser un número entero")
        
        if v < 1 or v > 10000:
            raise ValueError("Límite debe estar entre 1 y 10000")
        
        return v

class URLValidator:
    """Validador de URLs para prevenir SSRF y otros ataques."""
    
    # IPs y dominios bloqueados
    BLOCKED_IPS = {
        '127.0.0.1', '0.0.0.0', 'localhost',
        '169.254.169.254',  # AWS metadata
        '::1', '0000:0000:0000:0000:0000:0000:0000:0001'
    }
    
    BLOCKED_DOMAINS = {
        'metadata.google.internal',
        'metadata.azure.com',
        'metadata.aws.amazon.com'
    }
    
    ALLOWED_SCHEMES = {'http', 'https'}
    
    @classmethod
    def validate_url(cls, url: str) -> bool:
        """
        Validar URL para prevenir SSRF.
        
        Args:
            url: URL a validar
            
        Returns:
            True si la URL es segura
            
        Raises:
            ValueError: Si la URL es insegura
        """
        try:
            parsed = urlparse(url)
        except Exception:
            raise ValueError("URL malformada")
        
        # Verificar esquema
        if parsed.scheme not in cls.ALLOWED_SCHEMES:
            raise ValueError(f"Esquema no permitido: {parsed.scheme}")
        
        # Verificar dominio
        hostname = parsed.hostname
        if not hostname:
            raise ValueError("Hostname vacío")
        
        # Verificar dominios bloqueados
        if hostname in cls.BLOCKED_DOMAINS:
            raise ValueError(f"Dominio bloqueado: {hostname}")
        
        # Verificar IPs bloqueadas
        try:
            ip = ipaddress.ip_address(hostname)
            
            # Bloquear IPs privadas y loopback
            if ip.is_private or ip.is_loopback or ip.is_multicast:
                raise ValueError(f"IP no permitida: {hostname}")
            
            # Verificar lista negra específica
            if str(ip) in cls.BLOCKED_IPS:
                raise ValueError(f"IP bloqueada: {hostname}")
                
        except ipaddress.AddressValueError:
            # No es una IP, es un dominio - está bien
            pass
        
        return True

# ============================================
# RATE LIMITING AVANZADO
# ============================================

class RateLimiter:
    """Sistema avanzado de rate limiting con múltiples estrategias."""
    
    def __init__(self):
        self.requests: Dict[str, List[float]] = {}
        self.blocked_ips: Dict[str, float] = {}
        
        # Configuración de límites
        self.limits = {
            'per_minute': 60,
            'per_hour': 1000,
            'per_day': 10000,
            'burst': 10  # Ráfaga máxima en 1 segundo
        }
        
        # Tiempo de bloqueo (en segundos)
        self.block_duration = 300  # 5 minutos
    
    def is_allowed(self, identifier: str, endpoint: str = "") -> bool:
        """
        Verificar si una request está permitida.
        
        Args:
            identifier: IP o identificador único del cliente
            endpoint: Endpoint específico (para límites diferenciados)
            
        Returns:
            True si está permitido, False si excede límites
        """
        current_time = time.time()
        
        # Verificar si está bloqueado
        if identifier in self.blocked_ips:
            if current_time < self.blocked_ips[identifier]:
                logger.warning(f"Cliente bloqueado: {identifier}")
                return False
            else:
                # Remover del bloqueo
                del self.blocked_ips[identifier]
        
        # Inicializar si es nuevo
        if identifier not in self.requests:
            self.requests[identifier] = []
        
        # Limpiar requests antiguas (más de 1 día)
        day_ago = current_time - 86400
        self.requests[identifier] = [
            req_time for req_time in self.requests[identifier] 
            if req_time > day_ago
        ]
        
        # Verificar límites
        recent_requests = self.requests[identifier]
        
        # Límite de ráfaga (último segundo)
        burst_requests = [r for r in recent_requests if r > current_time - 1]
        if len(burst_requests) >= self.limits['burst']:
            self._block_client(identifier, "burst limit exceeded")
            return False
        
        # Límite por minuto
        minute_requests = [r for r in recent_requests if r > current_time - 60]
        if len(minute_requests) >= self.limits['per_minute']:
            self._block_client(identifier, "per-minute limit exceeded")
            return False
        
        # Límite por hora
        hour_requests = [r for r in recent_requests if r > current_time - 3600]
        if len(hour_requests) >= self.limits['per_hour']:
            self._block_client(identifier, "per-hour limit exceeded")
            return False
        
        # Límite por día
        if len(recent_requests) >= self.limits['per_day']:
            self._block_client(identifier, "per-day limit exceeded")
            return False
        
        # Registrar la request
        self.requests[identifier].append(current_time)
        
        return True
    
    def _block_client(self, identifier: str, reason: str):
        """Bloquear cliente temporalmente."""
        block_until = time.time() + self.block_duration
        self.blocked_ips[identifier] = block_until
        
        logger.warning(f"Cliente bloqueado por {self.block_duration}s: {identifier} - {reason}")

# ============================================
# SANITIZACIÓN Y VALIDACIÓN DE ENTRADA
# ============================================

class InputSanitizer:
    """Sanitizador avanzado de entradas para prevenir inyecciones."""
    
    # Patrones peligrosos
    DANGEROUS_PATTERNS = [
        r'<script[^>]*>.*?</script>',  # XSS básico
        r'javascript:',  # URLs javascript
        r'data:text/html',  # Data URLs peligrosas
        r'vbscript:',  # VBScript
        r'on\w+\s*=',  # Event handlers
        r'expression\s*\(',  # CSS expressions
        r'<\s*iframe',  # iframes
        r'<\s*object',  # objects
        r'<\s*embed',   # embeds
        r'<\s*link',    # links externos
        r'<\s*meta',    # meta tags
        r'<\s*base',    # base tags
    ]
    
    # Patrones de inyección SQL
    SQL_INJECTION_PATTERNS = [
        r'(union\s+select)',
        r'(select\s+\*\s+from)',
        r'(insert\s+into)',
        r'(delete\s+from)',
        r'(update\s+\w+\s+set)',
        r'(drop\s+table)',
        r'(drop\s+database)',
        r'(\bor\b\s+\d+\s*=\s*\d+)',
        r'(\band\b\s+\d+\s*=\s*\d+)',
        r'(\/\*.*?\*\/)',  # SQL comments
        r'(--\s.*)',      # SQL comments
        r'(\bexec\s*\()',  # Execute functions
    ]
    
    @classmethod
    def sanitize_string(cls, value: str, context: str = "general") -> str:
        """
        Sanitizar string de entrada.
        
        Args:
            value: Valor a sanitizar
            context: Contexto de uso (general, sql, html, etc.)
            
        Returns:
            String sanitizado
            
        Raises:
            ValueError: Si se detectan patrones peligrosos
        """
        if not isinstance(value, str):
            raise ValueError("El valor debe ser un string")
        
        # Verificar longitud
        if len(value) > 10000:
            raise ValueError("Input demasiado largo")
        
        # Normalizar
        normalized = value.strip().lower()
        
        # Verificar patrones peligrosos
        for pattern in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, normalized, re.IGNORECASE):
                logger.warning(f"Patrón peligroso detectado: {pattern} en '{value[:50]}...'")
                raise ValueError("Input contiene contenido peligroso")
        
        # Verificar inyección SQL si es contexto SQL
        if context in ['sql', 'database']:
            for pattern in cls.SQL_INJECTION_PATTERNS:
                if re.search(pattern, normalized, re.IGNORECASE):
                    logger.warning(f"Posible inyección SQL: {pattern} en '{value[:50]}...'")
                    raise ValueError("Input contiene posible inyección SQL")
        
        # Escapar caracteres HTML
        if context == 'html':
            value = value.replace('&', '&amp;')
            value = value.replace('<', '&lt;')
            value = value.replace('>', '&gt;')
            value = value.replace('"', '&quot;')
            value = value.replace("'", '&#x27;')
        
        return value
    
    @classmethod
    def validate_json_payload(cls, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validar y sanitizar payload JSON.
        
        Args:
            payload: Payload JSON
            
        Returns:
            Payload sanitizado
        """
        if not isinstance(payload, dict):
            raise ValueError("Payload debe ser un objeto JSON")
        
        # Límite de tamaño del payload
        payload_str = json.dumps(payload)
        if len(payload_str) > 100000:  # 100KB
            raise ValueError("Payload demasiado grande")
        
        # Verificar profundidad máxima
        def check_depth(obj, max_depth=10, current_depth=0):
            if current_depth > max_depth:
                raise ValueError("Payload tiene demasiada profundidad de anidación")
            
            if isinstance(obj, dict):
                for value in obj.values():
                    check_depth(value, max_depth, current_depth + 1)
            elif isinstance(obj, list):
                for item in obj:
                    check_depth(item, max_depth, current_depth + 1)
        
        check_depth(payload)
        
        # Sanitizar strings en el payload
        def sanitize_payload(obj):
            if isinstance(obj, dict):
                return {
                    cls.sanitize_string(str(k)): sanitize_payload(v)
                    for k, v in obj.items()
                    if not str(k).startswith('_')  # Filtrar campos privados
                }
            elif isinstance(obj, list):
                return [sanitize_payload(item) for item in obj[:1000]]  # Límite de items
            elif isinstance(obj, str):
                return cls.sanitize_string(obj)
            else:
                return obj
        
        return sanitize_payload(payload)

# ============================================
# HEADERS DE SEGURIDAD
# ============================================

class SecurityHeaders:
    """Generador de headers de seguridad HTTP."""
    
    @staticmethod
    def get_security_headers() -> Dict[str, str]:
        """
        Obtener headers de seguridad recomendados.
        
        Returns:
            Diccionario con headers de seguridad
        """
        return {
            # Protección XSS
            'X-XSS-Protection': '1; mode=block',
            
            # Prevenir MIME type sniffing
            'X-Content-Type-Options': 'nosniff',
            
            # Protección clickjacking
            'X-Frame-Options': 'DENY',
            
            # HSTS (solo HTTPS)
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
            
            # CSP básico
            'Content-Security-Policy': (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "connect-src 'self'; "
                "font-src 'self'; "
                "object-src 'none'; "
                "media-src 'self'; "
                "frame-src 'none';"
            ),
            
            # Referrer policy
            'Referrer-Policy': 'strict-origin-when-cross-origin',
            
            # Permissions policy
            'Permissions-Policy': (
                'camera=(), microphone=(), geolocation=(), '
                'gyroscope=(), magnetometer=(), payment=()'
            ),
            
            # Cache control para endpoints sensibles
            'Cache-Control': 'no-store, no-cache, must-revalidate, private',
            'Pragma': 'no-cache',
            'Expires': '0',
        }

# ============================================
# MIDDLEWARE DE SEGURIDAD
# ============================================

class SecurityMiddleware(BaseHTTPMiddleware):
    """Middleware de seguridad integral."""
    
    def __init__(self, app, rate_limiter: RateLimiter = None):
        super().__init__(app)
        self.rate_limiter = rate_limiter or RateLimiter()
        self.security_headers = SecurityHeaders()
    
    async def dispatch(self, request: Request, call_next):
        """Procesar request con validaciones de seguridad."""
        start_time = time.time()
        
        # 1. Obtener IP del cliente
        client_ip = self._get_client_ip(request)
        
        # 2. Rate limiting
        if not self.rate_limiter.is_allowed(client_ip, str(request.url.path)):
            return Response(
                content=json.dumps({"error": "Rate limit exceeded"}),
                status_code=429,
                media_type="application/json"
            )
        
        # 3. Validar método HTTP
        if request.method not in ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'HEAD']:
            return Response(
                content=json.dumps({"error": "Method not allowed"}),
                status_code=405,
                media_type="application/json"
            )
        
        # 4. Validar headers
        self._validate_headers(request)
        
        # 5. Procesar request
        try:
            response = await call_next(request)
        except Exception as e:
            logger.error(f"Error procesando request: {e}")
            response = Response(
                content=json.dumps({"error": "Internal server error"}),
                status_code=500,
                media_type="application/json"
            )
        
        # 6. Añadir headers de seguridad
        security_headers = self.security_headers.get_security_headers()
        for header_name, header_value in security_headers.items():
            response.headers[header_name] = header_value
        
        # 7. Log de auditoría
        processing_time = time.time() - start_time
        logger.info(
            f"Request processed: {client_ip} {request.method} {request.url.path} "
            f"-> {response.status_code} ({processing_time:.3f}s)"
        )
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Obtener IP real del cliente."""
        # Verificar headers de proxy
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            # Tomar la primera IP (la del cliente original)
            return forwarded_for.split(',')[0].strip()
        
        real_ip = request.headers.get('X-Real-IP')
        if real_ip:
            return real_ip.strip()
        
        # Fallback a IP de conexión directa
        if request.client:
            return request.client.host
        
        return "unknown"
    
    def _validate_headers(self, request: Request):
        """Validar headers de la request."""
        # Verificar User-Agent (bloquear bots conocidos)
        user_agent = request.headers.get('User-Agent', '').lower()
        
        blocked_agents = ['sqlmap', 'nikto', 'nmap', 'masscan', 'zap']
        if any(agent in user_agent for agent in blocked_agents):
            raise HTTPException(status_code=403, detail="Forbidden user agent")
        
        # Verificar Content-Type para requests con body
        if request.method in ['POST', 'PUT', 'PATCH']:
            content_type = request.headers.get('Content-Type', '')
            allowed_types = [
                'application/json',
                'application/x-www-form-urlencoded',
                'multipart/form-data'
            ]
            
            if not any(ct in content_type for ct in allowed_types):
                raise HTTPException(status_code=400, detail="Invalid content type")

# ============================================
# INSTANCIAS GLOBALES
# ============================================

# Instancias singleton
rate_limiter = RateLimiter()
input_sanitizer = InputSanitizer()
url_validator = URLValidator()

# ============================================
# FUNCIONES DE UTILIDAD
# ============================================

def validate_external_request(data: Dict[str, Any]) -> SecureAPIRequest:
    """
    Validar request a API externa de forma robusta.
    
    Args:
        data: Datos de la request
        
    Returns:
        Request validado
        
    Raises:
        HTTPException: Si la validación falla
    """
    try:
        # Sanitizar payload
        sanitized_data = input_sanitizer.validate_json_payload(data)
        
        # Validar con Pydantic
        validated_request = SecureAPIRequest(**sanitized_data)
        
        return validated_request
        
    except ValidationError as e:
        logger.warning(f"Validación fallida: {e}")
        raise HTTPException(status_code=400, detail=f"Datos inválidos: {e}")
    except ValueError as e:
        logger.warning(f"Valor inválido: {e}")
        raise HTTPException(status_code=400, detail=str(e))

async def secure_external_call(
    url: str,
    method: str = "GET",
    params: Optional[Dict] = None,
    data: Optional[Dict] = None,
    headers: Optional[Dict] = None,
    timeout: int = 10
) -> Dict[str, Any]:
    """
    Realizar llamada externa segura con todas las validaciones.
    
    Args:
        url: URL de destino
        method: Método HTTP
        params: Parámetros de query
        data: Datos del body
        headers: Headers adicionales
        timeout: Timeout en segundos
        
    Returns:
        Respuesta de la API
        
    Raises:
        HTTPException: Si hay errores de seguridad o conectividad
    """
    try:
        # 1. Validar URL
        url_validator.validate_url(url)
        
        # 2. Preparar headers seguros
        safe_headers = {
            'User-Agent': 'CryptoAI-Bot/1.0',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        
        if headers:
            # Filtrar headers peligrosos
            safe_header_names = {
                'authorization', 'x-api-key', 'content-type',
                'accept', 'user-agent', 'accept-encoding'
            }
            
            for key, value in headers.items():
                if key.lower() in safe_header_names:
                    safe_headers[key] = str(value)[:1000]  # Límite de longitud
        
        # 3. Sanitizar parámetros
        if params:
            safe_params = {}
            for key, value in params.items():
                if len(str(key)) <= 100 and len(str(value)) <= 1000:
                    safe_params[input_sanitizer.sanitize_string(str(key))] = \
                        input_sanitizer.sanitize_string(str(value))
            params = safe_params
        
        # 4. Sanitizar data
        if data:
            data = input_sanitizer.validate_json_payload(data)
        
        # 5. Realizar llamada con timeout y límites
        async with httpx.AsyncClient(
            timeout=min(timeout, 30),  # Máximo 30 segundos
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5)
        ) as client:
            
            response = await client.request(
                method=method.upper(),
                url=url,
                params=params,
                json=data,
                headers=safe_headers
            )
            
            # 6. Validar respuesta
            if response.status_code >= 400:
                logger.warning(f"API externa retornó error {response.status_code}: {url}")
                raise HTTPException(
                    status_code=502,
                    detail=f"Error en API externa: {response.status_code}"
                )
            
            # 7. Limitar tamaño de respuesta
            content_length = response.headers.get('content-length')
            if content_length and int(content_length) > 10_000_000:  # 10MB
                raise HTTPException(status_code=413, detail="Respuesta demasiado grande")
            
            # 8. Parsear y validar JSON
            try:
                result = response.json()
                
                # Validar que no sea demasiado grande
                if len(str(result)) > 10_000_000:  # 10MB como string
                    raise HTTPException(status_code=413, detail="Respuesta demasiado grande")
                
                return result
                
            except json.JSONDecodeError:
                raise HTTPException(status_code=502, detail="Respuesta no es JSON válido")
    
    except httpx.TimeoutException:
        logger.warning(f"Timeout en llamada a {url}")
        raise HTTPException(status_code=504, detail="Timeout en API externa")
    
    except httpx.RequestError as e:
        logger.error(f"Error de conexión a {url}: {e}")
        raise HTTPException(status_code=503, detail="Error de conectividad")
    
    except Exception as e:
        logger.error(f"Error inesperado en llamada externa: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

def mask_sensitive_data(data: str, mask_char: str = "*", visible_chars: int = 4) -> str:
    """
    Enmascarar datos sensibles para logs.
    
    Args:
        data: Dato a enmascarar
        mask_char: Carácter de máscara
        visible_chars: Caracteres visibles al inicio y final
        
    Returns:
        Dato enmascarado
    """
    if not data or len(data) <= visible_chars * 2:
        return mask_char * len(data) if data else ""
    
    return (
        data[:visible_chars] + 
        mask_char * (len(data) - visible_chars * 2) + 
        data[-visible_chars:]
    )

# ============================================
# LOGGING SEGURO
# ============================================

class SecureLogger:
    """Logger que automáticamente enmascara datos sensibles."""
    
    SENSITIVE_PATTERNS = [
        (r'(api[_-]?key["\s]*[:=]["\s]*)([^"\s,}]+)', r'\1****'),
        (r'(token["\s]*[:=]["\s]*)([^"\s,}]+)', r'\1****'),
        (r'(password["\s]*[:=]["\s]*)([^"\s,}]+)', r'\1****'),
        (r'(secret["\s]*[:=]["\s]*)([^"\s,}]+)', r'\1****'),
        (r'(\b\w*key\w*["\s]*[:=]["\s]*)([^"\s,}]+)', r'\1****'),
    ]
    
    @classmethod
    def safe_log(cls, message: str, level: str = "info"):
        """Log mensaje enmascarando datos sensibles."""
        safe_message = message
        
        for pattern, replacement in cls.SENSITIVE_PATTERNS:
            safe_message = re.sub(pattern, replacement, safe_message, flags=re.IGNORECASE)
        
        # Obtener logger y registrar
        logger = logging.getLogger(__name__)
        getattr(logger, level.lower())(safe_message)

# Instancia global
secure_logger = SecureLogger()