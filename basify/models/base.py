from tortoise.models import Model
from tortoise import fields
from datetime import datetime
from typing import Optional
from pydantic import BaseModel as PydanticBaseModel
from tortoise.contrib.pydantic import pydantic_model_creator
import logging

logger = logging.getLogger(__name__)


class BaseModel(Model):
    """
    Osnovni model koji nasleđuju svi modeli u aplikaciji.
    Automatski uključuje created_by field ako je auth dostupan.
    """
    id = fields.IntField(pk=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    is_active = fields.BooleanField(default=True)
    
    # Auth integration - optional created_by field
    # Ovo će biti None ako auth nije enabled ili nije dostupan
    created_by = fields.CharField(
        max_length=255, 
        null=True, 
        blank=True,
        description="Username koji je kreirao ovaj entitet"
    )

    class Meta:
        abstract = True

    def __str__(self):
        return f"{self.__class__.__name__}(id={self.id})"
    
    async def set_created_by(self, user_info):
        """
        Helper metoda za postavljanje created_by na osnovu user info.
        Radi sa dict user info ili AnonymousUser objektom.
        """
        from basify.auth.dependencies import AnonymousUser
        
        if isinstance(user_info, AnonymousUser):
            self.created_by = None
        elif isinstance(user_info, dict):
            self.created_by = user_info.get("username")
        else:
            logger.warning(f"Unknown user info type: {type(user_info)}")
            self.created_by = None


class BaseSchema(PydanticBaseModel):
    """
    Osnovni Pydantic schema za serializaciju
    """
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    is_active: Optional[bool] = True
    created_by: Optional[str] = None

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
    # created_by se ne menja pri update-u