from __future__ import annotations

from datetime import UTC, datetime
from typing import TypedDict
from uuid import uuid4

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

    async def ensure_browser_harness(self) -> str:
        attempt_id = "browser-harness"
        existing = await self.get_configuration(attempt_id)
        if existing is not None:
            return attempt_id
        now = datetime.now(UTC).isoformat()
        configuration = InterviewConfiguration(
            job_listing="Practice a general software engineering interview.",
        )
        async with self._database.transaction() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO interview_attempts (
                    id, thread_id, status, configuration_json, created_at, updated_at
                ) VALUES (?, ?, 'ready', ?, ?, ?)
                """,
                (
                    attempt_id,
                    f"harness-{uuid4()}",
                    configuration.model_dump_json(),
                    now,
                    now,
                ),
            )
        return attempt_id

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


def _public_role(role: str) -> str:
    return {"human": "user", "ai": "assistant"}.get(role, role)
