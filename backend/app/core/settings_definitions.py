from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Final


class SettingKey(StrEnum):
    API_KEY = "api_key"
    CHAT_MODEL = "chat_model"
    TRANSCRIPTION_MODEL = "transcription_model"
    SPEECH_MODEL = "speech_model"
    VISION_MODEL = "vision_model"
    VOICE = "voice"
    TTS_ENABLED = "tts_enabled"
    STT_ENABLED = "stt_enabled"
    THEME = "theme"

    @property
    def definition(self) -> SettingDefinition:
        return SETTING_DEFINITIONS[self]

    @property
    def default(self) -> str:
        return self.definition.default

    @property
    def secret(self) -> bool:
        return self.definition.secret

    @property
    def options(self) -> tuple[str, ...]:
        return self.definition.options


@dataclass(frozen=True)
class SettingDefinition:
    secret: bool = False
    default: str = ""
    options: tuple[str, ...] = ()


SETTING_DEFINITIONS: Final[dict[SettingKey, SettingDefinition]] = {
    SettingKey.API_KEY: SettingDefinition(secret=True),
    SettingKey.CHAT_MODEL: SettingDefinition(
        default="gpt-4o-mini",
        options=(
            "gpt-4o-mini",
            "gpt-4o",
            "gpt-4.1-mini",
            "gpt-4.1",
            "gpt-5-mini",
            "gpt-5",
        ),
    ),
    SettingKey.TRANSCRIPTION_MODEL: SettingDefinition(
        default="gpt-4o-mini-transcribe",
        options=("gpt-4o-mini-transcribe", "gpt-4o-transcribe", "whisper-1"),
    ),
    SettingKey.SPEECH_MODEL: SettingDefinition(
        default="gpt-4o-mini-tts",
        options=("gpt-4o-mini-tts", "tts-1", "tts-1-hd"),
    ),
    SettingKey.VISION_MODEL: SettingDefinition(
        default="gpt-4o-mini",
        options=("gpt-4o-mini", "gpt-4o", "gpt-4.1-mini", "gpt-4.1"),
    ),
    SettingKey.VOICE: SettingDefinition(
        default="marin",
        options=(
            "marin",
            "cedar",
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
        ),
    ),
    SettingKey.TTS_ENABLED: SettingDefinition(),
    SettingKey.STT_ENABLED: SettingDefinition(),
    SettingKey.THEME: SettingDefinition(
        default="system",
        options=("system", "light", "dark"),
    ),
}


def setting_keys() -> tuple[str, ...]:
    """Return persisted key names without duplicating the registry."""
    return tuple(key.value for key in SETTING_DEFINITIONS)
