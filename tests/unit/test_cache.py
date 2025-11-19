"""
Unit tests for Redis Cache functionality
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock

from basify.cache.redis_client import RedisClient, get_redis_client, reset_redis_client
from basify.cache.decorators import cache_result, cache_user_session, invalidate_cache


class TestRedisClient:
    """Test Redis client functionality"""
    
    def test_redis_client_disabled(self):
        """Test Redis client when disabled"""
        client = RedisClient(enabled=False)
        assert not client.is_available()
        assert client.get("test_key") is None
        assert not client.set("test_key", "test_value")
    
    @patch('basify.cache.redis_client.REDIS_AVAILABLE', False)
    def test_redis_client_package_not_available(self):
        """Test Redis client when redis package not installed"""
        client = RedisClient(enabled=True)
        assert not client.is_available()
        assert client.get("test_key") is None
    
    @patch('basify.cache.redis_client.redis')
    def test_redis_client_connection_success(self, mock_redis):
        """Test successful Redis connection"""
        # Mock Redis client
        mock_redis_instance = Mock()
        mock_redis_instance.ping.return_value = True
        mock_redis.Redis.return_value = mock_redis_instance
        
        client = RedisClient(enabled=True)
        assert client.is_available()
    
    @patch('basify.cache.redis_client.redis')
    def test_redis_client_connection_failure(self, mock_redis):
        """Test Redis connection failure"""
        # Mock Redis connection failure
        mock_redis.Redis.side_effect = Exception("Connection failed")
        
        client = RedisClient(enabled=True)
        assert not client.is_available()
    
    @patch('basify.cache.redis_client.redis')
    def test_redis_client_get_set(self, mock_redis):
        """Test Redis get/set operations"""
        import json
        
        # Mock Redis client
        mock_redis_instance = Mock()
        mock_redis_instance.ping.return_value = True
        mock_redis_instance.get.return_value = json.dumps({"test": "value"}).encode()
        mock_redis_instance.setex.return_value = True
        mock_redis.Redis.return_value = mock_redis_instance
        
        client = RedisClient(enabled=True)
        
        # Test set
        result = client.set("test_key", {"test": "value"}, 300)
        assert result is True
        
        # Test get
        result = client.get("test_key")
        assert result == {"test": "value"}
    
    @patch('basify.cache.redis_client.redis')
    def test_redis_client_graceful_degradation(self, mock_redis):
        """Test graceful degradation on Redis errors"""
        # Mock Redis client that works initially but then fails
        mock_redis_instance = Mock()
        mock_redis_instance.ping.return_value = True
        mock_redis_instance.get.side_effect = Exception("Redis error")
        mock_redis_instance.setex.side_effect = Exception("Redis error")
        mock_redis.Redis.return_value = mock_redis_instance
        
        client = RedisClient(enabled=True)
        
        # Should return default values on errors
        assert client.get("test_key", "default") == "default"
        assert client.set("test_key", "value") is False


class TestCacheDecorators:
    """Test cache decorators"""
    
    @pytest.fixture(autouse=True)
    def setup_mock_redis(self):
        """Setup mock Redis client for tests"""
        with patch('basify.cache.decorators.get_redis_client') as mock_get_client:
            self.mock_redis_client = Mock()
            mock_get_client.return_value = self.mock_redis_client
            
            # Default behavior - cache miss
            self.mock_redis_client.get.return_value = None
            self.mock_redis_client.set.return_value = True
            self.mock_redis_client.ttl_default = 300
            self.mock_redis_client.ttl_auth = 900
            
            yield
    
    def test_cache_result_sync_function(self):
        """Test cache_result decorator with sync function"""
        call_count = 0
        
        @cache_result(ttl=300, prefix="test")
        def test_function(x, y):
            nonlocal call_count
            call_count += 1
            return x + y
        
        # First call - cache miss
        result = test_function(1, 2)
        assert result == 3
        assert call_count == 1
        self.mock_redis_client.get.assert_called_once()
        self.mock_redis_client.set.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cache_result_async_function(self):
        """Test cache_result decorator with async function"""
        call_count = 0
        
        @cache_result(ttl=300, prefix="test")
        async def test_async_function(x, y):
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)  # Simulate async work
            return x * y
        
        # First call - cache miss
        result = await test_async_function(3, 4)
        assert result == 12
        assert call_count == 1
        self.mock_redis_client.get.assert_called_once()
        self.mock_redis_client.set.assert_called_once()
    
    def test_cache_result_cache_hit(self):
        """Test cache_result decorator with cache hit"""
        # Mock cache hit
        self.mock_redis_client.get.return_value = "cached_result"
        
        call_count = 0
        
        @cache_result(ttl=300)
        def test_function():
            nonlocal call_count
            call_count += 1
            return "fresh_result"
        
        # Should return cached result without calling function
        result = test_function()
        assert result == "cached_result"
        assert call_count == 0
        self.mock_redis_client.get.assert_called_once()
        self.mock_redis_client.set.assert_not_called()
    
    def test_cache_user_session_decorator(self):
        """Test cache_user_session decorator"""
        call_count = 0
        
        @cache_user_session(ttl=600)
        def validate_user(user_id, token):
            nonlocal call_count
            call_count += 1
            return {"user_id": user_id, "valid": True}
        
        # First call - cache miss
        result = validate_user(123, "token123")
        assert result == {"user_id": 123, "valid": True}
        assert call_count == 1
        
        # Should use auth TTL by default if ttl not specified
        @cache_user_session()
        def validate_token(token):
            return {"valid": True}
        
        validate_token("test_token")
        # Check that it uses auth TTL
        calls = self.mock_redis_client.set.call_args_list
        assert any(call[0][2] == 900 for call in calls)  # Should use ttl_auth
    
    @pytest.mark.asyncio
    async def test_invalidate_cache_decorator(self):
        """Test invalidate_cache decorator"""
        self.mock_redis_client.delete_pattern.return_value = 5
        
        @invalidate_cache(patterns=["user:{0}:*", "session:*"])
        async def update_user(user_id, **data):
            return {"user_id": user_id, "updated": True}
        
        result = await update_user(123, name="John")
        assert result == {"user_id": 123, "updated": True}
        
        # Should call delete_pattern for each pattern
        assert self.mock_redis_client.delete_pattern.call_count == 2
        calls = self.mock_redis_client.delete_pattern.call_args_list
        assert calls[0][0][0] == "user:123:*"  # Pattern with user_id substituted
        assert calls[1][0][0] == "session:*"
    
    def test_cache_decorators_without_redis(self):
        """Test that decorators work gracefully without Redis"""
        with patch('basify.cache.decorators.get_redis_client') as mock_get_client:
            mock_client = Mock()
            mock_client.get.return_value = None  # Always cache miss
            mock_client.set.return_value = False  # Can't cache
            mock_get_client.return_value = mock_client
            
            call_count = 0
            
            @cache_result(ttl=300)
            def test_function():
                nonlocal call_count
                call_count += 1
                return "result"
            
            # Should still work, just without caching
            result = test_function()
            assert result == "result"
            assert call_count == 1


class TestServiceClientCaching:
    """Test ServiceClient caching integration"""
    
    def test_should_cache_request(self):
        """Test _should_cache_request logic"""
        from basify.clients.http_client import ServiceClient
        from basify.clients.service_discovery import ServiceDiscovery
        
        with patch('basify.cache.redis_client.redis'):
            client = ServiceClient(service_discovery=ServiceDiscovery(), enable_cache=True)
            
            # Should cache GET requests
            assert client._should_cache_request("GET", "user-service", "/api/users/123")
            
            # Should not cache POST/PUT/DELETE
            assert not client._should_cache_request("POST", "user-service", "/api/users")
            assert not client._should_cache_request("PUT", "user-service", "/api/users/123")
            assert not client._should_cache_request("DELETE", "user-service", "/api/users/123")
            
            # Should not cache health checks
            assert not client._should_cache_request("GET", "user-service", "/health")
            assert not client._should_cache_request("GET", "user-service", "health")
    
    def test_generate_cache_key(self):
        """Test cache key generation"""
        from basify.clients.http_client import ServiceClient
        from basify.clients.service_discovery import ServiceDiscovery
        
        with patch('basify.cache.redis_client.redis'):
            client = ServiceClient(service_discovery=ServiceDiscovery(), enable_cache=True)
            
            # Test basic key generation
            key1 = client._generate_cache_key("GET", "user-service", "/api/users/123")
            key2 = client._generate_cache_key("GET", "user-service", "/api/users/123")
            assert key1 == key2  # Same inputs should produce same key
            
            # Different params should produce different keys
            key3 = client._generate_cache_key("GET", "user-service", "/api/users", {"page": 1})
            key4 = client._generate_cache_key("GET", "user-service", "/api/users", {"page": 2})
            assert key3 != key4
            
            # Keys should be consistent and contain service name
            assert "user-service" in key1
            assert key1.startswith("service:")


@pytest.fixture
def reset_global_client():
    """Reset global Redis client after each test"""
    yield
    reset_redis_client()


def test_get_redis_client_singleton(reset_global_client):
    """Test that get_redis_client returns singleton"""
    client1 = get_redis_client()
    client2 = get_redis_client()
    assert client1 is client2