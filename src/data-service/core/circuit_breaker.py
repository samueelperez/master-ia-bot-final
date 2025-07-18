"""
Circuit breaker implementation for the External Data Service.
"""
import logging
import time
import functools
from enum import Enum
from typing import Any, Callable, Dict, Optional

from core.config import settings

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation, requests are allowed
    OPEN = "open"      # Circuit is open, requests are not allowed
    HALF_OPEN = "half_open"  # Testing if the service is back to normal


class CircuitBreaker:
    """
    Circuit breaker implementation to prevent repeated calls to failing services.
    """
    
    def __init__(self):
        """Initialize the circuit breaker."""
        self._circuits: Dict[str, Dict[str, Any]] = {}
    
    def _get_circuit(self, name: str) -> Dict[str, Any]:
        """
        Get or create a circuit.
        
        Args:
            name: Circuit name
            
        Returns:
            Circuit data
        """
        if name not in self._circuits:
            self._circuits[name] = {
                "state": CircuitState.CLOSED,
                "failure_count": 0,
                "last_failure_time": 0,
                "recovery_timeout": settings.CIRCUIT_BREAKER_RECOVERY_TIMEOUT,
                "failure_threshold": settings.CIRCUIT_BREAKER_FAILURE_THRESHOLD
            }
        
        return self._circuits[name]
    
    def _record_success(self, name: str) -> None:
        """
        Record a successful call.
        
        Args:
            name: Circuit name
        """
        circuit = self._get_circuit(name)
        
        if circuit["state"] == CircuitState.HALF_OPEN:
            # If the circuit is half-open and the call succeeded, close it
            circuit["state"] = CircuitState.CLOSED
            circuit["failure_count"] = 0
            logger.info(f"Circuit {name} is now CLOSED")
    
    def _record_failure(self, name: str) -> None:
        """
        Record a failed call.
        
        Args:
            name: Circuit name
        """
        circuit = self._get_circuit(name)
        
        circuit["failure_count"] += 1
        circuit["last_failure_time"] = time.time()
        
        if circuit["state"] == CircuitState.CLOSED and circuit["failure_count"] >= circuit["failure_threshold"]:
            # If the circuit is closed and we've reached the failure threshold, open it
            circuit["state"] = CircuitState.OPEN
            logger.warning(f"Circuit {name} is now OPEN")
        elif circuit["state"] == CircuitState.HALF_OPEN:
            # If the circuit is half-open and the call failed, open it again
            circuit["state"] = CircuitState.OPEN
            logger.warning(f"Circuit {name} is now OPEN (after half-open failure)")
    
    def _check_circuit(self, name: str) -> bool:
        """
        Check if a circuit is closed or can be tested.
        
        Args:
            name: Circuit name
            
        Returns:
            True if the circuit is closed or can be tested, False otherwise
        """
        circuit = self._get_circuit(name)
        
        if circuit["state"] == CircuitState.CLOSED:
            # Circuit is closed, allow the call
            return True
        
        if circuit["state"] == CircuitState.OPEN:
            # Check if the recovery timeout has elapsed
            elapsed = time.time() - circuit["last_failure_time"]
            
            if elapsed >= circuit["recovery_timeout"]:
                # Recovery timeout has elapsed, allow one test call
                circuit["state"] = CircuitState.HALF_OPEN
                logger.info(f"Circuit {name} is now HALF_OPEN")
                return True
            
            # Circuit is open and recovery timeout hasn't elapsed, don't allow the call
            logger.warning(f"Circuit {name} is OPEN, call rejected")
            return False
        
        # Circuit is half-open, allow one test call
        return True


# Create a singleton circuit breaker instance
_circuit_breaker = CircuitBreaker()

async def with_circuit_breaker(name: str, func: Callable) -> Any:
    """
    Execute a function with circuit breaker protection.
    
    Args:
        name: Circuit name
        func: Function to execute
        
    Returns:
        Function result
    """
    # Check if the circuit is closed or can be tested
    if not _circuit_breaker._check_circuit(name):
        # Circuit is open, return a fallback value or raise an exception
        logger.warning(f"Circuit {name} is open, using fallback")
        
        # For economic calendar service, return empty data
        if "economic" in name:
            if "symbol" in name:
                return {
                    "high_impact_events": [],
                    "upcoming_events": [],
                    "symbol_events": []
                }
            else:
                return {
                    "high_impact_events": [],
                    "upcoming_events": []
                }
        
        # For other services, return empty data
        return []
    
    try:
        # Call the function
        result = await func()
        
        # Record success
        _circuit_breaker._record_success(name)
        
        return result
    except Exception as e:
        # Record failure
        _circuit_breaker._record_failure(name)
        
        # Re-raise the exception
        raise e


def circuit_breaker(name: str) -> Callable:
    """
    Circuit breaker decorator.
    
    Args:
        name: Circuit name
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Check if the circuit is closed or can be tested
            if not _circuit_breaker._check_circuit(name):
                # Circuit is open, return a fallback value or raise an exception
                logger.warning(f"Circuit {name} is open, using fallback")
                
                # For economic calendar service, return empty data
                if "economic" in name:
                    if "symbol" in name:
                        return {
                            "high_impact_events": [],
                            "upcoming_events": [],
                            "symbol_events": []
                        }
                    else:
                        return {
                            "high_impact_events": [],
                            "upcoming_events": []
                        }
                
                # For other services, return empty data
                return []
            
            try:
                # Call the function
                result = await func(*args, **kwargs)
                
                # Record success
                _circuit_breaker._record_success(name)
                
                return result
            except Exception as e:
                # Record failure
                _circuit_breaker._record_failure(name)
                
                # Re-raise the exception
                raise e
        
        return wrapper
    
    return decorator
