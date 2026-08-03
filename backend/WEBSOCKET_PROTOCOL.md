# Interview WebSocket Protocol

Interview Studio uses protocol version `1.2` at:

```text
/api/v1/interviews/{attempt_id}/ws
```

Clients send JSON objects containing `type` and `payload`. Every server event has
this envelope:

```json
{
  "protocol_version": "1.2",
  "event_id": "uuid",
  "attempt_id": "uuid",
  "timestamp": "ISO-8601 timestamp",
  "type": "event.name",
  "payload": {}
}
```

Audio and unfinished speech segments are transient. Completed candidate and
interviewer messages are persisted as the canonical transcript. Whiteboard PNG
bytes use HTTP endpoints; the WebSocket carries only persisted snapshot IDs.

## 1. Connection and session lifecycle

The client loads history before connecting. A new attempt generates its greeting
with `session.start`; an incomplete attempt uses `session.resume` without creating
a duplicate question. Completed attempts remain read-only.

```mermaid
sequenceDiagram
    autonumber
    actor User as Candidate
    participant UI as Browser client
    participant API as FastAPI server
    participant DB as SQLite persistence
    participant AI as Interview engine

    User->>UI: Open interview attempt
    UI->>API: HTTP GET attempt history
    API->>DB: Load status, context, transcript
    DB-->>API: Canonical history
    API-->>UI: History response
    UI->>API: Connect WebSocket
    API->>DB: Resolve session, modes, capabilities

    alt Empty transcript
        UI->>API: session.start
        API-->>UI: session.ready
        API-->>UI: interview.state (connecting)
        API->>AI: stream_start
        loop Greeting tokens
            AI-->>API: Token
            API-->>UI: assistant.text.delta
        end
        AI->>DB: Persist greeting and checkpoint
        API-->>UI: assistant.text.completed
        API-->>UI: interview.state (ready_for_answer)
    else Existing incomplete transcript
        UI->>API: session.resume
        API->>DB: Mark attempt in progress
        API-->>UI: mode.updated
        API-->>UI: interview.state (ready_for_answer)
    else Completed transcript
        UI->>API: ping
        API-->>UI: pong
        Note over UI,API: The client renders history in read-only mode
    end
```

## 2. Candidate input and diagram context

Typed input is one complete candidate turn. Voice input contains one or more
bounded recording segments; STT results accumulate transiently until
`user.turn.end` creates one canonical candidate message. Local VAD closes a
segment after silence and starts the handoff countdown. Resumed speech retains
the candidate's turn.

For a changed system-design canvas, the client first saves the scene and PNG via
HTTP. It then sends `canvas.snapshot` before the text or voice handoff. Vision is
optional; failure produces a warning and the interview continues from transcript
context.

```mermaid
sequenceDiagram
    autonumber
    actor User as Candidate
    participant UI as Browser client
    participant API as FastAPI server
    participant DB as SQLite persistence
    participant STT as Speech-to-text engine
    participant Vision as Diagram vision engine
    participant AI as Interview engine

    alt Typed answer
        User->>UI: Enter answer
        opt Canvas changed
            UI->>API: HTTP PUT versioned scene
            API->>DB: Optimistic scene save
            DB-->>API: New scene version
            API-->>UI: Saved scene
            UI->>API: HTTP POST PNG snapshot
            API->>DB: Persist snapshot
            DB-->>API: snapshot_id
            API-->>UI: Snapshot metadata
            UI->>API: canvas.snapshot (snapshot_id)
            API->>DB: Load persisted PNG
            opt Vision configured
                API->>Vision: Observe diagram
                Vision-->>API: Bounded observation
            end
            API-->>UI: canvas.ready
        end
        UI->>API: user.text (text)
        API-->>UI: assistant.audio.cancelled
    else Continuous voice answer
        User->>UI: Enable microphone and speak
        loop Until candidate handoff
            UI->>API: user.audio.start (media_type)
            API-->>UI: interview.state (listening)
            loop Bounded input chunks
                UI->>API: user.audio.chunk (base64 audio)
                API-->>UI: transcript.partial (received_bytes)
            end
            UI->>API: user.audio.end
            API-->>UI: interview.state (transcribing)
            API->>STT: Transcribe segment
            STT-->>API: Segment text
            API-->>UI: transcript.segment.final (text, sequence)
            API-->>UI: interview.state (ready_for_answer)
            Note over User,UI: Silence starts countdown and resumed speech keeps the turn
        end
        opt Canvas changed
            UI->>API: HTTP save scene and PNG snapshot
            API->>DB: Persist scene and snapshot
            DB-->>API: snapshot_id
            API-->>UI: Snapshot metadata
            UI->>API: canvas.snapshot (snapshot_id)
            opt Vision configured
                API->>Vision: Observe diagram
                Vision-->>API: Bounded observation
            end
            API-->>UI: canvas.ready or warning
        end
        UI->>API: user.turn.end
        API-->>UI: transcript.final (combined segments)
        API-->>UI: interview.state (responding)
    end

    API->>AI: respond(answer, optional diagram observation)
```

