import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch
import aiohttp
from basify.clients.http_client import (
    ServiceClient, 
    ServiceClientError, 
    ServiceUnavailableError, 
    ServiceTimeoutError
)
from basify.clients.service_discovery import ServiceDiscovery


class TestServiceClient:
    
    @pytest.fixture
    def mock_discovery(self):
        """Create mock service discovery"""
        discovery = Mock(spec=ServiceDiscovery)
        discovery.get_service_url.return_value = "http://test-service:8001"
        return discovery
    
    @pytest.fixture
    def service_client(self, mock_discovery):
        """Create service client with mock discovery"""
        return ServiceClient(
            timeout=1.0,
            max_retries=1,
            retry_delay=0.1,
            service_discovery=mock_discovery
        )
    
    @pytest.mark.unit
    def test_service_discovery_called(self, service_client, mock_discovery):
        """Test that service discovery is properly called"""
        url = service_client.service_discovery.get_service_url("test-service")
        assert url == "http://test-service:8001"
        mock_discovery.get_service_url.assert_called_once_with("test-service")
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_service_not_found_in_discovery(self, service_client):
        """Test behavior when service is not found in discovery"""
        service_client.service_discovery.get_service_url.return_value = None
        
        with pytest.raises(ServiceUnavailableError, match="Service 'unknown-service' not found"):
            await service_client.get("unknown-service", "/api/test")
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_health_check_with_mocked_response(self, service_client, mock_discovery):
        """Test health check with mocked aiohttp response"""
        
        async def mock_get(service_name, endpoint):
            if endpoint == "/health":
                return {"status": "healthy"}
            raise Exception("Unexpected endpoint")
        
        # Patch the get method of the service client
        with patch.object(service_client, 'get', side_effect=mock_get):
            result = await service_client.health_check("test-service")
            assert result is True
    
    @pytest.mark.unit
    @pytest.mark.asyncio 
    async def test_health_check_unhealthy(self, service_client, mock_discovery):
        """Test health check when service returns unhealthy"""
        
        async def mock_get(service_name, endpoint):
            if endpoint == "/health":
                return {"status": "unhealthy"}
            raise Exception("Unexpected endpoint")
        
        with patch.object(service_client, 'get', side_effect=mock_get):
            result = await service_client.health_check("test-service")
            assert result is False
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_health_check_exception(self, service_client, mock_discovery):
        """Test health check when get method raises exception"""
        
        async def mock_get(service_name, endpoint):
            raise ServiceUnavailableError("Service down")
        
        with patch.object(service_client, 'get', side_effect=mock_get):
            result = await service_client.health_check("test-service")
            assert result is False
    
    @pytest.mark.unit
    def test_initialization_with_env_vars(self):
        """Test initialization with environment variables"""
        with patch.dict('os.environ', {
            'SERVICE_CLIENT_TIMEOUT': '10.0',
            'SERVICE_CLIENT_MAX_RETRIES': '5',
            'SERVICE_CLIENT_RETRY_DELAY': '2.0'
        }):
            client = ServiceClient()
            
            assert client.timeout == 10.0
            assert client.max_retries == 5
            assert client.retry_delay == 2.0
    
    @pytest.mark.unit 
    def test_initialization_with_custom_values(self):
        """Test initialization with custom values overriding env vars"""
        with patch.dict('os.environ', {
            'SERVICE_CLIENT_TIMEOUT': '10.0',
        }):
            client = ServiceClient(timeout=3.0)
            
            assert client.timeout == 3.0  # Custom value should override env var
    
    @pytest.mark.unit
    def test_service_discovery_integration(self, service_client):
        """Test that service client has service discovery properly set"""
        assert service_client.service_discovery is not None
        assert hasattr(service_client.service_discovery, 'get_service_url')
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_make_request_service_not_found(self, service_client):
        """Test _make_request when service discovery returns None"""
        service_client.service_discovery.get_service_url.return_value = None
        
        with pytest.raises(ServiceUnavailableError, match="not found in service discovery"):
            await service_client._make_request("GET", "nonexistent-service", "/api/test")