from __future__ import annotations

from collections.abc import AsyncIterator, Iterator, Sequence
from datetime import UTC, datetime
from typing import Any, cast
from uuid import uuid4

from langchain_core.messages import BaseMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import (
    WRITES_IDX_MAP,
    BaseCheckpointSaver,
    ChannelVersions,
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
)

from backend.app.core.database import SQLiteManager
from backend.app.infrastructure.json_codec import StrictJsonCodec


class InterviewSQLiteCheckpointer(BaseCheckpointSaver[Any]):
    """Async shallow saver backed by canonical transcript and one state row."""

    def __init__(self, database: SQLiteManager, codec: StrictJsonCodec | None = None) -> None:
        super().__init__()
        self._database = database
        self._codec = codec or StrictJsonCodec()

    def get_tuple(self, config: RunnableConfig) -> CheckpointTuple | None:
        raise NotImplementedError("Use aget_tuple with the asynchronous application saver")

    def list(
        self,
        config: RunnableConfig | None,
        *,
        filter: dict[str, Any] | None = None,
        before: RunnableConfig | None = None,
        limit: int | None = None,
    ) -> Iterator[CheckpointTuple]:
        raise NotImplementedError("Use alist with the asynchronous application saver")

    def put(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> RunnableConfig:
        raise NotImplementedError("Use aput with the asynchronous application saver")

    def put_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        raise NotImplementedError("Use aput_writes with the asynchronous application saver")

    def delete_thread(self, thread_id: str) -> None:
        raise NotImplementedError("Use adelete_thread with the asynchronous application saver")

    async def aput(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> RunnableConfig:
        del new_versions
        thread_id, namespace, _ = self._coordinates(config)
        attempt_id = await self._attempt_id(thread_id)
        checkpoint_id = str(checkpoint["id"])
        now = _utc_now()
        channel_values = dict(checkpoint.get("channel_values", {}))
        messages = channel_values.pop("messages", [])
        if not isinstance(messages, list) or not all(
            isinstance(message, BaseMessage) for message in messages
        ):
            raise TypeError("The messages channel must contain LangChain messages")

        state_payload = {
            "channel_values": channel_values,
            "pending_sends": checkpoint.get("pending_sends", []),
        }
        state_json = self._codec.dumps(state_payload)
        channel_versions_json = self._codec.dumps(checkpoint.get("channel_versions", {}))
        versions_seen_json = self._codec.dumps(checkpoint.get("versions_seen", {}))
        updated_channels_json = self._codec.dumps(checkpoint.get("updated_channels"))
        metadata_json = self._codec.dumps(metadata)

        async with self._database.transaction() as connection:
            for sequence, message in enumerate(messages):
                assert isinstance(message, BaseMessage)
                message_id = str(message.id)
                connection.execute(
                    """
                    INSERT INTO interview_messages (
                        id, attempt_id, langgraph_message_id, sequence, role,
                        message_type, content_json, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(attempt_id, langgraph_message_id) DO UPDATE SET
                        sequence = excluded.sequence,
                        role = excluded.role,
                        message_type = excluded.message_type,
                        content_json = excluded.content_json
                    """,
                    (
                        str(uuid4()),
                        attempt_id,
                        message_id,
                        sequence,
                        message.type,
                        message.type,
                        self._codec.dumps_message(message),
                        now,
                    ),
                )
            connection.execute(
                """
                INSERT INTO interview_graph_state (
                    attempt_id, thread_id, checkpoint_namespace, checkpoint_id,
                    checkpoint_version, timestamp, state_json, channel_versions_json,
                    versions_seen_json, updated_channels_json, metadata_json,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(thread_id, checkpoint_namespace) DO UPDATE SET
                    attempt_id = excluded.attempt_id,
                    checkpoint_id = excluded.checkpoint_id,
                    checkpoint_version = excluded.checkpoint_version,
                    timestamp = excluded.timestamp,
                    state_json = excluded.state_json,
                    channel_versions_json = excluded.channel_versions_json,
                    versions_seen_json = excluded.versions_seen_json,
                    updated_channels_json = excluded.updated_channels_json,
                    metadata_json = excluded.metadata_json,
                    updated_at = excluded.updated_at
                """,
                (
                    attempt_id,
                    thread_id,
                    namespace,
                    checkpoint_id,
                    int(checkpoint.get("v", 2)),
                    str(checkpoint["ts"]),
                    state_json,
                    channel_versions_json,
                    versions_seen_json,
                    updated_channels_json,
                    metadata_json,
                    now,
                    now,
                ),
            )
            connection.execute(
                """
                DELETE FROM interview_graph_writes
                WHERE thread_id = ? AND checkpoint_namespace = ? AND checkpoint_id != ?
                """,
                (thread_id, namespace, checkpoint_id),
            )

        return RunnableConfig(
            configurable={
                "thread_id": thread_id,
                "checkpoint_ns": namespace,
                "checkpoint_id": checkpoint_id,
            }
        )

    async def aput_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        thread_id, namespace, checkpoint_id = self._coordinates(config)
        if not checkpoint_id:
            raise ValueError("checkpoint_id is required when storing pending writes")
        attempt_id = await self._attempt_id(thread_id)
        now = _utc_now()
        async with self._database.transaction() as connection:
            for index, (channel, value) in enumerate(writes):
                write_index = WRITES_IDX_MAP.get(channel, index)
                connection.execute(
                    """
                    INSERT INTO interview_graph_writes (
                        attempt_id, thread_id, checkpoint_namespace, checkpoint_id,
                        task_id, task_path, write_index, channel, value_json, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(
                        thread_id, checkpoint_namespace, checkpoint_id, task_id, write_index
                    ) DO UPDATE SET
                        channel = excluded.channel,
                        value_json = excluded.value_json,
                        task_path = excluded.task_path
                    """,
                    (
                        attempt_id,
                        thread_id,
                        namespace,
                        checkpoint_id,
                        task_id,
                        task_path,
                        write_index,
                        channel,
                        self._codec.dumps(value),
                        now,
                    ),
                )

    async def aget_tuple(self, config: RunnableConfig) -> CheckpointTuple | None:
        thread_id, namespace, requested_id = self._coordinates(config)
        parameters: tuple[Any, ...] = (thread_id, namespace)
        checkpoint_filter = ""
        if requested_id:
            checkpoint_filter = " AND checkpoint_id = ?"
            parameters += (requested_id,)
        row = await self._database.fetchone(
            f"""
            SELECT * FROM interview_graph_state
            WHERE thread_id = ? AND checkpoint_namespace = ?{checkpoint_filter}
            """,
            parameters,
        )
        if row is None:
            return None
        message_rows = await self._database.fetchall(
            """
            SELECT content_json FROM interview_messages
            WHERE attempt_id = ? ORDER BY sequence
            """,
            (row["attempt_id"],),
        )
        state = self._codec.loads(str(row["state_json"]))
        channel_values = dict(state["channel_values"])
        channel_values["messages"] = [
            self._codec.loads_message(str(message["content_json"])) for message in message_rows
        ]
        checkpoint = cast(
            Checkpoint,
            {
                "v": int(row["checkpoint_version"]),
                "id": str(row["checkpoint_id"]),
                "ts": str(row["timestamp"]),
                "channel_values": channel_values,
                "channel_versions": self._codec.loads(str(row["channel_versions_json"])),
                "versions_seen": self._codec.loads(str(row["versions_seen_json"])),
                "pending_sends": state.get("pending_sends", []),
                "updated_channels": self._codec.loads(str(row["updated_channels_json"])),
            },
        )
        write_rows = await self._database.fetchall(
            """
            SELECT task_id, channel, value_json FROM interview_graph_writes
            WHERE thread_id = ? AND checkpoint_namespace = ? AND checkpoint_id = ?
            ORDER BY task_id, write_index
            """,
            (thread_id, namespace, row["checkpoint_id"]),
        )
        stored_config = RunnableConfig(
            configurable={
                "thread_id": thread_id,
                "checkpoint_ns": namespace,
                "checkpoint_id": str(row["checkpoint_id"]),
            }
        )
        return CheckpointTuple(
            config=stored_config,
            checkpoint=checkpoint,
            metadata=cast(CheckpointMetadata, self._codec.loads(str(row["metadata_json"]))),
            pending_writes=[
                (str(item["task_id"]), str(item["channel"]), self._codec.loads(item["value_json"]))
                for item in write_rows
            ],
        )

    async def alist(
        self,
        config: RunnableConfig | None,
        *,
        filter: dict[str, Any] | None = None,
        before: RunnableConfig | None = None,
        limit: int | None = None,
    ) -> AsyncIterator[CheckpointTuple]:
        if filter:
            raise ValueError("Metadata filters are unsupported by the shallow saver")
        if before is not None or limit == 0:
            return
        if config is None:
            rows = await self._database.fetchall(
                """
                SELECT thread_id, checkpoint_namespace
                FROM interview_graph_state ORDER BY updated_at DESC
                """
            )
            for row in rows[:limit]:
                result = await self.aget_tuple(
                    RunnableConfig(
                        configurable={
                            "thread_id": str(row["thread_id"]),
                            "checkpoint_ns": str(row["checkpoint_namespace"]),
                        }
                    )
                )
                if result is not None:
                    yield result
            return
        result = await self.aget_tuple(config)
        if result is not None:
            yield result

    async def adelete_thread(self, thread_id: str) -> None:
        async with self._database.transaction() as connection:
            connection.execute(
                "DELETE FROM interview_graph_writes WHERE thread_id = ?", (thread_id,)
            )
            connection.execute(
                "DELETE FROM interview_graph_state WHERE thread_id = ?", (thread_id,)
            )

    async def _attempt_id(self, thread_id: str) -> str:
        row = await self._database.fetchone(
            "SELECT id FROM interview_attempts WHERE thread_id = ?", (thread_id,)
        )
        if row is None:
            raise ValueError(f"No interview attempt exists for thread '{thread_id}'")
        return str(row["id"])

    @staticmethod
    def _coordinates(config: RunnableConfig) -> tuple[str, str, str]:
        configurable = config.get("configurable", {})
        thread_id = str(configurable.get("thread_id", "")).strip()
        if not thread_id:
            raise ValueError("thread_id is required")
        return (
            thread_id,
            str(configurable.get("checkpoint_ns", "")),
            str(configurable.get("checkpoint_id", "")),
        )


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()
