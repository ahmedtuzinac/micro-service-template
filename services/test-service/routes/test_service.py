from fastapi import APIRouter, HTTPException, Query, Depends, status
from fastapi.security import HTTPBearer
from tortoise.exceptions import DoesNotExist
from typing import List, Optional
from models import TestService, TestServiceSchema, TestServiceCreateSchema, TestServiceUpdateSchema

router = APIRouter()


def get_service_client():
    """Dependency injection za service client"""
    from main import app_instance
    return app_instance.service_client


# Specific routes MUST be before parametric routes to avoid conflicts

@router.get("/services", response_model=dict)  
async def list_available_services(service_client=Depends(get_service_client)):
    """
    Lista dostupnih servisa i njihov health status
    """
    try:
        from main import app_instance
        services = app_instance.service_discovery.list_services()
        
        # Ukloni trenutni servis iz liste
        current_service = "test-service"
        if current_service in services:
            services.pop(current_service)
        
        # Proveri health status svih servisa
        service_status = {}
        for service_name, service_url in services.items():
            try:
                is_healthy = await service_client.health_check(service_name)
                service_status[service_name] = {
                    "url": service_url,
                    "healthy": is_healthy,
                    "status": "online" if is_healthy else "offline"
                }
            except Exception as e:
                service_status[service_name] = {
                    "url": service_url,
                    "healthy": False,
                    "status": "error",
                    "error": str(e)
                }
        
        return {
            "current_service": current_service,
            "available_services": service_status,
            "total_services": len(service_status)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get services: {str(e)}")


# Auth dependency helper functions
async def get_auth_client():
    """Helper za dobijanje auth client-a"""
    from main import app_instance
    if not app_instance.auth_client:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Auth service nije konfigurisan. Postavi AUTH_SERVICE_URL environment variable."
        )
    return app_instance.auth_client


async def get_current_user(token: str = Depends(HTTPBearer())):
    """
    Auth dependency za dobijanje trenutnog korisnika
    Koristi auth-service za validaciju tokena
    """
    auth_client = await get_auth_client()
    
    # Validira token preko auth-service
    user_info = await auth_client.validate_token(token.credentials)
    if not user_info or not user_info.get("valid"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user_info


async def require_admin(current_user: dict = Depends(get_current_user)):
    """Auth dependency za admin-only endpoints"""
    user_roles = current_user.get("roles", [])
    if "admin" not in user_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


# Auth-protected endpoint primer (demo)
@router.get("/profile", response_model=dict)
async def get_user_profile():
    """
    Demo endpoint - pokazuje da li je auth konfigurisan
    """
    # Lazy import da izbegnem circular import
    from main import app_instance
    
    if not app_instance.auth_client:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Auth service nije konfigurisan. Postavi AUTH_SERVICE_URL environment variable."
        )
    
    return {
        "message": "Auth is configured! Check /protected endpoint for real auth example.",
        "service": "test-service",
        "auth_service_url": app_instance.auth_service_url,
        "endpoints": {
            "/protected": "Requires valid JWT token",
            "/admin-only": "Requires admin role"
        }
    }


# PROTECTED ROUTE - requires JWT token
@router.get("/protected", response_model=dict)
async def protected_endpoint(current_user: dict = Depends(get_current_user)):
    """
    🔐 PROTECTED ENDPOINT - zahteva validan JWT token
    
    Test sa:
    curl -H "Authorization: Bearer YOUR_JWT_TOKEN" http://localhost:PORT/api/v1/test_service/protected
    """
    return {
        "message": "✅ Success! You are authenticated.",
        "service": "test-service",
        "user_info": {
            "user_id": current_user.get("user_id"),
            "username": current_user.get("username"),
            "email": current_user.get("email"),
            "roles": current_user.get("roles", [])
        },
        "endpoint": "protected",
        "timestamp": "now"
    }


# ADMIN-ONLY ROUTE - requires admin role
@router.get("/admin-only", response_model=dict)
async def admin_only_endpoint(admin_user: dict = Depends(require_admin)):
    """
    🔐 ADMIN-ONLY ENDPOINT - zahteva admin role
    
    Test sa admin JWT tokenom:
    curl -H "Authorization: Bearer ADMIN_JWT_TOKEN" http://localhost:PORT/api/v1/test_service/admin-only
    """
    return {
        "message": "✅ Admin access granted!",
        "service": "test-service",
        "admin_info": {
            "user_id": admin_user.get("user_id"),
            "username": admin_user.get("username"),
            "roles": admin_user.get("roles", [])
        },
        "endpoint": "admin-only",
        "permissions": "full_access"
    }


@router.get("/", response_model=List[TestServiceSchema])
async def list_test_service(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    is_active: Optional[bool] = Query(None)
):
    """
    List all test_service
    """
    query = TestService.all()
    
    if is_active is not None:
        query = query.filter(is_active=is_active)
    
    test_service = await query.offset(skip).limit(limit)
    return [TestServiceSchema.model_validate(item) for item in test_service]


@router.get("/{item_id}", response_model=TestServiceSchema)
async def get_test_service_by_id(item_id: int):
    """
    Get test_service by ID
    """
    try:
        item = await TestService.get(id=item_id)
        return TestServiceSchema.model_validate(item)
    except DoesNotExist:
        raise HTTPException(status_code=404, detail="TestService not found")


@router.post("/", response_model=TestServiceSchema, status_code=201)
async def create_test_service(item_data: TestServiceCreateSchema):
    """
    Create new test_service
    """
    item = await TestService.create(**item_data.model_dump())
    return TestServiceSchema.model_validate(item)


@router.put("/{item_id}", response_model=TestServiceSchema)
async def update_test_service(item_id: int, item_data: TestServiceUpdateSchema):
    """
    Update test_service
    """
    try:
        item = await TestService.get(id=item_id)
        update_data = {k: v for k, v in item_data.model_dump().items() if v is not None}
        
        if update_data:
            await item.update_from_dict(update_data)
            await item.save()
        
        return TestServiceSchema.model_validate(item)
    except DoesNotExist:
        raise HTTPException(status_code=404, detail="TestService not found")


@router.delete("/{item_id}", status_code=204)
async def delete_test_service(item_id: int, hard_delete: bool = Query(False)):
    """
    Delete test_service (soft delete by default)
    """
    try:
        item = await TestService.get(id=item_id)
        
        if hard_delete:
            await item.delete()
        else:
            item.is_active = False
            await item.save()
            
    except DoesNotExist:
        raise HTTPException(status_code=404, detail="TestService not found")