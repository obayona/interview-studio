# Interview Studio

Interview Studio is a single-user AI interview practice application with an
Astro/React frontend and FastAPI backend. Development documentation lives in
[backend/README.md](backend/README.md) and [frontend/README.md](frontend/README.md).

## Architecture

Interview Studio runs as Docker containers in two distinct modes:

| | Local | Server |
|---|---|---|
| **Use case** | Personal practice on your machine | Public-facing deployment on a VPS |
| **Compose file** | `deployment/local/compose.yml` | `deployment/docker-compose.yml` |
| **Containers** | `backend` + `web` (Astro in nginx) | `backend` + `nginx` + `certbot` |
| **Images** | Pulled from GHCR (pre-built) | Built from source via Dockerfiles |
| **Network** | `127.0.0.1` only | Public, TLS via Let's Encrypt |
| **Auth** | None (single-user, loopback only) | Username/password via session cookie |
| **Domain** | Not required | Required (public DNS hostname) |
| **TLS** | No | Yes (certbot auto-renewal) |

Both modes share the same backend (FastAPI + SQLite) and use named Docker volumes
for persistent data. The `backend` container always exposes port 8000 internally;
nginx proxies requests to it.

### How the server containers work

```
Internet → :443 nginx (TLS) → :8000 backend (FastAPI)
                  ↕                    ↕
             certbot              SQLite (volume)
          (auto-renewal)
```

1. **nginx** terminates TLS, serves static Astro assets, proxies `/api/` and
   WebSocket connections to the backend, and handles auth subrequests.
2. **backend** runs the FastAPI application with uvicorn. It manages
   authentication, interview sessions, and the SQLite database.
3. **certbot** renews the Let's Encrypt certificate twice daily via the shared
   ACME webroot. nginx detects renewed files and reloads them without restarting.

### Local deployment

The local bundle runs at `http://localhost:8080` and binds strictly to loopback.
No domain, TLS, login, or secrets configuration is needed. Docker treats
localhost as a trustworthy context, so microphone access works after the browser
permission prompt.

**Requirements:** Docker Desktop (Windows/macOS) or Docker Engine with Compose v2
(Linux).

