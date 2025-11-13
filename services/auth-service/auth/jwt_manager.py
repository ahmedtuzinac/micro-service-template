"""
JWT Token Management za auth-service
"""
import jwt
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any


# JWT Configuration iz environment varijabli
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
JWT_REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7"))
JWT_ISSUER = os.getenv("JWT_ISSUER", "auth-service")


class JWTManager:
    """JWT token manager za auth-service"""
    
    @staticmethod
    def create_access_token(user_id: int, username: str, roles: list = None) -> tuple[str, datetime]:
        """
        Kreira JWT access token
        
        Returns:
            (token, expires_at)
        """
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        
        payload = {
            "user_id": user_id,
            "username": username,
            "roles": roles or [],
            "token_type": "access",
            "exp": expires_at,
            "iat": datetime.now(timezone.utc),
            "iss": JWT_ISSUER,
            "jti": str(uuid.uuid4())
        }
        
        token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        return token, expires_at
    
    @staticmethod
    def create_refresh_token(user_id: int) -> tuple[str, str, datetime]:
        """
        Kreira JWT refresh token
        
        Returns:
            (token, token_id, expires_at)
        """
        token_id = str(uuid.uuid4())
        expires_at = datetime.now(timezone.utc) + timedelta(days=JWT_REFRESH_TOKEN_EXPIRE_DAYS)
        
        payload = {
            "user_id": user_id,
            "token_type": "refresh",
            "exp": expires_at,
            "iat": datetime.now(timezone.utc),
            "iss": JWT_ISSUER,
            "jti": token_id
        }
        
        token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        return token, token_id, expires_at
    
    @staticmethod
    def verify_token(token: str) -> Optional[Dict[str, Any]]:
        """
        Verifikuje JWT token
        
        Returns:
            Decoded payload ili None ako je token invalid
        """
        try:
            payload = jwt.decode(
                token, 
                JWT_SECRET_KEY, 
                algorithms=[JWT_ALGORITHM],
                issuer=JWT_ISSUER
            )
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    @staticmethod
    def decode_token_unsafe(token: str) -> Optional[Dict[str, Any]]:
        """
        Dekoduje token bez verifikacije (za debug)
        
        Returns:
            Decoded payload ili None
        """
        try:
            payload = jwt.decode(token, options={"verify_signature": False})
            return payload
        except jwt.InvalidTokenError:
            return None
    
    @staticmethod
    def is_token_expired(token: str) -> bool:
        """Proverava da li je token expired"""
        payload = JWTManager.decode_token_unsafe(token)
        if not payload:
            return True
        
        exp = payload.get("exp")
        if not exp:
            return True
        
        # exp je timestamp, konvertuj u datetime
        exp_datetime = datetime.fromtimestamp(exp, tz=timezone.utc)
        return datetime.now(timezone.utc) > exp_datetime