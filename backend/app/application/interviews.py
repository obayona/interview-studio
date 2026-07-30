from __future__ import annotations

from collections.abc import AsyncIterator

from backend.app.core.config import SettingsService
from backend.app.core.errors import AttemptNotFoundError, ProviderNotConfiguredError
from backend.app.infrastructure.checkpointer import InterviewSQLiteCheckpointer
from backend.app.infrastructure.openai_audio import OpenAISpeechToText, OpenAITextToSpeech
from backend.app.repositories.attempts import AttemptRepository
from backend.interview_engine import InterviewEngine, InterviewEngineBuilder


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

    async def open(self, attempt_id: str) -> tuple[str, InterviewEngine]:
        attempt = await self._attempts.get_configuration(attempt_id)
        if attempt is None:
            raise AttemptNotFoundError(attempt_id)
        thread_id, configuration = attempt
        ai = await self._settings.ai()
        if not ai.interview_ready:
            raise ProviderNotConfiguredError()
        stt = OpenAISpeechToText(ai.api_key, ai.transcription_model)
        tts = OpenAITextToSpeech(ai.api_key, ai.speech_model, ai.voice)
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
            .set_media_capabilities(configuration.media)
        )
        if configuration.media.speech_to_text:
            builder.set_speech_to_text(stt)
        if configuration.media.text_to_speech:
            builder.set_text_to_speech(tts)
        return thread_id, builder.build()

    async def media_modes(self, attempt_id: str) -> dict[str, bool]:
        attempt = await self._attempts.get_configuration(attempt_id)
        if attempt is None:
            raise AttemptNotFoundError(attempt_id)
        _, configuration = attempt
        preferences = await self._attempts.media_preferences(attempt_id)
        if preferences is None:
            raise AttemptNotFoundError(attempt_id)
        available = await self.media_capabilities()
        return {
            "speech_to_text": bool(
                (
                    configuration.media.speech_to_text
                    if preferences["speech_to_text"] is None
                    else preferences["speech_to_text"]
                )
                and available["speech_to_text"]
            ),
            "text_to_speech": bool(
                (
                    configuration.media.text_to_speech
                    if preferences["text_to_speech"] is None
                    else preferences["text_to_speech"]
                )
                and available["text_to_speech"]
            ),
        }

    async def set_media_preference(self, attempt_id: str, key: str, enabled: bool) -> None:
        if await self._attempts.get_configuration(attempt_id) is None:
            raise AttemptNotFoundError(attempt_id)
        await self._attempts.set_media_preference(attempt_id, key, enabled)

    async def media_capabilities(self) -> dict[str, bool]:
        ai = await self._settings.ai()
        return {
            "speech_to_text": bool(ai.stt_enabled and ai.api_key and ai.transcription_model),
            "text_to_speech": bool(ai.tts_enabled and ai.api_key and ai.speech_model and ai.voice),
        }

    async def transcribe(self, attempt_id: str, audio: bytes, filename: str) -> str:
        if await self._attempts.get_configuration(attempt_id) is None:
            raise AttemptNotFoundError(attempt_id)
        capabilities = await self.media_capabilities()
        if not capabilities["speech_to_text"]:
            raise ValueError("Speech-to-text is not available for this interview")
        ai = await self._settings.ai()
        return await OpenAISpeechToText(ai.api_key, ai.transcription_model).transcribe(
            audio, filename
        )

    async def synthesize(self, attempt_id: str, text: str) -> bytes:
        if await self._attempts.get_configuration(attempt_id) is None:
            raise AttemptNotFoundError(attempt_id)
        capabilities = await self.media_capabilities()
        if not capabilities["text_to_speech"]:
            return b""
        ai = await self._settings.ai()
        return await OpenAITextToSpeech(ai.api_key, ai.speech_model, ai.voice).synthesize(text)

    async def start(self, attempt_id: str) -> AsyncIterator[str]:
        thread_id, engine = await self.open(attempt_id)
        await self._attempts.mark_started(attempt_id)
        state = await self._checkpointer.aget_tuple({"configurable": {"thread_id": thread_id}})
        if state is None:
            async for token in engine.stream_start(thread_id):
                yield token
            await self._complete_if_ended(attempt_id, thread_id, engine)

    async def respond(self, attempt_id: str, text: str) -> AsyncIterator[str]:
        thread_id, engine = await self.open(attempt_id)
        await self._attempts.mark_started(attempt_id)
        async for token in engine.stream_response(thread_id, text):
            yield token
        await self._complete_if_ended(attempt_id, thread_id, engine)

    async def pause(self, attempt_id: str) -> None:
        if await self._attempts.get_configuration(attempt_id) is None:
            raise AttemptNotFoundError(attempt_id)
        await self._attempts.mark_paused(attempt_id)

    async def resume(self, attempt_id: str) -> None:
        if await self._attempts.get_configuration(attempt_id) is None:
            raise AttemptNotFoundError(attempt_id)
        await self._attempts.mark_started(attempt_id)

    async def end(self, attempt_id: str) -> AsyncIterator[str]:
        thread_id, engine = await self.open(attempt_id)
        async for token in engine.stream_end(thread_id):
            yield token
        await self._complete_if_ended(attempt_id, thread_id, engine)

    async def status(self, attempt_id: str) -> str:
        status = await self._attempts.status(attempt_id)
        if status is None:
            raise AttemptNotFoundError(attempt_id)
        return status

    async def _complete_if_ended(
        self,
        attempt_id: str,
        thread_id: str,
        engine: InterviewEngine,
    ) -> None:
        state = await engine.get_state(thread_id)
        if state.get("ended"):
            await self._attempts.mark_ended(
                attempt_id,
                state.get("termination_reason") or "topics_covered",
            )
