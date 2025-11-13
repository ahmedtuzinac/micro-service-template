"""
Auth Service Models - Centralized Authentication
"""
from basify.models.base import BaseModel
from tortoise import fields
from tortoise.models import Model
from typing import Optional, List
from pydantic import BaseModel as PydanticModel, EmailStr
from datetime import datetime
from enum import Enum


class RoleType(str, Enum):
    """Predefined role types"""
    ADMIN = "admin"
    USER = "user" 
    SERVICE = "service"


class AuthUser(Model):
    """
    Central User model for authentication.
    Ovo je jedino mesto gde se čuvaju korisnici u sistemu.
    """
    id = fields.IntField(pk=True)
    
    # Basic user info
    email = fields.CharField(max_length=255, unique=True, index=True)
    username = fields.CharField(max_length=100, unique=True, index=True)
    first_name = fields.CharField(max_length=100)
    last_name = fields.CharField(max_length=100)
    
    # Auth fields
    password_hash = fields.TextField()
    is_active = fields.BooleanField(default=True)
    is_verified = fields.BooleanField(default=False)
    is_superuser = fields.BooleanField(default=False)
    
    # Timestamps
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    last_login = fields.DatetimeField(null=True)
    
    # Relations
    roles: fields.ManyToManyRelation["Role"] = fields.ManyToManyField(
        "models.Role", 
        related_name="users",
        through="user_roles"
    )
    
    refresh_tokens: fields.ReverseRelation["RefreshToken"]
    
    class Meta:
        table = "auth_users"
        
    def __str__(self) -> str:
        return f"{self.username} ({self.email})"
    
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


class Role(Model):
    """Role model za RBAC sistem"""
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=100, unique=True)
    display_name = fields.CharField(max_length=200)
    description = fields.TextField(null=True)
    is_active = fields.BooleanField(default=True)
    
    # Timestamps
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    
    # Relations
    permissions: fields.ManyToManyRelation["Permission"] = fields.ManyToManyField(
        "models.Permission",
        related_name="roles", 
        through="role_permissions"
    )
    
    users: fields.ManyToManyRelation[AuthUser]
    
    class Meta:
        table = "auth_roles"
        
    def __str__(self) -> str:
        return self.display_name or self.name


class Permission(Model):
    """Permission model za granular access control"""
    id = fields.IntField(pk=True)
    code = fields.CharField(max_length=100, unique=True)  # e.g., "read:users", "write:orders"
    name = fields.CharField(max_length=200)
    description = fields.TextField(null=True)
    resource = fields.CharField(max_length=100)  # e.g., "users", "orders"
    action = fields.CharField(max_length=50)     # e.g., "read", "write", "delete"
    is_active = fields.BooleanField(default=True)
    
    # Timestamps
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    
    # Relations
    roles: fields.ManyToManyRelation[Role]
    
    class Meta:
        table = "auth_permissions"
        
    def __str__(self) -> str:
        return f"{self.code} - {self.name}"


class RefreshToken(Model):
    """Refresh token model za secure token management"""
    id = fields.IntField(pk=True)
    token_id = fields.CharField(max_length=255, unique=True)  # JWT jti claim
    user: fields.ForeignKeyRelation[AuthUser] = fields.ForeignKeyField(
        "models.AuthUser", 
        related_name="refresh_tokens"
    )
    expires_at = fields.DatetimeField()
    is_revoked = fields.BooleanField(default=False)
    
    # Timestamps
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    
    # Optional tracking
    device_info = fields.CharField(max_length=500, null=True)
    ip_address = fields.CharField(max_length=45, null=True)
    
    class Meta:
        table = "auth_refresh_tokens"
        
    def __str__(self) -> str:
        return f"RefreshToken for {self.user.username}"


# Pydantic schemas za API

class UserCreateSchema(PydanticModel):
    """Schema za registraciju novog korisnika"""
    email: EmailStr
    username: str
    first_name: str
    last_name: str
    password: str


class UserResponseSchema(PydanticModel):
    """Schema za user response (bez password)"""
    id: int
    email: str
    username: str
    first_name: str
    last_name: str
    full_name: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_login: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class LoginSchema(PydanticModel):
    """Schema za login request"""
    email: str
    password: str


class TokenResponseSchema(PydanticModel):
    """Schema za token response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class RefreshTokenSchema(PydanticModel):
    """Schema za refresh token request"""
    refresh_token: str