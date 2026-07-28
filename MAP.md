# Interview Studio System Map

Last synchronized: 2026-07-28

## Current status

- Phase 0: Partial. The implementation plan exists; Phase 1 adds the Python tooling required by the interview engine. Frontend tooling remains deferred to Phase 4.
- Phase 1: Complete and verified on 2026-07-28.
- Phases 2–12: Not started.

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

## Interfaces, routes, and persistence

- Public backend interfaces: `backend.interview_engine.InterviewEngineBuilder`, `InterviewEngine`, typed configuration models, and enums.
- Engine operations: `stream_start`, `stream_response`, `stream_end`, and `get_state`.
- HTTP routes: None.
- WebSocket routes: None.
- Database entities and migrations: None in Phase 1.

## Known constraints

- `MAP.md` did not exist before Phase 1 started; this file was derived from the repository.
- `PHASE_PROMPT.md` has a pre-existing user modification and must not be overwritten.
- Natural voice interruption is not implemented in Phase 1. The media ports preserve the future boundary; push-to-talk is the reliable Phase 7 baseline and browser VAD/barge-in is a higher-complexity progressive enhancement.

## Verification

- Ruff lint: Passed.
- Ruff formatting check: Passed.
- Strict mypy: Passed for all 9 package source files.
- Pytest: 11 pure-function and model-validation tests passed; graph/model behavior is not simulated through complex mocks.
- `backend/cli/engine-usage.py` is the Phase 1 manual engine exercise. Backend integration tests begin only after the backend exists in Phase 2.
- Repository diff whitespace check: Passed.
