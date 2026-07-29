# Interview Studio System Map

Last synchronized: 2026-07-28

## Current status

- Phase 0: Partial. The implementation plan exists; Phase 1 adds the Python tooling required by the interview engine. Frontend tooling remains deferred to Phase 4.
- Phase 1: Complete and verified on 2026-07-28.
- Phase 2: Complete and verified on 2026-07-28.
- Phase 3: Complete and verified on 2026-07-28.
- Phase 4: Complete and verified on 2026-07-28.
- Phases 5–12: Not started.

## Repository baseline

- `AGENT.md`: Functional source of truth.
- `PLAN.md`: Mandatory implementation sequence and architectural decisions.
- `TASK.md`: Phase execution checklist.
- `PROMPTS.md`: Append-only user prompt record.
- `prototypes/`: Reference HTML and screenshots; no application frontend exists yet.
- `backend/`: Not present at initial synchronization.

## Implemented modules

- `backend/interview_engine/models.py`: Typed candidate, configuration, limits, media, interview type, persona, difficulty, and termination models.
- `backend/interview_engine/state.py`: LangGraph interview state with message reduction and lifecycle fields.
- `backend/interview_engine/topics.py`: Default competency plans per interview type.
- `backend/interview_engine/prompts.py`: Versioned structured-interview system, context, turn, follow-up, and closing prompts.
- `backend/interview_engine/ports.py`: Provider-neutral STT and TTS abstract ports for future phases.
- `backend/interview_engine/graph.py`: Deterministic lifecycle routing with model-generated greeting, questions, follow-ups, transitions, and closing.
- `backend/interview_engine/engine.py`: Text streaming, response, explicit-end, and state-retrieval API.
- `backend/interview_engine/builder.py`: Fluent dependency and configuration builder.
- `backend/cli/engine-usage.py`: Async development CLI with buffered assistant output.
- `backend/cli/generate_graph.py`: Builds the real compiled graph and renders `backend/cli/graph.png` without making a model request.
- `backend/__init__.py`: Backend package boundary; `backend.interview_engine` imports work from the repository root without installation or path manipulation.
- `backend/requirements*.txt`: Runtime and development dependencies only; the interview engine is not an installable distribution.
- `pyproject.toml`: Repository-level Python quality-tool configuration.
- `backend/README.md`: Environment, dependency, import, and CLI instructions.
- `backend/README.md` embeds the generated interview graph and documents its regeneration command.
- `backend/app/core/database.py`: Application-owned asynchronous SQLite manager with serialized explicit transactions, WAL, foreign keys, busy timeout, Yoyo startup migrations, and clean shutdown.
- `backend/app/core/config.py`: Application-facing `SettingsService` facade for typed reads, capabilities, CRUD, and provider testing.
- `backend/app/core/settings_definitions.py`: `SettingKey` enum and definition dictionary from which persistence validation, secret metadata, and defaults are derived.
- `backend/app/core/errors.py`: Transport-neutral structured application errors.
- `backend/app/repositories/settings.py`: Parameterized SQLite settings reads.
- `backend/migrations/001_phase2_core.py`: Reversible Phase 2 schema migration.
- `backend/app/infrastructure/json_codec.py`: Versioned strict JSON codec and explicit LangChain message adapter; unsupported and binary values are rejected.
- `backend/app/infrastructure/checkpointer.py`: Async `BaseCheckpointSaver` implementation with canonical transcript extraction, atomic shallow state upsert, idempotent pending writes, current-only listing, reconstruction, and graph-state deletion.
- `backend/app/repositories/attempts.py`: Attempt configuration lookup, canonical transcript reads, and idempotent browser-harness bootstrap.
- `backend/app/application/interviews.py`: Operation-scoped settings resolution and interview-engine orchestration using the application checkpointer.
- `backend/app/api/websocket.py`: Versioned interview WebSocket adapter for session start/end, text answers, streaming assistant deltas/completions, ping/pong, and structured errors.
- `backend/app/api/interviews.py`: Canonical transcript history endpoint for reconnect hydration.
- `backend/app/api/index.py`: Inline accessible minimal browser chat harness.
- `backend/app/main.py`: FastAPI factory, lifespan wiring, request IDs, structured application errors, root page, health, readiness, and capabilities.
- `backend/tests/integration/`: Temporary-database migration, startup, capability, strict-codec, saver-conformance, and real compiled-LangGraph resume coverage.
- `backend/app/core/secrets.py`: Versioned AES-GCM secret box with a restricted local master-key file.
- `backend/app/api/settings.py`: Validated settings status/update/removal and OpenAI provider-test routes.
- `backend/tests/integration/test_settings.py`: Settings validation, masking, encryption, capability refresh, removal, provider absence, and tamper tests.
- `frontend/`: Astro 7 and React 19 SPA-style frontend managed with pnpm 11, with strict TypeScript, ESLint, Prettier, Stylelint, and Vitest tooling.
- `frontend/src/layouts/AppLayout.astro`: Persistent fixed shell with sidebar, header, responsive navigation, and Astro client routing transitions.
- `frontend/src/components/ui/`: Reusable Font Awesome icon, button, form, input, select, switch, card, badge, toast, dialog, spinner, skeleton, empty-state, and error-state components.
- `frontend/src/styles/`: Ventura Tech-derived design tokens, component styles, responsive layout, dark mode, focus states, and reduced-motion behavior.
- `frontend/src/services/`: Typed normalized HTTP client, settings API, and versioned interview WebSocket foundation.
- `frontend/src/features/settings/`: Integrated OpenAI, interaction, theme, model, voice, capability, provider-test, and secret-removal settings UI.
- `frontend/src/pages/`: Working dashboard, profile, processes, process-details, interview, feedback, and settings routes.
- `frontend/README.md`: pnpm-based setup, development, verification, deployment configuration, routes, and source-structure guide.

