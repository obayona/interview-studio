# Interview Studio — Complete Implementation Plan

## 1. Architecture and Delivery Strategy

Build Interview Studio incrementally through the 12 phases defined in `AGENT.md`. Each phase must be independently runnable, tested, documented, and accepted before the next phase begins.

### Target structure

```text
backend/
  app/
    api/                  # FastAPI HTTP and WebSocket controllers
    application/          # Use cases and orchestration services
    domain/               # Entities, value objects, policies
    infrastructure/       # SQLite, OpenAI, web fetching, encryption
    repositories/         # Repository contracts and SQLite implementations
    core/                 # Config, logging, errors, lifecycle
    main.py
  interview_engine/       # Standalone LangGraph interview package
  profile_parser/         # CV extraction and normalization
  report_engine/          # Interview evaluation package
  migrations/             # Ordered Yoyo migrations
  cli/
  tests/
frontend/
  src/
    components/
    features/
    layouts/
    pages/
    services/
    styles/
    types/
  public/
desktop/
deployment/
  docker/
  nginx/
  scripts/
prototypes/
AGENT.md
PLAN.md
TASK.md
MAP.md
PROMPTS.md
```

### Architectural rules

- Use clean boundaries without excessive abstraction:
  - Domain entities contain business rules.
  - Application services coordinate repositories and integrations.
  - Infrastructure implements SQLite, OpenAI, encryption, web fetching, PDF parsing, and filesystem concerns.
  - FastAPI controllers only validate transport data and invoke application services.
- Use constructor injection and one application-owned SQLite connection manager.
- Use raw parameterized SQL and repository classes; do not add an ORM.
- Keep AI packages independent of FastAPI and UI code.
- Store all timestamps as UTC ISO-8601 strings and generate identifiers as UUIDs.
- Use SQLite foreign keys, WAL mode, busy timeout, explicit transactions, and indexed foreign keys.
- Use JSON only for variable AI configuration, report details, and canvas scenes; keep queryable fields relational.
- Maintain `MAP.md` as the verified system map and `TASK.md` as the phase checklist.
- Append every implementation prompt to `PROMPTS.md`.
- At each phase boundary, synchronize `PLAN.md`, `TASK.md`, and `MAP.md` with the actual code.

## 2. Cross-Cutting Technical Decisions

### Runtime and configuration

- Python 3.12 and a repository-local `.venv`.
- FastAPI with an application lifespan that initializes logging, the SQLite manager, migrations, configuration, and integration factories.
- Astro with React islands/client routing behavior and the View Transitions API.
- Native CSS using BEM, CSS custom properties, responsive layouts, and `1rem = 10px`.
- OpenAI is the initial provider behind provider-neutral interfaces.
- No `.env` dependency at runtime. Development-only environment values may seed settings or tests but must never override persisted user settings silently.
- Services resolve settings at operation start so updated keys and toggles take effect without restart.

### Secret management

- Encrypt API credentials before storing them in SQLite.
- Use authenticated encryption with versioned ciphertext.
- Desktop installations generate a restricted-permission local master-secret file.
- Web deployments require a mounted secret file or explicit installation-time secret.
- API responses never return decrypted keys; return `configured`, masked suffix, and last-updated metadata.
- Logs, exceptions, WebSocket payloads, and reports must never contain credentials.

### Server access

- Development and desktop modes disable authentication by default and bind to loopback.
- Server mode enables FastAPI session authentication:
  - Installation-time password setup.
  - Argon2 password hashing.
  - Secure, HTTP-only, same-site cookies.
  - CSRF protection for state-changing HTTP endpoints.
  - WebSocket origin and authenticated-session validation.
  - Login rate limiting and session invalidation.
- Nginx terminates TLS but does not own the login mechanism.

### AI execution

