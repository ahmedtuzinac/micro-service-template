from fastapi import APIRouter
from .test_service import router as test_service_router

router = APIRouter()

# Include all route modules
router.include_router(test_service_router, prefix="/test_service", tags=["test-service"])