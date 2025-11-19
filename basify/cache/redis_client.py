"""
Redis Client Wrapper for Basify Framework

Provides Redis connection management, health checks, and graceful degradation
"""

import os
import json
import pickle
import logging
from typing import Any, Optional, Union
from urllib.parse import urlparse

try:
    import redis
    from redis.exceptions import ConnectionError, TimeoutError, RedisError
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None
    ConnectionError = TimeoutError = RedisError = Exception

logger = logging.getLogger(__name__)


class RedisClient:
    """
    Redis client wrapper sa connection management i fallback behavior
    """
    
    def __init__(self, redis_url: Optional[str] = None, enabled: bool = True):
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.enabled = enabled and bool(os.getenv("REDIS_ENABLED", "true").lower() == "true")
        self.client: Optional[redis.Redis] = None
        self._connected = False
        
        # TTL defaults iz environment
        self.ttl_default = int(os.getenv("REDIS_TTL_DEFAULT", "300"))  # 5 minutes
        self.ttl_auth = int(os.getenv("REDIS_TTL_AUTH", "900"))        # 15 minutes  
        self.ttl_services = int(os.getenv("REDIS_TTL_SERVICES", "600")) # 10 minutes
        
        if self.enabled and REDIS_AVAILABLE:
            self._connect()
        else:
            if not REDIS_AVAILABLE:
                logger.warning("Redis package not installed. Cache will be disabled.")
            if not self.enabled:
                logger.info("Redis caching disabled by configuration.")
    
    def _connect(self) -> bool:
        """Konektuj se na Redis sa error handling"""
        try:
            # Parse Redis URL
            parsed_url = urlparse(self.redis_url)
            
            self.client = redis.Redis(
                host=parsed_url.hostname or 'localhost',
                port=parsed_url.port or 6379,
                db=int(parsed_url.path.lstrip('/')) if parsed_url.path else 0,
                password=parsed_url.password,
                decode_responses=False,  # We handle encoding manually
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
            
            # Test connection
            self.client.ping()
            self._connected = True
            logger.info(f"Redis connected: {self.redis_url}")
            return True
            
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}. Cache will be disabled.")
            self.client = None
            self._connected = False
            return False
    
    def is_available(self) -> bool:
        """Proverava da li je Redis dostupan"""
        if not self.enabled or not REDIS_AVAILABLE or not self.client:
            return False
        
        try:
            self.client.ping()
            if not self._connected:
                self._connected = True
                logger.info("Redis connection restored")
            return True
        except Exception:
            if self._connected:
                logger.warning("Redis connection lost")
                self._connected = False
            return False
    
    def get(self, key: str, default=None) -> Any:
        """Get value from cache with automatic deserialization"""
        if not self.is_available():
            return default
        
        try:
            value = self.client.get(key)
            if value is None:
                return default
            
            # Try JSON first, fallback to pickle
            try:
                return json.loads(value.decode('utf-8'))
            except (json.JSONDecodeError, UnicodeDecodeError):
                return pickle.loads(value)
                
        except Exception as e:
            logger.warning(f"Redis GET failed for key '{key}': {e}")
            return default
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with automatic serialization"""
        if not self.is_available():
            return False
        
        try:
            # Use JSON for simple types, pickle for complex types
            try:
                serialized = json.dumps(value, default=str).encode('utf-8')
            except (TypeError, ValueError):
                serialized = pickle.dumps(value)
            
            ttl = ttl or self.ttl_default
            return bool(self.client.setex(key, ttl, serialized))
            
        except Exception as e:
            logger.warning(f"Redis SET failed for key '{key}': {e}")
            return False
    
    def delete(self, *keys: str) -> int:
        """Delete keys from cache"""
        if not self.is_available() or not keys:
            return 0
        
        try:
            return self.client.delete(*keys)
        except Exception as e:
            logger.warning(f"Redis DELETE failed for keys {keys}: {e}")
            return 0
    
    def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern"""
        if not self.is_available():
            return 0
        
        try:
            keys = self.client.keys(pattern)
            if keys:
                return self.client.delete(*keys)
            return 0
        except Exception as e:
            logger.warning(f"Redis DELETE_PATTERN failed for pattern '{pattern}': {e}")
            return 0
    
    def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        if not self.is_available():
            return False
        
        try:
            return bool(self.client.exists(key))
        except Exception as e:
            logger.warning(f"Redis EXISTS failed for key '{key}': {e}")
            return False
    
    def ttl(self, key: str) -> int:
        """Get TTL for key (-1 if no expiry, -2 if key doesn't exist)"""
        if not self.is_available():
            return -2
        
        try:
            return self.client.ttl(key)
        except Exception as e:
            logger.warning(f"Redis TTL failed for key '{key}': {e}")
            return -2
    
    def flush_all(self) -> bool:
        """Flush all cache data (use carefully!)"""
        if not self.is_available():
            return False
        
        try:
            self.client.flushdb()
            logger.info("Redis cache flushed")
            return True
        except Exception as e:
            logger.error(f"Redis FLUSH failed: {e}")
            return False
    
    def health_check(self) -> dict:
        """Get Redis health information"""
        if not self.enabled:
            return {"status": "disabled", "redis_available": REDIS_AVAILABLE}
        
        if not REDIS_AVAILABLE:
            return {"status": "error", "message": "Redis package not installed"}
        
        try:
            if self.client:
                info = self.client.info()
                return {
                    "status": "healthy",
                    "connected": self._connected,
                    "redis_version": info.get("redis_version"),
                    "used_memory_human": info.get("used_memory_human"),
                    "connected_clients": info.get("connected_clients")
                }
            else:
                return {"status": "error", "message": "No Redis client"}
        except Exception as e:
            return {"status": "error", "message": str(e)}


# Global Redis client instance
_redis_client: Optional[RedisClient] = None


def get_redis_client() -> RedisClient:
    """Get global Redis client instance (singleton)"""
    global _redis_client
    
    if _redis_client is None:
        _redis_client = RedisClient()
    
    return _redis_client


def reset_redis_client():
    """Reset global Redis client (for testing)"""
    global _redis_client
    _redis_client = None