Download `interview-studio-local-VERSION.tar.gz` from the matching
[GitHub Release](https://github.com/obayona/interview-studio/releases) and
extract it. The bundle contains:

```
interview-studio-local-VERSION/
  .env.example          # Default configuration
  compose.yml           # Backend + web containers
  README.md             # Bundle-specific guide
  scripts/              # Start, stop, backup, restore, update, uninstall
```

#### Quick start (Linux/macOS)

```bash
./scripts/start-local.sh
```

#### Quick start (Windows PowerShell)

```powershell
.\scripts\Start-Local.ps1
```

If PowerShell blocks the script:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
```

The first start creates `.env.local` with safe defaults:

```dotenv
LOCAL_PORT=8080
APP_VERSION=1.0.0
BACKUP_DIR=./backups
```

Change `LOCAL_PORT` before starting if 8080 is occupied. The application opens
automatically at `http://localhost:8080`.

#### Operations

| Operation | POSIX | PowerShell |
| --- | --- | --- |
| Stop (retain data) | `./scripts/stop-local.sh` | `.\scripts\Stop-Local.ps1` |
| Back up | `./scripts/backup-local.sh` | `.\scripts\Backup-Local.ps1` |
| Restore | `./scripts/restore-local.sh 20260803T120000Z` | `.\scripts\Restore-Local.ps1 -BackupName 20260803T120000Z` |
| Update | `./scripts/update-local.sh 1.0.1` | `.\scripts\Update-Local.ps1 -Version 1.0.1` |
| Uninstall (retain data) | `./scripts/uninstall-local.sh` | `.\scripts\Uninstall-Local.ps1` |
| Uninstall (delete data) | `./scripts/uninstall-local.sh --delete-data` | `.\scripts\Uninstall-Local.ps1 -DeleteData` |

Backups contain a consistent SQLite copy, its matching encryption key, a
manifest, and SHA-256 checksums. Restore stops writes, verifies checksums,
replaces files atomically, re-applies migrations, and restarts. Data-deleting
uninstall requires typing `DELETE` and is irreversible.

#### Troubleshooting

- **Port occupied:** change `LOCAL_PORT` in `.env.local` and start again.
- **Inspect status:** `docker compose --env-file .env.local -f compose.yml ps`
- **View logs:** same command prefix with `logs --tail=200`.
- **Rollback:** run `update-local.sh` with the previous version. If the schema
  is incompatible, restore the backup created before the update.

See the bundle's [local deployment guide](deployment/local/README.md) for full
details.

### Server deployment

The server deployment builds images from source and runs backend, nginx, and
certbot with Docker Compose. All commands run from the repository root.

**Requirements:**

- A Linux host with Docker Engine and Docker Compose v2.
- One public DNS hostname pointing to the host.
- Inbound TCP ports 80 and 443 open.
- Python 3 and curl installed on the host.

#### Step 1: Configure the environment

```bash
cp .env.example .env
chmod 600 .env
```

Generate the encryption key:

```bash
openssl rand -base64 32
```

Edit `.env` and replace every value:

| Variable | Description |
|---|---|
| `DOMAIN` | Your public DNS hostname (e.g. `interviews.example.com`) |
| `LETSENCRYPT_EMAIL` | Email for Let's Encrypt notifications |
| `APP_USERNAME` | Login username (1-128 characters) |
| `APP_PASSWORD` | Login password (at least 16 characters) |
| `APP_ENCRYPTION_KEY` | Base64-encoded 32-byte key from `openssl rand -base64 32` |
| `APP_SESSION_LIFETIME_SECONDS` | Session duration (default `86400` = 24h) |
| `BACKUP_DIR` | Host directory for backups (default `./backups`) |

Keep the OpenAI API key out of `.env`; configure it from the application
Settings page after signing in.

#### Step 2: Install

```bash
./deployment/scripts/install.sh
```

The installer validates the environment, builds images, runs migrations and
fixtures, and starts the app. nginx serves HTTPS immediately with a temporary
self-signed certificate so you can verify the app end-to-end. Re-running the
installer is safe: port checks are skipped when the app's own nginx container is
already running.

#### Step 3: Issue TLS certificates

```bash
./deployment/scripts/setup-certificates.sh
```

This obtains a certificate from the Let's Encrypt production issuer, starts
auto-renewal, and loads it into nginx. It is idempotent and can be re-run at any
time (for example to replace a certificate issued before a domain change).

#### Operations

All server commands run from the repository root. Use `--project-directory .`
so Docker Compose reads `.env` from the repo root and resolves relative paths
against it:

```bash
# Start / stop
docker compose --project-directory . -f deployment/docker-compose.yml up -d
docker compose --project-directory . -f deployment/docker-compose.yml down

# Status and logs
docker compose --project-directory . -f deployment/docker-compose.yml ps
docker compose --project-directory . -f deployment/docker-compose.yml logs -f --tail=200

# Backup and restore
./deployment/scripts/backup.sh
./deployment/scripts/restore.sh 20260803T120000Z

# Upgrade (backs up, pulls new images, migrates, restarts)
./deployment/scripts/upgrade.sh
```

#### Credential management

Changing `APP_PASSWORD` and restarting the backend replaces its Argon2 hash and
invalidates every existing session. Changing `APP_ENCRYPTION_KEY` after data has
been stored is rejected; restore the matching key from backup instead.

#### Certificate management

`./deployment/scripts/setup-certificates.sh` issues or refreshes the
certificate and can be re-run at any time; it runs a one-shot `certbot
certonly` inside the certbot container, then starts the renewal loop. Certbot
checks renewal twice daily through the shared ACME webroot. nginx detects
renewed files and reloads them without restarting active interviews.

Inspect renewal manually:

```bash
docker compose --project-directory . -f deployment/docker-compose.yml run --rm \
  --entrypoint certbot certbot renew --dry-run \
  --webroot --webroot-path /var/www/certbot
```

#### Validating configuration

To check `.env` without running an installation:

```bash
python3 -m deployment.scripts.validate_env .env --compose-file deployment/docker-compose.yml
```

To run full installation validation (checks ports, Docker, file permissions):

```bash
python3 -m deployment.scripts.validate_env .env --installation \
  --compose-file deployment/docker-compose.yml --project-directory .
```

## Image releases

The workflow in `.github/workflows/release.yml` is the authoritative release
path. It publishes two immutable container images to GitHub Container Registry:

- `ghcr.io/obayona/interview-studio-backend:{version}`
- `ghcr.io/obayona/interview-studio-web:{version}`

Both also receive `sha-{commit}` tags for traceability. The workflow never
publishes `latest`.

Before the first release, make both GHCR packages public in their package
settings.

### Release process

1. Ensure `main` is green and documentation reflects reality.
2. Choose a semantic version and update it in three places:
   - `backend/app/core/version.py`
   - `frontend/package.json`
   - `deployment/local/.env.example`
3. Run the full verification suite locally (backend lint/typecheck/tests, frontend
   format/lint/check/test/build).
4. Commit the version change.
5. Create and push an annotated tag:

   ```bash
   git tag -a v1.0.0 -m "Interview Studio v1.0.0"
   git push origin v1.0.0
   ```

6. Monitor **Release local Docker distribution** in GitHub Actions.
7. Confirm both GHCR packages expose the immutable version and SHA tags.
8. Download the generated bundle and perform a clean installation smoke test.
9. Complete release notes with migrations, visible changes, backup requirements,
   and rollback instructions.

### What the workflow does

1. **Validates** the version is synchronized across backend, frontend, and local
   environment metadata.
2. **Verifies** the full backend and frontend test suites.
3. **Builds** two `linux/amd64` images from source:
   - Backend: `deployment/docker/backend.Dockerfile`
   - Web: `deployment/docker/local-nginx.Dockerfile` (builds Astro, copies into
     nginx)
4. **Smoke-tests** the local topology with the built images.
5. **Pushes** to GHCR with both version and SHA tags.
6. **Packages** a release bundle (`interview-studio-local-{version}.tar.gz`)
   containing the local compose file, scripts, and nginx config.
7. **Publishes** the bundle to the matching GitHub Release.

Use GitHub's **Re-run jobs** action after a transient workflow failure. The
workflow detects already-published images and skips rebuilding. Published semantic
tags are immutable; a correction requires a new patch release.

### Build from source (diagnostics only)

For local development or debugging, build images without the release workflow:

```bash
cp deployment/local/.env.example deployment/local/.env.local
docker compose --env-file deployment/local/.env.local \
  -f deployment/local/compose.yml -f deployment/local/compose.build.yml build
```

## Project structure

```
.
├── backend/                  # FastAPI backend (Python 3.12)
├── frontend/                 # Astro 7 + React 19 frontend
├── deployment/
│   ├── docker/
│   │   ├── backend.Dockerfile        # Server backend image
│   │   ├── nginx.Dockerfile          # Server nginx (TLS, auth_request)
│   │   └── local-nginx.Dockerfile    # Local nginx (no TLS)
│   ├── docker-compose.yml            # Server deployment compose
│   ├── local/
│   │   ├── compose.yml               # Local deployment compose
│   │   ├── compose.build.yml         # Override for building from source
│   │   ├── nginx.conf                # Local nginx config
│   │   ├── .env.example              # Local defaults
│   │   ├── README.md                 # Local bundle guide
│   │   └── scripts/                  # POSIX + PowerShell operations
│   ├── nginx/
│   │   └── default.conf.template     # Server nginx config (envsubst)
│   └── scripts/
│       ├── install.sh                # Server first-time install
│       ├── setup-certificates.sh     # Issue/replace Let's Encrypt certs
│       ├── upgrade.sh                # Server upgrade
│       ├── backup.sh                 # Server backup
│       ├── restore.sh                # Server restore
│       ├── validate_env.py           # Configuration validator
│       ├── prepare_local_release.py  # Release bundle builder
│       ├── nginx-entrypoint.sh       # Server nginx entrypoint
│       └── renew-certificates.sh     # Certbot renewal loop
├── .env.example              # Server deployment template
└── README.md                 # This file
```
