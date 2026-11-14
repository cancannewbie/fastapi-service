from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from fastapi_service.app import create_app
from fastapi_service.config import Settings
from fastapi_service.db.models import UserModel


def test_openapi_token_url_uses_app_prefix(settings: Settings) -> None:
    app = create_app(settings.model_copy(update={"api_prefix": "/custom"}))
    schema = app.openapi()
    flow = schema["components"]["securitySchemes"]["OAuth2PasswordBearer"]["flows"]["password"]
    assert flow["tokenUrl"] == "custom/auth/token"


@pytest.mark.asyncio
async def test_registration_login_and_current_user(client: AsyncClient) -> None:
    username = f"user-{uuid4()}"
    response = await client.post(
        "/api/v1/auth/register", json={"username": username, "password": "correct horse battery"}
    )
    assert response.status_code == 201
    user = response.json()
    assert user == {"id": user["id"], "username": username}

    app = client._transport.app  # type: ignore[union-attr]
    async with app.state.session_factory() as session:
        stored = await session.scalar(select(UserModel).where(UserModel.username == username))
        assert stored is not None
        assert stored.password_hash != "correct horse battery"
        assert stored.password_hash.startswith("$argon2")

    duplicate = await client.post(
        "/api/v1/auth/register", json={"username": username, "password": "another password"}
    )
    assert duplicate.status_code == 409
    for name, password in [(username, "wrong password"), ("missing-user", "wrong password")]:
        result = await client.post(
            "/api/v1/auth/token", data={"username": name, "password": password}
        )
        assert result.status_code == 401
        assert result.headers["www-authenticate"] == "Bearer"

    token_response = await client.post(
        "/api/v1/auth/token", data={"username": username, "password": "correct horse battery"}
    )
    assert token_response.status_code == 200
    token = token_response.json()
    assert token["token_type"] == "bearer"
    me = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token['access_token']}"}
    )
    assert me.status_code == 200
    assert me.json() == user


@pytest.mark.asyncio
async def test_rejects_invalid_tokens(client: AsyncClient, settings: Settings) -> None:
    now = datetime.now(UTC)
    secret = settings.jwt_secret.get_secret_value()
    claims = {"sub": "1", "iat": now, "exp": now + timedelta(minutes=5)}
    tokens = [
        "malformed",
        jwt.encode(claims, "wrong-secret-at-least-32-bytes-long", algorithm="HS256"),
        jwt.encode({**claims, "exp": now - timedelta(seconds=1)}, secret, algorithm="HS256"),
        jwt.encode({"sub": "1", "iat": now}, secret, algorithm="HS256"),
        jwt.encode({**claims, "sub": "not-a-user-id"}, secret, algorithm="HS256"),
        jwt.encode({**claims, "sub": "2147483647"}, secret, algorithm="HS256"),
    ]
    assert (await client.get("/api/v1/auth/me")).status_code == 401
    for token in tokens:
        response = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 401
        assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.asyncio
async def test_registration_validation(client: AsyncClient) -> None:
    for payload in [
        {"username": "", "password": "long enough"},
        {"username": "has spaces", "password": "long enough"},
        {"username": "valid", "password": "short"},
    ]:
        assert (await client.post("/api/v1/auth/register", json=payload)).status_code == 422
