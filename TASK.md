# Interview Studio Task Ledger

## Phase 1 — Interview Engine

- [x] Query `MAP.md` before starting and reconcile it with the repository.
- [x] Record the initial system map and Phase 1 boundaries.
- [x] Create the importable `backend.interview_engine` module and development tooling without packaging it as an installable distribution.
- [x] Define typed interview inputs, state, enums, and validation.
- [x] Define provider-neutral STT and TTS ports.
- [x] Implement versioned, job-relevant, bias-aware prompts.
- [x] Implement the LangGraph lifecycle and adaptive interview flow.
- [x] Implement the fluent builder with `MemorySaver` defaults and injectable dependencies.
- [x] Add `interview-engine` library logging.
- [x] Add the asynchronous CLI streaming exercise.
- [x] Add unit tests only for pure lifecycle, validation, topic, and prompt functions.
- [x] Use `backend/cli/interview-engine-usage.py` as the Phase 1 manual engine exercise; do not add backend integration tests before Phase 2.
- [x] Run formatting, linting, typing, and test verification.
- [x] Synchronize `MAP.md` with the implemented system.
- [x] Mark Phase 1 complete in `PLAN.md`, `TASK.md`, and `MAP.md`.

Phase 1 completed and verified on 2026-07-28.

## Phase 1 follow-up

- [x] Add a CLI graph-image generator and reference its generated PNG from the backend README.

## Phase 2 — FastAPI Wrapper and Persistence

- [x] Query `MAP.md` before starting and reconcile it with the repository.
- [x] Create FastAPI application layers and lifespan initialization.
- [x] Implement the shared SQLite connection manager and transaction boundary.
- [x] Enable WAL, foreign keys, busy timeout, and clean shutdown.
- [x] Integrate Yoyo migrations.
- [x] Create application-owned settings, attempt, transcript, graph-state, and graph-write tables.
- [x] Implement the strict versioned JSON codec and LangChain message adapters.
- [x] Implement the asynchronous shallow `InterviewSQLiteCheckpointer`.
- [x] Configure web interview engines with the application checkpointer.
- [x] Add the settings repository and typed configuration store.
- [x] Ensure startup succeeds without API credentials.
- [x] Build the interview application service, attempt validation, and WebSocket adapter.
- [x] Serve backend API metadata at the root.
- [x] Add health, readiness, capabilities, request IDs, and structured errors.
- [x] Add unit and temporary-database integration tests.
- [x] Verify fresh/existing migrations, formatting, linting, typing, and tests.
- [x] Synchronize `MAP.md` with the implemented system.
- [x] Mark Phase 2 complete in `PLAN.md`, `TASK.md`, and `MAP.md`.

Phase 2 completed and verified on 2026-07-28.

## Phase 2 follow-up

- [x] Add canonical transcript history retrieval for reconnecting clients.
- [x] Update interview clients to hydrate history and avoid restarting resumed interviews.

## Phase 3 — Settings

- [x] Query `MAP.md` before starting and reconcile it with the repository.
- [x] Register OpenAI, model, voice, media, theme, and general settings.
- [x] Implement safe settings status, update, removal, and provider testing routes.
- [x] Encrypt secret settings and never return plaintext values.
- [x] Return capability explanations based on current settings.
- [x] Validate provider, model, voice, theme, and known-key combinations.
- [x] Add settings unit/integration coverage for immediate refresh, removal, masking, encryption, and failures.
- [x] Verify formatting, linting, typing, tests, and settings compatibility.
- [x] Synchronize `MAP.md` with the final implemented system.
- [x] Mark Phase 3 complete in `PLAN.md`, `TASK.md`, and `MAP.md`.

Phase 3 completed and verified on 2026-07-28.

## Phase 3 follow-up

- [x] Consolidate repository access behind the single `SettingsService` application facade.
- [x] Remove `settings_repository` from FastAPI application state.
- [x] Re-run formatting, linting, typing, and tests after the wiring refactor.

## Phase 3 settings registry follow-up

