from fastapi import APIRouter
from .inventory_service import router as inventory_service_router

router = APIRouter()

# Include all route modules
router.include_router(inventory_service_router, prefix="/inventory_service", tags=["inventory-service"])