from __future__ import annotations

from typing import cast

from fastapi import APIRouter, Request

from backend.app.core.errors import AttemptNotFoundError
from backend.app.repositories.attempts import AttemptRepository, TranscriptMessage

router = APIRouter(prefix="/api/v1/interviews", tags=["interviews"])


@router.get("/{attempt_id}/history")
async def interview_history(request: Request, attempt_id: str) -> dict[str, object]:
    attempts = cast(AttemptRepository, request.app.state.attempts)
    if await attempts.get_configuration(attempt_id) is None:
        raise AttemptNotFoundError(attempt_id)
    messages: list[TranscriptMessage] = await attempts.transcript(attempt_id)
    return {"attempt_id": attempt_id, "messages": messages}
