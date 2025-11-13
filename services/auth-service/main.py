import os
from basify import BasifyApp
from routes import router

# PostgreSQL konfiguracija iz environment varijabli
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")

# Default database URL
DEFAULT_DATABASE_URL = f"postgres://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/auth_db"

# Kreiranje Basify aplikacije
app_instance = BasifyApp(
    service_name="auth-service",
    version="1.0.0",
    description="Auth Service",
    database_url=os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL),
    models_modules=["models", "basify.models.user"]
)

# Dodavanje auth router-a
app_instance.add_router(router, prefix="/auth", tags=["authentication"])

# FastAPI aplikacija za uvicorn
app = app_instance.get_app()