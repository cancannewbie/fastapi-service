"""Tests for the items CRUD endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient

ITEMS = "/api/v1/items"


def test_create_and_read_item(client: TestClient) -> None:
    created = client.post(ITEMS, json={"name": "Widget", "price": 9.99})
    assert created.status_code == 201
    body = created.json()
    assert body["id"] == 1
    assert body["name"] == "Widget"
    assert body["price"] == 9.99
    assert body["description"] is None

    fetched = client.get(f"{ITEMS}/{body['id']}")
    assert fetched.status_code == 200
    assert fetched.json() == body


def test_list_items(client: TestClient) -> None:
    assert client.get(ITEMS).json() == []

    client.post(ITEMS, json={"name": "A", "price": 1.0})
    client.post(ITEMS, json={"name": "B", "price": 2.0})

    listed = client.get(ITEMS)
    assert listed.status_code == 200
    assert [item["name"] for item in listed.json()] == ["A", "B"]


def test_update_item_only_touches_provided_fields(client: TestClient) -> None:
    item_id = client.post(ITEMS, json={"name": "Widget", "price": 9.99}).json()["id"]

    updated = client.patch(f"{ITEMS}/{item_id}", json={"price": 12.5})
    assert updated.status_code == 200
    assert updated.json()["price"] == 12.5
    assert updated.json()["name"] == "Widget"


def test_delete_item(client: TestClient) -> None:
    item_id = client.post(ITEMS, json={"name": "Widget", "price": 9.99}).json()["id"]

    deleted = client.delete(f"{ITEMS}/{item_id}")
    assert deleted.status_code == 204

    assert client.get(f"{ITEMS}/{item_id}").status_code == 404


def test_missing_item_returns_error_envelope(client: TestClient) -> None:
    response = client.get(f"{ITEMS}/999")
    assert response.status_code == 404
    assert response.json() == {"error": {"code": "not_found", "message": "Item 999 does not exist"}}


def test_invalid_payload_returns_validation_envelope(client: TestClient) -> None:
    response = client.post(ITEMS, json={"name": "  ", "price": -1})
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    assert error["details"]
