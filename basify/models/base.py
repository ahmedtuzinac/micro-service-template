from tortoise.models import Model
from tortoise import fields
from datetime import datetime
from typing import Optional
from pydantic import BaseModel as PydanticBaseModel


class BaseModel(Model):
    """
    Osnovni model koji nasleđuju svi modeli u aplikaciji
    """
    id = fields.IntField(pk=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    is_active = fields.BooleanField(default=True)

    class Meta:
        abstract = True

    def __str__(self):
        return f"{self.__class__.__name__}(id={self.id})"


class BaseSchema(PydanticBaseModel):
    """
    Osnovni Pydantic schema za serializaciju
    """
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    is_active: Optional[bool] = True

    class Config:
        from_attributes = True


class CreateSchema(PydanticBaseModel):
    """
    Schema za kreiranje novih entiteta
    """
    pass


class UpdateSchema(PydanticBaseModel):
    """
    Schema za ažuriranje postojećih entiteta
    """
    is_active: Optional[bool] = None