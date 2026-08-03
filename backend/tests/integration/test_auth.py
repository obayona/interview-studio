from __future__ import annotations

from pathlib import Path

import httpx

from backend.app.core.config import AppConfig
from backend.app.main import create_app
from backend.tests.integration.helpers import prepare_database


def server_config(tmp_path: Path, password: str = "correct horse battery staple") -> AppConfig:
    return AppConfig(
        database_path=tmp_path / "app.sqlite3",
        migrations_path=Path(__file__).parents[2] / "migrations",
        secret_path=tmp_path / ".secret-key",
        server_mode=True,
        auth_username="owner",
        auth_password=password,
        session_lifetime_seconds=3600,
        trusted_origins=("https://studio.example.com",),
        encryption_key=b"k" * 32,
    )


async def test_server_authentication_csrf_logout_and_password_rotation(tmp_path: Path) -> None:
    config = server_config(tmp_path)
    await prepare_database(config)
    app = create_app(config)

    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="https://studio.example.com"
        ) as client:
            assert (await client.get("/health/ready")).status_code == 200
            anonymous = await client.get("/api/v1/settings")
            assert anonymous.status_code == 401
            assert anonymous.json()["request_id"]
            assert (
                await client.post(
                    "/api/v1/auth/login",
                    json={"username": "owner", "password": "wrong"},
                )
            ).status_code == 401

            login = await client.post(
                "/api/v1/auth/login",
                json={"username": "owner", "password": "correct horse battery staple"},
            )
            assert login.status_code == 200
            cookie = login.headers["set-cookie"]
            assert "HttpOnly" in cookie
            assert "Secure" in cookie
            assert "SameSite=strict" in cookie
            csrf_token = login.json()["csrf_token"]
            assert (await client.get("/api/v1/auth/session")).status_code == 200

            rejected = await client.patch("/api/v1/settings", json={"chat_model": "gpt-4.1-mini"})
            assert rejected.status_code == 403
            accepted = await client.patch(
                "/api/v1/settings",
                json={"chat_model": "gpt-4.1-mini"},
                headers={"x-csrf-token": csrf_token},
            )
            assert accepted.status_code == 200
            assert (
                await client.post("/api/v1/auth/logout", headers={"x-csrf-token": csrf_token})
            ).status_code == 204
            assert (await client.get("/api/v1/settings")).status_code == 401

    rotated_app = create_app(server_config(tmp_path, "a different secure password"))
    async with rotated_app.router.lifespan_context(rotated_app):
        transport = httpx.ASGITransport(app=rotated_app)
        async with httpx.AsyncClient(
            transport=transport, base_url="https://studio.example.com"
        ) as client:
            old_password = await client.post(
                "/api/v1/auth/login",
                json={"username": "owner", "password": "correct horse battery staple"},
            )
            assert old_password.status_code == 401
            new_password = await client.post(
                "/api/v1/auth/login",
                json={"username": "owner", "password": "a different secure password"},
            )
            assert new_password.status_code == 200


async def test_login_rate_limit_is_bounded(tmp_path: Path) -> None:
    config = server_config(tmp_path)
    await prepare_database(config)
    app = create_app(config)

    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="https://studio.example.com"
        ) as client:
            for _ in range(5):
                response = await client.post(
                    "/api/v1/auth/login",
                    json={"username": "owner", "password": "wrong"},
                )
                assert response.status_code == 401
            limited = await client.post(
                "/api/v1/auth/login",
                json={"username": "owner", "password": "wrong"},
            )
            assert limited.status_code == 429
