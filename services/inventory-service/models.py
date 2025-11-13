from basify.models.base import BaseModel, BaseSchema, CreateSchema, UpdateSchema
from tortoise import fields
from typing import Optional


class Inventory(BaseModel):
    """
    Model for inventory-service service
    """
    name = fields.CharField(max_length=255)
    description = fields.TextField(null=True, blank=True)
    
    class Meta:
        table = "inventorys"

    def __str__(self):
        return f"{self.name} (ID: {self.id})"


class InventorySchema(BaseSchema):
    """
    Schema for Inventory model
    """
    name: str
    description: Optional[str] = None


class InventoryCreateSchema(CreateSchema):
    """
    Schema for creating new Inventory
    """
    name: str
    description: Optional[str] = None


class InventoryUpdateSchema(UpdateSchema):
    """
    Schema for updating Inventory
    """
    name: Optional[str] = None
    description: Optional[str] = None