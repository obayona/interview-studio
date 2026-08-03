from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from backend.interview_engine.models import (
    InterviewConfiguration,
    InterviewType,
    TerminationReason,
)
from backend.interview_engine.prompts import (
    SYSTEM_PROMPT,
    build_closing_instruction,
    build_interview_context,
    build_system_design_turn_instruction,
    build_turn_instruction,
)
from backend.interview_engine.state import InterviewState
from backend.interview_engine.topics import topics_for


def utc_now() -> datetime:
    return datetime.now(UTC)


def elapsed_seconds(started_at: str, now: datetime | None = None) -> float:
    started = datetime.fromisoformat(started_at)
    return max(0.0, ((now or utc_now()) - started).total_seconds())


def determine_termination(
    state: InterviewState,
    configuration: InterviewConfiguration,
) -> TerminationReason | None:
    if state.get("user_requested_end"):
        return TerminationReason.USER_REQUESTED
    if state.get("elapsed_seconds", 0) >= configuration.limits.max_duration_minutes * 60:
        return TerminationReason.TIME_LIMIT
    if state.get("question_count", 0) >= configuration.limits.max_questions:
        return TerminationReason.QUESTION_LIMIT
    topics = state.get("topics", [])
    covered = set(state.get("topics_covered", []))
    if topics and all(topic in covered for topic in topics):
        return TerminationReason.TOPICS_COVERED
    return None


class InterviewGraph:
    def __init__(
        self,
        configuration: InterviewConfiguration,
        chat_model: BaseChatModel,
        checkpointer: BaseCheckpointSaver[Any],
    ) -> None:
        self._configuration = configuration
        self._chat_model = chat_model
        self.compiled: Any = self._compile(checkpointer)

    def initial_state(self) -> InterviewState:
        topics = list(self._configuration.topics or topics_for(self._configuration.interview_type))
        return InterviewState(
            messages=[],
            topics=topics,
            topics_covered=[],
            current_topic=None,
            question_count=0,
            follow_up_count=0,
            started_at=utc_now().isoformat(),
            elapsed_seconds=0,
            ended=False,
            user_requested_end=False,
            termination_reason=None,
            last_processed_message_id=None,
            diagram_observation=None,
        )

    def _compile(self, checkpointer: BaseCheckpointSaver[Any]) -> CompiledStateGraph[Any, Any]:
        graph = StateGraph(InterviewState)
        graph.add_node("prepare", self._prepare)
        graph.add_node("interviewer", self._interviewer)
        graph.add_node("closing", self._closing)
        graph.add_edge(START, "prepare")
        graph.add_conditional_edges(
            "prepare",
            self._route_after_prepare,
            {"interviewer": "interviewer", "closing": "closing", "end": END},
        )
        graph.add_edge("interviewer", END)
        graph.add_edge("closing", END)
        return graph.compile(checkpointer=checkpointer)

    async def _prepare(self, state: InterviewState) -> InterviewState:
        updates = InterviewState()
        started_at = state.get("started_at") or utc_now().isoformat()
        updates["started_at"] = started_at
        updates["elapsed_seconds"] = elapsed_seconds(started_at)
        if not state.get("topics"):
            updates["topics"] = list(
                self._configuration.topics or topics_for(self._configuration.interview_type)
            )

        messages = state.get("messages", [])
        last_message = messages[-1] if messages else None
        if not isinstance(last_message, HumanMessage):
            return updates
        if last_message.id and last_message.id == state.get("last_processed_message_id"):
            return updates

        current_topic = state.get("current_topic")
        follow_up_count = state.get("follow_up_count", 0)
        covered = list(state.get("topics_covered", []))
        if current_topic:
            if follow_up_count < self._configuration.limits.follow_up_questions_per_topic:
                updates["follow_up_count"] = follow_up_count + 1
            else:
                if current_topic not in covered:
                    covered.append(current_topic)
                updates["topics_covered"] = covered
                updates["current_topic"] = None
                updates["follow_up_count"] = 0
        updates["last_processed_message_id"] = last_message.id
        return updates

    async def _route_after_prepare(self, state: InterviewState) -> str:
        if state.get("ended"):
            return "end"

        reason = determine_termination(state, self._configuration)
        if reason:
            return "closing"

        messages = state.get("messages", [])
        if not messages or isinstance(messages[-1], HumanMessage):
            return "interviewer"
        return "end"

    async def _interviewer(self, state: InterviewState) -> InterviewState:
        current_topic = state.get("current_topic")
        topics_covered = set(state.get("topics_covered", []))
        topic = current_topic or next(
            (item for item in state.get("topics", []) if item not in topics_covered),
            "role-relevant experience",
        )
        is_follow_up = current_topic is not None and state.get("follow_up_count", 0) > 0
        response = await self._chat_model.ainvoke(
            [
                SystemMessage(content=SYSTEM_PROMPT),
                SystemMessage(content=build_interview_context(self._configuration)),
                *state.get("messages", []),
                SystemMessage(
                    content=(
                        build_system_design_turn_instruction(
                            state,
                            topic=topic,
                            diagram_observation=state.get("diagram_observation"),
                        )
                        if self._configuration.interview_type == InterviewType.SYSTEM_DESIGN
                        else build_turn_instruction(
                            state,
                            topic=topic,
                            is_follow_up=is_follow_up,
                        )
                    )
                ),
            ]
        )
        return InterviewState(
            messages=[response],
            current_topic=topic,
            question_count=state.get("question_count", 0) + 1,
            diagram_observation=None,
        )

    async def _closing(self, state: InterviewState) -> InterviewState:
        reason = determine_termination(state, self._configuration)
        reason_value = (reason or TerminationReason.USER_REQUESTED).value
        response = await self._chat_model.ainvoke(
            [
                SystemMessage(content=SYSTEM_PROMPT),
                SystemMessage(content=build_interview_context(self._configuration)),
                *state.get("messages", []),
                *(
                    [
                        SystemMessage(
                            content=(
                                "Final whiteboard observation for interview context:\n"
                                f"{state.get('diagram_observation', '')}"
                            )
                        )
                    ]
                    if state.get("diagram_observation")
                    else []
                ),
                SystemMessage(content=build_closing_instruction(reason_value)),
            ]
        )
        return InterviewState(
            messages=[response],
            ended=True,
            termination_reason=reason_value,
            diagram_observation=None,
        )
