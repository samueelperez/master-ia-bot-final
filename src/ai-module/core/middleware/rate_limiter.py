"""
Sistema de Rate Limiting avanzado para el módulo AI.
Implementación limpia con múltiples estrategias y monitoreo.
"""

import time
import logging
from typing import Dict, Set, Tuple
from dataclasses import dataclass, field
from threading import Lock
import asyncio

from ..config.security_config import SecurityConfig

logger = logging.getLogger(__name__)


@dataclass
class RequestMetrics:
    """Métricas de requests para monitoreo."""
    minute_count: int = 0
    hour_count: int = 0
    burst_count: int = 0
    first_request: float = field(default_factory=time.time)
    last_request: float = field(default_factory=time.time)
    blocked_until: float = 0.0


class RateLimiter:
    """
    Rate limiter avanzado con múltiples estrategias y limpieza automática.
    Implementa limiting por minuto, hora y burst protection.
    """
    
    def __init__(self):
        self.clients: Dict[str, RequestMetrics] = {}
        self.blocked_ips: Set[str] = set()
        self._lock = Lock()
        self._cleanup_interval = 300  # 5 minutos
        self._last_cleanup = time.time()
        
        logger.info("Rate Limiter inicializado")
    
    def _get_current_minute(self) -> int:
        """Obtener minuto actual para bucketing."""
        return int(time.time() // 60)
    
    def _get_current_hour(self) -> int:
        """Obtener hora actual para bucketing."""
        return int(time.time() // 3600)
    
    def _cleanup_old_entries(self) -> None:
        """Limpiar entradas antiguas para prevenir memory leaks."""
        current_time = time.time()
        
        # Solo limpiar cada 5 minutos
        if current_time - self._last_cleanup < self._cleanup_interval:
            return
        
        with self._lock:
            expired_clients = []
            
            for client_ip, metrics in self.clients.items():
                # Remover clientes inactivos por más de 2 horas
                if current_time - metrics.last_request > 7200:
                    expired_clients.append(client_ip)
                
                # Resetear contadores si han pasado los períodos correspondientes
                current_minute = self._get_current_minute()
                current_hour = self._get_current_hour()
                
                minute_from_first = int(metrics.first_request // 60)
                hour_from_first = int(metrics.first_request // 3600)
                
                if current_minute > minute_from_first:
                    metrics.minute_count = 0
                    metrics.burst_count = 0
                    metrics.first_request = current_time
                
                if current_hour > hour_from_first:
                    metrics.hour_count = 0
            
            # Remover clientes expirados
            for client_ip in expired_clients:
                del self.clients[client_ip]
            
            # Limpiar IPs bloqueadas expiradas
            self.blocked_ips = {
                ip for ip in self.blocked_ips 
                if self.clients.get(ip, RequestMetrics()).blocked_until > current_time
            }
            
            self._last_cleanup = current_time
            
            if expired_clients:
                logger.info(f"Rate Limiter: Limpieza completada. Removidos {len(expired_clients)} clientes expirados")
    
    def _check_burst_limit(self, client_ip: str, metrics: RequestMetrics) -> bool:
        """Verificar límite de burst (ráfagas)."""
        current_time = time.time()
        
        # Resetear burst count si ha pasado más de 1 segundo
        if current_time - metrics.last_request > 1.0:
            metrics.burst_count = 0
        
        return metrics.burst_count < SecurityConfig.RATE_LIMIT_BURST
    
    def _check_minute_limit(self, client_ip: str, metrics: RequestMetrics) -> bool:
        """Verificar límite por minuto."""
        current_minute = self._get_current_minute()
        minute_from_first = int(metrics.first_request // 60)
        
        # Si estamos en un nuevo minuto, resetear contador
        if current_minute > minute_from_first:
            metrics.minute_count = 0
            metrics.first_request = time.time()
        
        return metrics.minute_count < SecurityConfig.RATE_LIMIT_PER_MINUTE
    
    def _check_hour_limit(self, client_ip: str, metrics: RequestMetrics) -> bool:
        """Verificar límite por hora."""
        return metrics.hour_count < SecurityConfig.RATE_LIMIT_PER_HOUR
    
    def _block_client(self, client_ip: str, duration: int, reason: str) -> None:
        """Bloquear cliente por duración específica."""
        metrics = self.clients.get(client_ip, RequestMetrics())
        metrics.blocked_until = time.time() + duration
        self.clients[client_ip] = metrics
        self.blocked_ips.add(client_ip)
        
        logger.warning(f"Cliente {client_ip} bloqueado por {duration}s. Razón: {reason}")
    
    def is_allowed(self, client_ip: str) -> Tuple[bool, str]:
        """
        Verificar si la request está permitida.
        
        Returns:
            (allowed: bool, reason: str)
        """
        self._cleanup_old_entries()
        
        current_time = time.time()
        
        with self._lock:
            # Verificar si está bloqueado actualmente
            if client_ip in self.blocked_ips:
                metrics = self.clients.get(client_ip, RequestMetrics())
                if current_time < metrics.blocked_until:
                    remaining = int(metrics.blocked_until - current_time)
                    return False, f"IP bloqueada. Tiempo restante: {remaining}s"
                else:
                    # Desbloquear IP
                    self.blocked_ips.discard(client_ip)
                    logger.info(f"IP {client_ip} desbloqueada automáticamente")
            
            # Obtener o crear métricas del cliente
            if client_ip not in self.clients:
                self.clients[client_ip] = RequestMetrics()
            
            metrics = self.clients[client_ip]
            
            # Verificar límites en orden de severidad
            
            # 1. Verificar burst limit (más restrictivo)
            if not self._check_burst_limit(client_ip, metrics):
                self._block_client(client_ip, 60, "Límite de burst excedido")
                return False, "Demasiadas requests en poco tiempo. Intenta en 1 minuto"
            
            # 2. Verificar límite por minuto
            if not self._check_minute_limit(client_ip, metrics):
                self._block_client(client_ip, 300, "Límite por minuto excedido")
                return False, "Límite por minuto excedido. Intenta en 5 minutos"
            
            # 3. Verificar límite por hora
            if not self._check_hour_limit(client_ip, metrics):
                self._block_client(client_ip, 3600, "Límite por hora excedido")
                return False, "Límite por hora excedido. Intenta en 1 hora"
            
            return True, "Request permitida"
    
    def record_request(self, client_ip: str) -> None:
        """Registrar una request exitosa."""
        current_time = time.time()
        
        with self._lock:
            if client_ip not in self.clients:
                self.clients[client_ip] = RequestMetrics()
            
            metrics = self.clients[client_ip]
            metrics.burst_count += 1
            metrics.minute_count += 1
            metrics.hour_count += 1
            metrics.last_request = current_time
    
    def get_client_stats(self, client_ip: str) -> Dict[str, any]:
        """Obtener estadísticas de un cliente específico."""
        with self._lock:
            if client_ip not in self.clients:
                return {"error": "Cliente no encontrado"}
            
            metrics = self.clients[client_ip]
            current_time = time.time()
            
            return {
                "client_ip": client_ip,
                "minute_count": metrics.minute_count,
                "hour_count": metrics.hour_count,
                "burst_count": metrics.burst_count,
                "is_blocked": client_ip in self.blocked_ips,
                "blocked_until": metrics.blocked_until if client_ip in self.blocked_ips else None,
                "time_since_last_request": current_time - metrics.last_request,
                "limits": {
                    "per_minute": SecurityConfig.RATE_LIMIT_PER_MINUTE,
                    "per_hour": SecurityConfig.RATE_LIMIT_PER_HOUR,
                    "burst": SecurityConfig.RATE_LIMIT_BURST
                }
            }
    
    def get_global_stats(self) -> Dict[str, any]:
        """Obtener estadísticas globales del rate limiter."""
        self._cleanup_old_entries()
        
        with self._lock:
            total_clients = len(self.clients)
            blocked_clients = len(self.blocked_ips)
            active_clients = sum(
                1 for metrics in self.clients.values()
                if time.time() - metrics.last_request < 300  # Activos en últimos 5 min
            )
            
            return {
                "total_clients": total_clients,
                "blocked_clients": blocked_clients,
                "active_clients": active_clients,
                "last_cleanup": self._last_cleanup,
                "limits": {
                    "per_minute": SecurityConfig.RATE_LIMIT_PER_MINUTE,
                    "per_hour": SecurityConfig.RATE_LIMIT_PER_HOUR,
                    "burst": SecurityConfig.RATE_LIMIT_BURST
                }
            }
    
    async def reset_client_limits(self, client_ip: str) -> bool:
        """Resetear límites de un cliente específico (admin only)."""
        with self._lock:
            if client_ip in self.clients:
                del self.clients[client_ip]
            
            self.blocked_ips.discard(client_ip)
            logger.info(f"Límites reseteados para cliente: {client_ip}")
            return True
        
        return False


# Instancia global del rate limiter
rate_limiter = RateLimiter() 