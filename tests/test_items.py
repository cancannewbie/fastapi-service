"""Task API tests against PostgreSQL, including ownership isolation."""

from httpx import AsyncClient

TASKS = "/api/v1/tasks"


async def auth_headers(client: AsyncClient, username: str) -> dict[str, str]:
    registered = await client.post(
        "/api/v1/auth/register", json={"username": username, "password": "correct-horse-42"}
    )
    assert registered.status_code == 201
    token = await client.post(
        "/api/v1/auth/token", data={"username": username, "password": "correct-horse-42"}
    )
    assert token.status_code == 200
    return {"Authorization": f"Bearer {token.json()['access_token']}"}


async def test_task_crud_and_validation(client: AsyncClient) -> None:
    assert (await client.get(TASKS)).status_code == 401
    headers = await auth_headers(client, "alice")
    assert (await client.get(TASKS, headers=headers)).json() == []
    created = await client.post(TASKS, headers=headers, json={"title": "  Plan work  "})
    assert created.status_code == 201
    task = created.json()
    assert task["title"] == "Plan work"
    assert task["status"] == "todo"
    task_id = task["id"]
    assert (await client.get(f"{TASKS}/{task_id}", headers=headers)).json() == task
    updated = await client.patch(
        f"{TASKS}/{task_id}",
        headers=headers,
        json={"status": "in_progress", "description": "Notes"},
    )
    assert updated.json()["status"] == "in_progress"
    assert updated.json()["title"] == "Plan work"
    assert (
        await client.patch(f"{TASKS}/{task_id}", headers=headers, json={"status": None})
    ).status_code == 422
    assert (await client.post(TASKS, headers=headers, json={"title": "   "})).status_code == 422
    assert (await client.delete(f"{TASKS}/{task_id}", headers=headers)).status_code == 204
    assert (await client.get(f"{TASKS}/{task_id}", headers=headers)).status_code == 404


async def test_tasks_are_private_to_owner(client: AsyncClient) -> None:
    alice = await auth_headers(client, "alice")
    bob = await auth_headers(client, "bob")
    task = await client.post(TASKS, headers=alice, json={"title": "Private"})
    task_id = task.json()["id"]
    assert (await client.get(TASKS, headers=bob)).json() == []
    assert (await client.get(f"{TASKS}/{task_id}", headers=bob)).status_code == 404
    assert (
        await client.patch(f"{TASKS}/{task_id}", headers=bob, json={"status": "done"})
    ).status_code == 404
    assert (await client.delete(f"{TASKS}/{task_id}", headers=bob)).status_code == 404
    assert (await client.get(f"{TASKS}/{task_id}", headers=alice)).status_code == 200
