from __future__ import annotations

from pathlib import Path

import httpx

from backend.app.core.config import AppConfig
from backend.app.core.secrets import SecretBox
from backend.app.core.settings_definitions import SettingKey, setting_keys
from backend.app.main import create_app
from backend.tests.integration.helpers import prepare_database


async def test_settings_are_validated_masked_encrypted_and_live(tmp_path: Path) -> None:
    config = AppConfig(
        database_path=tmp_path / "settings.sqlite3",
        migrations_path=Path(__file__).parents[2] / "migrations",
        secret_path=tmp_path / ".secret-key",
    )
    await prepare_database(config)
    app = create_app(config)
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            initial = await client.get("/api/v1/settings")
            assert initial.status_code == 200
            initial_by_key = {item["key"]: item for item in initial.json()["settings"]}
            assert initial_by_key["api_key"]["configured"] is False
            assert initial_by_key["chat_model"]["value"] == "gpt-4o-mini"
            assert "gpt-4.1" in initial_by_key["chat_model"]["options"]
            assert initial_by_key["voice"]["value"] == "marin"
            assert "marin" in initial_by_key["voice"]["options"]
            assert initial_by_key["theme"]["value"] == "system"

            invalid = await client.patch("/api/v1/settings", json={"voice": "not-a-voice"})
            assert invalid.status_code == 422
            invalid_model = await client.patch(
                "/api/v1/settings", json={"speech_model": "not-a-model"}
            )
            assert invalid_model.status_code == 422

            updated = await client.patch(
                "/api/v1/settings",
                json={
                    "api_key": "sk-test-secret",
                    "chat_model": "gpt-4o-mini",
                    "tts_enabled": True,
                    "stt_enabled": True,
                    "voice": "alloy",
                    "theme": "dark",
                },
            )
            body = updated.json()
            assert updated.status_code == 200
            assert "sk-test-secret" not in updated.text
            api_status = next(item for item in body["settings"] if item["key"] == "api_key")
            assert api_status["configured"] is True
            assert api_status["masked_suffix"] == "cret"

            capabilities = (await client.get("/api/v1/capabilities")).json()
            assert capabilities["speech_to_text"]["available"] is True
            assert capabilities["text_to_speech"]["available"] is True

            removed = await client.delete("/api/v1/settings/api_key")
            assert (
                next(item for item in removed.json()["settings"] if item["key"] == "api_key")[
                    "configured"
                ]
                is False
            )
            connection = await client.post("/api/v1/settings/test-provider", json={})
            assert connection.status_code == 200
            assert connection.json()["ok"] is False

        raw = app.state.database.connection.execute(
            "SELECT value FROM settings WHERE key = 'api_key'"
        ).fetchone()
        assert raw is None


def test_secret_box_is_authenticated_and_versioned(tmp_path: Path) -> None:
    box = SecretBox(tmp_path / ".secret-key")
    ciphertext = box.encrypt("super-secret")
    assert ciphertext.startswith("v1:")
    assert box.decrypt(ciphertext) == "super-secret"
    tampered = ciphertext[:-1] + ("A" if ciphertext[-1] != "A" else "B")
    try:
        box.decrypt(tampered)
    except Exception as error:
        assert type(error).__name__ in {"InvalidTag", "ValueError"}
    else:
        raise AssertionError("Tampered ciphertext was accepted")


def test_setting_enum_exposes_key_and_metadata_from_one_registry() -> None:
    assert SettingKey.CHAT_MODEL.value == "chat_model"
    assert SettingKey.CHAT_MODEL.default == "gpt-4o-mini"
    assert SettingKey.VOICE.default == "marin"
    assert "gpt-4o-transcribe" in SettingKey.TRANSCRIPTION_MODEL.options
    assert "api_key" in setting_keys()
