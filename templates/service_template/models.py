from basify.models.base import BaseModel, BaseSchema, CreateSchema, UpdateSchema
from tortoise import fields
from typing import Optional


class {{MODEL_NAME}}(BaseModel):
    """
    Model for {{SERVICE_NAME}} service
    """
    name = fields.CharField(max_length=255)
    description = fields.TextField(null=True, blank=True)
    
    class Meta:
        table = "{{TABLE_NAME}}"

    def __str__(self):
        return f"{self.name} (ID: {self.id})"


class {{MODEL_NAME}}Schema(BaseSchema):
    """
    Schema for {{MODEL_NAME}} model
    """
    name: str
    description: Optional[str] = None


class {{MODEL_NAME}}CreateSchema(CreateSchema):
    """
    Schema for creating new {{MODEL_NAME}}
    """
    name: str
    description: Optional[str] = None


class {{MODEL_NAME}}UpdateSchema(UpdateSchema):
    """
    Schema for updating {{MODEL_NAME}}
    """
    name: Optional[str] = None
    description: Optional[str] = None