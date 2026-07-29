from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.app.application.interviews import InterviewService
from backend.app.core.errors import ApplicationError

PROTOCOL_VERSION = "1.0"
router = APIRouter()


def _event(attempt_id: str, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "protocol_version": PROTOCOL_VERSION,
        "event_id": str(uuid4()),
        "attempt_id": attempt_id,
        "timestamp": datetime.now(UTC).isoformat(),
        "type": event_type,
        "payload": payload,
    }


async def _stream(
    websocket: WebSocket,
    attempt_id: str,
    tokens: AsyncIterator[str],
) -> None:
    completed = ""
    async for token in tokens:
        completed += token
        await websocket.send_json(_event(attempt_id, "assistant.text.delta", {"text": token}))
    if completed:
        await websocket.send_json(
            _event(attempt_id, "assistant.text.completed", {"text": completed})
        )


@router.websocket("/api/v1/interviews/{attempt_id}/ws")
async def interview_websocket(websocket: WebSocket, attempt_id: str) -> None:
    await websocket.accept()
    service: InterviewService = websocket.app.state.interviews
    try:
        while True:
            incoming = await websocket.receive_json()
            event_type = incoming.get("type")
            try:
                if event_type == "session.start":
                    await websocket.send_json(_event(attempt_id, "session.ready", {}))
                    await _stream(websocket, attempt_id, service.start(attempt_id))
                elif event_type == "user.text":
                    text = incoming.get("payload", {}).get("text", "")
                    await _stream(websocket, attempt_id, service.respond(attempt_id, text))
                elif event_type == "session.end":
                    await _stream(websocket, attempt_id, service.end(attempt_id))
                elif event_type == "ping":
                    await websocket.send_json(_event(attempt_id, "pong", {}))
                else:
                    await websocket.send_json(
                        _event(
                            attempt_id,
                            "error",
                            {
                                "code": "unsupported_event",
                                "message": f"Unsupported client event: {event_type}",
                                "field_errors": {},
                            },
                        )
                    )
            except ApplicationError as error:
                await websocket.send_json(
                    _event(
                        attempt_id,
                        "error",
                        {
                            "code": error.code,
                            "message": error.message,
                            "field_errors": error.field_errors,
                        },
                    )
                )
            except (TypeError, ValueError) as error:
                await websocket.send_json(
                    _event(
                        attempt_id,
                        "error",
                        {
                            "code": "invalid_event",
                            "message": str(error),
                            "field_errors": {},
                        },
                    )
                )
    except WebSocketDisconnect:
        return
