from __future__ import annotations

from pathlib import Path
from typing import cast

import httpx
import pytest

from backend.app.application.interviews import InterviewService
from backend.app.core.config import AppConfig
from backend.app.core.errors import ProviderNotConfiguredError
from backend.app.main import create_app
from backend.tests.integration.helpers import prepare_database


async def test_prepared_database_boots_without_credentials(tmp_path: Path) -> None:
    config = AppConfig(
        database_path=tmp_path / "app.sqlite3",
        migrations_path=Path(__file__).parents[2] / "migrations",
        secret_path=tmp_path / ".secret-key",
    )
    await prepare_database(config)
    app = create_app(config)

    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            assert (await client.get("/health/live")).json() == {"status": "ok"}
            assert (await client.get("/health/ready")).json() == {"status": "ready"}
            response = await client.get("/api/v1/capabilities")
            assert response.status_code == 200
            assert response.json()["interview"]["available"] is False
            assert "WebSocket" in (await client.get("/")).text
            history = await client.get("/api/v1/interviews/browser-harness/history")
            assert history.json() == {"attempt_id": "browser-harness", "messages": []}
            missing = await client.get("/api/v1/interviews/missing/history")
            assert missing.status_code == 404
            assert missing.json()["code"] == "attempt_not_found"
            configured = await client.patch("/api/v1/settings", json={"chat_model": "gpt-4.1-mini"})
            assert configured.status_code == 200

        service = cast(InterviewService, app.state.interviews)
        with pytest.raises(ProviderNotConfiguredError):
            await anext(service.start("browser-harness"))

    await prepare_database(config)
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            assert (await client.get("/health/ready")).status_code == 200
            settings = (await client.get("/api/v1/settings")).json()["settings"]
            chat_model = next(item for item in settings if item["key"] == "chat_model")
            assert chat_model["value"] == "gpt-4.1-mini"
