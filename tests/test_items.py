"""Tests for the items CRUD endpoints (backed by PostgreSQL)."""

from __future__ import annotations

from datetime import datetime, timedelta

from httpx import AsyncClient

ITEMS = "/api/v1/items"


async def test_create_and_read_item(client: AsyncClient) -> None:
    created = await client.post(ITEMS, json={"name": "Widget", "price": 9.99})
    assert created.status_code == 201
    body = created.json()
    assert body["id"] == 1
    assert body["name"] == "Widget"
    assert body["price"] == 9.99
    assert body["description"] is None

    created_at = datetime.fromisoformat(body["created_at"])
    assert created_at.utcoffset() == timedelta(0)

    fetched = await client.get(f"{ITEMS}/{body['id']}")
    assert fetched.status_code == 200
    assert fetched.json() == body


async def test_list_items(client: AsyncClient) -> None:
    assert (await client.get(ITEMS)).json() == []

    await client.post(ITEMS, json={"name": "A", "price": 1.0})
    await client.post(ITEMS, json={"name": "B", "price": 2.0})

    listed = await client.get(ITEMS)
    assert listed.status_code == 200
    assert [item["name"] for item in listed.json()] == ["A", "B"]


async def test_update_item_only_touches_provided_fields(client: AsyncClient) -> None:
    item_id = (await client.post(ITEMS, json={"name": "Widget", "price": 9.99})).json()["id"]

    updated = await client.patch(f"{ITEMS}/{item_id}", json={"price": 12.5})
    assert updated.status_code == 200
    assert updated.json()["price"] == 12.5
    assert updated.json()["name"] == "Widget"


async def test_delete_item(client: AsyncClient) -> None:
    item_id = (await client.post(ITEMS, json={"name": "Widget", "price": 9.99})).json()["id"]

    deleted = await client.delete(f"{ITEMS}/{item_id}")
    assert deleted.status_code == 204

    assert (await client.get(f"{ITEMS}/{item_id}")).status_code == 404


async def test_missing_item_returns_error_envelope(client: AsyncClient) -> None:
    response = await client.get(f"{ITEMS}/999")
    assert response.status_code == 404
    assert response.json() == {"error": {"code": "not_found", "message": "Item 999 does not exist"}}


async def test_invalid_payload_returns_validation_envelope(client: AsyncClient) -> None:
    response = await client.post(ITEMS, json={"name": "  ", "price": -1})
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    assert error["details"]


async def test_price_is_stored_as_an_exact_decimal(client: AsyncClient) -> None:
    created = await client.post(ITEMS, json={"name": "Widget", "price": 19.99})
    assert created.status_code == 201
    # Numeric(12, 2) keeps two decimals; the API still exposes a float.
    assert created.json()["price"] == 19.99
