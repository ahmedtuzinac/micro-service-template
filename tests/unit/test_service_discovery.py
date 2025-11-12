import os
import pytest
import tempfile
from unittest.mock import patch, mock_open
from basify.clients.service_discovery import ServiceDiscovery


class TestServiceDiscovery:
    
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
    def discovery_with_mock_compose(self, mock_docker_compose_content):
        """Create a ServiceDiscovery instance with mocked compose file"""
        with patch('builtins.open', mock_open(read_data=mock_docker_compose_content)):
            with patch('os.path.exists', return_value=True):
                return ServiceDiscovery()
    
    def test_init_default_environment(self, discovery_with_mock_compose):
        """Test initialization with default environment"""
        assert discovery_with_mock_compose.environment in ["local", "docker"]
        assert isinstance(discovery_with_mock_compose._available_services, dict)
        assert "user-service" in discovery_with_mock_compose._available_services
    
    @patch.dict(os.environ, {"ENVIRONMENT": "local"})
    def test_local_environment(self, mock_docker_compose_content):
        """Test service discovery in local environment"""
        with patch('builtins.open', mock_open(read_data=mock_docker_compose_content)):
            with patch('os.path.exists', return_value=True):
                discovery = ServiceDiscovery()
                assert discovery.environment == "local"
                
                url = discovery.get_service_url("user-service")
                assert url == "http://localhost:8001"
    
    @patch.dict(os.environ, {"ENVIRONMENT": "docker"})
    def test_docker_environment(self, mock_docker_compose_content):
        """Test service discovery in docker environment"""
        with patch('builtins.open', mock_open(read_data=mock_docker_compose_content)):
            with patch('os.path.exists', return_value=True):
                discovery = ServiceDiscovery()
                assert discovery.environment == "docker"
                
                url = discovery.get_service_url("user-service")
                assert url == "http://user-service:8001"
    
    @patch.dict(os.environ, {"USER_SERVICE_URL": "http://custom-host:9001"})
    def test_explicit_service_url(self, discovery_with_mock_compose):
        """Test explicit service URL override"""
        url = discovery_with_mock_compose.get_service_url("user-service")
        assert url == "http://custom-host:9001"
    
    @patch.dict(os.environ, {"USER_SERVICE_PORT": "9999"})
    def test_explicit_service_port(self, discovery_with_mock_compose):
        """Test explicit service port override"""
        url = discovery_with_mock_compose.get_service_url("user-service")
        
        if discovery_with_mock_compose.environment == "local":
            assert "localhost:9999" in url
        else:
            assert "user-service:9999" in url
    
    def test_unknown_service(self, discovery_with_mock_compose):
        """Test behavior with unknown service"""
        url = discovery_with_mock_compose.get_service_url("unknown-service")
        assert url is None
    
    def test_register_service(self, discovery_with_mock_compose):
        """Test manual service registration"""
        discovery_with_mock_compose.register_service("test-service", "http://test-host:8080")
        
        url = discovery_with_mock_compose.get_service_url("test-service")
        assert url == "http://test-host:8080"
    
    def test_unregister_service(self, discovery_with_mock_compose):
        """Test service unregistration"""
        discovery_with_mock_compose.register_service("unknown-service", "http://test-host:8080")
        
        # Verify it's registered
        url_before = discovery_with_mock_compose.get_service_url("unknown-service")
        assert url_before == "http://test-host:8080"
        
        # Unregister it
        discovery_with_mock_compose.unregister_service("unknown-service")
        
        # Should fall back to default behavior (None for unknown service)
        url_after = discovery_with_mock_compose.get_service_url("unknown-service")
        assert url_after is None  # No default port for unknown-service
    
    def test_list_services(self, discovery_with_mock_compose):
        """Test listing all services"""
        discovery_with_mock_compose.register_service("custom-service", "http://custom-host:8080")
        
        services = discovery_with_mock_compose.list_services()
        
        assert isinstance(services, dict)
        assert "custom-service" in services
        assert services["custom-service"] == "http://custom-host:8080"
        
        # Check that services from compose are included
        assert "user-service" in services
        assert "order-service" in services
    
    def test_clear_cache(self, discovery_with_mock_compose):
        """Test cache clearing"""
        discovery_with_mock_compose.register_service("test-service", "http://test-host:8080")
        assert "test-service" in discovery_with_mock_compose._service_cache
        
        discovery_with_mock_compose.clear_cache()
        assert len(discovery_with_mock_compose._service_cache) == 0
        
        # Service should still be discoverable via compose file
        url = discovery_with_mock_compose.get_service_url("user-service")
        assert url is not None
    
    @pytest.mark.unit
    def test_service_name_normalization(self, discovery_with_mock_compose):
        """Test that service names are handled consistently"""
        # Test with different service name formats
        url1 = discovery_with_mock_compose.get_service_url("user-service")
        url2 = discovery_with_mock_compose.get_service_url("user_service")  # Should not work
        
        assert url1 is not None
        assert url2 is None  # Different name format should not work