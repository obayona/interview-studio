# Interview Studio Frontend

Astro 7 and React 19 frontend for Interview Studio. Astro renders the persistent
application shell and route pages, while React islands provide interactive
features such as settings.

## Requirements

- Node.js 24 or a compatible current Node.js release
- pnpm 11
- The Interview Studio FastAPI backend for API-backed features

Install dependencies from the repository root:

```bash
pnpm --dir frontend install
```

## Development

Start the backend from the repository root:

```bash
.venv/bin/python -m uvicorn backend.app.main:app --reload
```

In another terminal, start the frontend:

```bash
pnpm --dir frontend run dev
```

Open `http://127.0.0.1:4321`. During development, Astro proxies `/api` and
`/health` requests to `http://127.0.0.1:8000`.

The application can render without the backend, but API-backed pages display
their unavailable or error states.

## Commands

Run these commands from the repository root:

```bash
pnpm --dir frontend run dev
pnpm --dir frontend run check
pnpm --dir frontend run lint
pnpm --dir frontend run format:check
pnpm --dir frontend run test
pnpm --dir frontend run build
pnpm --dir frontend run preview
pnpm --dir frontend audit --prod
```

`build` runs Astro diagnostics before generating the static site in
`frontend/dist/`.

## Configuration

The client uses same-origin HTTP and WebSocket URLs by default. Separate-origin
deployments can set these public build-time variables:

```dotenv
PUBLIC_API_BASE_URL=https://api.example.com
PUBLIC_WS_BASE_URL=wss://api.example.com
```

Omit trailing slashes because the client appends route paths beginning with
`/api`.

The supported Docker deployment omits both variables. Its multi-stage Nginx
image compiles Astro to static assets and forwards same-origin `/api` and
WebSocket requests to FastAPI. Node and Astro are not present at runtime.

Server deployments expose `/login` before the authenticated application. The
shared API client bootstraps its CSRF token from the session endpoint, attaches
it to mutations, and returns expired sessions to login while retaining the
requested local route. Local development remains unauthenticated.

## Structure

```text
src/
  components/
    layout/       Astro shell components
    ui/           Reusable accessible React components
  features/
    dashboard/    Home aggregates, activity, report trends, and onboarding
    feedback/     Attempt evaluation and deterministic process feedback
    interview/    Streaming text/audio simulator and browser media controls
    profile/      Profile editor, autosave, avatar, and CV import
    processes/    Process list, configurable creation/editing, and attempt history
    settings/     Settings page React island
  layouts/        Persistent application layout
  pages/          Astro file-based routes
  services/       Typed HTTP, settings, and WebSocket clients
  styles/         Design tokens and shared component styles
  types/          API transport types
```

Settings and profile forms update optimistically and persist after 700 ms of
inactivity or when a field loses focus. Their explicit Save buttons flush pending
changes, become disabled while saving, and provide visible status/toast feedback.
CV import keeps its modal spinner visible until AI extraction and the resulting
profile save both finish.

The current routes are:

- `/`
- `/profile`
- `/processes`
- `/processes/new`
- `/processes/edit`
- `/processes/details`
- `/interview`
- `/feedback`
- `/settings`

The home dashboard loads persisted process, attempt, and report aggregates from
`GET /api/v1/dashboard`. It provides responsive loading, empty, error/retry, and
populated states plus first-run links for AI settings, profile completion,
process creation, and the first interview. The unsupported prototype sections
for upcoming sessions and interview readiness are intentionally omitted.

Design tokens support light, dark, and system themes. Shared styles include
visible keyboard focus and reduced-motion behavior.

The interview route requires `attempt` and `process` query parameters. It hydrates
canonical history before connecting, supports typed answers in every mode, and
uses explicit browser microphone permission and local VAD when STT is available.
Voice answers rotate bounded transcript segments without yielding the floor, then
show a five-second interviewer-handoff countdown after silence. Resumed speech
cancels the countdown, and **Finish answer now** appears only during that window.
Candidate capture remains suspended while the interviewer responds. Browsers
without Web Audio analysis fall back to press-and-release segment capture.
System-design attempts dynamically load Excalidraw in place of the interviewer
portrait. The editor provides basic architecture shapes, connectors, text,
freehand drawing, selection, undo/redo, zoom, pan, and clear. Scene JSON autosaves
after 700 ms, changed scenes are considered for a periodic PNG snapshot every 30
seconds, and toolbar actions create an explicit snapshot or download a PNG.
Mobile sessions render the persisted board in view-only mode.
Changed boards are checkpointed before typed or voice answers yield the candidate's
turn. The server may use the configured vision model to inform the next question and
links the checkpoint to the persisted answer; the interview remains text-only when
vision is unavailable. The whiteboard and transcript remain a split workspace, and
each can be hidden independently from the meeting controls.
New process stages inherit global voice preferences, and live attempt changes are
persisted across reloads. Microphone denial or blocked autoplay displays feedback
without changing the saved preference.
Process details list every attempt with its timestamp and status. Ready or paused
attempts can be started/resumed, completed attempts open read-only, and deletion
uses an explicit confirmation before removing the attempt history.
When an interview finishes, the simulator redirects to
`/feedback?attempt=…&process=…&evaluate=1`, where a blocking progress state remains
visible during request-bound evaluation. Reload or cancellation never stores a
partial report, and the page provides retry. Process details expose Evaluate or
View feedback per completed attempt, sequential pending evaluation, and
best-attempt-per-stage process feedback.
