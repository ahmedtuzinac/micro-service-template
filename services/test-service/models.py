from basify.models.base import BaseModel, BaseSchema, CreateSchema, UpdateSchema
from tortoise import fields
from typing import Optional


class TestService(BaseModel):
    """
    Model for test-service service
    """
    name = fields.CharField(max_length=255)
    description = fields.TextField(null=True, blank=True)
    
    class Meta:
        table = "test_services"

    def __str__(self):
        return f"{self.name} (ID: {self.id})"


class TestServiceSchema(BaseSchema):
    """
    Schema for TestService model
    """
    name: str
    description: Optional[str] = None


class TestServiceCreateSchema(CreateSchema):
    """
    Schema for creating new TestService
    """
    name: str
    description: Optional[str] = None


class TestServiceUpdateSchema(UpdateSchema):
    """
    Schema for updating TestService
    """
    name: Optional[str] = None
    description: Optional[str] = None