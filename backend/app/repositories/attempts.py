from __future__ import annotations

from datetime import UTC, datetime
from typing import TypedDict

from backend.app.core.database import SQLiteManager
from backend.app.infrastructure.json_codec import StrictJsonCodec
from backend.interview_engine.models import InterviewConfiguration


class TranscriptMessage(TypedDict):
    id: str
    sequence: int
    role: str
    text: str
    created_at: str


class AttemptRepository:
    def __init__(self, database: SQLiteManager) -> None:
        self._database = database

    async def get_configuration(self, attempt_id: str) -> tuple[str, InterviewConfiguration] | None:
        row = await self._database.fetchone(
            "SELECT thread_id, configuration_json FROM interview_attempts WHERE id = ?",
            (attempt_id,),
        )
        if row is None:
            return None
        return str(row["thread_id"]), InterviewConfiguration.model_validate_json(
            row["configuration_json"]
        )

    async def transcript(self, attempt_id: str) -> list[TranscriptMessage]:
        rows = await self._database.fetchall(
            """
            SELECT langgraph_message_id, sequence, role, content_json, created_at
            FROM interview_messages WHERE attempt_id = ? ORDER BY sequence
            """,
            (attempt_id,),
        )
        codec = StrictJsonCodec()
        transcript: list[TranscriptMessage] = []
        for row in rows:
            message = codec.loads_message(str(row["content_json"]))
            transcript.append(
                {
                    "id": str(row["langgraph_message_id"]),
                    "sequence": int(row["sequence"]),
                    "role": _public_role(str(row["role"])),
                    "text": message.text,
                    "created_at": str(row["created_at"]),
                }
            )
        return transcript

    async def mark_started(self, attempt_id: str) -> None:
        timestamp = datetime.now(UTC).isoformat()
        async with self._database.transaction() as connection:
            connection.execute(
                """
                UPDATE interview_attempts
                SET status = 'in_progress',
                    started_at = COALESCE(started_at, ?),
                    updated_at = ?
                WHERE id = ? AND status IN ('ready', 'in_progress')
                """,
                (timestamp, timestamp, attempt_id),
            )

    async def mark_ended(self, attempt_id: str, reason: str) -> None:
        timestamp = datetime.now(UTC).isoformat()
        async with self._database.transaction() as connection:
            attempt = connection.execute(
                "SELECT stage_id FROM interview_attempts WHERE id = ?",
                (attempt_id,),
            ).fetchone()
            if attempt is None:
                return
            connection.execute(
                """
                UPDATE interview_attempts
                SET status = 'completed', ended_at = ?,
                    termination_reason = ?, updated_at = ?
                WHERE id = ?
                """,
                (timestamp, reason, timestamp, attempt_id),
            )
            if attempt["stage_id"] is not None:
                connection.execute(
                    """
                    UPDATE interview_stages
                    SET status = 'completed', updated_at = ?
                    WHERE id = ?
                    """,
                    (timestamp, attempt["stage_id"]),
                )


def _public_role(role: str) -> str:
    return {"human": "user", "ai": "assistant"}.get(role, role)