## Technical decisions

- Python 3.12 is the supported runtime.
- Interview lifecycle routing is deterministic from typed state: elapsed time, question limit, topic coverage, explicit end, and configured follow-up depth.
- The chat model generates the greeting, questions, transitions, follow-ups, and closing language.
- Phase 1 is text-only; STT and TTS are represented by provider-neutral abstract ports.
- The engine logger is named `interview-engine` and does not install handlers.
- `MemorySaver` is the standalone default; callers can inject another LangGraph `BaseCheckpointSaver`.
- Runtime package code never reads `.env`; credentials are injected through the builder. The CLI may read `OPENAI_API_KEY` for development.
- The engine is an internal backend module imported as `backend.interview_engine`; it has no build metadata or editable-install requirement.
- The graph's conditional router is asynchronous, preventing unnecessary executor thread hops.
- Structured prompts follow job-competency and behavioral/situational interviewing guidance and prohibit non-job-related protected-characteristic questions.
- Phase 2 uses one application-owned `sqlite3` connection behind an asynchronous manager API and transaction lock; migrations run synchronously through Yoyo before the connection opens. A pool is intentionally unnecessary for the single-user SQLite architecture.
- Persisted configuration is resolved for every operation and runtime startup never reads `.env`.
- Graph state is JSON text only. Completed LangChain messages require stable IDs and are stored once in `interview_messages`; checkpoint state is reconstructed from the ordered canonical transcript.
- The saver supports LangGraph's async execution API only; synchronous methods fail explicitly so web graph execution cannot bypass the manager's asynchronous transaction boundary.
- FastAPI constructs a new interview engine when a WebSocket operation starts, after resolving current persisted settings, and injects the shared shallow saver.
- `app.state.settings` is the sole application settings dependency. `SettingsRepository` and `SecretBox` are private construction details of the lifespan and are not exposed through application state.
- Settings API mappings and repository known-key checks derive from `SETTING_DEFINITIONS`; persistence uses flat enum values such as `api_key` while higher-level classes retain conceptual grouping.
- `SettingKey` exposes `.value`, `.default`, and `.secret` from the single definition dictionary; `setting_keys()` supplies key-only iterations without a second registry.
- The browser harness owns a deterministic attempt ID but a generated stable thread ID persisted in SQLite, allowing disconnect/resume without introducing the Phase 6 attempt CRUD early.
- Reconnecting clients fetch canonical history first. A non-empty history resumes immediately and may send `user.text` without `session.start`; an empty or unavailable history causes the harness to send `session.start`.
- Phase 3 exposes settings status, updates, removal, and provider testing through the `SettingsService` facade and safe HTTP routes.
- Phase 3 uses a local 256-bit master key at `backend/.secret-key` by default; `AppConfig.secret_path` supports an installation-specific path. The key file is mode `0600` and ignored by git.
- Secret settings use versioned AES-GCM authenticated encryption with associated data; plaintext is never returned by the API. Values are encrypted when written.
- Settings are constrained by a known-key registry; arbitrary client keys are rejected. Model names, voice, theme, and provider values are validated before persistence.
- Phase 4 uses Astro pages with React islands only for interactive state; the shell and placeholders render as static HTML.
- The frontend uses native CSS with BEM naming, `1rem = 10px`, design tokens, system-aware themes, and Font Awesome through one reusable icon component.
- Development HTTP calls use Astro's same-origin `/api` proxy to FastAPI; production base URLs can be supplied with public build-time variables.
- Responsive navigation makes the off-canvas sidebar inert and hidden from assistive technology while closed, supports Escape and link-based closing, and avoids duplicate listeners across Astro page transitions.
- Frontend dependency installation and scripts use pnpm; `pnpm-lock.yaml` is the authoritative lockfile.

