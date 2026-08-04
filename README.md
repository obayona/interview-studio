# Interview Studio

Interview Studio is a single-user AI interview practice application with an
Astro/React frontend and FastAPI backend. Development documentation lives in
[backend/README.md](backend/README.md) and [frontend/README.md](frontend/README.md).

## Local Docker app

The simplest single-user distribution is the versioned local Docker release.
It requires Docker Engine with Compose v2 on Linux, or Docker Desktop using Linux
containers on Windows or macOS. Download `interview-studio-local-VERSION.tar.gz`
from the matching GitHub Release and extract it.

The first start creates `.env.local` with these safe defaults:

```dotenv
LOCAL_PORT=8080
APP_VERSION=1.0.0
BACKUP_DIR=./backups
```

Edit the port before starting if 8080 is already occupied. On Linux or macOS,
run:

```bash
./scripts/start-local.sh
```

Windows users run `.\scripts\Start-Local.ps1` from PowerShell. The application
opens at `http://localhost:8080` by default and is bound strictly to loopback.
No domain, TLS certificate, login, or deployment secret is required. Change
`LOCAL_PORT` in `.env.local` when 8080 conflicts with another local service.

Common POSIX operations are:

```bash
./scripts/stop-local.sh
./scripts/backup-local.sh
./scripts/update-local.sh 1.0.1
./scripts/restore-local.sh 20260803T120000Z
./scripts/uninstall-local.sh
```

Equivalent `Stop-Local.ps1`, `Backup-Local.ps1`, `Update-Local.ps1`,
`Restore-Local.ps1`, and `Uninstall-Local.ps1` commands are included for
PowerShell. Ordinary stop, update, and uninstall retain application data. Data
deletion is available only through the explicitly confirmed uninstall option.

See the bundle's [local deployment guide](deployment/local/README.md) for start,
stop, backup, restore, update, rollback, and explicit uninstall choices.

## Web deployment

The supported server deployment compiles Astro into static Nginx assets and
runs FastAPI, Nginx, and Certbot with Docker Compose. The browser uses the same
HTTPS origin for pages, APIs, and interview WebSockets.

Requirements:

- a Linux host with Docker Engine and Docker Compose v2;
- one public DNS hostname pointing to the host;
- inbound TCP ports 80 and 443;
- Python 3 and curl for installation validation.

Create the private deployment configuration:

```bash
cp .env.example .env
chmod 600 .env
openssl rand -base64 32
```

Edit `.env`, replacing every example value. Paste the generated value into
`APP_ENCRYPTION_KEY`. Keep the OpenAI API key out of `.env`; configure it from
the application Settings page after signing in.

For the first certificate request, use staging to avoid Let's Encrypt rate
limits by setting both `DEPLOYMENT_ENV=staging` and
`LETSENCRYPT_STAGING=true`. After it succeeds, switch both values to production
and run installation again:

```bash
./deployment/scripts/install.sh
```

The installer validates the configuration and ports, builds the images, runs
migrations and fixtures independently, starts HTTP challenge handling, obtains
the certificate, activates HTTPS, starts renewal, and verifies readiness.

Normal operations:

```bash
docker compose up -d
docker compose ps
docker compose logs -f --tail=200
docker compose down
./deployment/scripts/backup.sh
./deployment/scripts/restore.sh 20260803T120000Z
./deployment/scripts/upgrade.sh
```

Changing `APP_PASSWORD` and restarting the backend replaces its Argon2 hash and
invalidates every existing session. Changing `APP_ENCRYPTION_KEY` after data has
been stored is rejected; restore the matching key from backup instead.

Backups are written beneath `BACKUP_DIR`. Each contains an online-consistent
SQLite copy, the required settings encryption key, and checksums. Protect this
directory like `.env`. Restore stops backend writes, verifies both files,
replaces them atomically, reapplies migrations, and starts the backend again.

Certbot checks renewal twice daily through the shared ACME webroot. Nginx
detects renewed files and reloads them without restarting active interviews.
Inspect renewal manually with:

```bash
docker compose run --rm --entrypoint certbot certbot renew --dry-run \
  --webroot --webroot-path /var/www/certbot
```

## Creating image releases

The semantic-tag workflow in `.github/workflows/release.yml` is the authoritative
release path. Before the first release, make both GHCR packages public in their
package settings. The workflow has repository `contents: write` and
`packages: write` permissions and publishes:

- `ghcr.io/obayona/interview-studio-backend:1.0.0`;
- `ghcr.io/obayona/interview-studio-web:1.0.0`;
- matching `sha-COMMIT` tags for traceability.

It never publishes `latest`. To release:

1. Ensure `main` is green and `PLAN.md`, `TASK.md`, and `MAP.md` reflect reality.
2. Choose a semantic version and update `backend/app/core/version.py`,
   `frontend/package.json`, and `deployment/local/.env.example` to the same value.
3. Run the complete backend/frontend verification suite locally.
4. Commit the version change.
5. Create and push an annotated tag:

   ```bash
   git tag -a v1.0.0 -m "Interview Studio v1.0.0"
   git push origin v1.0.0
   ```

6. Monitor **Release local Docker distribution** in GitHub Actions.
7. Confirm both public GHCR packages expose the immutable version and SHA tags.
8. Download the generated bundle and perform a clean installation smoke test.
9. Complete release notes with migrations, visible changes, backup requirements,
   and rollback instructions.

Use GitHub's **Re-run jobs** action after a transient workflow failure. The
workflow detects already-published matching version/SHA tags and consumes them
instead of rebuilding or overwriting the version. Published semantic image tags
are immutable; a correction requires a new patch release. If a rollback crosses
an incompatible migration, choose the previous `APP_VERSION` and restore the
pre-upgrade backup—database rollback is never automatic.

For diagnostics only, build local images from source:

```bash
cp deployment/local/.env.example deployment/local/.env.local
docker compose --env-file deployment/local/.env.local \
  -f deployment/local/compose.yml -f deployment/local/compose.build.yml build
```
