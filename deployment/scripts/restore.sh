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

COMPOSE="docker compose --project-directory . -f deployment/docker-compose.yml"

python3 -m deployment.scripts.validate_env .env --compose-file deployment/docker-compose.yml

restart_backend() {
  $COMPOSE up -d backend >/dev/null 2>&1 || true
}
trap restart_backend EXIT INT TERM
$COMPOSE stop backend
$COMPOSE --profile tools run --rm restore \
  python -m backend.cli.deployment_data restore --source "/backups/$1"
$COMPOSE --profile tools run --rm migrate
$COMPOSE up -d backend
trap - EXIT INT TERM