- Interview interaction is streaming and checkpointed through a domain-aware shallow SQLite saver.
- The saver implements LangGraph's asynchronous `BaseCheckpointSaver` API but uses application-owned tables rather than LangGraph's standard SQLite schema.
- Persist only the latest graph state for each interview thread; historical checkpoint snapshots, time travel, and checkpoint branching are intentionally unsupported.
- `interview_messages` is the canonical transcript. The checkpoint state references and reconstructs messages from those rows instead of serializing a duplicate message history.
- Checkpoint data uses strict JSON text serialization. Pickle, binary checkpoint blobs, and implicit fallback serializers are prohibited.
- Report generation is request-bound:
  - The UI shows an evaluation progress state while the request is active.
  - Closing the page or losing the request can cancel evaluation.
  - Persist only completed reports.
  - Provide an explicit retry/evaluate button.
- All AI calls receive timeouts, cancellation propagation, bounded retries for transient failures, and user-safe errors.
- Log provider request IDs and token usage where available, without storing prompts containing secrets.

### Company and candidate ingestion

- Job listings and company information accept either pasted text or a public URL.
- URL fetching must block private, loopback, link-local, metadata, and unsupported network targets to prevent SSRF.
- Limit redirects, response size, MIME types, and request duration.
- Extract readable page text and retain source URL and retrieval time.
- Parse uploaded PDF CVs.
- Store LinkedIn and portfolio URLs as profile links; do not scrape LinkedIn.
- Portfolio/company URLs may be fetched only when the user explicitly requests import/research.

### Accessibility and UI behavior

- Preserve semantic landmarks, keyboard navigation, visible focus, high contrast, reduced-motion support, and meaningful labels.
- Use Font Awesome through one reusable icon component.
- Use reusable toast and `<dialog>` components instead of `alert`, `confirm`, or `prompt`.
- Every data screen includes loading, empty, error, and success states.
- Dark mode follows system preference initially and supports an explicit persisted override.
- Prototype images define visual direction, not unsupported product behavior.

### Frontend form persistence guide

- Use `frontend/src/hooks/useAutosave.ts` for editable data pages instead of implementing page-specific debounce, snapshot, request-sequencing, or save-status logic.
- Update controlled form state optimistically so the interface responds immediately; retain the local value when persistence fails and report the failure through a toast.
- Persist changes after 700 ms of inactivity and flush the current snapshot when focus leaves a field or control.
- Switches, selects, checkboxes, text inputs, ordered collections, and other ordinary controls follow the same autosave contract.
- Keep an explicit Save action when it helps user confidence. It flushes the latest snapshot, displays a disabled `Saving…` state while active, and shows success or already-current feedback.
- Do not add Discard actions unless a workflow has an explicit draft boundary and restoring the last server snapshot is a defined product action.
- Suppress duplicate requests for an unchanged or already-saving snapshot and ignore stale responses when a newer request is authoritative.
- Normalize successful API responses through the hook before recording the saved snapshot, while preserving newer optimistic edits.
- Long-running or consequential operations such as CV import use an explicit submit action and a blocking progress state. Keep that state visible until parsing and resulting persistence both finish; errors retain the user’s recoverable input.
- Every new editable page must test debounced autosave, focus-loss flushing where relevant, explicit-save loading behavior, and error-toast handling.

## 3. Core Data Model and Migration Sequence

Create one migration per coherent schema change and supply reversible rollback logic where data loss is not inherently unavoidable.

### Core tables

