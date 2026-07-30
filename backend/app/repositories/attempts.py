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

    async def status(self, attempt_id: str) -> str | None:
        row = await self._database.fetchone(
            "SELECT status FROM interview_attempts WHERE id = ?",
            (attempt_id,),
        )
        return None if row is None else str(row["status"])

    async def media_preferences(self, attempt_id: str) -> dict[str, bool | None] | None:
        row = await self._database.fetchone(
            """
            SELECT current_stt_enabled, current_tts_enabled
            FROM interview_attempts WHERE id = ?
            """,
            (attempt_id,),
        )
        if row is None:
            return None
        return {
            "speech_to_text": (
                None if row["current_stt_enabled"] is None else bool(row["current_stt_enabled"])
            ),
            "text_to_speech": (
                None if row["current_tts_enabled"] is None else bool(row["current_tts_enabled"])
            ),
        }

    async def set_media_preference(self, attempt_id: str, key: str, value: bool) -> None:
        column = {
            "speech_to_text": "current_stt_enabled",
            "text_to_speech": "current_tts_enabled",
        }.get(key)
        if column is None:
            raise ValueError(f"Unsupported media preference: {key}")
        timestamp = datetime.now(UTC).isoformat()
        async with self._database.transaction() as connection:
            connection.execute(
                f"UPDATE interview_attempts SET {column} = ?, updated_at = ? WHERE id = ?",
                (int(value), timestamp, attempt_id),
            )

    async def mark_started(self, attempt_id: str) -> None:
        timestamp = datetime.now(UTC).isoformat()
        async with self._database.transaction() as connection:
            connection.execute(
                """
                UPDATE interview_attempts
                SET status = 'in_progress',
                    started_at = COALESCE(started_at, ?),
                    updated_at = ?
                WHERE id = ? AND status IN ('ready', 'in_progress', 'paused')
                """,
                (timestamp, timestamp, attempt_id),
            )

    async def mark_paused(self, attempt_id: str) -> None:
        timestamp = datetime.now(UTC).isoformat()
        async with self._database.transaction() as connection:
            connection.execute(
                """
                UPDATE interview_attempts
                SET status = 'paused', updated_at = ?
                WHERE id = ? AND status = 'in_progress'
                """,
                (timestamp, attempt_id),
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

    async def delete(self, attempt_id: str) -> bool:
        timestamp = datetime.now(UTC).isoformat()
        async with self._database.transaction() as connection:
            attempt = connection.execute(
                """
                SELECT a.stage_id, s.process_id
                FROM interview_attempts a
                LEFT JOIN interview_stages s ON s.id = a.stage_id
                WHERE a.id = ?
                """,
                (attempt_id,),
            ).fetchone()
            if attempt is None:
                return False
            connection.execute("DELETE FROM interview_attempts WHERE id = ?", (attempt_id,))
            stage_id = attempt["stage_id"]
            if stage_id is not None:
                remaining = connection.execute(
                    """
                    SELECT
                        COUNT(*) AS attempt_count,
                        MAX(CASE WHEN status = 'completed' THEN 1 ELSE 0 END)
                            AS has_completed
                    FROM interview_attempts
                    WHERE stage_id = ?
                    """,
                    (stage_id,),
                ).fetchone()
                stage = connection.execute(
                    "SELECT enabled FROM interview_stages WHERE id = ?",
                    (stage_id,),
                ).fetchone()
                if remaining is not None and stage is not None:
                    if int(remaining["has_completed"] or 0):
                        status = "completed"
                    elif int(remaining["attempt_count"]):
                        status = "in_progress"
                    else:
                        status = "not_started" if bool(stage["enabled"]) else "skipped"
                    connection.execute(
                        """
                        UPDATE interview_stages
                        SET status = ?, updated_at = ?
                        WHERE id = ?
                        """,
                        (status, timestamp, stage_id),
                    )
                if attempt["process_id"] is not None:
                    connection.execute(
                        """
                        UPDATE interview_processes
                        SET updated_at = ?
                        WHERE id = ?
                        """,
                        (timestamp, attempt["process_id"]),
                    )
        return True


def _public_role(role: str) -> str:
    return {"human": "user", "ai": "assistant"}.get(role, role)
