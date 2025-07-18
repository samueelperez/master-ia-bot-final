"""
Sistema de Rate Limiting avanzado para el backend.
Incluye múltiples estrategias y bloqueo temporal.
"""

import time
import logging
from typing import Dict, Optional, Tuple, Set
from collections import defaultdict, deque
from dataclasses import dataclass, field
import threading
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

@dataclass
class RateLimitInfo:
    """Información sobre límites de rate limiting."""
    requests_per_minute: int = 0
    requests_per_hour: int = 0
    requests_per_day: int = 0
    burst_requests: int = 0
    last_request_time: float = 0
    blocked_until: float = 0
    total_requests: int = 0
    blocked_requests: int = 0


class RateLimiter:
    """Sistema de rate limiting con múltiples estrategias."""
    
    def __init__(
        self,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        requests_per_day: int = 10000,
        burst_limit: int = 10,
        block_duration: int = 300  # 5 minutos
    ):
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.requests_per_day = requests_per_day
        self.burst_limit = burst_limit
        self.block_duration = block_duration
        
        # Almacenamiento thread-safe
        self.lock = threading.RLock()
        self.client_data: Dict[str, RateLimitInfo] = defaultdict(RateLimitInfo)
        
        # Ventanas deslizantes para rate limiting
        self.minute_windows: Dict[str, deque] = defaultdict(lambda: deque(maxlen=self.requests_per_minute))
        self.hour_windows: Dict[str, deque] = defaultdict(lambda: deque(maxlen=self.requests_per_hour))
        self.day_windows: Dict[str, deque] = defaultdict(lambda: deque(maxlen=self.requests_per_day))
        
        # IPs bloqueadas
        self.blocked_ips: Set[str] = set()
        
        logger.info("Rate Limiter inicializado")
    
    def _cleanup_old_entries(self):
        """Limpiar entradas antiguas para prevenir memory leaks."""
        current_time = time.time()
        cutoff_time = current_time - (24 * 60 * 60)  # 24 horas
        
        with self.lock:
            # Limpiar datos de clientes inactivos
            inactive_clients = []
            for client_id, info in self.client_data.items():
                if info.last_request_time < cutoff_time:
                    inactive_clients.append(client_id)
            
            for client_id in inactive_clients:
                del self.client_data[client_id]
                if client_id in self.minute_windows:
                    del self.minute_windows[client_id]
                if client_id in self.hour_windows:
                    del self.hour_windows[client_id]
                if client_id in self.day_windows:
                    del self.day_windows[client_id]
                
                logger.debug(f"Limpiado datos de cliente inactivo: {client_id}")
    
    def _is_within_time_window(self, timestamps: deque, window_seconds: int) -> bool:
        """Verificar si estamos dentro de una ventana de tiempo específica."""
        if not timestamps:
            return True
        
        current_time = time.time()
        cutoff_time = current_time - window_seconds
        
        # Remover timestamps antiguos
        while timestamps and timestamps[0] < cutoff_time:
            timestamps.popleft()
        
        return len(timestamps) < self._get_limit_for_window(window_seconds)
    
    def _get_limit_for_window(self, window_seconds: int) -> int:
        """Obtener el límite apropiado para una ventana de tiempo."""
        if window_seconds <= 60:
            return self.requests_per_minute
        elif window_seconds <= 3600:
            return self.requests_per_hour
        else:
            return self.requests_per_day
    
    def _check_burst_limit(self, client_id: str) -> bool:
        """Verificar límite de ráfaga (burst)."""
        with self.lock:
            current_time = time.time()
            info = self.client_data[client_id]
            
            # Si han pasado más de 1 segundo desde la última request, resetear contador burst
            if current_time - info.last_request_time > 1.0:
                info.burst_requests = 0
            
            return info.burst_requests < self.burst_limit
    
    def is_allowed(self, client_id: str) -> Tuple[bool, Dict[str, any]]:
        """
        Verificar si un cliente puede hacer una request.
        
        Args:
            client_id: Identificador único del cliente (IP, user ID, etc.)
        
        Returns:
            Tuple de (permitido, información_de_límites)
        """
        with self.lock:
            current_time = time.time()
            info = self.client_data[client_id]
            
            # Verificar si el cliente está bloqueado
            if current_time < info.blocked_until:
                remaining_block_time = int(info.blocked_until - current_time)
                return False, {
                    "blocked": True,
                    "reason": "Cliente temporalmente bloqueado",
                    "retry_after": remaining_block_time,
                    "blocked_until": datetime.fromtimestamp(info.blocked_until).isoformat()
                }
            
            # Verificar límite de ráfaga
            if not self._check_burst_limit(client_id):
                info.blocked_until = current_time + self.block_duration
                info.blocked_requests += 1
                logger.warning(f"Cliente {client_id} bloqueado por exceder límite de ráfaga")
                
                return False, {
                    "blocked": True,
                    "reason": "Límite de ráfaga excedido",
                    "retry_after": self.block_duration,
                    "burst_limit": self.burst_limit
                }
            
            # Verificar límites de ventana deslizante
            minute_window = self.minute_windows[client_id]
            hour_window = self.hour_windows[client_id]
            day_window = self.day_windows[client_id]
            
            # Verificar ventana de minuto
            if not self._is_within_time_window(minute_window, 60):
                info.blocked_until = current_time + self.block_duration
                info.blocked_requests += 1
                logger.warning(f"Cliente {client_id} bloqueado por exceder límite por minuto")
                
                return False, {
                    "blocked": True,
                    "reason": "Límite por minuto excedido",
                    "retry_after": self.block_duration,
                    "limit_per_minute": self.requests_per_minute,
                    "current_minute_requests": len(minute_window)
                }
            
            # Verificar ventana de hora
            if not self._is_within_time_window(hour_window, 3600):
                info.blocked_until = current_time + self.block_duration
                info.blocked_requests += 1
                logger.warning(f"Cliente {client_id} bloqueado por exceder límite por hora")
                
                return False, {
                    "blocked": True,
                    "reason": "Límite por hora excedido",
                    "retry_after": self.block_duration,
                    "limit_per_hour": self.requests_per_hour,
                    "current_hour_requests": len(hour_window)
                }
            
            # Verificar ventana de día
            if not self._is_within_time_window(day_window, 86400):
                info.blocked_until = current_time + self.block_duration
                info.blocked_requests += 1
                logger.warning(f"Cliente {client_id} bloqueado por exceder límite por día")
                
                return False, {
                    "blocked": True,
                    "reason": "Límite por día excedido",
                    "retry_after": self.block_duration,
                    "limit_per_day": self.requests_per_day,
                    "current_day_requests": len(day_window)
                }
            
            # Request permitida
            return True, {
                "allowed": True,
                "remaining_minute": self.requests_per_minute - len(minute_window),
                "remaining_hour": self.requests_per_hour - len(hour_window),
                "remaining_day": self.requests_per_day - len(day_window),
                "reset_minute": int(current_time + 60),
                "reset_hour": int(current_time + 3600),
                "reset_day": int(current_time + 86400)
            }
    
    def record_request(self, client_id: str) -> None:
        """
        Registrar una request exitosa.
        
        Args:
            client_id: Identificador único del cliente
        """
        with self.lock:
            current_time = time.time()
            info = self.client_data[client_id]
            
            # Actualizar información del cliente
            info.last_request_time = current_time
            info.total_requests += 1
            info.burst_requests += 1
            
            # Agregar timestamp a las ventanas
            self.minute_windows[client_id].append(current_time)
            self.hour_windows[client_id].append(current_time)
            self.day_windows[client_id].append(current_time)
            
            # Limpiar entradas antiguas periódicamente
            if info.total_requests % 100 == 0:
                self._cleanup_old_entries()
    
    def get_client_stats(self, client_id: str) -> Dict[str, any]:
        """
        Obtener estadísticas de un cliente.
        
        Args:
            client_id: Identificador único del cliente
        
        Returns:
            Diccionario con estadísticas del cliente
        """
        with self.lock:
            info = self.client_data[client_id]
            current_time = time.time()
            
            # Limpiar ventanas antes de contar
            minute_window = self.minute_windows[client_id]
            hour_window = self.hour_windows[client_id]
            day_window = self.day_windows[client_id]
            
            self._is_within_time_window(minute_window, 60)
            self._is_within_time_window(hour_window, 3600)
            self._is_within_time_window(day_window, 86400)
            
            return {
                "client_id": client_id,
                "total_requests": info.total_requests,
                "blocked_requests": info.blocked_requests,
                "current_minute_requests": len(minute_window),
                "current_hour_requests": len(hour_window),
                "current_day_requests": len(day_window),
                "last_request_time": datetime.fromtimestamp(info.last_request_time).isoformat() if info.last_request_time > 0 else None,
                "is_blocked": current_time < info.blocked_until,
                "blocked_until": datetime.fromtimestamp(info.blocked_until).isoformat() if info.blocked_until > current_time else None,
                "limits": {
                    "per_minute": self.requests_per_minute,
                    "per_hour": self.requests_per_hour,
                    "per_day": self.requests_per_day,
                    "burst": self.burst_limit
                }
            }
    
    def get_global_stats(self) -> Dict[str, any]:
        """
        Obtener estadísticas globales del rate limiter.
        
        Returns:
            Diccionario con estadísticas globales
        """
        with self.lock:
            current_time = time.time()
            
            total_clients = len(self.client_data)
            total_requests = sum(info.total_requests for info in self.client_data.values())
            total_blocked = sum(info.blocked_requests for info in self.client_data.values())
            currently_blocked = sum(1 for info in self.client_data.values() if current_time < info.blocked_until)
            
            return {
                "total_clients": total_clients,
                "total_requests": total_requests,
                "total_blocked_requests": total_blocked,
                "currently_blocked_clients": currently_blocked,
                "block_rate": (total_blocked / total_requests * 100) if total_requests > 0 else 0,
                "rate_limiter_config": {
                    "requests_per_minute": self.requests_per_minute,
                    "requests_per_hour": self.requests_per_hour,
                    "requests_per_day": self.requests_per_day,
                    "burst_limit": self.burst_limit,
                    "block_duration": self.block_duration
                }
            }
    
    def reset_client(self, client_id: str) -> bool:
        """
        Resetear límites para un cliente específico.
        
        Args:
            client_id: Identificador único del cliente
        
        Returns:
            True si el cliente fue reseteado, False si no existía
        """
        with self.lock:
            if client_id in self.client_data:
                # Resetear información del cliente
                info = self.client_data[client_id]
                info.blocked_until = 0
                info.burst_requests = 0
                
                # Limpiar ventanas
                self.minute_windows[client_id].clear()
                self.hour_windows[client_id].clear()
                self.day_windows[client_id].clear()
                
                logger.info(f"Cliente {client_id} reseteado")
                return True
            
            return False
    
    def block_client(self, client_id: str, duration_seconds: int = None) -> None:
        """
        Bloquear manualmente un cliente.
        
        Args:
            client_id: Identificador único del cliente
            duration_seconds: Duración del bloqueo en segundos (por defecto usa block_duration)
        """
        with self.lock:
            current_time = time.time()
            block_duration = duration_seconds if duration_seconds is not None else self.block_duration
            
            info = self.client_data[client_id]
            info.blocked_until = current_time + block_duration
            info.blocked_requests += 1
            
            logger.warning(f"Cliente {client_id} bloqueado manualmente por {block_duration} segundos")
    
    def get_stats(self, client_id: str) -> Dict[str, any]:
        """
        Alias para get_client_stats para compatibilidad con scripts de validación.
        
        Args:
            client_id: Identificador único del cliente
        
        Returns:
            Diccionario con estadísticas del cliente
        """
        return self.get_client_stats(client_id) 