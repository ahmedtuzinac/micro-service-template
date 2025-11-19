"""
Testovi za JWT Manager functionality
"""
import pytest
import jwt
import os
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, Mock
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../services/auth-service'))

from auth.jwt_manager import JWTManager, JWT_SECRET_KEY, JWT_ALGORITHM, JWT_ISSUER


class TestJWTManager:
    
    @pytest.fixture
    def sample_user_data(self):
        """Sample user data for JWT testing"""
        return {
            "user_id": 1,
            "username": "testuser",
            "roles": ["user", "admin"]
        }
    
    @pytest.mark.auth
    @pytest.mark.unit
    def test_create_access_token(self, sample_user_data):
        """Test access token creation"""
        user_id = sample_user_data["user_id"]
        username = sample_user_data["username"]
        roles = sample_user_data["roles"]
        
        token, expires_at = JWTManager.create_access_token(user_id, username, roles)
        
        # Verify token is string
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Verify expires_at is datetime
        assert isinstance(expires_at, datetime)
        assert expires_at > datetime.now(timezone.utc)
        
        # Decode and verify token content
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        assert payload["user_id"] == user_id
        assert payload["username"] == username
        assert payload["roles"] == roles
        assert payload["token_type"] == "access"
        assert payload["iss"] == JWT_ISSUER
        assert "jti" in payload
        assert "exp" in payload
        assert "iat" in payload
    
    @pytest.mark.auth
    @pytest.mark.unit
    def test_create_access_token_no_roles(self, sample_user_data):
        """Test access token creation without roles"""
        token, expires_at = JWTManager.create_access_token(
            sample_user_data["user_id"], 
            sample_user_data["username"]
        )
        
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        assert payload["roles"] == []
    
    @pytest.mark.auth
    @pytest.mark.unit
    def test_create_refresh_token(self, sample_user_data):
        """Test refresh token creation"""
        user_id = sample_user_data["user_id"]
        
        token, token_id, expires_at = JWTManager.create_refresh_token(user_id)
        
        # Verify token is string
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Verify token_id is string UUID
        assert isinstance(token_id, str)
        assert len(token_id) == 36  # UUID format
        
        # Verify expires_at is datetime and far in future
        assert isinstance(expires_at, datetime)
        assert expires_at > datetime.now(timezone.utc) + timedelta(days=6)
        
        # Decode and verify token content
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        assert payload["user_id"] == user_id
        assert payload["token_type"] == "refresh"
        assert payload["iss"] == JWT_ISSUER
        assert payload["jti"] == token_id
        assert "exp" in payload
        assert "iat" in payload
    
    @pytest.mark.auth
    @pytest.mark.unit
    def test_verify_valid_token(self, sample_user_data):
        """Test verification of valid token"""
        token, _ = JWTManager.create_access_token(
            sample_user_data["user_id"], 
            sample_user_data["username"], 
            sample_user_data["roles"]
        )
        
        payload = JWTManager.verify_token(token)
        
        assert payload is not None
        assert payload["user_id"] == sample_user_data["user_id"]
        assert payload["username"] == sample_user_data["username"]
        assert payload["roles"] == sample_user_data["roles"]
        assert payload["token_type"] == "access"
    
    @pytest.mark.auth
    @pytest.mark.unit
    def test_verify_invalid_token(self):
        """Test verification of invalid token"""
        invalid_token = "invalid.token.here"
        
        payload = JWTManager.verify_token(invalid_token)
        assert payload is None
    
    @pytest.mark.auth
    @pytest.mark.unit
    def test_verify_expired_token(self, sample_user_data):
        """Test verification of expired token"""
        # Create token with past expiration
        past_time = datetime.now(timezone.utc) - timedelta(minutes=5)
        payload = {
            "user_id": sample_user_data["user_id"],
            "username": sample_user_data["username"],
            "roles": sample_user_data["roles"],
            "token_type": "access",
            "exp": past_time,
            "iat": datetime.now(timezone.utc),
            "iss": JWT_ISSUER
        }
        
        expired_token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        
        result = JWTManager.verify_token(expired_token)
        assert result is None
    
    @pytest.mark.auth
    @pytest.mark.unit
    def test_verify_wrong_issuer(self, sample_user_data):
        """Test verification of token with wrong issuer"""
        payload = {
            "user_id": sample_user_data["user_id"],
            "username": sample_user_data["username"],
            "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
            "iss": "wrong-issuer"
        }
        
        wrong_issuer_token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        
        result = JWTManager.verify_token(wrong_issuer_token)
        assert result is None
    
    @pytest.mark.auth
    @pytest.mark.unit
    def test_decode_token_unsafe(self, sample_user_data):
        """Test unsafe token decoding"""
        token, _ = JWTManager.create_access_token(
            sample_user_data["user_id"], 
            sample_user_data["username"]
        )
        
        payload = JWTManager.decode_token_unsafe(token)
        
        assert payload is not None
        assert payload["user_id"] == sample_user_data["user_id"]
        assert payload["username"] == sample_user_data["username"]
    
    @pytest.mark.auth
    @pytest.mark.unit
    def test_decode_token_unsafe_invalid(self):
        """Test unsafe decoding of invalid token"""
        invalid_token = "completely.invalid.token"
        
        payload = JWTManager.decode_token_unsafe(invalid_token)
        assert payload is None
    
    @pytest.mark.auth
    @pytest.mark.unit
    def test_is_token_expired_valid_token(self, sample_user_data):
        """Test expiration check on valid token"""
        token, _ = JWTManager.create_access_token(
            sample_user_data["user_id"], 
            sample_user_data["username"]
        )
        
        is_expired = JWTManager.is_token_expired(token)
        assert is_expired is False
    
    @pytest.mark.auth
    @pytest.mark.unit
    def test_is_token_expired_expired_token(self, sample_user_data):
        """Test expiration check on expired token"""
        # Create token with past expiration
        past_time = datetime.now(timezone.utc) - timedelta(minutes=5)
        payload = {
            "user_id": sample_user_data["user_id"],
            "username": sample_user_data["username"],
            "exp": past_time,
            "iss": JWT_ISSUER
        }
        
        expired_token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        
        is_expired = JWTManager.is_token_expired(expired_token)
        assert is_expired is True
    
    @pytest.mark.auth
    @pytest.mark.unit
    def test_is_token_expired_invalid_token(self):
        """Test expiration check on invalid token"""
        invalid_token = "invalid.token.here"
        
        is_expired = JWTManager.is_token_expired(invalid_token)
        assert is_expired is True
    
    @pytest.mark.auth
    @pytest.mark.unit
    def test_is_token_expired_no_exp_claim(self, sample_user_data):
        """Test expiration check on token without exp claim"""
        payload = {
            "user_id": sample_user_data["user_id"],
            "username": sample_user_data["username"]
            # No 'exp' claim
        }
        
        token_without_exp = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        
        is_expired = JWTManager.is_token_expired(token_without_exp)
        assert is_expired is True
    
    @pytest.mark.auth
    @pytest.mark.unit
    def test_jwt_config_from_environment(self):
        """Test JWT configuration from environment variables"""
        with patch.dict(os.environ, {
            'JWT_SECRET_KEY': 'test-secret-key',
            'JWT_ACCESS_TOKEN_EXPIRE_MINUTES': '30',
            'JWT_REFRESH_TOKEN_EXPIRE_DAYS': '14',
            'JWT_ISSUER': 'test-issuer'
        }):
            # Reload module to pick up new env vars
            import importlib
            import auth.jwt_manager
            importlib.reload(auth.jwt_manager)
            
            from auth.jwt_manager import (
                JWT_SECRET_KEY, 
                JWT_ACCESS_TOKEN_EXPIRE_MINUTES, 
                JWT_REFRESH_TOKEN_EXPIRE_DAYS,
                JWT_ISSUER
            )
            
            assert JWT_SECRET_KEY == 'test-secret-key'
            assert JWT_ACCESS_TOKEN_EXPIRE_MINUTES == 30
            assert JWT_REFRESH_TOKEN_EXPIRE_DAYS == 14
            assert JWT_ISSUER == 'test-issuer'
    
    @pytest.mark.auth
    @pytest.mark.unit
    def test_token_uniqueness(self, sample_user_data):
        """Test that tokens are unique even for same user"""
        user_id = sample_user_data["user_id"]
        username = sample_user_data["username"]
        
        token1, _ = JWTManager.create_access_token(user_id, username)
        token2, _ = JWTManager.create_access_token(user_id, username)
        
        assert token1 != token2
        
        # JTI should be different
        payload1 = JWTManager.decode_token_unsafe(token1)
        payload2 = JWTManager.decode_token_unsafe(token2)
        
        assert payload1["jti"] != payload2["jti"]
    
    @pytest.mark.auth
    @pytest.mark.unit
    def test_refresh_token_uniqueness(self, sample_user_data):
        """Test that refresh tokens are unique"""
        user_id = sample_user_data["user_id"]
        
        token1, token_id1, _ = JWTManager.create_refresh_token(user_id)
        token2, token_id2, _ = JWTManager.create_refresh_token(user_id)
        
        assert token1 != token2
        assert token_id1 != token_id2