- `settings`: key, encrypted value, secret flag, and timestamps.
- `developer_profiles`: identity, headline, summary, location, contact fields, skills, seniority, availability, avatar BLOB/MIME metadata, and timestamps.
- `profile_links`: profile, link type, and URL.
- `work_experiences`: employer, role, dates, current-role flag, description, and ordering.
- `projects`: name, role, description, technologies, URL, repository URL, and ordering.
- `interview_processes`: title, company/job inputs, normalized research, target role, overall status, and timestamps.
- `interview_stages`: process, type, order, enabled flag, configuration JSON, and status.
- `interview_attempts`: stage, attempt number, status, timing, effective configuration, unique LangGraph thread ID, and termination reason.
- `interview_messages`: canonical completed transcript messages with attempt, stable LangGraph message ID, sequence, role, message type, text content, timing, and optional provider metadata. Token deltas, partial STT results, graph metadata, and pending writes are not stored here.
- `interview_graph_state`: one shallow checkpoint row per attempt/thread and namespace, containing checkpoint ID, non-message state JSON, channel versions JSON, versions-seen JSON, updated-channels JSON, checkpoint metadata JSON, and timestamps.
- `interview_graph_writes`: temporary pending graph writes containing attempt, checkpoint, task ID/path, write index, channel, JSON value, and timestamp. Obsolete writes are removed after a newer checkpoint becomes authoritative.
- `audio_artifacts`: message/attempt relation, direction, format, duration, and BLOB or managed-path metadata.
- `interview_reports`: attempt, scores, strengths, weaknesses, recommendations, study plan, detailed JSON, model metadata, and timestamps.
- `system_design_sessions`: attempt, current scene JSON, scene version, and timestamps.
- `system_design_snapshots`: session, scene version, PNG BLOB, creation reason, and timestamps.
- `users` and `sessions`: created for optional server authentication.

### Integrity rules

- Deleting a process cascades through stages, attempts, messages, reports, and canvas records after explicit UI confirmation.
- Deleting an attempt also removes its graph state and pending writes through foreign-key cascades.
- Stage definitions remain stable once attempts exist; edits affect future attempts.
- Attempts are immutable historical records except for state transitions and end metadata.
- Reports are versioned by attempt and evaluation version.
- Settings use a known-key registry so arbitrary client-provided names cannot affect runtime behavior.
- Saving completed messages, graph state, channel versions, and pending-write reconciliation is atomic within one SQLite transaction.
- The graph state supports only JSON-compatible primitives, ISO-8601 timestamp strings, string enums, and explicitly adapted LangChain messages. Audio, images, and other binary values remain in domain tables and are referenced by ID.

## 4. Public Interfaces

### HTTP API conventions

- Prefix application endpoints with `/api/v1`.
- Use stable error objects containing `code`, `message`, `field_errors`, and `request_id`.
- Use multipart requests only for file uploads.
- Return `409` for invalid state transitions, `422` for validation errors, and `503` when provider configuration is absent.
- Add `/health/live`, `/health/ready`, and a capabilities endpoint.

### Planned endpoint groups

- `/api/v1/settings`: safe settings status, updates, credential removal, provider tests, and capabilities.
- `/api/v1/profile`: profile, avatar, work experience, projects, and CV import.
- `/api/v1/processes`: process CRUD, research/import, and ordered stages.
- `/api/v1/processes/{id}/stages`: stage order/configuration and attempt creation.
- `/api/v1/attempts/{id}`: details, transcript, history, and status transitions.
- `/api/v1/attempts/{id}/evaluate`: request-bound report generation.
- `/api/v1/reports/{id}`: report retrieval.
- `/api/v1/dashboard`: process, attempt, and score aggregates.
- `/api/v1/system-design/{attempt_id}`: versioned scenes and snapshots.
- `/api/v1/auth`: server-mode setup, login, logout, and session status.

### Interview WebSocket

Endpoint: `/api/v1/interviews/{attempt_id}/ws`

Client events:

- `session.start`
- `user.text`
- `user.audio.start`
- `user.audio.chunk`
- `user.audio.end`
- `audio.output.cancel`
- `mode.update`
- `canvas.snapshot`
- `session.pause`
- `session.resume`
- `session.end`
- `ping`

Server events:

- `session.ready`
- `assistant.text.delta`
- `assistant.text.completed`
- `assistant.audio.chunk`
- `transcript.partial`
- `transcript.final`
- `interview.state`
- `mode.updated`
- `report.available`
- `warning`
- `error`
- `pong`

Every event includes a protocol version, event ID, attempt ID, timestamp, and typed payload. Text transcripts remain authoritative when audio is enabled.

## 5. Phase-by-Phase Implementation

