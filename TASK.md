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
- [x] Add the asynchronous CLI streaming harness.
- [x] Add unit tests only for pure lifecycle, validation, topic, and prompt functions.
- [x] Use `backend/cli/engine-usage.py` as the Phase 1 manual engine exercise; do not add backend integration tests before Phase 2.
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
- [x] Serve the inline root-page WebSocket test UI.
- [x] Add health, readiness, capabilities, request IDs, and structured errors.
- [x] Add unit and temporary-database integration tests.
- [x] Verify fresh/existing migrations, formatting, linting, typing, and tests.
- [x] Synchronize `MAP.md` with the implemented system.
- [x] Mark Phase 2 complete in `PLAN.md`, `TASK.md`, and `MAP.md`.

Phase 2 completed and verified on 2026-07-28.

## Phase 2 follow-up

- [x] Add canonical transcript history retrieval for reconnecting clients.
- [x] Update the browser harness to hydrate history and avoid restarting resumed interviews.

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
