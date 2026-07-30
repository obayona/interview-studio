from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any, cast

from backend.app.api.websocket import _interaction_status
from backend.app.application.interviews import InterviewSession
from backend.app.core.config import AISettings
from backend.app.repositories.attempts import AttemptRepository
from backend.interview_engine import InterviewEngine
from backend.interview_engine.models import InterviewConfiguration
from backend.interview_engine.ports import SpeechToTextPort, TextToSpeechPort


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

    async def media_preferences(self, attempt_id: str) -> dict[str, bool] | None:
        return {"speech_to_text": True, "text_to_speech": True}


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


class SpeechToText(SpeechToTextPort):
    async def transcribe(self, audio: bytes, filename: str) -> str:
        return f"{filename}:{audio.decode()}"


class TextToSpeech(TextToSpeechPort):
    async def synthesize(self, text: str) -> bytes:
        return text.upper().encode()


async def test_media_modes_require_attempt_and_global_enablement() -> None:
    configuration = InterviewConfiguration(job_listing="Backend engineer")
    session = InterviewSession(
        "attempt-1",
        "thread-1",
        cast(Any, None),
        cast(AttemptRepository, Attempts(configuration)),
        cast(Any, Settings(AISettings(api_key="key", stt_enabled=True, tts_enabled=False))),
        cast(Any, None),
    )

    assert await session.media_modes() == {
        "speech_to_text": True,
        "text_to_speech": False,
    }
    assert await session.media_capabilities() == {
        "speech_to_text": True,
        "text_to_speech": False,
    }


async def test_natural_graph_completion_updates_attempt_status() -> None:
    attempts = Attempts(InterviewConfiguration(job_listing="Backend engineer"))
    session = InterviewSession(
        "attempt-1",
        "thread-1",
        cast(InterviewEngine, CompletedEngine()),
        cast(AttemptRepository, attempts),
        cast(Any, Settings(AISettings(api_key="key"))),
        cast(Any, None),
    )

    assert [token async for token in session.respond("My answer")] == [
        "This concludes our interview."
    ]
    assert attempts.ended_reason == "question_limit"


def test_persisted_attempt_status_maps_to_interaction_state() -> None:
    assert _interaction_status("in_progress") == "ready_for_answer"
    assert _interaction_status("completed") == "completed"


async def test_engine_delegates_media_operations_to_injected_ports() -> None:
    engine = InterviewEngine(
        InterviewConfiguration(job_listing="Backend engineer"),
        cast(Any, None),
        speech_to_text=SpeechToText(),
        text_to_speech=TextToSpeech(),
    )

    assert await engine.transcribe(b"audio", "answer.webm") == "answer.webm:audio"
    assert await engine.synthesize("hello") == b"HELLO"
