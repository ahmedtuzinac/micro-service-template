from fastapi import APIRouter, HTTPException, Query, Depends, status
from tortoise.exceptions import DoesNotExist
from typing import List, Optional
from models import Order, OrderSchema, OrderCreateSchema, OrderUpdateSchema

# Import auth dependencies from framework - uvek dostupni sa graceful degradation
from basify.auth import get_current_user, require_admin, optional_user

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
        discovered_services = app_instance.discovered_services
        
        services_status = {}
        for service_name, service_info in discovered_services.items():
            try:
                health_ok = await service_client.health_check(service_name)
                services_status[service_name] = {
                    "url": service_info["url"],
                    "healthy": health_ok,
                    "status": "running" if health_ok else "unhealthy"
                }
            except Exception as e:
                services_status[service_name] = {
                    "url": service_info["url"],
                    "healthy": False,
                    "status": f"error: {str(e)[:50]}..."
                }
        
        return {
            "discovered_services": len(discovered_services),
            "services": services_status
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error checking services: {str(e)}"
        )


@router.get("/info", response_model=dict)
async def service_info():
    """
    Informacije o servisu i auth statusu
    """
    from main import app_instance
    
    # Auth status - uvek proveravamo gracefully
    auth_status = {"available": True}  # Auth dependencies su uvek available
    
    if hasattr(app_instance, 'auth_client') and app_instance.auth_client:
        auth_status["configured"] = True
        auth_status["auth_service_url"] = getattr(app_instance, 'auth_service_url', None)
    else:
        auth_status["configured"] = False
    
    return {
        "service": "order-service",
        "model": "Order",
        "api_prefix": "/orders",
        "auth": auth_status,
        "endpoints": {
            "/orders": "List all order",
            "/orders/{id}": "Get order by ID",
            "/protected": "Protected endpoint (requires auth)",
            "/admin-only": "Admin-only endpoint"
        }
    }


# PROTECTED ROUTE - zahteva JWT token
@router.get("/protected", response_model=dict)
async def protected_endpoint(current_user: dict = Depends(get_current_user)):
    """
    🔐 PROTECTED ENDPOINT - zahteva validan JWT token
    
    Endpoint zaštićen JWT autentifikacijom. 
    Mora se proslediti validan Bearer token u Authorization header-u.
    """
    return {
        "message": "This is a protected endpoint!",
        "user": current_user,
        "timestamp": "2024-01-01T00:00:00Z"
    }


# ADMIN-ONLY ROUTE - zahteva admin role
@router.get("/admin-only", response_model=dict)
async def admin_only_endpoint(admin_user: dict = Depends(require_admin)):
    """
    👑 ADMIN-ONLY ENDPOINT - zahteva admin privilegije
    
    Endpoint dostupan samo korisnicima sa 'admin' rolom.
    """
    return {
        "message": "Admin access granted!",
        "admin": admin_user,
        "timestamp": "2024-01-01T00:00:00Z"
    }


# OPTIONAL AUTH ROUTE - može biti anonymous
@router.get("/optional-auth", response_model=dict)
async def optional_auth_endpoint(user = Depends(optional_user)):
    """
    🔓 OPTIONAL AUTH ENDPOINT - radi sa ili bez auth-a
    
    Endpoint koji može da radi sa authenticated ili anonymous korisnicima.
    """
    from basify.auth.dependencies import AnonymousUser
    
    if isinstance(user, AnonymousUser):
        return {
            "message": "Hello anonymous user!",
            "user_type": "anonymous",
            "timestamp": "2024-01-01T00:00:00Z"
        }
    else:
        return {
            "message": f"Hello {user.get('username', 'authenticated user')}!",
            "user_type": "authenticated", 
            "user": user,
            "timestamp": "2024-01-01T00:00:00Z"
        }


# CRUD ROUTES for Order

@router.get("/orders", response_model=List[OrderSchema])
async def get_order(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of records to return"),
    user = Depends(optional_user)  # Optional auth - track who's accessing
):
    """
    Dobijanje liste svih order sa paginacijom
    """
    order = await Order.all().offset(skip).limit(limit)
    return [OrderSchema.model_validate(obj) for obj in order]


@router.get("/orders/{order_id}", response_model=OrderSchema)
async def get_order_by_id(
    order_id: int,
    user = Depends(optional_user)  # Optional auth
):
    """
    Dobijanje order po ID-ju
    """
    try:
        order = await Order.get(id=order_id)
        return OrderSchema.model_validate(order)
    except DoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )


@router.post("/orders", response_model=OrderSchema, status_code=status.HTTP_201_CREATED)
async def create_order(
    order_data: OrderCreateSchema,
    user = Depends(optional_user)  # Optional auth - track creator
):
    """
    Kreiranje novog order
    """
    # Convert Pydantic model to dict
    order_dict = order_data.dict()
    
    # Create new instance
    order = await Order.create(**order_dict)
    
    # Set created_by if user is authenticated
    await order.set_created_by(user)
    await order.save()
    
    return OrderSchema.model_validate(order)


@router.put("/orders/{order_id}", response_model=OrderSchema)
async def update_order(
    order_id: int,
    order_data: OrderUpdateSchema,
    user = Depends(optional_user)  # Optional auth
):
    """
    Ažuriranje postojećeg order
    """
    try:
        order = await Order.get(id=order_id)
        
        # Update fields that are not None
        update_data = order_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(order, field, value)
            
        await order.save()
        return OrderSchema.model_validate(order)
        
    except DoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )


@router.delete("/orders/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_order(
    order_id: int,
    user = Depends(optional_user)  # Optional auth
):
    """
    Brisanje order po ID-ju
    """
    try:
        order = await Order.get(id=order_id)
        await order.delete()
        
    except DoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )