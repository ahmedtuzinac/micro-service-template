import asyncio
import os
import pytest
import pytest_asyncio
from typing import AsyncGenerator, Generator
from fastapi.testclient import TestClient
from httpx import AsyncClient
from tortoise import Tortoise

# Test environment setup
os.environ["ENVIRONMENT"] = "local"
os.environ["SERVICE_CLIENT_TIMEOUT"] = "2.0"
os.environ["SERVICE_CLIENT_MAX_RETRIES"] = "1"


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def setup_test_db() -> AsyncGenerator[None, None]:
    """Setup test database"""
    # Use SQLite in-memory database for testing
    db_url = "sqlite://:memory:"
    
    await Tortoise.init(
        db_url=db_url,
        modules={"models": ["basify.models.base"]},
        use_tz=True
    )
    
    await Tortoise.generate_schemas()
    
    yield
    
    await Tortoise.close_connections()


@pytest_asyncio.fixture
async def clean_db(setup_test_db) -> AsyncGenerator[None, None]:
    """Clean database before each test"""
    # Clear all tables
    for model in Tortoise.apps.get("models").values():
        if hasattr(model, "all"):
            await model.all().delete()
    
    yield


@pytest.fixture
def user_service_client() -> TestClient:
    """Test client for user-service"""
    from services.user_service.main import app
    return TestClient(app)


@pytest.fixture 
def order_service_client() -> TestClient:
    """Test client for order-service"""
    from services.order_service.main import app
    return TestClient(app)


@pytest_asyncio.fixture
async def async_user_client(setup_test_db) -> AsyncGenerator[AsyncClient, None]:
    """Async test client for user-service"""
    from services.user_service.main import app
    
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        yield client


@pytest_asyncio.fixture
async def async_order_client(setup_test_db) -> AsyncGenerator[AsyncClient, None]:
    """Async test client for order-service"""
    from services.order_service.main import app
    
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        yield client


@pytest.fixture
def mock_service_discovery():
    """Mock service discovery for testing"""
    from basify.clients.service_discovery import ServiceDiscovery
    
    discovery = ServiceDiscovery()
    
    # Override service URLs for testing
    discovery._service_cache = {
        "user-service": "http://localhost:8001",
        "order-service": "http://localhost:8002",
        "flow-service": "http://localhost:8004",
        "test-service": "http://localhost:8003"
    }
    
    return discovery


@pytest.fixture
def mock_service_client(mock_service_discovery):
    """Mock service client for testing"""
    from basify.clients.http_client import ServiceClient
    
    client = ServiceClient(
        timeout=1.0,
        max_retries=1,
        retry_delay=0.1,
        service_discovery=mock_service_discovery
    )
    
    return client


# Common test data
@pytest.fixture
def sample_user_data():
    """Sample user data for testing"""
    return {
        "name": "Test User",
        "email": "test@example.com",
        "is_active": True
    }


@pytest.fixture
def sample_order_data():
    """Sample order data for testing"""
    return {
        "user_id": 1,
        "product_name": "Test Product",
        "quantity": 2,
        "price": 99.99
    }