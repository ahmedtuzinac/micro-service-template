from fastapi import APIRouter
from .user_service import router as user_service_router

router = APIRouter()

# Include all route modules
router.include_router(user_service_router, prefix="/user_service", tags=["user-service"])