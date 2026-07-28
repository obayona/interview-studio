from __future__ import annotations

from typing import Annotated, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class InterviewState(TypedDict, total=False):
    messages: Annotated[list[AnyMessage], add_messages]
    topics: list[str]
    topics_covered: list[str]
    current_topic: str | None
    question_count: int
    follow_up_count: int
    started_at: str
    elapsed_seconds: float
    ended: bool
    user_requested_end: bool
    termination_reason: str | None
    last_processed_message_id: str | None
