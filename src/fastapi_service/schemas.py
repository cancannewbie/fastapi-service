"""Pydantic request/response models."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class ItemCreate(BaseModel):
    """Payload for creating an item."""

    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=1000)
    price: float = Field(ge=0)

    @field_validator("name")
    @classmethod
    def _name_must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("name must not be blank")
        return stripped


class ItemUpdate(BaseModel):
    """Payload for partially updating an item. Omitted fields stay unchanged."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    price: float | None = Field(default=None, ge=0)

    @field_validator("name")
    @classmethod
    def _name_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("name must not be blank")
        return stripped


class Item(BaseModel):
    """An item as stored by the service."""

    id: int
    name: str
    description: str | None = None
    price: float
    created_at: datetime
