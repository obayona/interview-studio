#!/bin/sh
set -eu

LOCAL_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
ENV_FILE="$LOCAL_ROOT/.env.local"
COMPOSE_FILE="$LOCAL_ROOT/compose.yml"

ensure_environment() {
  if [ ! -f "$ENV_FILE" ]; then
    cp "$LOCAL_ROOT/.env.example" "$ENV_FILE"
    printf 'Created %s with safe local defaults.\n' "$ENV_FILE"
  fi
  set -a
  # The local file contains only version, numeric port, and backup path values.
  # shellcheck disable=SC1090
  . "$ENV_FILE"
  set +a
  if ! printf '%s\n' "${APP_VERSION:-}" | grep -Eq '^[0-9]+\.[0-9]+\.[0-9]+$'; then
    printf 'APP_VERSION must be a semantic version such as 1.0.0.\n' >&2
    exit 2
  fi
  case "${LOCAL_PORT:-}" in
    ''|*[!0-9]*) printf 'LOCAL_PORT must be an integer from 1024 through 65535.\n' >&2; exit 2 ;;
  esac
  if [ "$LOCAL_PORT" -lt 1024 ] || [ "$LOCAL_PORT" -gt 65535 ]; then
    printf 'LOCAL_PORT must be from 1024 through 65535.\n' >&2
    exit 2
  fi
  if [ -z "${BACKUP_DIR:-}" ]; then
    printf 'BACKUP_DIR cannot be empty.\n' >&2
    exit 2
  fi
  case "$BACKUP_DIR" in
    /*) ;;
    *) BACKUP_DIR="$LOCAL_ROOT/${BACKUP_DIR#./}" ;;
  esac
  mkdir -p "$BACKUP_DIR"
  if [ ! -w "$BACKUP_DIR" ]; then
    printf 'BACKUP_DIR is not writable: %s\n' "$BACKUP_DIR" >&2
    exit 2
  fi
  export BACKUP_DIR
  LOCAL_BACKUP_UID=$(id -u)
  LOCAL_BACKUP_GID=$(id -g)
  export LOCAL_BACKUP_UID LOCAL_BACKUP_GID
  if ! command -v docker >/dev/null 2>&1 || ! docker compose version >/dev/null 2>&1; then
    printf 'Docker with Compose v2 is required.\n' >&2
    exit 2
  fi
}

local_compose() {
  docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"
}

wait_until_ready() {
  count=0
  while [ "$count" -lt 60 ]; do
    if local_compose exec -T backend python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health/ready', timeout=3)" >/dev/null 2>&1; then
      return 0
    fi
    count=$((count + 1))
    sleep 1
  done
  printf 'Interview Studio did not become ready within 60 seconds.\n' >&2
  local_compose ps >&2
  return 1
}

open_local_browser() {
  url="http://localhost:${LOCAL_PORT}"
  case "$(uname -s 2>/dev/null || true)" in
    Darwin) command -v open >/dev/null 2>&1 && open "$url" >/dev/null 2>&1 & ;;
    Linux) command -v xdg-open >/dev/null 2>&1 && xdg-open "$url" >/dev/null 2>&1 & ;;
  esac
  printf 'Interview Studio is ready at %s\n' "$url"
}

set_app_version() {
  version=$1
  if ! printf '%s\n' "$version" | grep -Eq '^[0-9]+\.[0-9]+\.[0-9]+$'; then
    printf 'Version must use semantic form such as 1.0.1.\n' >&2
    exit 2
  fi
  temporary="${ENV_FILE}.tmp"
  awk -v version="$version" '
    BEGIN { replaced = 0 }
    /^APP_VERSION=/ { print "APP_VERSION=" version; replaced = 1; next }
    { print }
    END { if (!replaced) print "APP_VERSION=" version }
  ' "$ENV_FILE" > "$temporary"
  mv "$temporary" "$ENV_FILE"
  APP_VERSION=$version
  export APP_VERSION
}
