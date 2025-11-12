import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from basify.app import BasifyApp


class TestBasifyApp:
    
    @pytest.fixture
    def sample_app(self):
        """Create a sample BasifyApp for testing"""
        return BasifyApp(
            service_name="test-service",
            version="1.0.0",
            description="Test service"
        )
    
    @pytest.mark.unit
    def test_app_initialization(self, sample_app):
        """Test basic app initialization"""
        assert sample_app.service_name == "test-service"
        assert sample_app.version == "1.0.0"
        assert sample_app.description == "Test service"
        assert sample_app.service_client is not None
        assert sample_app.service_discovery is not None
    
    @pytest.mark.unit
    def test_health_endpoint(self, sample_app):
        """Test health check endpoint"""
        client = TestClient(sample_app.get_app())
        
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "test-service"
        assert data["version"] == "1.0.0"
    
    @pytest.mark.unit
    def test_info_endpoint(self, sample_app):
        """Test service info endpoint"""
        client = TestClient(sample_app.get_app())
        
        response = client.get("/info")
        
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "test-service"
        assert data["version"] == "1.0.0"
        assert data["description"] == "Test service"
    
    @pytest.mark.unit
    def test_services_endpoint_mock(self, sample_app):
        """Test services listing endpoint with mocked service client"""
        client = TestClient(sample_app.get_app())
        
        # Mock the service discovery and health checks
        with patch.object(sample_app.service_discovery, 'list_services') as mock_list, \
             patch.object(sample_app.service_client, 'health_check') as mock_health:
            
            mock_list.return_value = {
                "test-service": "http://test-service:8001",
                "user-service": "http://user-service:8001",
                "order-service": "http://order-service:8002"
            }
            
            # Mock health check to return True for user-service, False for order-service
            async def mock_health_check(service_name):
                if service_name == "user-service":
                    return True
                elif service_name == "order-service":
                    return False
                return True
            
            mock_health.side_effect = mock_health_check
            
            response = client.get("/services")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["current_service"] == "test-service"
            assert "available_services" in data
            assert "user-service" in data["available_services"]
            assert "order-service" in data["available_services"]
            
            # Test-service should not be in the list (it's the current service)
            assert "test-service" not in data["available_services"]
            
            # Check health status
            assert data["available_services"]["user-service"]["status"] == "healthy"
            assert data["available_services"]["order-service"]["status"] == "unhealthy"
    
    @pytest.mark.unit
    def test_add_router(self, sample_app):
        """Test adding a router to the app"""
        from fastapi import APIRouter
        
        router = APIRouter()
        
        @router.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        sample_app.add_router(router, prefix="/api/v1", tags=["test"])
        
        client = TestClient(sample_app.get_app())
        response = client.get("/api/v1/test")
        
        assert response.status_code == 200
        assert response.json() == {"message": "test"}
    
    @pytest.mark.unit
    def test_cors_middleware(self, sample_app):
        """Test CORS middleware is properly configured"""
        client = TestClient(sample_app.get_app())
        
        response = client.options("/health", headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET"
        })
        
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers
    
    @pytest.mark.unit
    def test_logging_setup(self, sample_app):
        """Test that logging is properly configured"""
        assert sample_app.logger is not None
        assert sample_app.logger.name == "test-service"
    
    @pytest.mark.unit
    def test_environment_configuration(self):
        """Test app configuration from environment variables"""
        with patch.dict('os.environ', {
            'DATABASE_URL': 'postgres://test:test@localhost:5432/testdb'
        }):
            app = BasifyApp(service_name="env-test")
            
            assert app.database_url == 'postgres://test:test@localhost:5432/testdb'
    
    @pytest.mark.unit 
    def test_default_description(self):
        """Test default description generation"""
        app = BasifyApp(service_name="my-service")
        assert app.description == "my-service microservice"
    
    @pytest.mark.unit
    def test_custom_cors_origins(self):
        """Test custom CORS origins configuration"""
        app = BasifyApp(
            service_name="test",
            cors_origins=["http://localhost:3000", "https://example.com"]
        )
        
        assert app.cors_origins == ["http://localhost:3000", "https://example.com"]
    
    @pytest.mark.unit
    def test_get_app_returns_fastapi(self, sample_app):
        """Test that get_app returns a FastAPI instance"""
        app = sample_app.get_app()
        
        from fastapi import FastAPI
        assert isinstance(app, FastAPI)
        assert app.title == "test-service"
        assert app.version == "1.0.0"