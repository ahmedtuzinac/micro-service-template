"""
Auth Service Routes - Centralized Authentication Endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer
from tortoise.exceptions import DoesNotExist, IntegrityError
from typing import List
from datetime import datetime, timezone

from models import (
    AuthUser, Role, Permission, RefreshToken,
    UserCreateSchema, UserResponseSchema, 
    LoginSchema, TokenResponseSchema, RefreshTokenSchema
)
from auth.password import hash_password, verify_password, validate_password_strength
from auth.jwt_manager import JWTManager

router = APIRouter()
security = HTTPBearer()


async def get_current_user(token: str = Depends(security)) -> AuthUser:
    """Dependency za dobijanje trenutnog korisnika iz JWT token-a"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    payload = JWTManager.verify_token(token.credentials)
    if payload is None:
        raise credentials_exception
    
    user_id = payload.get("user_id")
    if user_id is None:
        raise credentials_exception
    
    try:
        user = await AuthUser.get(id=user_id, is_active=True)
        return user
    except DoesNotExist:
        raise credentials_exception


@router.post("/register", response_model=UserResponseSchema, status_code=status.HTTP_201_CREATED)
async def register_user(user_data: UserCreateSchema):
    """Registracija novog korisnika"""
    
    # Validacija password strength
    is_valid, error_msg = validate_password_strength(user_data.password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )
    
    # Hash password
    hashed_password = hash_password(user_data.password)
    
    try:
        # Kreacija korisnika
        user = await AuthUser.create(
            email=user_data.email,
            username=user_data.username,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            password_hash=hashed_password
        )
        
        # Dodeli default "user" role
        user_role, _ = await Role.get_or_create(
            name="user",
            defaults={
                "display_name": "Standard User",
                "description": "Default role for registered users"
            }
        )
        await user.roles.add(user_role)
        
        return UserResponseSchema.model_validate(user)
        
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User sa tim email-om ili username-om već postoji"
        )


@router.post("/login", response_model=TokenResponseSchema)
async def login_user(login_data: LoginSchema):
    """Login korisnika i generisanje JWT tokena"""
    
    try:
        user = await AuthUser.get(email=login_data.email, is_active=True)
    except DoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Verify password
    if not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Get user roles
    user_roles = await user.roles.all()
    role_names = [role.name for role in user_roles]
    
    # Generate tokens
    access_token, access_expires = JWTManager.create_access_token(
        user_id=user.id,
        username=user.username,
        roles=role_names
    )
    refresh_token, token_id, refresh_expires = JWTManager.create_refresh_token(user.id)
    
    # Save refresh token u bazi
    await RefreshToken.create(
        token_id=token_id,
        user=user,
        expires_at=refresh_expires
    )
    
    # Update last login
    user.last_login = datetime.now(timezone.utc)
    await user.save()
    
    return TokenResponseSchema(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=15 * 60  # 15 minutes in seconds
    )


@router.post("/refresh", response_model=TokenResponseSchema)
async def refresh_access_token(refresh_data: RefreshTokenSchema):
    """Refresh access token koristeći refresh token"""
    
    payload = JWTManager.verify_token(refresh_data.refresh_token)
    if payload is None or payload.get("token_type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    token_id = payload.get("jti")
    user_id = payload.get("user_id")
    
    try:
        # Proveri da li refresh token postoji u bazi i da nije revoked
        refresh_token = await RefreshToken.get(
            token_id=token_id,
            user_id=user_id,
            is_revoked=False
        )
        
        # Proveri da li je user aktivan
        user = await AuthUser.get(id=user_id, is_active=True)
        
        # Get user roles
        user_roles = await user.roles.all()
        role_names = [role.name for role in user_roles]
        
        # Generate novi access token
        access_token, access_expires = JWTManager.create_access_token(
            user_id=user.id,
            username=user.username,
            roles=role_names
        )
        
        return TokenResponseSchema(
            access_token=access_token,
            refresh_token=refresh_data.refresh_token,  # Keep isti refresh token
            expires_in=15 * 60  # 15 minutes in seconds
        )
        
    except DoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )


@router.post("/logout")
async def logout_user(refresh_data: RefreshTokenSchema):
    """Logout korisnika (revoke refresh token)"""
    
    payload = JWTManager.verify_token(refresh_data.refresh_token)
    if payload is None or payload.get("token_type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    token_id = payload.get("jti")
    
    try:
        refresh_token = await RefreshToken.get(token_id=token_id)
        refresh_token.is_revoked = True
        await refresh_token.save()
        
        return {"message": "Successfully logged out"}
        
    except DoesNotExist:
        return {"message": "Token already invalid"}


@router.get("/me", response_model=UserResponseSchema)
async def get_current_user_info(user: AuthUser = Depends(get_current_user)):
    """Dobij informacije o trenutnom korisniku"""
    return UserResponseSchema.model_validate(user)


@router.post("/validate")
async def validate_token(token: str = Depends(security)):
    """
    Endpoint za validaciju tokena - koristi ga drugi servisi
    
    Vraća user info ako je token valjan
    """
    try:
        user = await get_current_user(token)
        user_roles = await user.roles.all()
        role_names = [role.name for role in user_roles]
        
        return {
            "valid": True,
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
            "roles": role_names,
            "is_active": user.is_active
        }
    except HTTPException:
        return {"valid": False}


@router.get("/users", response_model=List[UserResponseSchema])
async def list_users(current_user: AuthUser = Depends(get_current_user)):
    """Lista svih korisnika - admin only endpoint"""
    
    # Proveri admin role
    user_roles = await current_user.roles.all()
    role_names = [role.name for role in user_roles]
    
    if "admin" not in role_names and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    users = await AuthUser.all()
    return [UserResponseSchema.model_validate(user) for user in users]