## Interfaces, routes, and persistence

- Public backend interfaces: `backend.interview_engine.InterviewEngineBuilder`, `InterviewEngine`, typed configuration models, and enums.
- Engine operations: `stream_start`, `stream_response`, `stream_end`, and `get_state`.
- HTTP routes: `GET /`, `GET /health/live`, `GET /health/ready`, `GET /api/v1/capabilities`, `GET /api/v1/interviews/{attempt_id}/history`, `GET/PATCH /api/v1/settings`, `DELETE /api/v1/settings/{key}`, and `POST /api/v1/settings/test-provider`.
- WebSocket route: `/api/v1/interviews/{attempt_id}/ws`.
- Implemented client WebSocket events: `session.start`, `user.text`, `session.end`, and `ping`.
- Implemented server WebSocket events: `session.ready`, `assistant.text.delta`, `assistant.text.completed`, `error`, and `pong`.
- Database entities: `settings`, minimal Phase 2 `interview_attempts`, canonical `interview_messages`, shallow `interview_graph_state`, and temporary `interview_graph_writes`.
- Migration `001_phase2_core` creates only application-owned tables; it intentionally does not create LangGraph standard checkpoint/blob tables.
- Phase 3 requires no schema migration: the existing key/value `settings` table supports the complete known-key registry and encrypted values.
- Frontend routes: `/`, `/profile`, `/processes`, `/processes/details`, `/interview`, `/feedback`, and `/settings`.

## Known constraints

- `MAP.md` did not exist before Phase 1 started; this file was derived from the repository.
- `PHASE_PROMPT.md` has a pre-existing user modification and must not be overwritten.
- Natural voice interruption is not implemented in Phase 1. The media ports preserve the future boundary; push-to-talk is the reliable Phase 7 baseline and browser VAD/barge-in is a higher-complexity progressive enhancement.
- Phase 2 exposes only the protocol subset required for text interview testing. Audio, mode changes, pause/resume controls, report events, and canvas events remain assigned to later phases.
- `interview_attempts` contains the minimal ownership/configuration fields required by the Phase 2 checkpointer and browser harness. Full process, stage, attempt lifecycle, and attempt repository behavior remain Phase 6.

## Verification

- Ruff lint: Passed.
- Ruff formatting check: Passed.
- Strict mypy: Passed for all 9 package source files.
- Pytest: 11 pure-function and model-validation tests passed; graph/model behavior is not simulated through complex mocks.
- `backend/cli/engine-usage.py` is the Phase 1 manual engine exercise. Backend integration tests begin only after the backend exists in Phase 2.
- Repository diff whitespace check: Passed.
- Phase 2 Ruff lint and formatting checks: Passed for 36 backend files.
- Phase 2 strict mypy: Passed for 27 application and engine source files.
- Phase 2 Pytest: 15 tests passed, including temporary SQLite startup/migration and real LangGraph async saver/resume integration.
- Yoyo migration apply and rollback: Passed on a fresh temporary SQLite database; repeated startup against an existing migrated database passed.
- Live FastAPI/WebSocket/provider exercise: Passed greeting streaming, disconnect, checkpoint resume, and next-response streaming. The temporary credential database was deleted afterward.
- Phase 3 Ruff lint and formatting checks: Passed for 40 backend files.
- Phase 3 strict mypy: Passed for 29 application and engine source files.
- Phase 3 Pytest: 17 tests passed, including settings CRUD, immediate capability refresh, masking, authenticated encryption, tamper rejection, removal, and missing-provider behavior.
- Phase 4 Prettier formatting: Passed for the complete frontend.
- Phase 4 ESLint and Stylelint: Passed.
- Phase 4 Astro strict diagnostics: 35 files checked with zero errors, warnings, or hints.
- Phase 4 Vitest: 4 tests passed across typed transport, switch behavior, settings integration, and axe-core accessibility coverage.
- Phase 4 production build: 7 static routes generated successfully.
- Phase 4 production dependency audit: No known vulnerabilities.
- Phase 4 browser validation: Desktop settings layout and the responsive loading layout were exercised with headless Chrome; focus, reduced-motion, responsive navigation, loading, and error behavior are represented in implementation and tests.
