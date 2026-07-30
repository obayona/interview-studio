from __future__ import annotations

from typing import cast

from fastapi import APIRouter, Request, Response

from backend.app.core.errors import AttemptNotFoundError
from backend.app.repositories.attempts import AttemptRepository, TranscriptMessage

router = APIRouter(prefix="/api/v1/interviews", tags=["interviews"])
attempts_router = APIRouter(prefix="/api/v1/attempts", tags=["attempts"])


@router.get("/{attempt_id}/history")
async def interview_history(request: Request, attempt_id: str) -> dict[str, object]:
    attempts = cast(AttemptRepository, request.app.state.attempts)
    if await attempts.get_configuration(attempt_id) is None:
        raise AttemptNotFoundError(attempt_id)
    messages: list[TranscriptMessage] = await attempts.transcript(attempt_id)
    return {
        "attempt_id": attempt_id,
        "status": await attempts.status(attempt_id),
        "context": await attempts.context(attempt_id),
        "messages": messages,
    }


@attempts_router.delete("/{attempt_id}", status_code=204)
async def delete_attempt(request: Request, attempt_id: str) -> Response:
    attempts = cast(AttemptRepository, request.app.state.attempts)
    if not await attempts.delete(attempt_id):
        raise AttemptNotFoundError(attempt_id)
    return Response(status_code=204)
