from basify.models.base import BaseModel, BaseSchema, CreateSchema, UpdateSchema
from tortoise import fields
from typing import Optional


class Order(BaseModel):
    """
    Model for order-service service
    """
    name = fields.CharField(max_length=255)
    description = fields.TextField(null=True, blank=True)
    
    class Meta:
        table = "orders"

    def __str__(self):
        return f"{self.name} (ID: {self.id})"


class OrderSchema(BaseSchema):
    """
    Schema for Order model
    """
    name: str
    description: Optional[str] = None


class OrderCreateSchema(CreateSchema):
    """
    Schema for creating new Order
    """
    name: str
    description: Optional[str] = None


class OrderUpdateSchema(UpdateSchema):
    """
    Schema for updating Order
    """
    name: Optional[str] = None
    description: Optional[str] = None