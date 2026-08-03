from __future__ import annotations

from typing import Any, Self

from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from pydantic import SecretStr

from backend.interview_engine.engine import InterviewEngine
from backend.interview_engine.graph import InterviewGraph
from backend.interview_engine.models import (
    CandidateProfile,
    DifficultyLevel,
    InterviewConfiguration,
    InterviewerProfile,
    InterviewLimits,
    InterviewType,
)
from backend.interview_engine.ports import DiagramObserverPort, SpeechToTextPort, TextToSpeechPort


class InterviewEngineBuilder:
    def __init__(self) -> None:
        self._api_key: str | None = None
        self._model_name = "gpt-4o-mini"
        self._chat_model: BaseChatModel | None = None
        self._checkpointer: BaseCheckpointSaver[Any] | None = None
        self._candidate = CandidateProfile()
        self._job_listing = ""
        self._company_info = ""
        self._interview_type = InterviewType.MIXED
        self._interviewer_profile = InterviewerProfile.TECH_LEAD
        self._difficulty = DifficultyLevel.MID
        self._user_instructions = ""
        self._language = "English"
        self._topics: tuple[str, ...] = ()
        self._limits = InterviewLimits()
        self._speech_to_text: SpeechToTextPort | None = None
        self._text_to_speech: TextToSpeechPort | None = None
        self._diagram_observer: DiagramObserverPort | None = None

    def set_openai_api(self, api_key: str) -> Self:
        self._api_key = api_key.strip()
        return self

    def set_model(self, model_name: str) -> Self:
        self._model_name = model_name.strip()
        return self

    def set_chat_model(self, chat_model: BaseChatModel) -> Self:
        self._chat_model = chat_model
        return self

    def set_checkpointer(self, checkpointer: BaseCheckpointSaver[Any]) -> Self:
        self._checkpointer = checkpointer
        return self

    def set_candidate(self, candidate: CandidateProfile) -> Self:
        self._candidate = candidate
        return self

    def set_job_listing(self, job_listing: str) -> Self:
        self._job_listing = job_listing
        return self

    def set_company_info(self, company_info: str) -> Self:
        self._company_info = company_info
        return self

    def set_interview_type(self, interview_type: InterviewType | str) -> Self:
        self._interview_type = InterviewType(interview_type)
        return self

    def set_interviewer_profile(self, profile: InterviewerProfile | str) -> Self:
        self._interviewer_profile = InterviewerProfile(profile)
        return self

    def set_difficulty(self, difficulty: DifficultyLevel | str) -> Self:
        self._difficulty = DifficultyLevel(difficulty)
        return self

    def set_user_instructions(self, instructions: str) -> Self:
        self._user_instructions = instructions
        return self

    def set_language(self, language: str) -> Self:
        self._language = language
        return self

    def set_topics(self, topics: list[str] | tuple[str, ...]) -> Self:
        self._topics = tuple(topics)
        return self

    def set_limits(self, limits: InterviewLimits) -> Self:
        self._limits = limits
        return self

    def set_speech_to_text(self, adapter: SpeechToTextPort) -> Self:
        self._speech_to_text = adapter
        return self

    def set_text_to_speech(self, adapter: TextToSpeechPort) -> Self:
        self._text_to_speech = adapter
        return self

    def set_diagram_observer(self, adapter: DiagramObserverPort) -> Self:
        self._diagram_observer = adapter
        return self

    def build(self) -> InterviewEngine:
        configuration = InterviewConfiguration(
            candidate=self._candidate,
            job_listing=self._job_listing,
            company_info=self._company_info,
            interview_type=self._interview_type,
            interviewer_profile=self._interviewer_profile,
            difficulty=self._difficulty,
            user_instructions=self._user_instructions,
            language=self._language,
            topics=self._topics,
            limits=self._limits,
        )
        chat_model = self._chat_model or self._build_openai_model()
        checkpointer = self._checkpointer or InMemorySaver()
        graph = InterviewGraph(configuration, chat_model, checkpointer)
        return InterviewEngine(
            configuration,
            graph,
            speech_to_text=self._speech_to_text,
            text_to_speech=self._text_to_speech,
            diagram_observer=self._diagram_observer,
        )

    def _build_openai_model(self) -> BaseChatModel:
        if not self._api_key:
            raise ValueError("An OpenAI API key or a chat model must be configured")
        if not self._model_name:
            raise ValueError("model_name cannot be empty")
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            api_key=SecretStr(self._api_key),
            model=self._model_name,
            temperature=0.4,
        )
