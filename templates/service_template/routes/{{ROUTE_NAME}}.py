from fastapi import APIRouter, HTTPException, Query, Depends
from tortoise.exceptions import DoesNotExist
from typing import List, Optional
from models import {{MODEL_NAME}}, {{MODEL_NAME}}Schema, {{MODEL_NAME}}CreateSchema, {{MODEL_NAME}}UpdateSchema

router = APIRouter()


def get_service_client():
    """Dependency injection za service client"""
    from main import app_instance
    return app_instance.service_client


@router.get("/", response_model=List[{{MODEL_NAME}}Schema])
async def list_{{ROUTE_NAME}}(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    is_active: Optional[bool] = Query(None)
):
    """
    List all {{ROUTE_NAME}}
    """
    query = {{MODEL_NAME}}.all()
    
    if is_active is not None:
        query = query.filter(is_active=is_active)
    
    {{ROUTE_NAME}} = await query.offset(skip).limit(limit)
    return [{{MODEL_NAME}}Schema.model_validate(item) for item in {{ROUTE_NAME}}]


@router.get("/{item_id}", response_model={{MODEL_NAME}}Schema)
async def get_{{ROUTE_NAME}}_by_id(item_id: int):
    """
    Get {{ROUTE_NAME}} by ID
    """
    try:
        item = await {{MODEL_NAME}}.get(id=item_id)
        return {{MODEL_NAME}}Schema.model_validate(item)
    except DoesNotExist:
        raise HTTPException(status_code=404, detail="{{MODEL_NAME}} not found")


@router.post("/", response_model={{MODEL_NAME}}Schema, status_code=201)
async def create_{{ROUTE_NAME}}(item_data: {{MODEL_NAME}}CreateSchema):
    """
    Create new {{ROUTE_NAME}}
    """
    item = await {{MODEL_NAME}}.create(**item_data.model_dump())
    return {{MODEL_NAME}}Schema.model_validate(item)


@router.put("/{item_id}", response_model={{MODEL_NAME}}Schema)
async def update_{{ROUTE_NAME}}(item_id: int, item_data: {{MODEL_NAME}}UpdateSchema):
    """
    Update {{ROUTE_NAME}}
    """
    try:
        item = await {{MODEL_NAME}}.get(id=item_id)
        update_data = {k: v for k, v in item_data.model_dump().items() if v is not None}
        
        if update_data:
            await item.update_from_dict(update_data)
            await item.save()
        
        return {{MODEL_NAME}}Schema.model_validate(item)
    except DoesNotExist:
        raise HTTPException(status_code=404, detail="{{MODEL_NAME}} not found")


@router.delete("/{item_id}", status_code=204)
async def delete_{{ROUTE_NAME}}(item_id: int, hard_delete: bool = Query(False)):
    """
    Delete {{ROUTE_NAME}} (soft delete by default)
    """
    try:
        item = await {{MODEL_NAME}}.get(id=item_id)
        
        if hard_delete:
            await item.delete()
        else:
            item.is_active = False
            await item.save()
            
    except DoesNotExist:
        raise HTTPException(status_code=404, detail="{{MODEL_NAME}} not found")


@router.get("/services", response_model=dict)
async def list_available_services(service_client=Depends(get_service_client)):
    """
    Lista dostupnih servisa i njihov health status
    """
    try:
        from main import app_instance
        services = app_instance.service_discovery.list_services()
        
        # Ukloni trenutni servis iz liste
        current_service = "{{SERVICE_NAME}}"
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