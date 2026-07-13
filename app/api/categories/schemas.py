"""
Category Pydantic schemas.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from app.core.enums import CategoryType


class CategoryCreate(BaseModel):
    """Create a custom category."""
    name: str = Field(..., min_length=1, max_length=100)
    type: CategoryType = CategoryType.EXPENSE
    icon: Optional[str] = None
    color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")


class CategoryUpdate(BaseModel):
    """Update a custom category."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    type: Optional[CategoryType] = None
    icon: Optional[str] = None
    color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")


class CategoryResponse(BaseModel):
    """Category response."""
    id: str
    name: str
    type: str
    icon: Optional[str] = None
    color: Optional[str] = None
    is_system: bool  # True if system default (user_id is NULL)
    is_active: bool
    created_at: str

    model_config = {"from_attributes": True}
