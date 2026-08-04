#!/bin/sh
set -eu
. "$(dirname -- "$0")/common.sh"

if [ "$#" -ne 1 ]; then
  printf 'Usage: %s BACKUP_NAME\n' "$0" >&2
  exit 2
fi
if ! printf '%s\n' "$1" | grep -Eq '^[0-9]{8}T[0-9]{6}Z$'; then
  printf 'Backup name must be a generated UTC timestamp.\n' >&2
  exit 2
fi

ensure_environment
restart() {
  local_compose up -d backend web >/dev/null 2>&1 || true
}
trap restart EXIT INT TERM
local_compose stop backend web
local_compose --profile tools run --rm restore \
  python -m backend.cli.deployment_data restore --source "/backups/$1"
local_compose --profile tools run --rm migrate
local_compose up -d backend web
wait_until_ready
trap - EXIT INT TERM
printf 'Backup %s restored.\n' "$1"
