from fastapi import APIRouter
from .auth_service import router as auth_service_router

router = APIRouter()

# Include auth routes
router.include_router(auth_service_router, tags=["authentication"])