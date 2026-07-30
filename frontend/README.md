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

The client uses same-origin HTTP and WebSocket URLs by default. Production
deployments can set these public build-time variables:

```dotenv
PUBLIC_API_BASE_URL=https://api.example.com
PUBLIC_WS_BASE_URL=wss://api.example.com
```

Omit trailing slashes because the client appends route paths beginning with
`/api`.

When these variables are omitted, deploy the frontend behind a reverse proxy
that forwards `/api` to FastAPI and supports WebSocket upgrades.

## Structure

```text
src/
  components/
    layout/       Astro shell components
    ui/           Reusable accessible React components
  features/
    profile/      Profile editor, autosave, avatar, and CV import
    settings/     Settings page React island
  layouts/        Persistent application layout
  pages/          Astro file-based routes
  services/       Typed HTTP, settings, and WebSocket clients
  styles/         Design tokens and shared component styles
  types/          API transport types
```

The current routes are:

- `/`
- `/profile`
- `/processes`
- `/processes/details`
- `/interview`
- `/feedback`
- `/settings`

Design tokens support light, dark, and system themes. Shared styles include
visible keyboard focus and reduced-motion behavior.
