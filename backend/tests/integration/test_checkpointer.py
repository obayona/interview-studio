from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, TypedDict
from unittest.mock import ANY

import pytest
from langchain_core.messages import AIMessage, AnyMessage, HumanMessage
from langgraph.checkpoint.base import empty_checkpoint
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from backend.app.core.database import SQLiteManager
from backend.app.infrastructure.checkpointer import InterviewSQLiteCheckpointer
from backend.app.infrastructure.json_codec import UnsupportedCheckpointValueError
from backend.app.repositories.attempts import AttemptRepository
from backend.interview_engine.models import InterviewConfiguration


@pytest.fixture
async def database(tmp_path: Path) -> SQLiteManager:
    manager = SQLiteManager(tmp_path / "test.sqlite3", Path(__file__).parents[2] / "migrations")
    await manager.start()
    now = datetime.now(UTC).isoformat()
    async with manager.transaction() as connection:
        connection.execute(
            """
            INSERT INTO interview_attempts (
                id, thread_id, status, configuration_json, created_at, updated_at
            ) VALUES ('attempt-1', 'thread-1', 'ready', ?, ?, ?)
            """,
            (InterviewConfiguration(job_listing="Backend role").model_dump_json(), now, now),
        )
    yield manager
    await manager.close()


async def test_shallow_round_trip_writes_idempotency_and_deletion(
    database: SQLiteManager,
) -> None:
    saver = InterviewSQLiteCheckpointer(database)
    config = {"configurable": {"thread_id": "thread-1"}}
    checkpoint = empty_checkpoint()
    checkpoint["channel_values"] = {
        "messages": [
            HumanMessage(content="Hello", id="human-1"),
            AIMessage(content="Welcome", id="ai-1"),
        ],
        "question_count": 1,
    }

    stored_config = await saver.aput(config, checkpoint, {"source": "loop"}, {})
    await saver.aput(config, checkpoint, {"source": "loop"}, {})
    await saver.aput_writes(stored_config, [("custom", {"safe": True})], "task-1")
    await saver.aput_writes(stored_config, [("custom", {"safe": True})], "task-1")

    restored = await saver.aget_tuple(config)
    assert restored is not None
    assert restored.checkpoint["channel_values"]["question_count"] == 1
    assert [message.id for message in restored.checkpoint["channel_values"]["messages"]] == [
        "human-1",
        "ai-1",
    ]
    assert restored.pending_writes == [("task-1", "custom", {"safe": True})]
    assert len([item async for item in saver.alist(config)]) == 1
    assert len(await database.fetchall("SELECT * FROM interview_messages")) == 2
    assert len(await database.fetchall("SELECT * FROM interview_graph_state")) == 1
    assert len(await database.fetchall("SELECT * FROM interview_graph_writes")) == 1
    assert await AttemptRepository(database).transcript("attempt-1") == [
        {
            "id": "human-1",
            "sequence": 0,
            "role": "user",
            "text": "Hello",
            "created_at": ANY,
        },
        {
            "id": "ai-1",
            "sequence": 1,
            "role": "assistant",
            "text": "Welcome",
            "created_at": ANY,
        },
    ]

    await saver.adelete_thread("thread-1")
    assert await saver.aget_tuple(config) is None
    assert len(await database.fetchall("SELECT * FROM interview_messages")) == 2


async def test_binary_checkpoint_values_are_rejected(database: SQLiteManager) -> None:
    saver = InterviewSQLiteCheckpointer(database)
    checkpoint = empty_checkpoint()
    checkpoint["channel_values"] = {"messages": [], "binary": b"not-allowed"}

    with pytest.raises(UnsupportedCheckpointValueError, match="binary values"):
        await saver.aput(
            {"configurable": {"thread_id": "thread-1"}},
            checkpoint,
            {},
            {},
        )


class ExampleState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    count: int


async def test_real_langgraph_async_execution_resumes_from_shallow_state(
    database: SQLiteManager,
) -> None:
    saver = InterviewSQLiteCheckpointer(database)

    async def respond(state: ExampleState) -> ExampleState:
        return {
            "messages": [
                AIMessage(content=f"Turn {state['count'] + 1}", id=f"ai-{state['count']}")
            ],
            "count": state["count"] + 1,
        }

    builder = StateGraph(ExampleState)
    builder.add_node("respond", respond)
    builder.add_edge(START, "respond")
    builder.add_edge("respond", END)
    graph = builder.compile(checkpointer=saver)
    config = {"configurable": {"thread_id": "thread-1"}}

    first = await graph.ainvoke(
        {"messages": [HumanMessage(content="First", id="human-1")], "count": 0},
        config,
    )
    second = await graph.ainvoke(
        {"messages": [HumanMessage(content="Second", id="human-2")]},
        config,
    )

    assert first["count"] == 1
    assert second["count"] == 2
    assert [message.id for message in second["messages"]] == [
        "human-1",
        "ai-0",
        "human-2",
        "ai-1",
    ]
    assert len(await database.fetchall("SELECT * FROM interview_graph_state")) == 1
    assert len(await database.fetchall("SELECT * FROM interview_messages")) == 4