- [x] Add a single setting-definition registry for API names, database keys, secrets, and defaults.
- [x] Derive repository validation and API update/delete mappings from the registry.
- [x] Re-run formatting, linting, typing, and tests after the registry refactor.
- [x] Simplify registry entries to one flat enum value with no duplicate API/database names.
- [x] Replace string lookup wrappers with the `SettingKey` enum and definition dictionary.
- [x] Remove current development database settings; backward compatibility is out of scope.
- [x] Expose enum metadata properties and a key-only registry helper.

## Phase 4 — Initial Astro/React Frontend

- [x] Query `MAP.md` before starting and reconcile it with the repository.
- [x] Establish the fixed Astro shell, sidebar, header, route outlet, transitions, and responsive navigation.
- [x] Implement reusable buttons, inputs, selects, switches, cards, badges, toasts, dialogs, spinners, skeletons, empty states, errors, icons, and form fields.
- [x] Build design tokens from the prototypes and Ventura Tech design guide.
- [x] Implement light/dark themes and reduced-motion behavior.
- [x] Add the typed API client, WebSocket foundation, normalized errors, and capability state.
- [x] Create working routes for dashboard, profile, processes, process details, interview, feedback, and settings.
- [x] Fully implement and integrate the settings page.
- [x] Add frontend tests and run formatting, linting, typing, tests, build, and accessibility checks.
- [x] Synchronize `MAP.md` with the final implemented system.
- [x] Mark Phase 4 complete in `PLAN.md`, `TASK.md`, and `MAP.md`.

Phase 4 completed and verified on 2026-07-28.

## Phase 5 — Candidate Profile and CV Import

- [x] Query `MAP.md` before starting and reconcile it with the repository.
- [x] Add the profile schema migration.
- [x] Implement profile, link, experience, project, and avatar repositories.
- [x] Implement profile CRUD and ordered collection APIs.
- [x] Validate and store avatar image uploads.
- [x] Convert size-limited PDF CV uploads to text and parse them with structured AI.
- [x] Implement transient CV import without storing files, extracted text, or AI output.
- [x] Build the complete profile frontend from the prototype.
- [x] Add debounced autosave, blur save, explicit Save, stale-response protection, and visible status.
- [x] Add ordered work-experience and project editors.
- [x] Add avatar and CV upload/import interfaces.
- [x] Add backend and frontend profile/CV tests.
- [x] Run migration, formatting, linting, typing, tests, build, and accessibility verification.
- [x] Synchronize `MAP.md` with the final implemented system.
- [x] Mark Phase 5 complete in `PLAN.md`, `TASK.md`, and `MAP.md`.

Phase 5 completed and verified on 2026-07-29.

## Phase 6 — Interview Processes

- [x] Query `MAP.md` before starting and reconcile it with the repository.
- [x] Add process, stage, and attempt migrations and repositories.
- [x] Implement list, creation, detail, update, and confirmed deletion.
- [x] Accept pasted or safely fetched job and company information with content preview.
- [x] Provide ordered configurable default stages and preserve skipped stages.
- [x] Persist all interview-engine configuration supported per stage.
- [x] Start enabled stages independently and store repetitions as numbered attempts.
- [x] Build the process list, creation, and detail pages with feedback placeholders.
- [x] Add a simple native list-to-detail title transition.
- [x] Add backend and frontend process tests.
- [x] Run migration, formatting, linting, typing, tests, build, and accessibility verification.
- [x] Synchronize `MAP.md` with the final implemented system.
- [x] Mark Phase 6 complete in `PLAN.md`, `TASK.md`, and `MAP.md`.

Phase 6 completed and verified on 2026-07-29.

## Phase 7 — TTS, STT, and Interview Simulator

- [x] Query `MAP.md` before starting and reconcile it with the repository.
- [x] Implement OpenAI transcription and speech adapters behind provider-neutral ports.
- [x] Extend the WebSocket protocol for bounded audio, transcripts, modes, cancellation, pause/resume, and state.
- [x] Resolve live modes from attempt settings, global settings, provider availability, and live overrides.
- [x] Buffer assistant text before TTS and sequence cancellable audio chunks.
- [x] Implement browser push-to-talk capture, playback, interruption, and reconnect.
- [x] Build the accessible interview simulator using the supplied interviewer image.
- [x] Add backend and frontend Phase 7 tests.
- [x] Run migration, formatting, linting, typing, tests, build, and accessibility verification.
- [x] Completely synchronize `MAP.md` with the implemented system.
- [x] Mark Phase 7 complete in `PLAN.md`, `TASK.md`, and `MAP.md`.

