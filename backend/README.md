# Interview Engine

Create and activate the repository virtual environment, then install its dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements-dev.txt
```

Run the development CLI:

```bash
python -m backend.cli.engine-usage --job "Backend engineer role"
```

Run the FastAPI application:

```bash
python -m uvicorn backend.app.main:app --reload
```

Then open `http://127.0.0.1:8000`. The inline browser harness uses the
`/api/v1/interviews/browser-harness/ws` WebSocket. The application starts and
serves health/capability information without credentials; interview events return a
structured configuration error until `api_key` exists in the `settings` table.

The SQLite database defaults to `backend/interview_studio.sqlite3`. Yoyo migrations
run at startup. Runtime application code never reads `.env`; persisted settings are
resolved when each interview session is opened.

Health and capability routes:

- `GET /health/live`
- `GET /health/ready`
- `GET /api/v1/capabilities`
- `GET /api/v1/interviews/{attempt_id}/history`

Settings routes:

- `GET/PATCH /api/v1/settings`
- `DELETE /api/v1/settings/{key}`
- `POST /api/v1/settings/test-provider`

Clients should request interview history before starting a WebSocket session. If
history is empty, send `session.start` to generate the greeting. If history is
present, render it and send future `user.text` events directly; this avoids
generating a duplicate question during checkpoint resume.

The CLI alone may read `OPENAI_API_KEY` for development convenience. The backend module does not read
environment variables; callers inject credentials, models, and checkpointers through
`InterviewEngineBuilder`.

Run the backend verification suite:

```bash
python -m ruff check backend
python -m ruff format --check backend
python -m mypy
python -m pytest
```

## Interview graph

![Interview engine graph](cli/graph.png)

Regenerate the diagram from the compiled LangGraph definition:

```bash
python -m backend.cli.generate_graph
```

## Interview prompt basis

The versioned prompt follows structured, job-related interviewing guidance:

- [U.S. Office of Personnel Management structured interviews](https://www.opm.gov/policy-data-oversight/assessment-and-selection/structured-interviews)
- [OPM structured interview guide](https://www.opm.gov/policy-data-oversight/assessment-and-selection/structured-interviews/guide/)
- [EEOC guidance on questions employers should avoid](https://www.eeoc.gov/employers/small-business/what-shouldnt-i-ask-when-hiring)
