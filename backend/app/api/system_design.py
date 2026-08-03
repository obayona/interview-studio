from __future__ import annotations

from typing import Annotated, cast

from fastapi import APIRouter, File, Form, Request, Response, UploadFile

from backend.app.application.system_design import SystemDesignService
from backend.app.domain.system_design import (
    MAX_SNAPSHOT_BYTES,
    SceneUpdate,
    SnapshotReason,
    SnapshotSummary,
    SystemDesignSession,
)

router = APIRouter(prefix="/api/v1/system-design", tags=["system-design"])


def service(request: Request) -> SystemDesignService:
    return cast(SystemDesignService, request.app.state.system_design)


@router.get("/{attempt_id}")
async def get_session(request: Request, attempt_id: str) -> SystemDesignSession:
    return await service(request).get(attempt_id)


@router.put("/{attempt_id}")
async def save_scene(request: Request, attempt_id: str, update: SceneUpdate) -> SystemDesignSession:
    return await service(request).save(attempt_id, update)


@router.post("/{attempt_id}/snapshots", status_code=201)
async def create_snapshot(
    request: Request,
    attempt_id: str,
    scene_version: Annotated[int, Form(ge=1)],
    reason: Annotated[SnapshotReason, Form()],
    image: Annotated[UploadFile, File()],
) -> SnapshotSummary:
    return await service(request).snapshot(
        attempt_id,
        scene_version,
        await image.read(MAX_SNAPSHOT_BYTES + 1),
        reason,
    )


@router.get("/{attempt_id}/snapshots/{snapshot_id}")
async def get_snapshot(request: Request, attempt_id: str, snapshot_id: str) -> Response:
    return Response(
        await service(request).snapshot_image(attempt_id, snapshot_id),
        media_type="image/png",
    )