Phase 7 completed and verified on 2026-07-30.

## Phase 8 — Evaluation and Feedback

- [x] Query `MAP.md` before starting and reconcile it with the repository.
- [x] Add the versioned report engine and validated evidence-bearing report schema.
- [x] Add report persistence, attempt evaluation, duplicate prevention, and process aggregation.
- [x] Add attempt and process report APIs with completed-attempt state enforcement.
- [x] Build automatic post-interview evaluation and the accessible feedback page.
- [x] Add process-detail evaluation, report, and pending-evaluation actions.
- [x] Add backend and frontend Phase 8 tests.
- [x] Run migration, formatting, linting, typing, tests, build, and accessibility verification.
- [x] Completely synchronize `MAP.md` with the implemented system.
- [x] Mark Phase 8 complete in `PLAN.md`, `TASK.md`, and `MAP.md`.

Phase 8 completed and verified on 2026-07-30.

## Phase 9 — Dashboard

- [x] Query `MAP.md` before starting and reconcile it with the repository.
- [x] Implement process, attempt, score, trend, recent-activity, strength, and weakness aggregates.
- [x] Add the typed dashboard application service and HTTP API.
- [x] Build the simplified dashboard from the supplied prototype.
- [x] Exclude upcoming sessions and interview-readiness features.
- [x] Add first-run guidance for settings, profile, process creation, and interviews.
- [x] Add backend and frontend Phase 9 tests.
- [x] Run migration, formatting, linting, typing, tests, build, and accessibility verification.
- [x] Completely synchronize `MAP.md` with the implemented system.
- [x] Mark Phase 9 complete in `PLAN.md`, `TASK.md`, and `MAP.md`.

Phase 9 completed and verified on 2026-07-30.

## Phase 10 — System Design Interview

### Phase 10A — Continuous voice turns

- [x] Query `MAP.md` before starting and reconcile it with the repository.
- [x] Split Phase 10 so voice capture can be tested before whiteboard work begins.
- [x] Implement explicitly enabled browser VAD with automatic speech-segment capture.
- [x] Send a voice turn after three seconds of silence and cancel the countdown when speech resumes.
- [x] Keep microphone access active between turns and suspend capture outside answer-ready states.
- [x] Preserve press-and-release capture when Web Audio analysis is unavailable.
- [x] Reuse the existing bounded WebSocket audio protocol without backend changes.
- [x] Add focused VAD and interview simulator tests.
- [x] Run frontend formatting, linting, diagnostics, tests, and production build.
- [x] Synchronize `MAP.md` with the implemented voice slice.

Phase 10A completed and verified on 2026-08-03. Later Phase 10 refinements are tracked below.

The Phase 10A.1 refinement below supersedes the initial direct handoff after three seconds of silence.

### Phase 10A.1 — Natural long-form voice turns

- [x] Separate bounded audio-segment completion from conversational-turn completion.
- [x] Accumulate ordered transient transcript segments and persist only the combined candidate turn.
- [x] Rotate approximately 45-second segments without forcing interviewer handoff.
- [x] Start a five-second handoff countdown after three seconds of silence and cancel it when speech resumes.
- [x] Show **Finish answer now** only during the handoff countdown.
- [x] Keep microphone capture suspended while the interviewer responds; do not implement barge-in.
- [x] Add visible listening, capturing, captured, countdown, and interviewer-turn feedback.
- [x] Clear unfinished voice state safely on pause, termination, and cancellation.
- [x] Add system-design-specific concise follow-up guidance.
- [x] Add backend protocol and frontend state-machine/UI coverage.
- [x] Run backend and frontend verification and synchronize documentation.

Phase 10A.1 completed and verified on 2026-08-03.

### Phase 10B — Whiteboard persistence and API

