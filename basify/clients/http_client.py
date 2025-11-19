import aiohttp
import asyncio
import json
import logging
import hashlib
from typing import Dict, Any, Optional, Union
from urllib.parse import urljoin
from .service_discovery import ServiceDiscovery

try:
    from ..cache import get_redis_client
    CACHE_AVAILABLE = True
except ImportError:
    CACHE_AVAILABLE = False
    get_redis_client = None


class ServiceClientError(Exception):
    """Base exception for service client errors"""
    pass


class ServiceUnavailableError(ServiceClientError):
    """Raised when service is unavailable after retries"""
    pass


class ServiceTimeoutError(ServiceClientError):
    """Raised when service request times out"""
    pass


class ServiceClient:
    """
    HTTP klijent za komunikaciju između mikroservisa
    Podržava retry logiku, timeout handling i error recovery
    """
    
    def __init__(
        self,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
        retry_delay: Optional[float] = None,
        service_discovery: Optional[ServiceDiscovery] = None,
        enable_cache: Optional[bool] = None
    ):
        # Load configuration from environment variables
        import os
        self.timeout = timeout or float(os.getenv("SERVICE_CLIENT_TIMEOUT", "5.0"))
        self.max_retries = max_retries or int(os.getenv("SERVICE_CLIENT_MAX_RETRIES", "3"))
        self.retry_delay = retry_delay or float(os.getenv("SERVICE_CLIENT_RETRY_DELAY", "1.0"))
        self.service_discovery = service_discovery or ServiceDiscovery()
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Caching configuration
        self.enable_cache = enable_cache if enable_cache is not None else CACHE_AVAILABLE
        self.redis_client = get_redis_client() if self.enable_cache and CACHE_AVAILABLE else None
        
        if self.enable_cache and not CACHE_AVAILABLE:
            self.logger.warning("Cache enabled but Redis client not available")
    
    def _generate_cache_key(self, method: str, service_name: str, endpoint: str, 
                           params: Optional[Dict] = None, data: Optional[Dict] = None) -> str:
        """Generate unique cache key for request"""
        key_parts = [method, service_name, endpoint]
        
        # Include params and data in key generation
        if params:
            key_parts.append(f"params:{sorted(params.items())}")
        if data:
            key_parts.append(f"data:{sorted(data.items())}")
        
        # Create hash for consistent key length
        key_string = "|".join(str(part) for part in key_parts)
        key_hash = hashlib.md5(key_string.encode()).hexdigest()[:16]
        
        return f"service:{service_name}:{method.lower()}:{key_hash}"
    
    def _should_cache_request(self, method: str, service_name: str, endpoint: str) -> bool:
        """Determine if request should be cached"""
        if not self.redis_client:
            return False
        
        # Only cache GET requests by default
        if method.upper() != "GET":
            return False
        
        # Don't cache health checks (they're quick and need real-time status)
        if endpoint.strip('/').lower() == 'health':
            return False
        
        return True
    
    async def _get_cached_response(self, cache_key: str) -> Optional[Union[Dict, list]]:
        """Get cached response if available"""
        if not self.redis_client:
            return None
        
        try:
            cached = self.redis_client.get(cache_key)
            if cached is not None:
                self.logger.debug(f"Cache HIT for key: {cache_key}")
                return cached
        except Exception as e:
            self.logger.warning(f"Cache GET failed for key {cache_key}: {e}")
        
        return None
    
    async def _set_cached_response(self, cache_key: str, response: Union[Dict, list], 
                                  service_name: str) -> bool:
        """Cache response with appropriate TTL"""
        if not self.redis_client:
            return False
        
        try:
            # Use service TTL for inter-service responses
            ttl = self.redis_client.ttl_services
            success = self.redis_client.set(cache_key, response, ttl)
            if success:
                self.logger.debug(f"Cache SET for key: {cache_key} (TTL: {ttl}s)")
            return success
        except Exception as e:
            self.logger.warning(f"Cache SET failed for key {cache_key}: {e}")
            return False
        
    async def get(
        self, 
        service_name: str, 
        endpoint: str, 
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Union[Dict[str, Any], list]:
        """GET zahtev ka drugom servisu"""
        return await self._make_request("GET", service_name, endpoint, params=params, headers=headers)
    
    async def post(
        self, 
        service_name: str, 
        endpoint: str, 
        data: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Union[Dict[str, Any], list]:
        """POST zahtev ka drugom servisu"""
        return await self._make_request("POST", service_name, endpoint, data=data, json_data=json_data, headers=headers)
    
    async def put(
        self, 
        service_name: str, 
        endpoint: str, 
        data: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Union[Dict[str, Any], list]:
        """PUT zahtev ka drugom servisu"""
        return await self._make_request("PUT", service_name, endpoint, data=data, json_data=json_data, headers=headers)
    
    async def delete(
        self, 
        service_name: str, 
        endpoint: str, 
        headers: Optional[Dict[str, str]] = None
    ) -> Union[Dict[str, Any], list]:
        """DELETE zahtev ka drugom servisu"""
        return await self._make_request("DELETE", service_name, endpoint, headers=headers)
    
    async def _make_request(
        self,
        method: str,
        service_name: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Union[Dict[str, Any], list]:
        """Izvršava HTTP zahtev sa retry logikom i caching"""
        
        # Check cache first for eligible requests
        cache_key = None
        should_cache = self._should_cache_request(method, service_name, endpoint)
        
        if should_cache:
            cache_key = self._generate_cache_key(method, service_name, endpoint, params, json_data or data)
            cached_response = await self._get_cached_response(cache_key)
            if cached_response is not None:
                return cached_response
        
        # Cache miss or non-cacheable request - proceed with actual HTTP call
        self.logger.debug(f"Cache MISS for {method} {service_name}{endpoint}")
        
        # Dobijanje URL-a za servis
        base_url = self.service_discovery.get_service_url(service_name)
        if not base_url:
            raise ServiceUnavailableError(f"Service '{service_name}' not found in service discovery")
        
        url = urljoin(base_url, endpoint.lstrip('/'))
        
        # Prepare headers
        request_headers = {"Content-Type": "application/json"}
        if headers:
            request_headers.update(headers)
        
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                self.logger.debug(f"[{service_name}] {method} {url} (attempt {attempt + 1}/{self.max_retries + 1})")
                
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                    kwargs = {
                        "headers": request_headers,
                        "params": params
                    }
                    
                    if json_data is not None:
                        kwargs["json"] = json_data
                    elif data is not None:
                        kwargs["data"] = json.dumps(data)
                    
                    async with session.request(method, url, **kwargs) as response:
                        # Log response status
                        self.logger.debug(f"[{service_name}] Response: {response.status}")
                        
                        if response.status >= 500:
                            # Server error - retry
                            raise ServiceUnavailableError(f"Server error {response.status}: {await response.text()}")
                        
                        if response.status >= 400:
                            # Client error - don't retry
                            error_text = await response.text()
                            raise ServiceClientError(f"Client error {response.status}: {error_text}")
                        
                        # Success response
                        if response.content_type and 'application/json' in response.content_type:
                            result = await response.json()
                        else:
                            result = {"data": await response.text()}
                        
                        # Cache successful response if applicable
                        if should_cache and cache_key and result:
                            await self._set_cached_response(cache_key, result, service_name)
                        
                        return result
                            
            except asyncio.TimeoutError as e:
                last_exception = ServiceTimeoutError(f"Request to {service_name} timed out after {self.timeout}s")
                self.logger.warning(f"[{service_name}] Timeout on attempt {attempt + 1}")
                
            except aiohttp.ClientError as e:
                last_exception = ServiceUnavailableError(f"Connection error to {service_name}: {str(e)}")
                self.logger.warning(f"[{service_name}] Connection error on attempt {attempt + 1}: {e}")
                
            except ServiceUnavailableError as e:
                last_exception = e
                self.logger.warning(f"[{service_name}] Service unavailable on attempt {attempt + 1}: {e}")
                
            except ServiceClientError:
                # Client errors should not be retried
                raise
                
            # Wait before retry (except on last attempt)
            if attempt < self.max_retries:
                delay = self.retry_delay * (2 ** attempt)  # Exponential backoff
                self.logger.debug(f"[{service_name}] Retrying in {delay}s...")
                await asyncio.sleep(delay)
        
        # All retries failed
        self.logger.error(f"[{service_name}] All {self.max_retries + 1} attempts failed")
        raise last_exception or ServiceUnavailableError(f"Service {service_name} unavailable after {self.max_retries + 1} attempts")
    
    async def health_check(self, service_name: str, use_cache: bool = True) -> bool:
        """Proverava da li je servis dostupan"""
        # Health checks can be cached briefly for performance
        cache_key = f"health:{service_name}"
        
        if use_cache and self.redis_client:
            cached_health = self.redis_client.get(cache_key)
            if cached_health is not None:
                self.logger.debug(f"Health check cache HIT for {service_name}")
                return cached_health
        
        try:
            response = await self.get(service_name, "/health")
            is_healthy = response.get("status") == "healthy"
            
            # Cache health check result for short time (1 minute)
            if use_cache and self.redis_client:
                self.redis_client.set(cache_key, is_healthy, ttl=60)
                
            return is_healthy
        except Exception as e:
            self.logger.debug(f"Health check failed for {service_name}: {e}")
            
            # Cache negative result for shorter time (30 seconds)
            if use_cache and self.redis_client:
                self.redis_client.set(cache_key, False, ttl=30)
                
            return False
    
    def invalidate_service_cache(self, service_name: str):
        """Invalidate all cached responses for a specific service"""
        if self.redis_client:
            pattern = f"service:{service_name}:*"
            deleted = self.redis_client.delete_pattern(pattern)
            if deleted > 0:
                self.logger.info(f"Invalidated {deleted} cache entries for service {service_name}")
            return deleted
        return 0