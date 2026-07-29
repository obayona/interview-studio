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


@dataclass(frozen=True)
class SettingDefinition:
    secret: bool = False
    default: str = ""


SETTING_DEFINITIONS: Final[dict[SettingKey, SettingDefinition]] = {
    SettingKey.API_KEY: SettingDefinition(secret=True),
    SettingKey.CHAT_MODEL: SettingDefinition(default="gpt-4o-mini"),
    SettingKey.TRANSCRIPTION_MODEL: SettingDefinition(),
    SettingKey.SPEECH_MODEL: SettingDefinition(),
    SettingKey.VISION_MODEL: SettingDefinition(),
    SettingKey.VOICE: SettingDefinition(),
    SettingKey.TTS_ENABLED: SettingDefinition(),
    SettingKey.STT_ENABLED: SettingDefinition(),
    SettingKey.THEME: SettingDefinition(default="system"),
}


def setting_keys() -> tuple[str, ...]:
    """Return persisted key names without duplicating the registry."""
    return tuple(key.value for key in SETTING_DEFINITIONS)
