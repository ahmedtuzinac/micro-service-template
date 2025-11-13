"""
Auth Dependencies Module

Centralized authentication dependencies for use across all services.
Extracted from service templates to reduce code duplication.

Features graceful degradation - auth endpoints uvek postoje,
ali rade sa anonymous korisnicima kada auth-service nije dostupan.
"""

from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Dict, Any, Union
import logging


logger = logging.getLogger(__name__)
security = HTTPBearer(auto_error=False)  # Ne baca grešku automatski


class AnonymousUser:
    """Predstavlja anonimnog korisnika kada auth nije dostupan"""
    
    def __init__(self):
        self.id = None
        self.username = "anonymous"
        self.email = None
        self.roles = []
        self.is_authenticated = False
        self.is_admin = False
        
    def get(self, key: str, default=None):
        """Dict-like pristup attributima"""
        return getattr(self, key, default)
        
    def dict(self):
        return {
            "id": self.id,
            "username": self.username, 
            "email": self.email,
            "roles": self.roles,
            "is_authenticated": self.is_authenticated,
            "is_admin": self.is_admin
        }


async def get_auth_client():
    """
    Helper za dobijanje auth client-a sa lazy initialization.
    
    Returns:
        AuthClient instance ili None ako nije dostupan
        
    Raises:
        Exception: Ako app instance nije pronađen
    """
    # Import here to avoid circular imports during framework initialization
    from basify.app import BasifyApp
    
    # Get current app instance - this assumes there's a way to get it
    # This is a simplified version - in practice you might need app context
    try:
        # This is a temporary solution - you might need to adjust based on your app structure
        import main
        app_instance = main.app_instance
    except (ImportError, AttributeError):
        logger.warning("Could not access app instance for auth client")
        return None
    
    # Ako auth_client nije inicijalizovan, pokušaj ponovo
    if not app_instance.auth_client:
        try:
            app_instance._init_auth_client()
        except Exception as e:
            logger.warning(f"Failed to initialize auth client: {e}")
            
    return app_instance.auth_client


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    allow_anonymous: bool = False
) -> Union[Dict[str, Any], AnonymousUser]:
    """
    Dobija trenutnog korisnika iz JWT tokena sa graceful degradation.
    
    Args:
        credentials: JWT token iz Authorization header-a
        allow_anonymous: Da li je dozvoljen anonymous pristup
        
    Returns:
        Dict sa podacima o korisniku ili AnonymousUser
        
    Raises:
        HTTPException: Samo ako auth je obavezan i token nije valjan
    """
    # Ako nema token
    if not credentials:
        if allow_anonymous:
            logger.debug("No auth token provided, returning anonymous user")
            return AnonymousUser()
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    try:
        auth_client = await get_auth_client()
        
        if not auth_client:
            logger.warning("Auth service not available")
            if allow_anonymous:
                return AnonymousUser()
            else:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Authentication service unavailable",
                )
        
        # Validacija tokena preko auth servisa
        user_info = await auth_client.validate_token(credentials.credentials)
        
        if not user_info or not user_info.get("valid"):
            if allow_anonymous:
                logger.warning("Invalid token provided, fallback to anonymous")
                return AnonymousUser()
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        
        # Auth service vraća user podatke direktno, ne u "user" key
        user_data = dict(user_info)  # Kopiraj user_info
        user_data["is_authenticated"] = True
        return user_data
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.error(f"Auth service error: {e}")
        
        if allow_anonymous:
            logger.info("Auth service down, fallback to anonymous user")
            return AnonymousUser()
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service unavailable",
            )


async def require_admin(
    current_user: Union[Dict[str, Any], AnonymousUser] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Auth dependency za admin-only endpoints.
    
    Args:
        current_user: User info from get_current_user dependency
        
    Returns:
        Dict sa admin user informacijama
        
    Raises:
        HTTPException: Ako user nema admin privilegije
    """
    # Proveri da li je AnonymousUser
    if isinstance(current_user, AnonymousUser):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required for admin access"
        )
        
    user_roles = current_user.get("roles", [])
    if "admin" not in user_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


async def optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Union[Dict[str, Any], AnonymousUser]:
    """
    Opciono dobijanje korisnika - uvek vraća korisnika ili anonymous.
    
    Args:
        credentials: Opcioni JWT token
        
    Returns:
        Dict sa podacima o korisniku ili AnonymousUser
    """
    return await get_current_user(credentials, allow_anonymous=True)


# Convenience function for role-based access
def require_role(role_name: str):
    """
    Factory function za kreiranje role-specific dependencies.
    
    Args:
        role_name: Ime role koji se zahteva
        
    Returns:
        Dependency function
        
    Example:
        require_moderator = require_role("moderator")
        
        @router.get("/moderate")
        async def moderate_content(user=Depends(require_moderator)):
            ...
    """
    async def role_dependency(
        current_user: Union[Dict[str, Any], AnonymousUser] = Depends(get_current_user)
    ) -> Dict[str, Any]:
        # Proveri da li je AnonymousUser
        if isinstance(current_user, AnonymousUser):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Authentication required for role '{role_name}'"
            )
            
        user_roles = current_user.get("roles", [])
        if role_name not in user_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{role_name}' required"
            )
        return current_user
    
    return role_dependency


# Convenience function for permission-based access  
def require_permission(permission: str):
    """
    Factory function za kreiranje permission-specific dependencies.
    
    Args:
        permission: Permission string (e.g., "read:users", "write:orders")
        
    Returns:
        Dependency function
        
    Example:
        require_user_write = require_permission("write:users")
        
        @router.post("/users")
        async def create_user(user=Depends(require_user_write)):
            ...
    """
    async def permission_dependency(
        current_user: Union[Dict[str, Any], AnonymousUser] = Depends(get_current_user)
    ) -> Dict[str, Any]:
        # Proveri da li je AnonymousUser
        if isinstance(current_user, AnonymousUser):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Authentication required for permission '{permission}'"
            )
            
        user_permissions = current_user.get("permissions", [])
        if permission not in user_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission}' required"
            )
        return current_user
    
    return permission_dependency