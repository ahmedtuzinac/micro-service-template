from basify.models.base import BaseModel, BaseSchema, CreateSchema, UpdateSchema
from tortoise import fields
from typing import Optional


class UserService(BaseModel):
    """
    Model for user-service service
    """
    name = fields.CharField(max_length=255)
    description = fields.TextField(null=True, blank=True)
    
    class Meta:
        table = "user_services"

    def __str__(self):
        return f"{self.name} (ID: {self.id})"


class UserServiceSchema(BaseSchema):
    """
    Schema for UserService model
    """
    name: str
    description: Optional[str] = None


class UserServiceCreateSchema(CreateSchema):
    """
    Schema for creating new UserService
    """
    name: str
    description: Optional[str] = None


class UserServiceUpdateSchema(UpdateSchema):
    """
    Schema for updating UserService
    """
    name: Optional[str] = None
    description: Optional[str] = None