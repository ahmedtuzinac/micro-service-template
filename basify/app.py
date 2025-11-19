from typing import Optional, List, Callable, Any
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager
import logging
import os
from .database import init_db, close_db
from .middleware.logging import LoggingMiddleware
from .middleware.error import ErrorHandlerMiddleware
from .clients.http_client import ServiceClient
from .clients.service_discovery import ServiceDiscovery


class BasifyApp:
    def __init__(
        self,
        service_name: str,
        version: str = "1.0.0",
        description: str = "",
        database_url: Optional[str] = None,
        models_modules: List[str] = None,
        cors_origins: List[str] = None,
        trusted_hosts: List[str] = None,
        auth_service_url: Optional[str] = None,
    ):
        self.service_name = service_name
        self.version = version
        self.description = description or f"{service_name} microservice"
        self.database_url = database_url or os.getenv("DATABASE_URL")
        self.models_modules = models_modules or []
        self.cors_origins = cors_origins or ["*"]
        self.trusted_hosts = trusted_hosts or ["*"]
        self.auth_service_url = auth_service_url or os.getenv("AUTH_SERVICE_URL")
        
        # Setup logging
        self._setup_logging()
        
        # Initialize service client with caching
        self.service_discovery = ServiceDiscovery()
        self.service_client = ServiceClient(
            service_discovery=self.service_discovery,
            enable_cache=True  # Enable caching for better performance
        )
        
        # Initialize Redis cache client
        try:
            from .cache import get_redis_client
            self.cache_client = get_redis_client()
            self.logger.info("Redis cache client initialized")
        except ImportError:
            self.cache_client = None
            self.logger.warning("Redis cache not available - install redis package for better performance")
        
        # Initialize auth client (optional)
        self.auth_client = None
        self._init_auth_client()
        
        # Initialize FastAPI app
        self.app = self._create_app()
        
    def _setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format=f"[{self.service_name}] %(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        self.logger = logging.getLogger(self.service_name)
    
    def _init_auth_client(self):
        """
        Inicijalizuje auth client - prvo pokušava AUTH_SERVICE_URL,
        zatim auto-detektuje auth-service preko service discovery
        """
        auth_url = self.auth_service_url
        
        # Ako nema eksplicitno setovanu URL, pokušaj auto-detekciju
        if not auth_url:
            try:
                services = self.service_discovery.list_services()
                if "auth-service" in services:
                    auth_url = services["auth-service"]
                    self.auth_service_url = auth_url
                    self.logger.info(f"Auto-detected auth-service at: {auth_url}")
            except Exception as e:
                self.logger.debug(f"Auth service auto-detection failed: {e}")
        
        # Inicijalizuj auth client ako imamo URL
        if auth_url:
            from .clients.auth_client import AuthClient
            self.auth_client = AuthClient(auth_url, self.service_client)
            self.logger.info(f"Auth client initialized for: {auth_url}")
        else:
            self.logger.info("Auth client not initialized - no auth-service found")

    @asynccontextmanager
    async def lifespan(self, app: FastAPI):
        if self.database_url:
            await init_db(
                database_url=self.database_url,
                models_modules=self.models_modules
            )
            self.logger.info("Database connected")
        
        self.logger.info(f"{self.service_name} started")
        yield
        
        if self.database_url:
            await close_db()
            self.logger.info("Database disconnected")
        
        self.logger.info(f"{self.service_name} stopped")

    def _create_app(self) -> FastAPI:
        app = FastAPI(
            title=self.service_name,
            description=self.description,
            version=self.version,
            lifespan=self.lifespan
        )
        
        # Add middleware
        self._add_middleware(app)
        
        # Add default routes
        self._add_default_routes(app)
        
        return app

    def _add_middleware(self, app: FastAPI):
        # Error handling middleware
        app.add_middleware(ErrorHandlerMiddleware)
        
        # Logging middleware
        app.add_middleware(LoggingMiddleware, service_name=self.service_name)
        
        # CORS middleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=self.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Trusted host middleware
        if "*" not in self.trusted_hosts:
            app.add_middleware(TrustedHostMiddleware, allowed_hosts=self.trusted_hosts)

    def _add_default_routes(self, app: FastAPI):
        @app.get("/health")
        async def health_check():
            return {
                "status": "healthy",
                "service": self.service_name,
                "version": self.version
            }

        @app.get("/info")
        async def service_info():
            return {
                "service": self.service_name,
                "version": self.version,
                "description": self.description
            }
        
        @app.get("/services")
        async def list_services():
            """Lista svih dostupnih servisa u sistemu"""
            services = self.service_discovery.list_services()
            service_status = {}
            
            for service_name, service_url in services.items():
                if service_name != self.service_name:  # Ne proveravaj sebe
                    is_healthy = await self.service_client.health_check(service_name)
                    service_status[service_name] = {
                        "url": service_url,
                        "status": "healthy" if is_healthy else "unhealthy"
                    }
            
            return {
                "current_service": self.service_name,
                "available_services": service_status
            }

    def add_router(self, router, prefix: str = "", tags: List[str] = None):
        self.app.include_router(router, prefix=prefix, tags=tags or [])
        
    def add_middleware(self, middleware_class, **kwargs):
        self.app.add_middleware(middleware_class, **kwargs)
        
    def get_app(self) -> FastAPI:
        return self.app