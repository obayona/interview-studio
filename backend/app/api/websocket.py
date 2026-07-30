from __future__ import annotations

import asyncio
import base64
import binascii
import re
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.app.application.interviews import InterviewService
from backend.app.core.errors import ApplicationError

PROTOCOL_VERSION = "1.0"
MAX_AUDIO_CHUNK_BYTES = 256 * 1024
MAX_AUDIO_SEGMENT_BYTES = 10 * 1024 * 1024
OUTPUT_CHUNK_BYTES = 48 * 1024
SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+")
router = APIRouter()


def _interaction_status(attempt_status: str) -> str:
    return "completed" if attempt_status == "completed" else "ready_for_answer"


def _event(attempt_id: str, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "protocol_version": PROTOCOL_VERSION,
        "event_id": str(uuid4()),
        "attempt_id": attempt_id,
        "timestamp": datetime.now(UTC).isoformat(),
        "type": event_type,
        "payload": payload,
    }


@router.websocket("/api/v1/interviews/{attempt_id}/ws")
async def interview_websocket(websocket: WebSocket, attempt_id: str) -> None:
    await websocket.accept()
    service: InterviewService = websocket.app.state.interviews
    session = await service.open_session(attempt_id)
    send_lock = asyncio.Lock()
    modes = await session.media_modes()
    capabilities = await session.media_capabilities()
    audio_input = bytearray()
    input_media_type = "audio/webm"
    output_sequence = 0
    tts_tasks: set[asyncio.Task[None]] = set()
    tts_tail: asyncio.Task[None] | None = None
    turn_task: asyncio.Task[None] | None = None

    async def send(event_type: str, payload: dict[str, Any]) -> None:
        async with send_lock:
            await websocket.send_json(_event(attempt_id, event_type, payload))

    async def cancel_audio() -> None:
        nonlocal tts_tail
        for task in tuple(tts_tasks):
            task.cancel()
        if tts_tasks:
            await asyncio.gather(*tts_tasks, return_exceptions=True)
        tts_tasks.clear()
        tts_tail = None
        await send("assistant.audio.cancelled", {})

    async def speak(text: str) -> None:
        nonlocal output_sequence
        audio_id = str(uuid4())
        try:
            audio = await session.synthesize(text)
            for offset in range(0, len(audio), OUTPUT_CHUNK_BYTES):
                output_sequence += 1
                await send(
                    "assistant.audio.chunk",
                    {
                        "audio": base64.b64encode(
                            audio[offset : offset + OUTPUT_CHUNK_BYTES]
                        ).decode("ascii"),
                        "media_type": "audio/mpeg",
                        "sequence": output_sequence,
                        "audio_id": audio_id,
                    },
                )
            if audio:
                await send(
                    "assistant.audio.completed",
                    {"sequence": output_sequence, "audio_id": audio_id},
                )
        except asyncio.CancelledError:
            raise
        except Exception:
            await send(
                "warning",
                {
                    "code": "speech_generation_failed",
                    "message": "Audio could not be generated; the text interview can continue.",
                },
            )

    def queue_speech(text: str) -> None:
        nonlocal tts_tail
        previous = tts_tail

        async def speak_in_order() -> None:
            if previous is not None:
                await previous
            await speak(text)

        task = asyncio.create_task(speak_in_order())
        tts_tail = task
        tts_tasks.add(task)
        task.add_done_callback(tts_tasks.discard)

    async def stream(tokens: AsyncIterator[str]) -> None:
        completed = ""
        speech_buffer = ""
        async for token in tokens:
            completed += token
            speech_buffer += token
            await send("assistant.text.delta", {"text": token})
            parts = SENTENCE_BOUNDARY.split(speech_buffer)
            if len(parts) > 1:
                for sentence in parts[:-1]:
                    if modes["text_to_speech"] and sentence.strip():
                        queue_speech(sentence.strip())
                speech_buffer = parts[-1]
            elif len(speech_buffer) >= 180:
                if modes["text_to_speech"]:
                    queue_speech(speech_buffer.strip())
                speech_buffer = ""
        if completed:
            await send("assistant.text.completed", {"text": completed})
        if modes["text_to_speech"] and speech_buffer.strip():
            queue_speech(speech_buffer.strip())
        attempt_status = await session.status()
        await send(
            "interview.state",
            {"status": _interaction_status(attempt_status)},
        )

    async def run_turn(tokens: AsyncIterator[str]) -> None:
        try:
            await stream(tokens)
        except ApplicationError as error:
            await send(
                "error",
                {
                    "code": error.code,
                    "message": error.message,
                    "field_errors": error.field_errors,
                },
            )
        except Exception:
            await send(
                "error",
                {
                    "code": "interview_turn_failed",
                    "message": "The interview turn could not be completed.",
                    "field_errors": {},
                },
            )

    async def start_turn(tokens: AsyncIterator[str]) -> None:
        nonlocal turn_task
        if turn_task and not turn_task.done():
            raise ValueError("Wait for the current interviewer response to finish")
        turn_task = asyncio.create_task(run_turn(tokens))

    try:
        while True:
            incoming = await websocket.receive_json()
            event_type = incoming.get("type")
            payload = incoming.get("payload", {})
            try:
                if event_type == "session.start":
                    await send(
                        "session.ready",
                        {"modes": modes, "capabilities": capabilities},
                    )
                    await send("interview.state", {"status": "connecting"})
                    await start_turn(session.start())
                elif event_type == "user.text":
                    await cancel_audio()
                    text = str(payload.get("text", "")).strip()
                    if not text:
                        raise ValueError("Answer text cannot be empty")
                    await start_turn(session.respond(text))
                elif event_type == "user.audio.start":
                    capabilities = await session.media_capabilities()
                    if not capabilities["speech_to_text"]:
                        raise ValueError("Speech-to-text is not available")
                    await cancel_audio()
                    audio_input.clear()
                    input_media_type = str(payload.get("media_type", "audio/webm"))
                    await send("interview.state", {"status": "listening"})
                elif event_type == "user.audio.chunk":
                    try:
                        chunk = base64.b64decode(str(payload.get("audio", "")), validate=True)
                    except (binascii.Error, ValueError) as error:
                        raise ValueError("Audio chunk is not valid base64") from error
                    if not chunk or len(chunk) > MAX_AUDIO_CHUNK_BYTES:
                        raise ValueError("Audio chunk must be between 1 byte and 256 KiB")
                    if len(audio_input) + len(chunk) > MAX_AUDIO_SEGMENT_BYTES:
                        raise ValueError("Audio segment exceeds 10 MiB")
                    audio_input.extend(chunk)
                    await send(
                        "transcript.partial",
                        {"text": "", "received_bytes": len(audio_input)},
                    )
                elif event_type == "user.audio.end":
                    if not audio_input:
                        raise ValueError("No audio was received")
                    await send("interview.state", {"status": "transcribing"})
                    extension = "webm" if "webm" in input_media_type else "audio"
                    text = await session.transcribe(bytes(audio_input), f"answer.{extension}")
                    audio_input.clear()
                    if not text:
                        raise ValueError("No speech was detected")
                    await send("transcript.final", {"text": text})
                    await start_turn(session.respond(text))
                elif event_type == "audio.output.cancel":
                    await cancel_audio()
                elif event_type == "mode.update":
                    capabilities = await session.media_capabilities()
                    if "text_to_speech" in payload:
                        requested = bool(payload["text_to_speech"])
                        await session.set_media_preference("text_to_speech", requested)
                        modes["text_to_speech"] = requested and capabilities["text_to_speech"]
                        if requested and not capabilities["text_to_speech"]:
                            await send(
                                "warning",
                                {
                                    "code": "text_to_speech_unavailable",
                                    "message": (
                                        "Spoken replies are unavailable. Enable them in "
                                        "Settings and verify the OpenAI API key."
                                    ),
                                },
                            )
                    if not modes["text_to_speech"]:
                        await cancel_audio()
                    await send(
                        "mode.updated",
                        {"modes": modes, "capabilities": capabilities},
                    )
                elif event_type == "session.pause":
                    await cancel_audio()
                    await session.pause()
                    await send("interview.state", {"status": "paused"})
                elif event_type == "session.resume":
                    await session.resume()
                    capabilities = await session.media_capabilities()
                    await send(
                        "mode.updated",
                        {"modes": modes, "capabilities": capabilities},
                    )
                    await send("interview.state", {"status": "ready_for_answer"})
                elif event_type == "session.end":
                    await cancel_audio()
                    await start_turn(session.end())
                elif event_type == "ping":
                    await send("pong", {})
                else:
                    await send(
                        "error",
                        {
                            "code": "unsupported_event",
                            "message": f"Unsupported client event: {event_type}",
                            "field_errors": {},
                        },
                    )
            except ApplicationError as error:
                await send(
                    "error",
                    {
                        "code": error.code,
                        "message": error.message,
                        "field_errors": error.field_errors,
                    },
                )
            except (TypeError, ValueError) as error:
                await send(
                    "error",
                    {
                        "code": "invalid_event",
                        "message": str(error),
                        "field_errors": {},
                    },
                )
    except WebSocketDisconnect:
        if turn_task:
            turn_task.cancel()
        for task in tts_tasks:
            task.cancel()
