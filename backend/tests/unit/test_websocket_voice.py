from __future__ import annotations

import asyncio
import base64
from collections.abc import AsyncIterator
from types import SimpleNamespace
from typing import Any, cast

from fastapi import WebSocket, WebSocketDisconnect

from backend.app.api.websocket import interview_websocket


class Session:
    received_answers: list[str]

    def __init__(self) -> None:
        self.received_answers = []

    async def media_modes(self) -> dict[str, bool]:
        return {"text_to_speech": False}

    async def media_capabilities(self) -> dict[str, bool]:
        return {"speech_to_text": True, "text_to_speech": False}

    async def transcribe(self, audio: bytes, filename: str) -> str:
        return audio.decode()

    async def respond(self, text: str) -> AsyncIterator[str]:
        self.received_answers.append(text)
        yield "Follow-up question?"

    async def status(self) -> str:
        return "in_progress"

    async def synthesize(self, text: str) -> bytes:
        return b""


class Service:
    def __init__(self, session: Session) -> None:
        self.session = session

    async def open_session(self, attempt_id: str) -> Session:
        return self.session


def event(event_type: str, payload: dict[str, object] | None = None) -> dict[str, object]:
    return {"type": event_type, "payload": payload or {}}


class Socket:
    def __init__(self, incoming: list[dict[str, object]], service: Service) -> None:
        self.incoming = incoming
        self.sent: list[dict[str, Any]] = []
        self.app = SimpleNamespace(state=SimpleNamespace(interviews=service))

    async def accept(self) -> None:
        return None

    async def receive_json(self) -> dict[str, object]:
        if self.incoming:
            return self.incoming.pop(0)
        await asyncio.sleep(0.01)
        raise WebSocketDisconnect()

    async def send_json(self, message: dict[str, Any]) -> None:
        self.sent.append(message)


async def test_audio_segments_accumulate_until_explicit_turn_end() -> None:
    session = Session()
    incoming: list[dict[str, object]] = []
    for text in ("First part.", "Second part."):
        incoming.extend(
            [
                event("user.audio.start", {"media_type": "audio/webm"}),
                event(
                    "user.audio.chunk",
                    {"audio": base64.b64encode(text.encode()).decode("ascii")},
                ),
                event("user.audio.end"),
            ]
        )
    incoming.append(event("user.turn.end"))
    socket = Socket(incoming, Service(session))

    await interview_websocket(cast(WebSocket, socket), "attempt-1")

    assert session.received_answers == ["First part. Second part."]
    event_types = [message["type"] for message in socket.sent]
    assert event_types.count("transcript.segment.final") == 2
    assert event_types.count("transcript.final") == 1
    segments = [
        message["payload"]
        for message in socket.sent
        if message["type"] == "transcript.segment.final"
    ]
    assert segments == [
        {"text": "First part.", "sequence": 1},
        {"text": "Second part.", "sequence": 2},
    ]