Input limits enforced by the server:

- Each `user.audio.chunk`: 1 byte to 256 KiB after base64 decoding.
- Each recording segment: at most 10 MiB.
- Browser segment rotation: approximately 45 seconds or 3 seconds of silence.
- Candidate handoff: 5-second countdown after a silence-ended segment.

## 3. Assistant streaming and spoken replies

The interview engine streams text tokens. The server buffers complete sentences
for TTS while text is still arriving, serializes speech jobs, and emits identified
MP3 chunks in playback order. The final interaction state is sent after queued
speech finishes. Snapshot association occurs after the graph has persisted the
canonical candidate message.

```mermaid
sequenceDiagram
    autonumber
    participant UI as Browser client
    participant API as FastAPI server
    participant DB as SQLite persistence
    participant AI as Interview engine
    participant TTS as Text-to-speech engine

    API->>AI: Continue interview turn
    loop Each assistant token
        AI-->>API: Token
        API-->>UI: assistant.text.delta
        opt Complete sentence and TTS enabled
            API->>TTS: Queue sentence after prior speech job
            TTS-->>API: MP3 bytes
            loop Bounded 48 KiB output chunks
                API-->>UI: assistant.audio.chunk (audio_id, sequence)
            end
            API-->>UI: assistant.audio.completed (audio_id)
        end
    end
    AI->>DB: Persist candidate message, reply, and checkpoint
    API-->>UI: assistant.text.completed
    API->>DB: Read attempt status
    API-->>UI: interview.state (ready_for_answer or completed)

    opt Snapshot accompanied the answer
        API->>DB: Associate snapshot with canonical candidate message
        API-->>UI: canvas.observed
    end
```

TTS generation failure emits `warning` and does not interrupt the text flow.
The browser groups chunks by `audio_id`; `sequence` preserves global output order.

## 4. Controls, cancellation, and termination

Pause and microphone disable cancel unfinished candidate speech. Pause additionally
clears queued assistant audio and persists the paused attempt status. Voice input
must be explicitly enabled again after resume.

```mermaid
sequenceDiagram
    autonumber
    actor User as Candidate
    participant UI as Browser client
    participant API as FastAPI server
    participant DB as SQLite persistence
    participant AI as Interview engine

    alt Cancel unfinished voice or disable microphone
        User->>UI: Cancel voice input
        UI->>API: user.turn.cancel
        API->>API: Clear audio, segments, pending diagram
        API-->>UI: interview.state (ready_for_answer)
    else Pause attempt
        User->>UI: Pause
        UI->>API: user.turn.cancel when voice is active
        UI->>API: session.pause
        API-->>UI: assistant.audio.cancelled
        API->>DB: Mark attempt paused
        API-->>UI: interview.state (paused)
    else Resume attempt
        User->>UI: Resume
        UI->>API: session.resume
        API->>DB: Mark attempt in progress
        API-->>UI: mode.updated
        API-->>UI: interview.state (ready_for_answer)
    else Toggle spoken replies
        UI->>API: mode.update (text_to_speech)
        API->>DB: Persist TTS preference
        API-->>UI: warning when requested mode is unavailable
        API-->>UI: mode.updated
    else Cancel assistant playback
        UI->>API: audio.output.cancel
        API->>API: Cancel queued TTS tasks
        API-->>UI: assistant.audio.cancelled
    else End interview
        User->>UI: End session
        UI->>API: session.end
        API-->>UI: assistant.audio.cancelled
        API->>AI: stream_end
        AI->>DB: Persist closing and completed state
        API-->>UI: Assistant text and optional audio events
        API-->>UI: interview.state (completed)
    end
```

Invalid client events return `error` with code `invalid_event` or
`unsupported_event`. Application failures retain their structured error code,
message, and field errors. Recoverable media, vision, or association failures use
`warning` so the text interview can continue.

## Event reference

Client events:

- `session.start`, `session.pause`, `session.resume`, `session.end`
- `user.text`
- `user.audio.start`, `user.audio.chunk`, `user.audio.end`
- `user.turn.end`, `user.turn.cancel`
- `canvas.snapshot`
- `mode.update`, `audio.output.cancel`
- `ping`

Server events:

- `session.ready`, `mode.updated`, `interview.state`
- `assistant.text.delta`, `assistant.text.completed`
- `assistant.audio.chunk`, `assistant.audio.completed`, `assistant.audio.cancelled`
- `transcript.partial`, `transcript.segment.final`, `transcript.final`
- `canvas.ready`, `canvas.observed`
- `warning`, `error`, `pong`
