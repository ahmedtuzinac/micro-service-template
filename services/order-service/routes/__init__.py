from fastapi import APIRouter
from .order_service import router as order_service_router

router = APIRouter()

# Include all route modules
router.include_router(order_service_router, prefix="/order_service", tags=["order-service"])