### Phase 0 — Foundation and Project Governance

- Create `PLAN.md`, `TASK.md`, and `MAP.md`.
- Record the phase checklist, completion criteria, architecture map, entities, routes, migrations, and decisions.
- Initialize Python and frontend tooling.
- Configure Ruff, mypy, pytest, coverage, TypeScript strict mode, ESLint, Prettier, and Stylelint.
- Establish logging, errors, request IDs, dependency boundaries, and naming conventions.
- Document development commands and the acceptance workflow.

Acceptance:

- Empty backend and frontend projects install and run.
- Formatter, linter, type-check, and test commands succeed.
- No runtime secret is committed.

### Phase 1 — Interview Engine ✅ Completed 2026-07-28

- Build `backend.interview_engine` as a normal backend package importable from the repository root without installation or `sys.path` changes.
- Define typed inputs for the candidate, job, company, interview type, interviewer, difficulty, instructions, limits, language, and media capabilities.
- Define LangGraph state for conversation, topic coverage, goals, question count, time, limits, follow-up context, completion, and termination reason.
- Generate the greeting, select topics, ask adaptive follow-ups, provide transitions, decide whether to continue, and close professionally.
- Keep the external interview loop outside the package.
- Stream with `stream_mode="messages"`.
- Default to `MemorySaver` for standalone package and CLI usage and accept compatible `BaseCheckpointSaver` implementations through the builder.
- Provide a fluent builder for provider, model, checkpointer, inputs, limits, and media adapters.
- Define provider-neutral STT/TTS ports without implementing audio.
- Build versioned, bias-aware prompt templates based on interview best practices.
- Add the `interview-engine` logger without configuring handlers.
- Implement `backend/cli/engine-usage.py`.
- Unit test only pure lifecycle, validation, topic-selection, and prompt-building functions.
- Use `backend/cli/engine-usage.py` as the Phase 1 manual end-to-end exercise for greeting, streaming, follow-ups, stopping, and checkpoint resume behavior.

Acceptance:

- The CLI completes a coherent text interview.
- Stop modes terminate deterministically.
- Checkpointed conversation can resume.
- The package has no FastAPI dependency.

### Phase 2 — FastAPI Wrapper and Persistence ✅ Completed 2026-07-28

- Create FastAPI application layers and lifespan initialization.
- Implement the shared SQLite connection manager and transaction boundary.
- Enable WAL, foreign keys, busy timeout, and clean shutdown.
- Integrate Yoyo migrations.
- Create the application-owned `interview_messages`, `interview_graph_state`, and `interview_graph_writes` tables through Yoyo migrations; do not create LangGraph's standard checkpoint or blob tables.
- Implement `InterviewSQLiteCheckpointer` as an asynchronous, shallow `BaseCheckpointSaver`:
  - `put` validates JSON compatibility, extracts completed messages, and atomically upserts the canonical transcript and latest non-message graph state.
  - `put_writes` stores JSON-only pending writes for the current checkpoint.
  - `get_tuple` loads the latest state and ordered transcript, reconstructs explicitly supported LangChain messages, attaches pending writes, and returns the `CheckpointTuple` expected by LangGraph.
  - `list` yields at most the current checkpoint because historical snapshots are unsupported.
  - `delete_thread` removes the associated state and pending writes; transcript deletion remains an application repository responsibility.
  - Implement the corresponding async methods used by `astream`; synchronous methods may be supplied only where required for API conformance.
- Use a strict, versioned JSON codec with explicit adapters. Reject unsupported values with a descriptive error; never fall back to Pickle, BLOB serialization, or base64-encoded binary state.
- Configure FastAPI-built interview engines with `InterviewSQLiteCheckpointer`; retain `MemorySaver` as the standalone engine default.
- Add the settings repository and typed configuration store.
- Ensure the backend boots without API credentials.
- Build the interview application service, attempt validation, and WebSocket adapter.
- Treat `interview_messages` as the product source of truth for UI, reports, analytics, and exports; no application feature may query graph-state JSON as transcript storage.
- Assign stable message IDs and make checkpoint writes idempotent so retries cannot duplicate transcript rows.
- Serve a small inline root-page WebSocket test UI.
- Add readiness/capability reporting and structured error handling.

