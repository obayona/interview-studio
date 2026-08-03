from __future__ import annotations

from backend.app.core.errors import ApplicationError, AttemptNotFoundError
from backend.app.domain.system_design import (
    MAX_SNAPSHOT_BYTES,
    SceneUpdate,
    SnapshotReason,
    SnapshotSummary,
    SystemDesignSession,
)
from backend.app.repositories.system_design import (
    SceneVersionConflictError,
    SystemDesignRepository,
)

EMPTY_SCENE: dict[str, object] = {"elements": [], "appState": {}, "files": {}}


class SystemDesignService:
    def __init__(self, repository: SystemDesignRepository) -> None:
        self._repository = repository

    async def get(self, attempt_id: str) -> SystemDesignSession:
        await self._ensure_system_design(attempt_id)
        session = await self._repository.get(attempt_id)
        return session or SystemDesignSession(
            attempt_id=attempt_id,
            scene=EMPTY_SCENE,
            scene_version=0,
        )

    async def save(self, attempt_id: str, update: SceneUpdate) -> SystemDesignSession:
        await self._ensure_system_design(attempt_id)
        try:
            return await self._repository.save(attempt_id, update.scene, update.expected_version)
        except SceneVersionConflictError as error:
            raise self._conflict(error.current_version) from error

    async def snapshot(
        self,
        attempt_id: str,
        scene_version: int,
        png: bytes,
        reason: SnapshotReason,
    ) -> SnapshotSummary:
        await self._ensure_system_design(attempt_id)
        if not png.startswith(b"\x89PNG\r\n\x1a\n"):
            raise ApplicationError(
                code="invalid_snapshot",
                message="Whiteboard snapshots must be PNG images.",
                status_code=422,
            )
        if len(png) > MAX_SNAPSHOT_BYTES:
            raise ApplicationError(
                code="snapshot_too_large",
                message="Whiteboard snapshots must not exceed 5 MiB.",
                status_code=422,
            )
        try:
            return await self._repository.add_snapshot(attempt_id, scene_version, png, reason)
        except SceneVersionConflictError as error:
            raise self._conflict(error.current_version) from error

    async def snapshot_image(self, attempt_id: str, snapshot_id: str) -> bytes:
        await self._ensure_system_design(attempt_id)
        image = await self._repository.snapshot(attempt_id, snapshot_id)
        if image is None:
            raise ApplicationError(
                code="snapshot_not_found",
                message="The whiteboard snapshot was not found.",
                status_code=404,
            )
        return image

    async def _ensure_system_design(self, attempt_id: str) -> None:
        stage_type = await self._repository.attempt_type(attempt_id)
        if stage_type is None:
            raise AttemptNotFoundError(attempt_id)
        if stage_type != "system_design":
            raise ApplicationError(
                code="not_system_design_attempt",
                message="Whiteboards are available only for system-design attempts.",
                status_code=409,
            )

    @staticmethod
    def _conflict(current_version: int) -> ApplicationError:
        return ApplicationError(
            code="stale_scene_version",
            message="The whiteboard changed in another session. Reload it before saving.",
            status_code=409,
            field_errors={"expected_version": [f"Current version is {current_version}."]},
        )
