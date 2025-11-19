"""
Cache Decorators for Basify Framework

Provides function-level caching decorators with Redis backend
"""

import hashlib
import inspect
import logging
from functools import wraps
from typing import Any, Callable, Optional, Union, List

from .redis_client import get_redis_client

logger = logging.getLogger(__name__)


def _generate_cache_key(func_name: str, args: tuple, kwargs: dict, prefix: str = "") -> str:
    """Generate unique cache key from function name and arguments"""
    # Create a hash of arguments for consistent key generation
    args_str = str(args) + str(sorted(kwargs.items()))
    args_hash = hashlib.md5(args_str.encode()).hexdigest()[:12]
    
    key_parts = [prefix, func_name, args_hash] if prefix else [func_name, args_hash]
    return ":".join(filter(None, key_parts))


def cache_result(ttl: Optional[int] = None, prefix: str = "func", key_func: Optional[Callable] = None):
    """
    Cache function results in Redis
    
    Args:
        ttl: Time-to-live in seconds (uses default if None)
        prefix: Cache key prefix 
        key_func: Custom function to generate cache key
        
    Usage:
        @cache_result(ttl=300, prefix="api")
        def get_user(user_id: int):
            return fetch_user_from_db(user_id)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            redis_client = get_redis_client()
            
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = _generate_cache_key(func.__name__, args, kwargs, prefix)
            
            # Try to get from cache first
            cached_result = redis_client.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache HIT for key: {cache_key}")
                return cached_result
            
            # Cache miss - execute function
            logger.debug(f"Cache MISS for key: {cache_key}")
            result = await func(*args, **kwargs)
            
            # Store result in cache
            if result is not None:  # Don't cache None results
                redis_client.set(cache_key, result, ttl)
            
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            redis_client = get_redis_client()
            
            # Generate cache key  
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = _generate_cache_key(func.__name__, args, kwargs, prefix)
            
            # Try to get from cache first
            cached_result = redis_client.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache HIT for key: {cache_key}")
                return cached_result
            
            # Cache miss - execute function
            logger.debug(f"Cache MISS for key: {cache_key}")
            result = func(*args, **kwargs)
            
            # Store result in cache
            if result is not None:  # Don't cache None results
                redis_client.set(cache_key, result, ttl)
            
            return result
        
        # Return appropriate wrapper based on function type
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def cache_user_session(ttl: Optional[int] = None, key_prefix: str = "user_session"):
    """
    Cache user session data (JWT validation results, permissions, etc.)
    
    Args:
        ttl: Time-to-live in seconds (uses auth TTL if None)
        key_prefix: Cache key prefix for user sessions
        
    Usage:
        @cache_user_session(ttl=900)
        def validate_jwt_token(token: str):
            return decode_and_validate_token(token)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            redis_client = get_redis_client()
            
            # Use auth TTL by default for user sessions
            session_ttl = ttl or redis_client.ttl_auth
            
            # Generate cache key (usually based on token or user_id)
            cache_key = _generate_cache_key(func.__name__, args, kwargs, key_prefix)
            
            # Try to get from cache first
            cached_result = redis_client.get(cache_key)
            if cached_result is not None:
                logger.debug(f"User session cache HIT for key: {cache_key}")
                return cached_result
            
            # Cache miss - execute function
            logger.debug(f"User session cache MISS for key: {cache_key}")
            result = await func(*args, **kwargs)
            
            # Store result in cache with auth TTL
            if result is not None:
                redis_client.set(cache_key, result, session_ttl)
            
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            redis_client = get_redis_client()
            
            # Use auth TTL by default for user sessions
            session_ttl = ttl or redis_client.ttl_auth
            
            # Generate cache key 
            cache_key = _generate_cache_key(func.__name__, args, kwargs, key_prefix)
            
            # Try to get from cache first
            cached_result = redis_client.get(cache_key)
            if cached_result is not None:
                logger.debug(f"User session cache HIT for key: {cache_key}")
                return cached_result
            
            # Cache miss - execute function
            logger.debug(f"User session cache MISS for key: {cache_key}")
            result = func(*args, **kwargs)
            
            # Store result in cache with auth TTL
            if result is not None:
                redis_client.set(cache_key, result, session_ttl)
            
            return result
        
        # Return appropriate wrapper based on function type
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def invalidate_cache(patterns: List[str], on_result: Optional[Callable] = None):
    """
    Invalidate cache entries after function execution
    
    Args:
        patterns: List of cache key patterns to invalidate
        on_result: Function to determine if cache should be invalidated based on result
        
    Usage:
        @invalidate_cache(patterns=["user:*", "user_session:*"])
        def update_user(user_id: int, **data):
            return update_user_in_db(user_id, **data)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            
            # Check if we should invalidate based on result
            should_invalidate = True
            if on_result:
                should_invalidate = on_result(result)
            
            if should_invalidate:
                redis_client = get_redis_client()
                for pattern in patterns:
                    # Replace placeholders in patterns with actual values if needed
                    try:
                        # Use args for positional and kwargs for named formatting
                        formatted_pattern = pattern.format(*args, **kwargs)
                    except (KeyError, IndexError, ValueError):
                        # If formatting fails, use pattern as-is
                        formatted_pattern = pattern
                    
                    deleted = redis_client.delete_pattern(formatted_pattern)
                    if deleted > 0:
                        logger.debug(f"Invalidated {deleted} cache keys matching pattern: {formatted_pattern}")
            
            return result
        
        @wraps(func) 
        def sync_wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            
            # Check if we should invalidate based on result
            should_invalidate = True
            if on_result:
                should_invalidate = on_result(result)
            
            if should_invalidate:
                redis_client = get_redis_client()
                for pattern in patterns:
                    # Replace placeholders in patterns with actual values if needed
                    try:
                        # Use args for positional and kwargs for named formatting
                        formatted_pattern = pattern.format(*args, **kwargs)
                    except (KeyError, IndexError, ValueError):
                        # If formatting fails, use pattern as-is
                        formatted_pattern = pattern
                    
                    deleted = redis_client.delete_pattern(formatted_pattern)
                    if deleted > 0:
                        logger.debug(f"Invalidated {deleted} cache keys matching pattern: {formatted_pattern}")
            
            return result
        
        # Return appropriate wrapper based on function type
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# Convenience decorators for common use cases
def cache_service_response(ttl: Optional[int] = None):
    """Cache inter-service API responses"""
    redis_client = get_redis_client()
    return cache_result(ttl=ttl or redis_client.ttl_services, prefix="service")


def cache_database_query(ttl: Optional[int] = None):
    """Cache database query results"""  
    redis_client = get_redis_client()
    return cache_result(ttl=ttl or redis_client.ttl_default, prefix="db")


def cache_auth_result(ttl: Optional[int] = None):
    """Cache authentication/authorization results"""
    redis_client = get_redis_client()
    return cache_user_session(ttl=ttl or redis_client.ttl_auth)


# Cache invalidation helpers
def invalidate_user_cache(user_id: Union[int, str]):
    """Invalidate all cache entries for a specific user"""
    redis_client = get_redis_client()
    patterns = [
        f"user_session:*:{user_id}:*",
        f"user:{user_id}:*", 
        f"func:get_user:*{user_id}*"
    ]
    
    total_deleted = 0
    for pattern in patterns:
        deleted = redis_client.delete_pattern(pattern)
        total_deleted += deleted
    
    logger.info(f"Invalidated {total_deleted} cache entries for user {user_id}")
    return total_deleted


def invalidate_service_cache(service_name: str):
    """Invalidate all cache entries for a specific service"""
    redis_client = get_redis_client()
    patterns = [
        f"service:*{service_name}*",
        f"func:*{service_name}*"
    ]
    
    total_deleted = 0  
    for pattern in patterns:
        deleted = redis_client.delete_pattern(pattern)
        total_deleted += deleted
    
    logger.info(f"Invalidated {total_deleted} cache entries for service {service_name}")
    return total_deleted