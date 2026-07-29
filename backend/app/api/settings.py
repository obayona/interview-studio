from __future__ import annotations

from typing import cast

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.app.core.config import SettingsService
from backend.app.core.errors import ApplicationError
from backend.app.core.settings_definitions import SettingKey

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])
VOICES = {
    "alloy",
    "ash",
    "ballad",
    "coral",
    "echo",
    "fable",
    "nova",
    "onyx",
    "sage",
    "shimmer",
    "verse",
}


class SettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    api_key: str | None = Field(default=None, max_length=500)
    chat_model: str | None = Field(default=None, max_length=120)
    transcription_model: str | None = Field(default=None, max_length=120)
    speech_model: str | None = Field(default=None, max_length=120)
    vision_model: str | None = Field(default=None, max_length=120)
    voice: str | None = Field(default=None, max_length=40)
    tts_enabled: bool | None = None
    stt_enabled: bool | None = None
    theme: str | None = Field(default=None, max_length=20)

    @field_validator("chat_model", "transcription_model", "speech_model", "vision_model")
    @classmethod
    def validate_model_name(cls, value: str | None) -> str | None:
        if value is not None and (
            not value.strip() or any(character.isspace() for character in value)
        ):
            raise ValueError("Model names must be non-empty and contain no whitespace")
        return value.strip() if value else value

    @field_validator("voice")
    @classmethod
    def validate_voice(cls, value: str | None) -> str | None:
        if value is not None and value not in VOICES:
            raise ValueError(f"Voice must be one of: {', '.join(sorted(VOICES))}")
        return value

    @field_validator("theme")
    @classmethod
    def validate_theme(cls, value: str | None) -> str | None:
        if value is not None and value not in {"system", "light", "dark"}:
            raise ValueError("Theme must be system, light, or dark")
        return value


class ProviderTestRequest(BaseModel):
    provider: str = "openai"


def _settings(request: Request) -> SettingsService:
    return cast(SettingsService, request.app.state.settings)


@router.get("")
async def get_settings(request: Request) -> dict[str, object]:
    return {"settings": await _settings(request).status()}


@router.patch("")
async def update_settings(request: Request, update: SettingsUpdate) -> dict[str, object]:
    values = update.model_dump(exclude_none=True)
    settings = _settings(request)
    return {
        "settings": await settings.update(
            {
                SettingKey(key).value: (
                    str(value).lower() if isinstance(value, bool) else str(value)
                )
                for key, value in values.items()
            }
        )
    }


@router.delete("/{key}")
async def remove_setting(request: Request, key: str) -> dict[str, object]:
    try:
        normalized = SettingKey(key).value
    except ValueError:
        normalized = key
    try:
        settings = _settings(request)
        status = await settings.remove(normalized)
    except ValueError as error:
        raise ApplicationError("unknown_setting", str(error), 422) from error
    return {"settings": status}


@router.post("/test-provider")
async def test_provider(request: Request, payload: ProviderTestRequest) -> dict[str, object]:
    if payload.provider != "openai":
        raise ApplicationError("unsupported_provider", "Only OpenAI is supported", 422)
    return await _settings(request).test_provider(payload.provider)
