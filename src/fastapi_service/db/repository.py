"""Data access for items.

``ItemRepository`` is the protocol the API layer depends on; the SQLAlchemy
implementation is swappable for another backend without touching the routes.
"""

from __future__ import annotations

from datetime import UTC
from decimal import Decimal
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..schemas import Item, ItemCreate, ItemUpdate
from .models import ItemModel

__all__ = ["ItemRepository", "SqlAlchemyItemRepository"]


class ItemRepository(Protocol):
    """Storage operations the routes need."""

    async def list(self) -> list[Item]: ...

    async def get(self, item_id: int) -> Item | None: ...

    async def create(self, data: ItemCreate) -> Item: ...

    async def update(self, item_id: int, data: ItemUpdate) -> Item | None: ...

    async def delete(self, item_id: int) -> bool: ...


def _to_item(model: ItemModel) -> Item:
    """Convert an ORM row into the API representation."""
    created_at = model.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=UTC)
    return Item(
        id=model.id,
        name=model.name,
        description=model.description,
        price=float(model.price),
        # The database renders timestamptz in its own session timezone;
        # the API always speaks UTC.
        created_at=created_at.astimezone(UTC),
    )


class SqlAlchemyItemRepository:
    """PostgreSQL-backed implementation of :class:`ItemRepository`."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(self) -> list[Item]:
        result = await self._session.execute(select(ItemModel).order_by(ItemModel.id))
        return [_to_item(model) for model in result.scalars().all()]

    async def get(self, item_id: int) -> Item | None:
        model = await self._session.get(ItemModel, item_id)
        return _to_item(model) if model is not None else None

    async def create(self, data: ItemCreate) -> Item:
        model = ItemModel(
            name=data.name,
            description=data.description,
            price=Decimal(str(data.price)),
        )
        self._session.add(model)
        await self._session.commit()
        await self._session.refresh(model)
        return _to_item(model)

    async def update(self, item_id: int, data: ItemUpdate) -> Item | None:
        model = await self._session.get(ItemModel, item_id)
        if model is None:
            return None
        for field, value in data.model_dump(exclude_unset=True).items():
            if field == "price":
                value = Decimal(str(value))
            setattr(model, field, value)
        await self._session.commit()
        await self._session.refresh(model)
        return _to_item(model)

    async def delete(self, item_id: int) -> bool:
        model = await self._session.get(ItemModel, item_id)
        if model is None:
            return False
        await self._session.delete(model)
        await self._session.commit()
        return True
