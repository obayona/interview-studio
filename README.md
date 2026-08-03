# Interview Studio

Interview Studio is a single-user AI interview practice application with an
Astro/React frontend and FastAPI backend. Development documentation lives in
[backend/README.md](backend/README.md) and [frontend/README.md](frontend/README.md).

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
