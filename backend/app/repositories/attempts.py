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


class AttemptContext(TypedDict):
    process_id: str
    process_title: str
    company_name: str
    target_role: str
    stage_type: str
    attempt_number: int
    company_info: str
    job_listing: str
    difficulty: str
    interviewer_profile: str
    language: str
    configured_topics: list[str]
    topics_covered: list[str]
    max_questions: int
    max_duration_minutes: int


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

    async def context(self, attempt_id: str) -> AttemptContext | None:
        row = await self._database.fetchone(
            """
            SELECT a.attempt_number, a.configuration_json,
                   COALESCE(s.stage_type, '') AS stage_type,
                   COALESCE(p.id, '') AS process_id,
                   COALESCE(p.title, '') AS process_title,
                   COALESCE(p.company_name, '') AS company_name,
                   COALESCE(p.target_role, '') AS target_role,
                   gs.state_json
            FROM interview_attempts a
            LEFT JOIN interview_stages s ON s.id = a.stage_id
            LEFT JOIN interview_processes p ON p.id = s.process_id
            LEFT JOIN interview_graph_state gs ON gs.attempt_id = a.id
            WHERE a.id = ?
            """,
            (attempt_id,),
        )
        if row is None:
            return None
        configuration = InterviewConfiguration.model_validate_json(str(row["configuration_json"]))
        graph_state: dict[str, object] = {}
        if row["state_json"] is not None:
            value = StrictJsonCodec().loads(str(row["state_json"]))
            if isinstance(value, dict):
                graph_state = value
        graph_topics = graph_state.get("topics", [])
        graph_topics_covered = graph_state.get("topics_covered", [])
        configured_topics = list(configuration.topics) or (
            [str(topic) for topic in graph_topics if isinstance(topic, str)]
            if isinstance(graph_topics, list)
            else []
        )
        topics_covered = (
            [str(topic) for topic in graph_topics_covered if isinstance(topic, str)]
            if isinstance(graph_topics_covered, list)
            else []
        )
        return {
            "process_id": str(row["process_id"]),
            "process_title": str(row["process_title"]),
            "company_name": str(row["company_name"]),
            "target_role": str(row["target_role"]),
            "stage_type": str(row["stage_type"] or configuration.interview_type.value),
            "attempt_number": int(row["attempt_number"]),
            "company_info": configuration.company_info,
            "job_listing": configuration.job_listing,
            "difficulty": configuration.difficulty.value,
            "interviewer_profile": configuration.interviewer_profile.value,
            "language": configuration.language,
            "configured_topics": configured_topics,
            "topics_covered": topics_covered,
            "max_questions": configuration.limits.max_questions,
            "max_duration_minutes": configuration.limits.max_duration_minutes,
        }

    async def media_preferences(self, attempt_id: str) -> dict[str, bool] | None:
        row = await self._database.fetchone(
            """
            SELECT current_tts_enabled
            FROM interview_attempts WHERE id = ?
            """,
            (attempt_id,),
        )
        if row is None:
            return None
        return {"text_to_speech": bool(row["current_tts_enabled"])}

    async def set_media_preference(self, attempt_id: str, key: str, value: bool) -> None:
        if key != "text_to_speech":
            raise ValueError(f"Unsupported media preference: {key}")
        timestamp = datetime.now(UTC).isoformat()
        async with self._database.transaction() as connection:
            connection.execute(
                "UPDATE interview_attempts "
                "SET current_tts_enabled = ?, updated_at = ? WHERE id = ?",
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
