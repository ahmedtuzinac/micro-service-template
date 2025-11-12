import pytest
import os
from unittest.mock import patch, mock_open
from basify.app import BasifyApp
from basify.clients.service_discovery import ServiceDiscovery
from basify.clients.http_client import ServiceClient
from fastapi.testclient import TestClient


class TestBasifyIntegration:
    
    @pytest.fixture
    def mock_docker_compose_content(self):
        """Mock docker-compose.yml content for testing"""
        return """
services:
  user-service:
    ports:
      - "8001:8001"
    environment:
      PORT: '8001'
  order-service:
    ports:
      - "8002:8002"  
    environment:
      PORT: '8002'
"""

    @pytest.fixture
    def user_app(self, mock_docker_compose_content):
        """Create a test user service app with mocked compose file"""
        with patch('builtins.open', mock_open(read_data=mock_docker_compose_content)):
            with patch('os.path.exists', return_value=True):
                return BasifyApp(
                    service_name="user-service",
                    version="1.0.0",
                    description="User Service for Testing"
                )
    
    @pytest.fixture  
    def order_app(self, mock_docker_compose_content):
        """Create a test order service app with mocked compose file"""
        with patch('builtins.open', mock_open(read_data=mock_docker_compose_content)):
            with patch('os.path.exists', return_value=True):
                return BasifyApp(
                    service_name="order-service",
                    version="1.0.0", 
                    description="Order Service for Testing"
                )
    
    @pytest.mark.integration
    def test_app_creation_with_service_client(self, user_app):
        """Test that BasifyApp properly creates service client"""
        assert user_app.service_client is not None
        assert isinstance(user_app.service_client, ServiceClient)
        assert user_app.service_discovery is not None
        assert isinstance(user_app.service_discovery, ServiceDiscovery)
    
    @pytest.mark.integration
    def test_service_discovery_across_apps(self, user_app, order_app):
        """Test service discovery works across apps"""
        
        # Both apps should have service discovery configured
        assert user_app.service_discovery is not None
        assert order_app.service_discovery is not None
        
        # Both should be able to resolve the other service
        user_to_order = user_app.service_discovery.get_service_url("order-service")
        order_to_user = order_app.service_discovery.get_service_url("user-service")
        
        assert user_to_order is not None
        assert order_to_user is not None
        
        # URLs should follow expected patterns
        assert "order-service" in user_to_order or "localhost" in user_to_order
        assert "user-service" in order_to_user or "localhost" in order_to_user
    
    @pytest.mark.integration
    def test_health_endpoints_across_services(self, user_app, order_app):
        """Test health endpoints work across different service apps"""
        
        # Create test clients
        user_client = TestClient(user_app.get_app())
        order_client = TestClient(order_app.get_app())
        
        # Test health endpoints
        user_health = user_client.get("/health")
        order_health = order_client.get("/health")
        
        assert user_health.status_code == 200
        assert order_health.status_code == 200
        
        user_data = user_health.json()
        order_data = order_health.json()
        
        assert user_data["service"] == "user-service"
        assert order_data["service"] == "order-service"
        assert user_data["status"] == "healthy"
        assert order_data["status"] == "healthy"
    
    @pytest.mark.integration
    def test_services_endpoint_basic(self, user_app):
        """Test /services endpoint basic functionality"""
        client = TestClient(user_app.get_app())
        
        # Mock service discovery to return multiple services
        with patch.object(user_app.service_discovery, 'list_services') as mock_list, \
             patch.object(user_app.service_client, 'health_check') as mock_health:
            
            mock_list.return_value = {
                "user-service": "http://user-service:8001",
                "order-service": "http://order-service:8002"
            }
            
            # Mock all services as healthy
            mock_health.return_value = True
            
            response = client.get("/services")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["current_service"] == "user-service"
            assert "available_services" in data
            
            services = data["available_services"]
            assert "order-service" in services
            assert "user-service" not in services  # Current service excluded
    
    @pytest.mark.integration
    def test_app_configuration_consistency(self, user_app, order_app):
        """Test that apps are configured consistently"""
        
        # Both apps should have service clients
        assert user_app.service_client is not None
        assert order_app.service_client is not None
        
        # Service clients should have same configuration
        assert user_app.service_client.timeout == order_app.service_client.timeout
        assert user_app.service_client.max_retries == order_app.service_client.max_retries
        
        # Both should have discovery configured
        assert user_app.service_discovery is not None
        assert order_app.service_discovery is not None
        
        # Discovery should be in same environment
        assert user_app.service_discovery.environment == order_app.service_discovery.environment
    
    @pytest.mark.integration
    @patch.dict(os.environ, {'ENVIRONMENT': 'local'})
    def test_environment_switching_local(self, mock_docker_compose_content):
        """Test behavior in local environment"""
        with patch('builtins.open', mock_open(read_data=mock_docker_compose_content)):
            with patch('os.path.exists', return_value=True):
                discovery = ServiceDiscovery()
                url = discovery.get_service_url("user-service")
                
                assert "localhost" in url
                assert discovery.environment == "local"
    
    @pytest.mark.integration
    @patch.dict(os.environ, {'ENVIRONMENT': 'docker'})
    def test_environment_switching_docker(self, mock_docker_compose_content):
        """Test behavior in docker environment"""
        with patch('builtins.open', mock_open(read_data=mock_docker_compose_content)):
            with patch('os.path.exists', return_value=True):
                discovery = ServiceDiscovery()
                url = discovery.get_service_url("user-service")
                
                assert "user-service" in url
                assert discovery.environment == "docker"
    
    @pytest.mark.integration
    def test_middleware_integration(self, user_app):
        """Test that middleware works properly in integration context"""
        
        client = TestClient(user_app.get_app())
        
        # Test CORS headers
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET"
            }
        )
        
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers
        
        # Test that requests are processed with logging middleware
        response = client.get("/health")
        assert response.status_code == 200
        
        # Test error handling middleware
        response = client.get("/nonexistent-endpoint")
        assert response.status_code == 404
    
    @pytest.mark.integration
    def test_service_client_timeout_configuration(self, user_app):
        """Test service client timeout configuration"""
        
        # Should have reasonable default timeout
        assert user_app.service_client.timeout > 0
        assert user_app.service_client.max_retries >= 0
        assert user_app.service_client.retry_delay >= 0
    
    @pytest.mark.integration
    @patch.dict(os.environ, {
        'SERVICE_CLIENT_TIMEOUT': '10.0',
        'SERVICE_CLIENT_MAX_RETRIES': '5'
    })
    def test_service_client_env_var_loading(self):
        """Test service client loads configuration from environment"""
        app = BasifyApp(service_name="test-service")
        
        assert app.service_client.timeout == 10.0
        assert app.service_client.max_retries == 5