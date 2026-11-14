"""CRUD endpoints for items, backed by PostgreSQL.

The routes depend on the :class:`ItemRepository` protocol, so the storage
backend can be swapped without touching this module.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.repository import ItemRepository, SqlAlchemyItemRepository
from ..db.session import get_session
from ..errors import NotFoundError
from ..schemas import Item, ItemCreate, ItemUpdate

router = APIRouter(prefix="/items", tags=["items"])


def get_repository(session: Annotated[AsyncSession, Depends(get_session)]) -> ItemRepository:
    """FastAPI dependency returning a repository bound to the request session."""
    return SqlAlchemyItemRepository(session)


Repository = Annotated[ItemRepository, Depends(get_repository)]


@router.get("", summary="List items")
async def list_items(repo: Repository) -> list[Item]:
    return await repo.list()


@router.post("", summary="Create an item", status_code=status.HTTP_201_CREATED)
async def create_item(payload: ItemCreate, repo: Repository) -> Item:
    return await repo.create(payload)


@router.get("/{item_id}", summary="Fetch a single item")
async def get_item(item_id: int, repo: Repository) -> Item:
    item = await repo.get(item_id)
    if item is None:
        raise NotFoundError(f"Item {item_id} does not exist")
    return item


@router.patch("/{item_id}", summary="Update an item")
async def update_item(item_id: int, payload: ItemUpdate, repo: Repository) -> Item:
    item = await repo.update(item_id, payload)
    if item is None:
        raise NotFoundError(f"Item {item_id} does not exist")
    return item


@router.delete("/{item_id}", summary="Delete an item", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(item_id: int, repo: Repository) -> Response:
    if not await repo.delete(item_id):
        raise NotFoundError(f"Item {item_id} does not exist")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
