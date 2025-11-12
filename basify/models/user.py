from tortoise import fields
from .base import BaseModel, BaseSchema, CreateSchema, UpdateSchema
from typing import Optional
from pydantic import EmailStr


class User(BaseModel):
    """
    Osnovni User model koji mogu da koriste svi servisi
    """
    email = fields.CharField(max_length=255, unique=True, index=True)
    username = fields.CharField(max_length=100, unique=True, index=True)
    first_name = fields.CharField(max_length=100)
    last_name = fields.CharField(max_length=100)
    is_verified = fields.BooleanField(default=False)
    
    class Meta:
        table = "users"

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


class UserSchema(BaseSchema):
    """
    Schema za User model
    """
    email: str
    username: str
    first_name: str
    last_name: str
    is_verified: bool
    full_name: Optional[str] = None


class UserCreateSchema(CreateSchema):
    """
    Schema za kreiranje novog korisnika
    """
    email: EmailStr
    username: str
    first_name: str
    last_name: str


class UserUpdateSchema(UpdateSchema):
    """
    Schema za ažuriranje korisnika
    """
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_verified: Optional[bool] = None