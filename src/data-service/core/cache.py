"""
Cache implementation for the External Data Service.
"""
import json
import logging
import time
import functools
from typing import Any, Dict, Optional, Callable

from core.config import settings

logger = logging.getLogger(__name__)


class Cache:
    """Simple in-memory cache with TTL."""
    
    def __init__(self):
        """Initialize the cache."""
        self._cache: Dict[str, Dict[str, Any]] = {}
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get a value from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found or expired
        """
        if key not in self._cache:
            return None
        
        cache_item = self._cache[key]
        
        # Check if expired
        if time.time() > cache_item["expires_at"]:
            logger.debug(f"Cache item {key} expired")
            del self._cache[key]
            return None
        
        logger.debug(f"Cache hit for {key}")
        return cache_item["value"]
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Set a value in the cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (defaults to CACHE_TTL from settings)
        """
        if ttl is None:
            ttl = settings.CACHE_TTL
        
        expires_at = time.time() + ttl
        
        self._cache[key] = {
            "value": value,
            "expires_at": expires_at
        }
        
        logger.debug(f"Cache set for {key}, expires in {ttl} seconds")
    
    async def delete(self, key: str) -> None:
        """
        Delete a value from the cache.
        
        Args:
            key: Cache key
        """
        if key in self._cache:
            del self._cache[key]
            logger.debug(f"Cache deleted for {key}")
    
    async def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()
        logger.debug("Cache cleared")


# Create a singleton cache instance
cache = Cache()

def cached(prefix: str, ttl: Optional[int] = None):
    """
    Decorator to cache function results.
    
    Args:
        prefix: Cache key prefix
        ttl: Time to live in seconds (defaults to CACHE_TTL from settings)
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Create a cache key based on function name, args, and kwargs
            key = f"{prefix}_{func.__name__}"
            
            # Try to get from cache
            cached_result = await cache.get(key)
            if cached_result is not None:
                logger.debug(f"Cache hit for {key}")
                return cached_result
            
            # Call the function
            result = await func(*args, **kwargs)
            
            # Cache the result
            await cache.set(key, result, ttl)
            
            return result
        return wrapper
    return decorator
