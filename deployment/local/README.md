# Interview Studio local Docker app

This bundle runs Interview Studio as a single-user web application at
`http://localhost:8080`. Docker publishes the site only on `127.0.0.1`; other
computers cannot connect. Browsers treat localhost as a trustworthy context, so
microphone access remains available after the usual permission prompt.

## Install and start

Install Docker Desktop (Windows/macOS) or Docker Engine with Compose v2 (Linux),
then extract this bundle. The default configuration is ready to use. To choose a
different port or backup directory, copy `.env.example` to `.env.local` and edit:

```dotenv
LOCAL_PORT=8080
APP_VERSION=1.0.0
BACKUP_DIR=./backups
```

Do not change `APP_VERSION` except when installing a published release. Start on
Linux or macOS with:

```bash
./scripts/start-local.sh
```

On Windows PowerShell:

```powershell
.\scripts\Start-Local.ps1
```

The command validates Docker, the semantic image version, and port range; pulls
the pinned images; checks for a port collision; runs migrations and fixtures;
creates the user-writable backup directory; waits for readiness; and opens the
browser. Configure the OpenAI key afterward from Settings. It is encrypted in
the persistent local data volume, never read from `.env.local`.

If PowerShell blocks a downloaded script, use a process-scoped policy without
changing the machine policy:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
```

## Operations

| Operation | POSIX | PowerShell |
| --- | --- | --- |
| Stop and retain data | `./scripts/stop-local.sh` | `.\scripts\Stop-Local.ps1` |
| Back up | `./scripts/backup-local.sh` | `.\scripts\Backup-Local.ps1` |
| Restore | `./scripts/restore-local.sh 20260803T120000Z` | `.\scripts\Restore-Local.ps1 -BackupName 20260803T120000Z` |
| Update | `./scripts/update-local.sh 1.0.1` | `.\scripts\Update-Local.ps1 -Version 1.0.1` |
| Uninstall, retain data | `./scripts/uninstall-local.sh` | `.\scripts\Uninstall-Local.ps1` |
| Uninstall and delete data | `./scripts/uninstall-local.sh --delete-data` | `.\scripts\Uninstall-Local.ps1 -DeleteData` |

Backups contain a consistent SQLite copy, its matching encryption key, a
manifest, and SHA-256 checksums. Restore stops writes and verifies those
checksums before replacing either file. The one-shot tool receives the minimum
volume access needed and returns completed backup ownership to the invoking user;
the web backend remains non-root. Update creates a backup before pulling, stops
writes before migration, and verifies readiness afterward.

Stopping, restarting, updating, and ordinary uninstall retain the named data
and key volumes. Data-removing uninstall requires typing `DELETE` and is
irreversible. Keep a backup outside Docker before choosing it.

## Troubleshooting and rollback

- If the port is occupied, choose an unused value from 1024 through 65535 in
  `.env.local`, then start again.
- Inspect status with
  `docker compose --env-file .env.local -f compose.yml ps` and logs with the
  same prefix followed by `logs --tail=200`.
- A pull failure leaves the installed data unchanged. Confirm Internet access
  and that both GHCR packages are public, then retry.
- To select a previous application version, run the update command with that
  version. Database migrations are not reversed automatically. If the previous
  release is incompatible with the upgraded schema, restore the backup created
  immediately before the update.

The release images support Linux/amd64 containers. Windows uses Docker Desktop
with Linux containers; a native Windows installer is intentionally outside this
release.
