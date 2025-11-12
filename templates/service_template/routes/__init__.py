from fastapi import APIRouter
from .{{ROUTE_NAME}} import router as {{ROUTE_NAME}}_router

router = APIRouter()

# Include all route modules
router.include_router({{ROUTE_NAME}}_router, prefix="/{{ROUTE_PREFIX}}", tags=["{{SERVICE_NAME}}"])