import aiohttp
import asyncio
import json
import logging
from typing import Dict, Any, Optional, Union
from urllib.parse import urljoin
from .service_discovery import ServiceDiscovery


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
        service_discovery: Optional[ServiceDiscovery] = None
    ):
        # Load configuration from environment variables
        import os
        self.timeout = timeout or float(os.getenv("SERVICE_CLIENT_TIMEOUT", "5.0"))
        self.max_retries = max_retries or int(os.getenv("SERVICE_CLIENT_MAX_RETRIES", "3"))
        self.retry_delay = retry_delay or float(os.getenv("SERVICE_CLIENT_RETRY_DELAY", "1.0"))
        self.service_discovery = service_discovery or ServiceDiscovery()
        self.logger = logging.getLogger(self.__class__.__name__)
        
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
        """Izvršava HTTP zahtev sa retry logikom"""
        
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
                            return await response.json()
                        else:
                            return {"data": await response.text()}
                            
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
    
    async def health_check(self, service_name: str) -> bool:
        """Proverava da li je servis dostupan"""
        try:
            response = await self.get(service_name, "/health")
            return response.get("status") == "healthy"
        except Exception as e:
            self.logger.debug(f"Health check failed for {service_name}: {e}")
            return False