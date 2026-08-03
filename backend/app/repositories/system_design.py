from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any, cast
from uuid import uuid4

from backend.app.core.database import SQLiteManager
from backend.app.domain.system_design import SnapshotReason, SnapshotSummary, SystemDesignSession


class SceneVersionConflictError(Exception):
    def __init__(self, current_version: int) -> None:
        self.current_version = current_version


class SystemDesignRepository:
    def __init__(self, database: SQLiteManager) -> None:
        self._database = database

    async def attempt_type(self, attempt_id: str) -> str | None:
        row = await self._database.fetchone(
            """
            SELECT s.stage_type
            FROM interview_attempts a
            JOIN interview_stages s ON s.id = a.stage_id
            WHERE a.id = ?
            """,
            (attempt_id,),
        )
        return None if row is None else str(row["stage_type"])

    async def get(self, attempt_id: str) -> SystemDesignSession | None:
        row = await self._database.fetchone(
            "SELECT * FROM system_design_sessions WHERE attempt_id = ?",
            (attempt_id,),
        )
        if row is None:
            return None
        return SystemDesignSession(
            attempt_id=attempt_id,
            scene=json.loads(str(row["scene_json"])),
            scene_version=int(row["scene_version"]),
            created_at=datetime.fromisoformat(str(row["created_at"])),
            updated_at=datetime.fromisoformat(str(row["updated_at"])),
            snapshots=await self._snapshots(attempt_id),
        )

    async def save(
        self, attempt_id: str, scene: dict[str, Any], expected_version: int
    ) -> SystemDesignSession:
        timestamp = datetime.now(UTC).isoformat()
        serialized = json.dumps(scene, separators=(",", ":"))
        async with self._database.transaction() as connection:
            row = connection.execute(
                "SELECT scene_version FROM system_design_sessions WHERE attempt_id = ?",
                (attempt_id,),
            ).fetchone()
            if row is None:
                if expected_version != 0:
                    raise SceneVersionConflictError(0)
                version = 1
                connection.execute(
                    """
                    INSERT INTO system_design_sessions (
                        attempt_id, scene_json, scene_version, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (attempt_id, serialized, version, timestamp, timestamp),
                )
            else:
                current_version = int(row["scene_version"])
                if current_version != expected_version:
                    raise SceneVersionConflictError(current_version)
                version = current_version + 1
                connection.execute(
                    """
                    UPDATE system_design_sessions
                    SET scene_json = ?, scene_version = ?, updated_at = ?
                    WHERE attempt_id = ? AND scene_version = ?
                    """,
                    (serialized, version, timestamp, attempt_id, current_version),
                )
        session = await self.get(attempt_id)
        if session is None:
            raise RuntimeError("The system-design scene could not be persisted")
        return session

    async def add_snapshot(
        self,
        attempt_id: str,
        scene_version: int,
        png: bytes,
        reason: SnapshotReason,
    ) -> SnapshotSummary:
        snapshot_id = str(uuid4())
        timestamp = datetime.now(UTC).isoformat()
        async with self._database.transaction() as connection:
            row = connection.execute(
                "SELECT scene_version FROM system_design_sessions WHERE attempt_id = ?",
                (attempt_id,),
            ).fetchone()
            current_version = 0 if row is None else int(row["scene_version"])
            if current_version != scene_version:
                raise SceneVersionConflictError(current_version)
            connection.execute(
                """
                INSERT INTO system_design_snapshots (
                    id, attempt_id, scene_version, png_blob, reason, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (snapshot_id, attempt_id, scene_version, png, reason, timestamp),
            )
        return SnapshotSummary(
            id=snapshot_id,
            scene_version=scene_version,
            reason=reason,
            created_at=datetime.fromisoformat(timestamp),
            image_url=f"/api/v1/system-design/{attempt_id}/snapshots/{snapshot_id}",
        )

    async def snapshot(self, attempt_id: str, snapshot_id: str) -> bytes | None:
        row = await self._database.fetchone(
            """
            SELECT png_blob FROM system_design_snapshots
            WHERE attempt_id = ? AND id = ?
            """,
            (attempt_id, snapshot_id),
        )
        return None if row is None else bytes(row["png_blob"])

    async def _snapshots(self, attempt_id: str) -> list[SnapshotSummary]:
        rows = await self._database.fetchall(
            """
            SELECT id, scene_version, reason, created_at
            FROM system_design_snapshots
            WHERE attempt_id = ? ORDER BY created_at
            """,
            (attempt_id,),
        )
        return [
            SnapshotSummary(
                id=str(row["id"]),
                scene_version=int(row["scene_version"]),
                reason=cast(SnapshotReason, str(row["reason"])),
                created_at=datetime.fromisoformat(str(row["created_at"])),
                image_url=(f"/api/v1/system-design/{attempt_id}/snapshots/{row['id']}"),
            )
            for row in rows
        ]