Acceptance:

- Fresh startup creates and migrates the database.
- Missing keys disable interviews without preventing startup.
- The browser harness completes and resumes an interview.
- Disconnects and simulated crashes leave a recoverable attempt using the latest checkpoint and pending writes.
- Repeated checkpoint saves retain one graph-state row per thread/namespace and never create historical snapshots or binary blobs.
- LangGraph saver conformance tests cover retrieval, writes, listing, deletion, idempotency, and asynchronous execution.
- Integration tests use temporary SQLite databases.

### Phase 3 — Settings ✅ Completed 2026-07-28

- Register the OpenAI API key, default chat/transcription/speech/vision models, TTS, STT, voice, theme, and general preferences.
- Implement safe CRUD and provider connection testing.
- Encrypt secrets and never return their plaintext values.
- Return clear capability explanations.
- Validate provider, model, and voice combinations.

Acceptance:

- Settings take effect without restart.
- Removing a key disables dependent capabilities.
- Masking, encryption, validation, and failures are tested.

### Phase 4 — Initial Astro/React Frontend ✅ Completed 2026-07-28

- Establish the fixed shell, sidebar, header, route outlet, transitions, and responsive navigation.
- Implement buttons, inputs, selects, switches, cards, badges, toasts, dialogs, spinners, skeletons, empty states, errors, icons, and form fields.
- Build design tokens from the prototypes and Ventura Tech design guide.
- Implement light/dark themes and reduced-motion behavior.
- Add a typed API client, WebSocket foundation, normalized errors, and capability state.
- Create working routes for dashboard, profile, processes, details, interview, feedback, and settings.
- Fully implement and integrate the settings page. @prototypes/ai_configuration_interviewos/screen.png

Acceptance:

- Routes load without replacing the persistent shell.
- Settings and capability warnings update correctly.
- Keyboard, focus, loading, error, and responsive states work.

### Phase 5 — Candidate Profile and CV Import ✅ Completed 2026-07-29

- Add migrations, repositories, and APIs for the profile, links, experience, projects, and avatar.
- Validate avatar MIME type, dimensions, and size before BLOB storage.
- Implement debounced autosave, blur save, explicit Save, stale-response protection, and visible status.
- Support ordered work experiences and projects.
- Accept size-limited PDF CVs.
- Extract text with a conventional PDF parser first.
- Interpret the extracted CV text entirely with structured AI through a checkpointer-free LangGraph workflow.
- Treat CV uploads as transient import input and never persist the file or extracted text.
- Store LinkedIn and portfolio URLs without LinkedIn scraping.

Acceptance:

- Profiles save and reload correctly.
- Invalid files are rejected.
- CV import returns validated structured fields without changing the stored profile.
- The frontend places imported values in the editable form for review and normal profile saving.

### Phase 6 — Interview Processes

- Add process, stage, and attempt migrations and repositories.
- Implement list, creation, detail, update, and confirmed deletion.
- Accept pasted or fetched job and company information.
- Provide ordered optional defaults: screening, behavioral, technical/experience, and system design.
- Configure difficulty, persona, limits, instructions, language, TTS, STT, and other engine options per stage.
- Keep skipped stages visible and re-enableable.
- Allow starting any enabled stage independently.
- Store repeated stages as new numbered attempts.
- Build the process list, creation, and detail pages.
- Use placeholders for feedback until Phase 8.
- Protect URL imports against SSRF and preview extracted content.

Acceptance:

- Stage configuration persists.
- Stages can start independently and repeat.
- Attempts never overwrite history.
- Text and URL inputs yield equivalent normalized data.

### Phase 7 — TTS, STT, and Interview Simulator

