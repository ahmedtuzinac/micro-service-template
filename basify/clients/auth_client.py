"""
Auth Client - HTTP klijent za komunikaciju sa auth-service

Omogućava drugim servisima da koriste centralizovan auth sistem.
"""
import aiohttp
import asyncio
from typing import Optional, Dict, Any
import logging
from .http_client import ServiceClient


class AuthClient:
    """
    HTTP klijent za komunikaciju sa auth-service.
    
    Koristi ga drugi servisi za:
    - Token validaciju  
    - User informacije
    - Auth dependency u routes
    """
    
    def __init__(self, auth_service_url: str, service_client: ServiceClient = None):
        self.auth_service_url = auth_service_url.rstrip("/")
        self.service_client = service_client
        self.logger = logging.getLogger("basify.auth_client")
        
    async def validate_token(self, access_token: str) -> Optional[Dict[str, Any]]:
        """
        Validira JWT token preko auth-service.
        
        Args:
            access_token: Bearer token (bez "Bearer " prefiksa)
            
        Returns:
            User info ako je token valjan, None ako nije
        """
        try:
            headers = {"Authorization": f"Bearer {access_token}"}
            
            if self.service_client:
                # Koristi ServiceClient ako je dostupan
                response = await self.service_client.post(
                    "auth-service",
                    "/auth/validate",
                    headers=headers
                )
            else:
                # Direct HTTP poziv
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{self.auth_service_url}/auth/validate",
                        headers=headers
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            return data if data.get("valid") else None
                        return None
                        
            return response if response and response.get("valid") else None
            
        except Exception as e:
            self.logger.error(f"Auth validation error: {e}")
            return None
    
    async def get_user_info(self, access_token: str) -> Optional[Dict[str, Any]]:
        """
        Dobija informacije o korisniku preko access token-a.
        
        Args:
            access_token: Bearer token (bez "Bearer " prefiksa)
            
        Returns:
            User info ili None
        """
        try:
            headers = {"Authorization": f"Bearer {access_token}"}
            
            if self.service_client:
                # Koristi ServiceClient
                response = await self.service_client.get(
                    "auth-service",
                    "/auth/me",
                    headers=headers
                )
                return response
            else:
                # Direct HTTP poziv
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"{self.auth_service_url}/auth/me",
                        headers=headers
                    ) as response:
                        if response.status == 200:
                            return await response.json()
                        return None
                        
        except Exception as e:
            self.logger.error(f"Get user info error: {e}")
            return None
    
    async def health_check(self) -> bool:
        """
        Proverava da li je auth-service dostupan.
        
        Returns:
            True ako je auth-service healthy
        """
        try:
            if self.service_client:
                return await self.service_client.health_check("auth-service")
            else:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{self.auth_service_url}/health") as response:
                        return response.status == 200
                        
        except Exception as e:
            self.logger.error(f"Auth service health check error: {e}")
            return False


class AuthUser:
    """
    User model za use u other services - lightweight verzija.
    Ovo NISU auth tabele, već samo user info dobijen iz auth-service.
    """
    
    def __init__(self, user_data: dict):
        self.id = user_data.get("user_id")
        self.username = user_data.get("username")
        self.email = user_data.get("email")
        self.roles = user_data.get("roles", [])
        self.is_active = user_data.get("is_active", True)
    
    def has_role(self, role_name: str) -> bool:
        """Proverava da li korisnik ima određenu rolu"""
        return role_name in self.roles
    
    def has_any_role(self, role_names: list) -> bool:
        """Proverava da li korisnik ima bilo koju od rola"""
        return any(role in self.roles for role in role_names)
    
    def __str__(self):
        return f"AuthUser({self.username})"
    
    def __repr__(self):
        return f"AuthUser(id={self.id}, username='{self.username}', roles={self.roles})"


def create_auth_dependency(auth_client: AuthClient):
    """
    Factory funkcija za kreiranje auth dependency.
    
    Usage in service routes:
    ```python
    from main import app_instance
    get_current_user = create_auth_dependency(app_instance.auth_client)
    
    @router.get("/protected")
    async def protected_endpoint(user=Depends(get_current_user)):
        return {"user_id": user.id}
    ```
    """
    from fastapi import Depends, HTTPException, status
    from fastapi.security import HTTPBearer
    
    security = HTTPBearer()
    
    async def get_current_user(token = Depends(security)) -> AuthUser:
        """Dependency za dobijanje trenutnog korisnika"""
        
        if not auth_client:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Auth service nije konfigurisan"
            )
        
        user_data = await auth_client.validate_token(token.credentials)
        if not user_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return AuthUser(user_data)
    
    return get_current_user


def create_role_dependency(auth_client: AuthClient, required_role: str):
    """
    Factory za kreiranje role-based dependency.
    
    Usage:
    ```python
    require_admin = create_role_dependency(auth_client, "admin")
    
    @router.delete("/admin-action")
    async def admin_only(user=Depends(require_admin)):
        return {"message": "Admin action"}
    ```
    """
    from fastapi import Depends, HTTPException, status
    
    get_current_user = create_auth_dependency(auth_client)
    
    async def require_role(user: AuthUser = Depends(get_current_user)) -> AuthUser:
        """Dependency za role-based access control"""
        
        if not user.has_role(required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{required_role}' required"
            )
        
        return user
    
    return require_role