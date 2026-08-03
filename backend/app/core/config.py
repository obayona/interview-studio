from __future__ import annotations

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

    @classmethod
    def default(cls) -> AppConfig:
        backend_root = Path(__file__).resolve().parents[2]
        return cls(
            database_path=backend_root / "interview_studio.sqlite3",
            migrations_path=backend_root / "migrations",
            secret_path=backend_root / ".secret-key",
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
