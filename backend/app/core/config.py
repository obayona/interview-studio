from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from backend.app.repositories.settings import SettingsRepository


@dataclass(frozen=True)
class AppConfig:
    database_path: Path
    migrations_path: Path

    @classmethod
    def default(cls) -> AppConfig:
        backend_root = Path(__file__).resolve().parents[2]
        return cls(
            database_path=backend_root / "interview_studio.sqlite3",
            migrations_path=backend_root / "migrations",
        )


class AISettings(BaseModel):
    model_config = ConfigDict(frozen=True)

    api_key: str = ""
    chat_model: str = "gpt-4o-mini"

    @property
    def interview_ready(self) -> bool:
        return bool(self.api_key.strip() and self.chat_model.strip())


class ConfigurationStore:
    """Small typed facade that resolves persisted settings on every operation."""

    def __init__(self, repository: SettingsRepository) -> None:
        self._repository = repository

    async def ai(self) -> AISettings:
        values = await self._repository.get_many(("ai.api_key", "ai.chat_model"))
        return AISettings(
            api_key=values.get("ai.api_key", ""),
            chat_model=values.get("ai.chat_model", "gpt-4o-mini"),
        )

    async def capabilities(self) -> dict[str, object]:
        ai = await self.ai()
        return {
            "interview": {
                "available": ai.interview_ready,
                "reason": None if ai.interview_ready else "OpenAI API key is not configured",
            },
            "speech_to_text": {"available": False, "reason": "Planned for Phase 7"},
            "text_to_speech": {"available": False, "reason": "Planned for Phase 7"},
        }
