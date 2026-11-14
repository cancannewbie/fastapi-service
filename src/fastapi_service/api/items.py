"""CRUD endpoints for items, backed by an in-memory repository.

The repository is a stand-in for a database. Swap it for a real one by
implementing the same methods and wiring it in ``app.py``.
"""

from __future__ import annotations

from datetime import UTC, datetime
from threading import Lock
from typing import Annotated, cast

from fastapi import APIRouter, Depends, Request, Response, status

from ..errors import NotFoundError
from ..schemas import Item, ItemCreate, ItemUpdate

router = APIRouter(prefix="/items", tags=["items"])


class InMemoryItemRepository:
    """Thread-safe dict-backed store for :class:`Item` objects."""

    def __init__(self) -> None:
        self._items: dict[int, Item] = {}
        self._next_id: int = 1
        self._lock = Lock()

    def list(self) -> list[Item]:
        with self._lock:
            return list(self._items.values())

    def get(self, item_id: int) -> Item | None:
        with self._lock:
            return self._items.get(item_id)

    def create(self, data: ItemCreate) -> Item:
        with self._lock:
            item = Item(
                id=self._next_id,
                name=data.name,
                description=data.description,
                price=data.price,
                created_at=datetime.now(UTC),
            )
            self._items[item.id] = item
            self._next_id += 1
            return item

    def update(self, item_id: int, data: ItemUpdate) -> Item | None:
        with self._lock:
            item = self._items.get(item_id)
            if item is None:
                return None
            updated = item.model_copy(update=data.model_dump(exclude_unset=True))
            self._items[item_id] = updated
            return updated

    def delete(self, item_id: int) -> bool:
        with self._lock:
            return self._items.pop(item_id, None) is not None


def get_repository(request: Request) -> InMemoryItemRepository:
    """FastAPI dependency returning the app-scoped repository."""
    return cast(InMemoryItemRepository, request.app.state.repository)


Repository = Annotated[InMemoryItemRepository, Depends(get_repository)]


@router.get("", summary="List items")
async def list_items(repo: Repository) -> list[Item]:
    return repo.list()


@router.post("", summary="Create an item", status_code=status.HTTP_201_CREATED)
async def create_item(payload: ItemCreate, repo: Repository) -> Item:
    return repo.create(payload)


@router.get("/{item_id}", summary="Fetch a single item")
async def get_item(item_id: int, repo: Repository) -> Item:
    item = repo.get(item_id)
    if item is None:
        raise NotFoundError(f"Item {item_id} does not exist")
    return item


@router.patch("/{item_id}", summary="Update an item")
async def update_item(item_id: int, payload: ItemUpdate, repo: Repository) -> Item:
    item = repo.update(item_id, payload)
    if item is None:
        raise NotFoundError(f"Item {item_id} does not exist")
    return item


@router.delete("/{item_id}", summary="Delete an item", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(item_id: int, repo: Repository) -> Response:
    if not repo.delete(item_id):
        raise NotFoundError(f"Item {item_id} does not exist")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