- Implement OpenAI transcription and speech adapters behind provider-neutral ports.
- Extend the WebSocket protocol for audio, transcript, mode, cancellation, and state events.
- Support all four TTS/STT combinations.
- Resolve modes from live override, attempt config, global default, and capabilities.
- Permit live mode changes.
- Buffer assistant text by sentence and latency before TTS calls.
- Sequence and cancel audio playback.
- Implement browser audio capture with explicit permission.
- Use push-to-talk as the reliable baseline and browser VAD as progressive enhancement.
- Stop playback and cancel queued audio when the user interrupts.
- Persist final transcripts; keep partial transcripts transient.
- Implement reconnect/resume.
- Build the interview simulator UI.
- Negotiate audio formats and enforce chunk limits.

Acceptance:

- All four modes complete interviews.
- Live mode changes work.
- Push-to-talk works without VAD.
- Interruptions cancel stale audio.
- Reconnect restores transcript and state.

### Phase 8 — Evaluation and Feedback

- Build `backend/report_engine` with typed input/output and no checkpointer.
- Evaluate completed or explicitly ended attempts.
- Generate overall and category scores, strengths, weaknesses, per-answer observations, advice, study plan, and transcript evidence references.
- Use bounded scores and a versioned JSON schema.
- Persist and retrieve completed reports.
- Keep evaluation request-bound with visible progress, safe cancellation, and manual retry.
- Prevent simultaneous duplicate evaluations.
- Build the feedback page with loading, failure, empty, and completed states.

Acceptance:

- Reports validate against the schema and cite transcript evidence.
- Cancellation stores no partial report.
- Retry works.
- Reports render accessibly.

### Phase 9 — Dashboard

- Implement process, attempt, score, trend, recent-activity, strength, and weakness aggregates.
- Build the simplified dashboard prototype.
- Exclude upcoming sessions and interview-readiness features.
- Add first-run guidance for profile, settings, process creation, and interviews.

Acceptance:

- Aggregates match stored records.
- Empty users receive useful onboarding.
- Dashboard actions navigate correctly.

### Phase 10 — System Design Interview

- Add an interactive React whiteboard with serializable scenes and image export.
- Persist editable scene JSON and periodic/explicit PNG snapshots.
- Autosave with debouncing and optimistic version checks.
- Send snapshots to a vision-capable model only on explicit submission, configured checkpoints, or interview end.
- Relate every snapshot to its transcript event and scene version.
- Preserve the standard interview graph while adding diagram observations.
- Support nodes, text, connectors, drawing, selection, undo/redo, zoom, pan, confirmed clear, and export.
- Fall back to text-only interviews when vision is unavailable.
- Build the split-pane simulator.

Acceptance:

- Diagrams survive reload and remain editable.
- AI responses are traceable to snapshots.
- Stale saves cannot overwrite newer scenes.
- Other interview types remain unchanged.

### Phase 11 — Desktop Packaging

- Prebuild the frontend and serve it through the packaged backend.
- Use pywebview for the desktop shell.
- On launch, select application data, load/create the secret, migrate SQLite, start FastAPI on loopback, await readiness, and open the window.
- On close, stop requests, WebSockets, FastAPI, and SQLite cleanly.
- Package Python, dependencies, backend, and frontend assets together.
- Produce a Windows x64 installer and Debian x64 `.deb`.
- Add icons, menu entries, install-path selection, and uninstall integration.
- Preserve user data on ordinary uninstall; make data deletion an explicit confirmed option.
- Add loopback-only binding, single-instance protection, and a startup-error window.

Acceptance:

- Clean Windows and Debian systems install, launch, migrate, run, close, and uninstall.
- No external Python installation is required.
- User data is not silently removed.

### Phase 12 — Web Deployment

