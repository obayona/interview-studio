from __future__ import annotations

from collections.abc import AsyncIterator

from backend.app.core.config import SettingsService
from backend.app.core.errors import AttemptNotFoundError, ProviderNotConfiguredError
from backend.app.infrastructure.checkpointer import InterviewSQLiteCheckpointer
from backend.app.infrastructure.openai_audio import OpenAISpeechToText, OpenAITextToSpeech
from backend.app.repositories.attempts import AttemptRepository
from backend.interview_engine import (
    InterviewEngine,
    InterviewEngineBuilder,
)


class InterviewSession:
    def __init__(
        self,
        attempt_id: str,
        thread_id: str,
        engine: InterviewEngine,
        attempts: AttemptRepository,
        settings: SettingsService,
        checkpointer: InterviewSQLiteCheckpointer,
    ) -> None:
        self.attempt_id = attempt_id
        self._thread_id = thread_id
        self._engine = engine
        self._attempts = attempts
        self._settings = settings
        self._checkpointer = checkpointer

    async def media_modes(self) -> dict[str, bool]:
        preferences = await self._attempts.media_preferences(self.attempt_id)
        if preferences is None:
            raise AttemptNotFoundError(self.attempt_id)
        available = await self.media_capabilities()
        return {
            "text_to_speech": preferences["text_to_speech"] and available["text_to_speech"],
        }

    async def media_capabilities(self) -> dict[str, bool]:
        ai = await self._settings.ai()
        return {
            "speech_to_text": bool(ai.stt_enabled and ai.api_key and ai.transcription_model),
            "text_to_speech": bool(ai.tts_enabled and ai.api_key and ai.speech_model and ai.voice),
        }

    async def set_media_preference(self, key: str, enabled: bool) -> None:
        await self._attempts.set_media_preference(self.attempt_id, key, enabled)

    async def transcribe(self, audio: bytes, filename: str) -> str:
        capabilities = await self.media_capabilities()
        if not capabilities["speech_to_text"]:
            raise ValueError("Speech-to-text is not available for this interview")
        return await self._engine.transcribe(audio, filename)

    async def synthesize(self, text: str) -> bytes:
        capabilities = await self.media_capabilities()
        if not capabilities["text_to_speech"]:
            return b""
        return await self._engine.synthesize(text)

    async def start(self) -> AsyncIterator[str]:
        await self._attempts.mark_started(self.attempt_id)
        state = await self._checkpointer.aget_tuple(
            {"configurable": {"thread_id": self._thread_id}}
        )
        if state is None:
            async for token in self._engine.stream_start(self._thread_id):
                yield token
            await self._complete_if_ended()

    async def respond(self, text: str) -> AsyncIterator[str]:
        await self._attempts.mark_started(self.attempt_id)
        async for token in self._engine.stream_response(self._thread_id, text):
            yield token
        await self._complete_if_ended()

    async def pause(self) -> None:
        await self._attempts.mark_paused(self.attempt_id)

    async def resume(self) -> None:
        await self._attempts.mark_started(self.attempt_id)

    async def end(self) -> AsyncIterator[str]:
        async for token in self._engine.stream_end(self._thread_id):
            yield token
        await self._complete_if_ended()

    async def status(self) -> str:
        status = await self._attempts.status(self.attempt_id)
        if status is None:
            raise AttemptNotFoundError(self.attempt_id)
        return status

    async def _complete_if_ended(self) -> None:
        state = await self._engine.get_state(self._thread_id)
        if state.get("ended"):
            await self._attempts.mark_ended(
                self.attempt_id,
                state.get("termination_reason") or "topics_covered",
            )


class InterviewService:
    def __init__(
        self,
        attempts: AttemptRepository,
        settings: SettingsService,
        checkpointer: InterviewSQLiteCheckpointer,
    ) -> None:
        self._attempts = attempts
        self._settings = settings
        self._checkpointer = checkpointer

    async def open_session(self, attempt_id: str) -> InterviewSession:
        attempt = await self._attempts.get_configuration(attempt_id)
        if attempt is None:
            raise AttemptNotFoundError(attempt_id)
        thread_id, configuration = attempt
        ai = await self._settings.ai()
        if not ai.interview_ready:
            raise ProviderNotConfiguredError()

        builder = (
            InterviewEngineBuilder()
            .set_openai_api(ai.api_key)
            .set_model(ai.chat_model)
            .set_checkpointer(self._checkpointer)
            .set_candidate(configuration.candidate)
            .set_job_listing(configuration.job_listing)
            .set_company_info(configuration.company_info)
            .set_interview_type(configuration.interview_type)
            .set_interviewer_profile(configuration.interviewer_profile)
            .set_difficulty(configuration.difficulty)
            .set_user_instructions(configuration.user_instructions)
            .set_language(configuration.language)
            .set_topics(configuration.topics)
            .set_limits(configuration.limits)
        )
        if ai.api_key and ai.transcription_model:
            builder.set_speech_to_text(OpenAISpeechToText(ai.api_key, ai.transcription_model))
        if ai.api_key and ai.speech_model and ai.voice:
            builder.set_text_to_speech(OpenAITextToSpeech(ai.api_key, ai.speech_model, ai.voice))
        return InterviewSession(
            attempt_id,
            thread_id,
            builder.build(),
            self._attempts,
            self._settings,
            self._checkpointer,
        )
