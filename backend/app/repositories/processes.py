from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from uuid import uuid4

from backend.app.core.database import SQLiteManager
from backend.app.domain.processes import (
    AttemptSummary,
    InterviewProcess,
    ProcessStage,
    ProcessSummary,
    StageConfiguration,
    StageInput,
)
from backend.interview_engine.models import InterviewType


def now() -> str:
    return datetime.now(UTC).isoformat()


class ProcessRepository:
    def __init__(self, database: SQLiteManager) -> None:
        self._database = database

    async def list_all(self) -> list[ProcessSummary]:
        rows = await self._database.fetchall(
            """
            SELECT p.*, COUNT(DISTINCT s.id) AS stage_count,
                   COUNT(DISTINCT CASE WHEN s.status = 'completed' THEN s.id END)
                       AS completed_stage_count,
                   COUNT(DISTINCT a.id) AS attempt_count
            FROM interview_processes p
            LEFT JOIN interview_stages s ON s.process_id = p.id
            LEFT JOIN interview_attempts a ON a.stage_id = s.id
            GROUP BY p.id
            ORDER BY p.updated_at DESC
            """
        )
        return [
            ProcessSummary(
                id=str(row["id"]),
                title=str(row["title"]),
                company_name=str(row["company_name"]),
                target_role=str(row["target_role"]),
                status=str(row["status"]),
                stage_count=int(row["stage_count"]),
                completed_stage_count=int(row["completed_stage_count"]),
                attempt_count=int(row["attempt_count"]),
                updated_at=str(row["updated_at"]),
            )
            for row in rows
        ]

    async def get(self, process_id: str) -> InterviewProcess | None:
        row = await self._database.fetchone(
            "SELECT * FROM interview_processes WHERE id = ?", (process_id,)
        )
        if row is None:
            return None
        stage_rows = await self._database.fetchall(
            "SELECT * FROM interview_stages WHERE process_id = ? ORDER BY position",
            (process_id,),
        )
        attempt_rows = await self._database.fetchall(
            """
            SELECT a.* FROM interview_attempts a
            JOIN interview_stages s ON s.id = a.stage_id
            WHERE s.process_id = ?
            ORDER BY s.position, a.attempt_number
            """,
            (process_id,),
        )
        attempts_by_stage: dict[str, list[AttemptSummary]] = {}
        for attempt in attempt_rows:
            attempts_by_stage.setdefault(str(attempt["stage_id"]), []).append(
                AttemptSummary(
                    id=str(attempt["id"]),
                    attempt_number=int(attempt["attempt_number"]),
                    status=str(attempt["status"]),
                    started_at=attempt["started_at"],
                    ended_at=attempt["ended_at"],
                    termination_reason=attempt["termination_reason"],
                    created_at=str(attempt["created_at"]),
                )
            )
        stages = [
            ProcessStage(
                id=str(stage["id"]),
                stage_type=InterviewType(str(stage["stage_type"])),
                position=int(stage["position"]),
                enabled=bool(stage["enabled"]),
                status=str(stage["status"]),
                configuration=StageConfiguration.model_validate_json(
                    str(stage["configuration_json"])
                ),
                attempts=attempts_by_stage.get(str(stage["id"]), []),
            )
            for stage in stage_rows
        ]
        return InterviewProcess(
            id=str(row["id"]),
            title=str(row["title"]),
            company_name=str(row["company_name"]),
            target_role=str(row["target_role"]),
            job_description=str(row["job_description"]),
            company_info=str(row["company_info"]),
            job_source_url=row["job_source_url"],
            company_source_url=row["company_source_url"],
            status=str(row["status"]),
            stages=stages,
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )

    async def create(
        self,
        *,
        title: str,
        company_name: str,
        target_role: str,
        job_description: str,
        company_info: str,
        job_source_url: str | None,
        company_source_url: str | None,
        stages: list[StageInput],
    ) -> InterviewProcess:
        process_id = str(uuid4())
        timestamp = now()
        async with self._database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO interview_processes (
                    id, title, company_name, target_role, job_description,
                    company_info, job_source_url, company_source_url, status,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?)
                """,
                (
                    process_id,
                    title,
                    company_name,
                    target_role,
                    job_description,
                    company_info,
                    job_source_url,
                    company_source_url,
                    timestamp,
                    timestamp,
                ),
            )
            self._replace_stages(connection, process_id, stages, timestamp)
        result = await self.get(process_id)
        if result is None:
            raise RuntimeError("Created process could not be read")
        return result

    async def update(
        self,
        process_id: str,
        values: dict[str, object],
        stages: list[StageInput] | None,
    ) -> InterviewProcess | None:
        current = await self.get(process_id)
        if current is None:
            return None
        timestamp = now()
        columns = {
            "title",
            "company_name",
            "target_role",
            "job_description",
            "company_info",
            "job_source_url",
            "company_source_url",
            "status",
        }
        async with self._database.transaction() as connection:
            for key, value in values.items():
                if key in columns:
                    connection.execute(
                        f"UPDATE interview_processes SET {key} = ?, updated_at = ? WHERE id = ?",
                        (value, timestamp, process_id),
                    )
            if stages is not None:
                existing_attempt = connection.execute(
                    """
                    SELECT 1 FROM interview_attempts a
                    JOIN interview_stages s ON s.id = a.stage_id
                    WHERE s.process_id = ? LIMIT 1
                    """,
                    (process_id,),
                ).fetchone()
                if existing_attempt is not None:
                    self._update_stages(connection, process_id, stages, timestamp)
                else:
                    connection.execute(
                        "DELETE FROM interview_stages WHERE process_id = ?", (process_id,)
                    )
                    self._replace_stages(connection, process_id, stages, timestamp)
        return await self.get(process_id)

    async def delete(self, process_id: str) -> bool:
        async with self._database.transaction() as connection:
            cursor = connection.execute(
                "DELETE FROM interview_processes WHERE id = ?", (process_id,)
            )
        return cursor.rowcount > 0

    async def create_attempt(
        self,
        process_id: str,
        stage_id: str,
        configuration_json: str,
        *,
        speech_to_text: bool,
        text_to_speech: bool,
    ) -> tuple[str, int] | None:
        timestamp = now()
        async with self._database.transaction() as connection:
            stage = connection.execute(
                """
                SELECT id FROM interview_stages
                WHERE id = ? AND process_id = ? AND enabled = 1
                """,
                (stage_id, process_id),
            ).fetchone()
            if stage is None:
                return None
            number = int(
                connection.execute(
                    "SELECT COALESCE(MAX(attempt_number), 0) + 1 "
                    "FROM interview_attempts WHERE stage_id = ?",
                    (stage_id,),
                ).fetchone()[0]
            )
            attempt_id = str(uuid4())
            connection.execute(
                """
                INSERT INTO interview_attempts (
                    id, stage_id, attempt_number, thread_id, status,
                    configuration_json, current_stt_enabled,
                    current_tts_enabled, created_at, updated_at
                ) VALUES (?, ?, ?, ?, 'ready', ?, ?, ?, ?, ?)
                """,
                (
                    attempt_id,
                    stage_id,
                    number,
                    str(uuid4()),
                    configuration_json,
                    int(speech_to_text),
                    int(text_to_speech),
                    timestamp,
                    timestamp,
                ),
            )
            connection.execute(
                """
                UPDATE interview_stages
                SET status = 'in_progress', updated_at = ?
                WHERE id = ? AND status IN ('not_started', 'skipped')
                """,
                (timestamp, stage_id),
            )
            connection.execute(
                "UPDATE interview_processes SET updated_at = ? WHERE id = ?",
                (timestamp, process_id),
            )
        return attempt_id, number

    @staticmethod
    def _replace_stages(
        connection: sqlite3.Connection,
        process_id: str,
        stages: list[StageInput],
        timestamp: str,
    ) -> None:
        connection.executemany(
            """
            INSERT INTO interview_stages (
                id, process_id, stage_type, position, enabled, status,
                configuration_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    stage.id,
                    process_id,
                    stage.stage_type.value,
                    position,
                    int(stage.enabled),
                    "not_started" if stage.enabled else "skipped",
                    stage.configuration.model_dump_json(),
                    timestamp,
                    timestamp,
                )
                for position, stage in enumerate(stages)
            ],
        )

    @staticmethod
    def _update_stages(
        connection: sqlite3.Connection,
        process_id: str,
        stages: list[StageInput],
        timestamp: str,
    ) -> None:
        known = {
            str(row["id"])
            for row in connection.execute(
                "SELECT id FROM interview_stages WHERE process_id = ?", (process_id,)
            ).fetchall()
        }
        if {stage.id for stage in stages} != known:
            raise ValueError("Stage identities cannot change after attempts exist")
        connection.execute(
            "UPDATE interview_stages SET position = position + 1000 WHERE process_id = ?",
            (process_id,),
        )
        for position, stage in enumerate(stages):
            connection.execute(
                """
                UPDATE interview_stages
                SET stage_type = ?, position = ?, enabled = ?,
                    status = CASE
                        WHEN ? = 0 AND status = 'not_started' THEN 'skipped'
                        WHEN ? = 1 AND status = 'skipped' THEN 'not_started'
                        ELSE status
                    END,
                    configuration_json = ?, updated_at = ?
                WHERE id = ? AND process_id = ?
                """,
                (
                    stage.stage_type.value,
                    position,
                    int(stage.enabled),
                    int(stage.enabled),
                    int(stage.enabled),
                    stage.configuration.model_dump_json(),
                    timestamp,
                    stage.id,
                    process_id,
                ),
            )
