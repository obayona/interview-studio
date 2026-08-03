from __future__ import annotations

import base64
import binascii
import os
from dataclasses import dataclass
from pathlib import Path

from openai import AsyncOpenAI
from pydantic import BaseModel, ConfigDict

from backend.app.core.settings_definitions import SettingKey
from backend.app.repositories.settings import SettingsRepository


@dataclass(frozen=True)
class AppConfig:
    database_path: Path
    migrations_path: Path
    secret_path: Path | None = None
    server_mode: bool = False
    auth_username: str = ""
    auth_password: str = ""
    session_lifetime_seconds: int = 86_400
    trusted_origins: tuple[str, ...] = ()
    encryption_key: bytes | None = None

    def __post_init__(self) -> None:
        if not self.server_mode:
            return
        if not 1 <= len(self.auth_username) <= 128:
            raise ValueError("APP_USERNAME must contain between 1 and 128 characters")
        if len(self.auth_password) < 16:
            raise ValueError("APP_PASSWORD must contain at least 16 characters")
        if self.encryption_key is None or len(self.encryption_key) != 32:
            raise ValueError("APP_ENCRYPTION_KEY is required in server mode")
        if not self.trusted_origins or any(
            not origin.startswith("https://") for origin in self.trusted_origins
        ):
            raise ValueError("Server mode requires at least one trusted HTTPS origin")

    @classmethod
    def default(cls) -> AppConfig:
        backend_root = Path(__file__).resolve().parents[2]
        server_mode = os.getenv("APP_SERVER_MODE", "false").lower() == "true"
        database_path = Path(
            os.getenv("APP_DATABASE_PATH", str(backend_root / "interview_studio.sqlite3"))
        )
        secret_path = Path(
            os.getenv("APP_SECRET_PATH", str(database_path.with_name(".secret-key")))
        )
        trusted_origins = tuple(
            origin.strip()
            for origin in os.getenv("APP_TRUSTED_ORIGINS", "").split(",")
            if origin.strip()
        )
        session_lifetime = int(os.getenv("APP_SESSION_LIFETIME_SECONDS", "86400"))
        username = os.getenv("APP_USERNAME", "")
        password = os.getenv("APP_PASSWORD", "")
        encryption_key_text = os.getenv("APP_ENCRYPTION_KEY", "")
        encryption_key: bytes | None = None
        if encryption_key_text:
            try:
                encryption_key = base64.b64decode(encryption_key_text, validate=True)
            except (binascii.Error, ValueError) as error:
                raise ValueError("APP_ENCRYPTION_KEY must be valid base64") from error
            if len(encryption_key) != 32:
                raise ValueError("APP_ENCRYPTION_KEY must decode to exactly 32 bytes")
        if server_mode and (not username or not password):
            raise ValueError("APP_USERNAME and APP_PASSWORD are required in server mode")
        if session_lifetime < 300:
            raise ValueError("APP_SESSION_LIFETIME_SECONDS must be at least 300")
        return cls(
            database_path=database_path,
            migrations_path=backend_root / "migrations",
            secret_path=secret_path,
            server_mode=server_mode,
            auth_username=username,
            auth_password=password,
            session_lifetime_seconds=session_lifetime,
            trusted_origins=trusted_origins,
            encryption_key=encryption_key,
        )


class AISettings(BaseModel):
    model_config = ConfigDict(frozen=True)

    api_key: str = ""
    chat_model: str = "gpt-4o-mini"
    transcription_model: str = "gpt-4o-mini-transcribe"
    speech_model: str = "gpt-4o-mini-tts"
    vision_model: str = "gpt-4o-mini"
    voice: str = "marin"
    stt_enabled: bool = False
    tts_enabled: bool = False

    @property
    def interview_ready(self) -> bool:
        return bool(self.api_key.strip() and self.chat_model.strip())


class SettingsService:
    """Application-facing settings facade over persistence and secret handling."""

    def __init__(self, repository: SettingsRepository) -> None:
        self._repository = repository

    async def ai(self) -> AISettings:
        values = await self._repository.get_many(
            (
                SettingKey.API_KEY.value,
                SettingKey.CHAT_MODEL.value,
                SettingKey.TRANSCRIPTION_MODEL.value,
                SettingKey.SPEECH_MODEL.value,
                SettingKey.VISION_MODEL.value,
                SettingKey.VOICE.value,
                SettingKey.STT_ENABLED.value,
                SettingKey.TTS_ENABLED.value,
            )
        )
        return AISettings(
            api_key=values.get(SettingKey.API_KEY.value, ""),
            chat_model=values.get(
                SettingKey.CHAT_MODEL.value,
                SettingKey.CHAT_MODEL.default,
            ),
            transcription_model=values.get(
                SettingKey.TRANSCRIPTION_MODEL.value,
                SettingKey.TRANSCRIPTION_MODEL.default,
            ),
            speech_model=values.get(
                SettingKey.SPEECH_MODEL.value,
                SettingKey.SPEECH_MODEL.default,
            ),
            vision_model=values.get(
                SettingKey.VISION_MODEL.value,
                SettingKey.VISION_MODEL.default,
            ),
            voice=values.get(SettingKey.VOICE.value, SettingKey.VOICE.default),
            stt_enabled=values.get(SettingKey.STT_ENABLED.value) == "true",
            tts_enabled=values.get(SettingKey.TTS_ENABLED.value) == "true",
        )

    async def capabilities(self) -> dict[str, object]:
        ai = await self.ai()
        stt_available = bool(ai.stt_enabled and ai.api_key and ai.transcription_model)
        tts_available = bool(ai.tts_enabled and ai.api_key and ai.speech_model and ai.voice)
        return {
            "interview": {
                "available": ai.interview_ready,
                "reason": None if ai.interview_ready else "OpenAI API key is not configured",
            },
            "speech_to_text": {
                "available": stt_available,
                "reason": None if stt_available else "Enable STT and configure an OpenAI API key",
            },
            "text_to_speech": {
                "available": tts_available,
                "reason": None if tts_available else "Enable TTS and configure an OpenAI API key",
            },
        }

    async def status(self) -> list[dict[str, object]]:
        return await self._repository.status()

    async def update(self, values: dict[str, str]) -> list[dict[str, object]]:
        await self._repository.set_many(values)
        return await self.status()

    async def remove(self, key: str) -> list[dict[str, object]]:
        await self._repository.remove(key)
        return await self.status()

    async def test_provider(self, provider: str) -> dict[str, object]:
        if provider != "openai":
            return {"ok": False, "message": "Only OpenAI is supported"}
        api_key_key = SettingKey.API_KEY.value
        values = await self._repository.get_many((api_key_key,))
        api_key = values.get(api_key_key, "")
        if not api_key:
            return {"ok": False, "message": "OpenAI API key is not configured"}
        try:
            client = AsyncOpenAI(api_key=api_key, timeout=10.0, max_retries=0)
            await client.models.list()
        except Exception:
            return {"ok": False, "message": "OpenAI connection failed"}
        return {"ok": True, "message": "OpenAI connection succeeded"}
