"""
Middleware de seguridad principal para el backend.
Integra rate limiting, validación de entrada y headers de seguridad.
"""

import time
import logging
import json
import uuid
from typing import Callable
from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from ..config.security_config import SecurityConfig, SecurityHeaders
from ..middleware.rate_limiter import RateLimiter
from ..validation.input_validator import input_validator

logger = logging.getLogger(__name__)

class SecurityMiddleware(BaseHTTPMiddleware):
    """Middleware principal de seguridad."""
    
    def __init__(self, app, rate_limiter: RateLimiter = None):
        super().__init__(app)
        self.rate_limiter = rate_limiter or RateLimiter(
            requests_per_minute=SecurityConfig.RATE_LIMIT_PER_MINUTE,
            requests_per_hour=SecurityConfig.RATE_LIMIT_PER_HOUR,
            requests_per_day=SecurityConfig.RATE_LIMIT_PER_DAY,
            burst_limit=SecurityConfig.RATE_LIMIT_BURST
        )
        
        # User agents maliciosos conocidos
        self.malicious_user_agents = {
            'sqlmap', 'nikto', 'nmap', 'dirb', 'dirbuster', 'gobuster',
            'wfuzz', 'burpsuite', 'owasp zap', 'acunetix', 'nessus',
            'masscan', 'zgrab', 'curl/7.', 'wget/', 'python-requests',
            'scrapy', 'bot', 'crawler', 'spider'
        }
        
        logger.info("SecurityMiddleware inicializado")
    
    def _get_client_ip(self, request: Request) -> str:
        """
        Obtener IP real del cliente considerando proxies.
        
        Args:
            request: Request object
        
        Returns:
            IP del cliente
        """
        # Verificar headers de proxy en orden de prioridad
        forwarded_ips = (
            request.headers.get("X-Forwarded-For") or
            request.headers.get("X-Real-IP") or
            request.headers.get("CF-Connecting-IP") or
            request.headers.get("X-Client-IP")
        )
        
        if forwarded_ips:
            # Tomar la primera IP de la lista (la del cliente original)
            client_ip = forwarded_ips.split(',')[0].strip()
            return client_ip
        
        return request.client.host if request.client else "unknown"
    
    def _is_malicious_user_agent(self, user_agent: str) -> bool:
        """
        Verificar si el user agent es malicioso.
        
        Args:
            user_agent: User agent string
        
        Returns:
            True si es malicioso
        """
        if not user_agent:
            return True  # Sin user agent es sospechoso
        
        user_agent_lower = user_agent.lower()
        return any(malicious in user_agent_lower for malicious in self.malicious_user_agents)
    
    def _validate_request_headers(self, request: Request) -> bool:
        """
        Validar headers de la request.
        
        Args:
            request: Request object
        
        Returns:
            True si los headers son válidos
        """
        # Verificar User-Agent
        user_agent = request.headers.get("User-Agent", "")
        if self._is_malicious_user_agent(user_agent):
            logger.warning(f"User agent malicioso detectado: {user_agent}")
            return False
        
        # Verificar Host header
        host = request.headers.get("Host", "")
        if host and host not in SecurityConfig.ALLOWED_HOSTS:
            # Permitir también localhost con puerto
            allowed = any(
                host.startswith(allowed_host) 
                for allowed_host in SecurityConfig.ALLOWED_HOSTS
            )
            if not allowed:
                logger.warning(f"Host no permitido: {host}")
                return False
        
        return True
    
    async def _validate_request_body(self, request: Request) -> bool:
        """
        Validar el cuerpo de la request.
        
        Args:
            request: Request object
        
        Returns:
            True si el cuerpo es válido
        """
        try:
            # Verificar Content-Length
            content_length = request.headers.get("Content-Length")
            if content_length:
                size = int(content_length)
                if size > SecurityConfig.MAX_PAYLOAD_SIZE:
                    logger.warning(f"Payload muy grande: {size} bytes")
                    return False
            
            # Para requests con cuerpo JSON, validar estructura básica
            content_type = request.headers.get("Content-Type", "")
            if "application/json" in content_type:
                try:
                    body = await request.body()
                    if body:
                        # Validar tamaño del payload
                        input_validator.validate_payload_size(body.decode('utf-8'))
                        
                        # Validar que sea JSON válido
                        json.loads(body.decode('utf-8'))
                except (json.JSONDecodeError, ValueError, UnicodeDecodeError) as e:
                    logger.warning(f"JSON inválido en request: {e}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validando request body: {e}")
            return False
    
    def _add_security_headers(self, response: Response) -> Response:
        """
        Agregar headers de seguridad a la respuesta.
        
        Args:
            response: Response object
        
        Returns:
            Response con headers de seguridad
        """
        security_headers = SecurityHeaders.get_security_headers()
        
        for header_name, header_value in security_headers.items():
            response.headers[header_name] = header_value
        
        # Agregar headers adicionales
        response.headers["X-Request-ID"] = getattr(response, 'request_id', str(uuid.uuid4()))
        response.headers["Server"] = "Backend-API/1.0"
        
        return response
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Procesar request a través del middleware de seguridad.
        
        Args:
            request: Request entrante
            call_next: Siguiente middleware/handler
        
        Returns:
            Response procesada
        """
        start_time = time.time()
        request_id = str(uuid.uuid4())
        client_ip = self._get_client_ip(request)
        
        # Agregar información al request para otros middlewares
        request.state.request_id = request_id
        request.state.client_ip = client_ip
        request.state.start_time = start_time
        
        try:
            # 1. Validar headers
            if not self._validate_request_headers(request):
                logger.warning(f"Headers inválidos desde {client_ip} - Request ID: {request_id}")
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"error": "Headers de request inválidos", "request_id": request_id}
                )
            
            # 2. Rate limiting
            allowed, rate_info = self.rate_limiter.is_allowed(client_ip)
            if not allowed:
                logger.warning(f"Rate limit excedido para {client_ip} - Request ID: {request_id}")
                
                response = JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "error": "Rate limit excedido",
                        "reason": rate_info.get("reason", "Demasiadas requests"),
                        "retry_after": rate_info.get("retry_after", 300),
                        "request_id": request_id
                    }
                )
                
                # Agregar headers de rate limiting
                response.headers["Retry-After"] = str(rate_info.get("retry_after", 300))
                response.headers["X-RateLimit-Limit"] = str(SecurityConfig.RATE_LIMIT_PER_MINUTE)
                response.headers["X-RateLimit-Remaining"] = "0"
                
                return self._add_security_headers(response)
            
            # 3. Validar cuerpo de la request
            if not await self._validate_request_body(request):
                logger.warning(f"Request body inválido desde {client_ip} - Request ID: {request_id}")
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"error": "Cuerpo de request inválido", "request_id": request_id}
                )
            
            # 4. Registrar request exitosa en rate limiter
            self.rate_limiter.record_request(client_ip)
            
            # 5. Agregar headers de rate limiting a la request info
            remaining_info = rate_info if allowed else {}
            
            # 6. Procesar request
            response = await call_next(request)
            
            # 7. Agregar headers de rate limiting a la response
            if allowed and remaining_info:
                response.headers["X-RateLimit-Limit-Minute"] = str(SecurityConfig.RATE_LIMIT_PER_MINUTE)
                response.headers["X-RateLimit-Remaining-Minute"] = str(remaining_info.get("remaining_minute", 0))
                response.headers["X-RateLimit-Reset-Minute"] = str(remaining_info.get("reset_minute", 0))
                
                response.headers["X-RateLimit-Limit-Hour"] = str(SecurityConfig.RATE_LIMIT_PER_HOUR)
                response.headers["X-RateLimit-Remaining-Hour"] = str(remaining_info.get("remaining_hour", 0))
                response.headers["X-RateLimit-Reset-Hour"] = str(remaining_info.get("reset_hour", 0))
            
            # 8. Agregar headers de seguridad
            response = self._add_security_headers(response)
            
            # 9. Logging de request exitosa
            processing_time = time.time() - start_time
            logger.info(
                f"Request procesada - IP: {client_ip}, "
                f"Method: {request.method}, Path: {request.url.path}, "
                f"Status: {response.status_code}, Time: {processing_time:.3f}s, "
                f"Request ID: {request_id}"
            )
            
            return response
            
        except HTTPException as e:
            # Manejo de errores HTTP conocidos
            processing_time = time.time() - start_time
            logger.warning(
                f"HTTPException - IP: {client_ip}, Status: {e.status_code}, "
                f"Detail: {e.detail}, Time: {processing_time:.3f}s, "
                f"Request ID: {request_id}"
            )
            
            response = JSONResponse(
                status_code=e.status_code,
                content={"error": e.detail, "request_id": request_id}
            )
            return self._add_security_headers(response)
            
        except Exception as e:
            # Manejo de errores inesperados
            processing_time = time.time() - start_time
            logger.error(
                f"Error inesperado - IP: {client_ip}, Error: {str(e)}, "
                f"Time: {processing_time:.3f}s, Request ID: {request_id}",
                exc_info=True
            )
            
            response = JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "Error interno del servidor",
                    "request_id": request_id
                }
            )
            return self._add_security_headers(response) 