from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any, cast

from backend.app.api.websocket import _interaction_status
from backend.app.application.interviews import InterviewService
from backend.app.core.config import AISettings
from backend.app.repositories.attempts import AttemptRepository
from backend.interview_engine import InterviewEngine
from backend.interview_engine.models import InterviewConfiguration, MediaCapabilities


class Attempts:
    def __init__(self, configuration: InterviewConfiguration) -> None:
        self.configuration = configuration
        self.ended_reason: str | None = None

    async def get_configuration(self, attempt_id: str) -> tuple[str, InterviewConfiguration] | None:
        return ("thread-1", self.configuration) if attempt_id == "attempt-1" else None

    async def mark_started(self, attempt_id: str) -> None:
        return None

    async def mark_ended(self, attempt_id: str, reason: str) -> None:
        self.ended_reason = reason

    async def media_preferences(self, attempt_id: str) -> dict[str, bool | None] | None:
        return {"speech_to_text": None, "text_to_speech": None}


class Settings:
    def __init__(self, ai: AISettings) -> None:
        self.value = ai

    async def ai(self) -> AISettings:
        return self.value


class CompletedEngine:
    async def stream_response(self, thread_id: str, text: str) -> AsyncIterator[str]:
        yield "This concludes our interview."

    async def get_state(self, thread_id: str) -> dict[str, object]:
        return {"ended": True, "termination_reason": "question_limit"}


class CompletingService(InterviewService):
    def __init__(self, attempts: Attempts) -> None:
        super().__init__(
            cast(AttemptRepository, attempts),
            cast(Any, Settings(AISettings(api_key="key"))),
            cast(Any, None),
        )
        self.engine = cast(InterviewEngine, CompletedEngine())

    async def open(self, attempt_id: str) -> tuple[str, InterviewEngine]:
        return "thread-1", self.engine


async def test_media_modes_require_attempt_and_global_enablement() -> None:
    configuration = InterviewConfiguration(
        job_listing="Backend engineer",
        media=MediaCapabilities(speech_to_text=True, text_to_speech=True),
    )
    service = InterviewService(
        cast(AttemptRepository, Attempts(configuration)),
        cast(Any, Settings(AISettings(api_key="key", stt_enabled=True, tts_enabled=False))),
        cast(Any, None),
    )

    assert await service.media_modes("attempt-1") == {
        "speech_to_text": True,
        "text_to_speech": False,
    }
    assert await service.media_capabilities() == {
        "speech_to_text": True,
        "text_to_speech": False,
    }


async def test_natural_graph_completion_updates_attempt_status() -> None:
    attempts = Attempts(InterviewConfiguration(job_listing="Backend engineer"))
    service = CompletingService(attempts)

    assert [token async for token in service.respond("attempt-1", "My answer")] == [
        "This concludes our interview."
    ]
    assert attempts.ended_reason == "question_limit"


def test_persisted_attempt_status_maps_to_interaction_state() -> None:
    assert _interaction_status("in_progress") == "ready_for_answer"
    assert _interaction_status("completed") == "completed"
