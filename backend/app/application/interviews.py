from __future__ import annotations

from collections.abc import AsyncIterator

from backend.app.core.config import ConfigurationStore
from backend.app.core.errors import AttemptNotFoundError, ProviderNotConfiguredError
from backend.app.infrastructure.checkpointer import InterviewSQLiteCheckpointer
from backend.app.repositories.attempts import AttemptRepository
from backend.interview_engine import InterviewEngine, InterviewEngineBuilder


class InterviewService:
    def __init__(
        self,
        attempts: AttemptRepository,
        settings: ConfigurationStore,
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
        return thread_id, builder.build()

    async def start(self, attempt_id: str) -> AsyncIterator[str]:
        thread_id, engine = await self.open(attempt_id)
        state = await self._checkpointer.aget_tuple({"configurable": {"thread_id": thread_id}})
        if state is None:
            async for token in engine.stream_start(thread_id):
                yield token

    async def respond(self, attempt_id: str, text: str) -> AsyncIterator[str]:
        thread_id, engine = await self.open(attempt_id)
        async for token in engine.stream_response(thread_id, text):
            yield token

    async def end(self, attempt_id: str) -> AsyncIterator[str]:
        thread_id, engine = await self.open(attempt_id)
        async for token in engine.stream_end(thread_id):
            yield token
