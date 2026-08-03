#!/bin/sh
set -eu

if [ "$#" -ne 1 ]; then
  printf 'Usage: %s BACKUP_NAME\n' "$0" >&2
  exit 2
fi
case "$1" in
  *[!0-9TZ]*) printf 'Backup name must be a generated UTC timestamp.\n' >&2; exit 2 ;;
esac

repository_root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
cd "$repository_root"
python3 -m deployment.scripts.validate_env .env

restart_backend() {
  docker compose up -d backend >/dev/null 2>&1 || true
}
trap restart_backend EXIT INT TERM
docker compose stop backend
docker compose --profile tools run --rm restore \
  python -m backend.cli.deployment_data restore --source "/backups/$1"
docker compose --profile tools run --rm migrate
docker compose up -d backend
trap - EXIT INT TERM