- Build production application artifacts.
- Add Docker Compose services for FastAPI, Nginx, and Certbot.
- Persist SQLite, artifacts, certificates, and encryption secrets in explicit volumes.
- Bootstrap over HTTP and transition to HTTPS with renewal.
- Validate domain, email, ports, permissions, and secrets in installation scripts.
- Enable FastAPI session authentication in server mode.
- Configure the initial password through a one-time CLI or installer action.
- Configure Nginx for TLS, WebSockets, security headers, limits, timeouts, and redirects.
- Document SQLite backup, restore, upgrades, and migrations.
- Run containers as non-root where practical.
- Add health checks and log-rotation guidance.

Acceptance:

- Fresh installation transitions successfully to HTTPS.
- Anonymous HTTP and WebSocket access is rejected in server mode.
- Authentication, CSRF, certificate renewal, backup, restore, and upgrades are tested.

## 6. Testing Strategy

### Unit tests

- LangGraph transitions, prompts, stopping policies, and builder validation.
- Custom checkpointer JSON codec, message adaptation, state reconstruction, idempotency, shallow overwrite behavior, and rejection of unsupported or binary values.
- Configuration resolution and secret encryption.
- Domain rules and state transitions.
- URL validation and SSRF blocking.
- CV normalization and merging.
- WebSocket event serialization.
- Audio buffering and mode resolution.
- Report schema and score handling.
- Dashboard mapping.
- Canvas version conflict handling.

### Backend integration tests

Use a temporary SQLite database with real migrations:

- Settings updates and immediate refresh.
- Process-to-report lifecycle.
- Opt-in real-provider four-round interview.
- WebSocket streaming, disconnect, and resume.
- Checkpointer crash recovery at graph-step boundaries and atomic consistency between transcript, state, and pending writes.
- All TTS/STT modes when credentials are supplied.
- CV import.
- URL extraction against controlled test servers.
- Scene and snapshot association.
- Server-mode authentication and CSRF.

### Frontend tests

- Component tests for forms, dialogs, toasts, switches, autosave, and errors.
- Feature tests for settings, profiles, processes, interviews, reports, and canvas persistence.
- Mock only the transport boundary.

### End-to-end tests

Limit Playwright to three flows:

1. First-run configuration, profile, and process creation.
2. Text interview, evaluation, and feedback.
3. Repeated attempt and history verification.

Run automated accessibility checks as advisory initially and make critical violations release-blocking before packaging.

## 7. Per-Phase Completion Protocol

For every phase:

1. Confirm code against `MAP.md` and correct documentation discrepancies.
2. Add phase tasks to `TASK.md`.
3. Implement only the phase and direct prerequisites.
4. Verify migrations on fresh and existing databases.
5. Run formatting checks, linters, type checks, unit tests, and relevant integration tests.
6. Perform the phase-specific manual acceptance flow.
7. Update `MAP.md` with actual modules, routes, entities, migrations, decisions, and impact.
8. Mark verified tasks complete in `TASK.md`.
9. Mark the phase complete in `PLAN.md` only after acceptance passes.
10. Append the implementation prompt to `PROMPTS.md`.
11. Stop for review before beginning the next phase.

## 8. Assumptions and Defaults

- The repository is greenfield; prototypes and specifications are the initial inputs.
- The application remains single-user, including server deployments.
- OpenAI is the initial AI provider behind provider-neutral ports.
- Model names are settings rather than hardcoded business rules.
- Job and company research supports pasted text and explicit public-URL extraction.
- LinkedIn is stored as a link and is not scraped.
- API credentials are encrypted with a local installation secret.
- LangGraph persistence uses the custom shallow `InterviewSQLiteCheckpointer`: one JSON-text state row per thread/namespace, canonical messages stored once in `interview_messages`, and temporary JSON pending writes. Historical checkpoints and binary serialization are out of scope.
- Reports are request-bound and retryable; no external job queue is introduced.
- Desktop builds are self-contained.
- Development and desktop modes default to unauthenticated loopback access.
- Server mode defaults to mandatory FastAPI session authentication.
- System-design sessions persist editable scene JSON and PNG snapshots.
- Push-to-talk is guaranteed; VAD is an optional enhancement.
- SQLite supports one user and one application instance; horizontal scaling is outside scope.
