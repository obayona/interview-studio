from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

MAX_SCENE_BYTES = 5 * 1024 * 1024
MAX_SNAPSHOT_BYTES = 5 * 1024 * 1024
SnapshotReason = Literal["periodic", "explicit", "interview_end"]


class SceneUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_version: int = Field(ge=0)
    scene: dict[str, Any]

    @field_validator("scene")
    @classmethod
    def validate_scene(cls, scene: dict[str, Any]) -> dict[str, Any]:
        if len(json.dumps(scene, separators=(",", ":")).encode()) > MAX_SCENE_BYTES:
            raise ValueError("Scene JSON must not exceed 5 MiB")
        if not isinstance(scene.get("elements", []), list):
            raise ValueError("Scene elements must be a list")
        return scene


class SnapshotSummary(BaseModel):
    id: str
    scene_version: int
    reason: SnapshotReason
    created_at: datetime
    image_url: str


class SystemDesignSession(BaseModel):
    attempt_id: str
    scene: dict[str, Any]
    scene_version: int
    created_at: datetime | None = None
    updated_at: datetime | None = None
    snapshots: list[SnapshotSummary] = Field(default_factory=list)
