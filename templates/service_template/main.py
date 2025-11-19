import os
from basify import BasifyApp
from routes import router

# PostgreSQL configuration from environment variables
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")

# Redis cache configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
REDIS_ENABLED = os.getenv("REDIS_ENABLED", "true").lower() == "true"

# Default database URL
DEFAULT_DATABASE_URL = f"postgres://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{{DATABASE_NAME}}"

# Create Basify application instance with modern features
app_instance = BasifyApp(
    service_name="{{SERVICE_NAME}}",
    version="1.0.0",
    description="{{SERVICE_DESCRIPTION}}",
    database_url=os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL),
    models_modules=["models"]
    # Note: Cache and auth are automatically enabled by BasifyApp
    # Cache client available as: app_instance.cache_client
    # Service client available as: app_instance.service_client (with caching enabled)
)

# Add API router
app_instance.add_router(router, prefix="/api/v1", tags=["{{SERVICE_NAME}}"])

# FastAPI application for uvicorn
app = app_instance.get_app()

# Dependency injection helpers
def get_service_client():
    """Get service client for inter-service communication"""
    return app_instance.service_client

def get_cache_client():
    """Get Redis cache client for manual caching"""
    return getattr(app_instance, 'cache_client', None)