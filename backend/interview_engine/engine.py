from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import cast
from uuid import uuid4

from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage
from langchain_core.runnables import RunnableConfig

from backend.interview_engine.graph import InterviewGraph
from backend.interview_engine.models import InterviewConfiguration
from backend.interview_engine.ports import DiagramObserverPort, SpeechToTextPort, TextToSpeechPort
from backend.interview_engine.state import InterviewState

logger = logging.getLogger("interview-engine")


class InterviewEngine:
    def __init__(
        self,
        configuration: InterviewConfiguration,
        graph: InterviewGraph,
        speech_to_text: SpeechToTextPort | None = None,
        text_to_speech: TextToSpeechPort | None = None,
        diagram_observer: DiagramObserverPort | None = None,
    ) -> None:
        self.configuration = configuration
        self._graph = graph
        self._speech_to_text = speech_to_text
        self._text_to_speech = text_to_speech
        self._diagram_observer = diagram_observer

    async def transcribe(self, audio: bytes, filename: str) -> str:
        if self._speech_to_text is None:
            raise ValueError("Speech-to-text is not configured")
        return await self._speech_to_text.transcribe(audio, filename)

    async def synthesize(self, text: str) -> bytes:
        if self._text_to_speech is None:
            raise ValueError("Text-to-speech is not configured")
        return await self._text_to_speech.synthesize(text)

    async def observe_diagram(self, png: bytes, context: str) -> str | None:
        if self._diagram_observer is None:
            return None
        return await self._diagram_observer.observe(png, context)

    async def stream_start(self, thread_id: str) -> AsyncIterator[str]:
        logger.debug("Starting interview thread %s", thread_id)
        async for token in self._stream(self._graph.initial_state(), thread_id):
            yield token

    async def stream_response(
        self, thread_id: str, answer: str, diagram_observation: str | None = None
    ) -> AsyncIterator[str]:
        normalized_answer = answer.strip()
        if not normalized_answer:
            raise ValueError("Interview answers cannot be empty")
        logger.debug("Processing candidate response for thread %s", thread_id)
        input_state = InterviewState(
            messages=[HumanMessage(content=normalized_answer, id=str(uuid4()))],
            diagram_observation=diagram_observation,
        )
        async for token in self._stream(input_state, thread_id):
            yield token

    async def stream_end(
        self, thread_id: str, diagram_observation: str | None = None
    ) -> AsyncIterator[str]:
        logger.debug("Ending interview thread %s at candidate request", thread_id)
        input_state = InterviewState(
            user_requested_end=True, diagram_observation=diagram_observation
        )
        async for token in self._stream(input_state, thread_id):
            yield token

    async def get_state(self, thread_id: str) -> InterviewState:
        snapshot = await self._graph.compiled.aget_state(self._runtime_config(thread_id))
        return cast(InterviewState, snapshot.values)

    async def _stream(
        self,
        input_state: InterviewState,
        thread_id: str,
    ) -> AsyncIterator[str]:
        try:
            async for message, metadata in self._graph.compiled.astream(
                input_state,
                config=self._runtime_config(thread_id),
                stream_mode="messages",
            ):
                if (
                    metadata.get("langgraph_node") in {"interviewer", "closing"}
                    and isinstance(message, (AIMessage, AIMessageChunk))
                    and message.text
                ):
                    yield message.text
        except Exception:
            logger.error("Interview graph failed for thread %s", thread_id, exc_info=True)
            raise

    @staticmethod
    def _runtime_config(thread_id: str) -> RunnableConfig:
        if not thread_id.strip():
            raise ValueError("thread_id cannot be empty")
        return RunnableConfig(configurable={"thread_id": thread_id})