- [x] Query `MAP.md` and reconcile the Phase 10B schema and interview context.
- [x] Add attempt-owned system-design sessions and PNG snapshots with cascade deletion.
- [x] Add typed scene validation, system-design eligibility checks, and optimistic version conflicts.
- [x] Add scene retrieval/save and snapshot create/retrieve HTTP APIs.
- [x] Integrate the repository and application service into FastAPI lifespan wiring.
- [x] Add Excalidraw as the interactive whiteboard instead of implementing drawing primitives.
- [x] Add debounced scene autosave through the shared autosave hook with serialized save requests.
- [x] Add changed-scene periodic snapshots, explicit snapshots, and local PNG export.
- [x] Render the whiteboard only for system-design attempts and use view-only mode on mobile.
- [x] Add migration, repository/API, stale-version, cascade, autosave, and snapshot tests.
- [x] Run backend/frontend verification and synchronize documentation.

Phase 10B completed and verified on 2026-08-03.

### Phase 10C — Diagram-aware interview and split-pane UI

- [x] Query `MAP.md` and reconcile the Phase 10C graph, protocol, persistence, and UI scope.
- [x] Start the concrete system-design exercise on the second interviewer turn at the latest.
- [x] Add the provider-neutral diagram observer and configured OpenAI vision adapter.
- [x] Add changed-scene checkpoints before text/voice handoff and interview termination.
- [x] Add versioned `canvas.snapshot`, `canvas.ready`, and `canvas.observed` WebSocket events.
- [x] Add diagram observations to the standard interview graph without changing canonical candidate text.
- [x] Relate snapshots to canonical transcript messages and retain scene-version traceability.
- [x] Continue text-only when vision is unavailable or diagram analysis fails.
- [x] Retain the split whiteboard/transcript layout and add an accessible whiteboard visibility control.
- [x] Add prompt, persistence, engine-delegation, checkpoint-ordering, and UI tests.
- [x] Run backend/frontend verification and synchronize documentation.
- [x] Mark Phase 10 complete in `PLAN.md`, `TASK.md`, and `MAP.md`.

Phase 10C and Phase 10 completed and verified on 2026-08-03.

## Phase 11 — Secure Web Deployment

### Phase 11A — Repository and production-build foundation

- [x] Query `MAP.md` and preserve the current repository state.
- [x] Keep backend/frontend siblings and move Python tooling configuration under `backend/`.
- [x] Add non-root FastAPI and multi-stage static Astro/Nginx image definitions.
- [x] Preserve same-origin production HTTP and WebSocket URLs.
- [x] Synchronize `MAP.md` with the build and structure decisions.

### Phase 11B — Single-user server authentication

- [x] Add singleton users and hashed opaque sessions through migration 006.
- [x] Reconcile authoritative environment credentials with Argon2 and invalidate rotated sessions.
- [x] Add login, session, logout, secure cookies, CSRF, and bounded rate limiting.
- [x] Require authenticated exact-origin interview WebSockets.
- [x] Add the accessible login/logout frontend and shared CSRF-aware API client.
- [x] Add backend and frontend authentication coverage and synchronize `MAP.md`.

### Phase 11C — Docker Compose runtime

- [x] Add backend, Nginx, Certbot, migration, fixture, backup, and restore services.
- [x] Add explicit persistent data, secret, certificate, ACME, and runtime TLS volumes.
- [x] Configure static routing, API/WebSocket proxying, auth subrequests, limits, timeouts, and security headers.
- [x] Add health checks, graceful shutdown, restart policy, and bounded log rotation.
- [x] Build both production images and validate an isolated Compose runtime.

### Phase 11D — Environment, TLS, and operations

- [x] Add `.env.example` and strict installation-time configuration validation.
- [x] Add HTTP challenge bootstrap, certificate issuance, periodic renewal, and atomic Nginx reload.
- [x] Add checksummed SQLite/settings-key backup and verified offline restore.
- [x] Add migration-first installation and upgrade scripts.
- [x] Document installation, staging-to-production TLS, operations, rotation, backup, restore, and upgrades.

### Phase 11E — Governance and completion

- [x] Run complete backend and frontend verification.
- [x] Validate Compose expansion, shell scripts, production images, and the isolated HTTPS runtime.
- [x] Completely synchronize `MAP.md` with the implemented deployment.
- [x] Append the Phase 11 implementation prompt to `PROMPTS.md`.
- [x] Mark Phase 11 complete in `PLAN.md`, `TASK.md`, and `MAP.md`.

Phase 11 completed and verified on 2026-08-03.
