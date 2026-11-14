"""Tests for the bundled frontend and its API configuration."""

from httpx import ASGITransport, AsyncClient

from fastapi_service.app import create_app
from fastapi_service.config import Settings


async def test_frontend_assets_and_config(settings: Settings) -> None:
    app = create_app(settings.model_copy(update={"api_prefix": "/custom/api"}))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        page = await client.get("/")
        assert page.status_code == 200
        assert "任务管理" in page.text
        assert (await client.get("/static/app.js")).status_code == 200
        assert (await client.get("/static/style.css")).status_code == 200
        assert (await client.get("/frontend-config")).json() == {"api_prefix": "/custom/api"}
    await app.state.engine.dispose()
