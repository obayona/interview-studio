#!/bin/sh
set -eu
. "$(dirname -- "$0")/common.sh"

ensure_environment
if [ "$#" -gt 1 ]; then
  printf 'Usage: %s [VERSION]\n' "$0" >&2
  exit 2
fi
previous_version=$APP_VERSION
local_compose --profile tools run --rm backup
if [ "$#" -eq 1 ]; then
  set_app_version "$1"
fi
local_compose pull backend
recover() {
  if [ "$APP_VERSION" != "$previous_version" ]; then
    set_app_version "$previous_version"
  fi
  local_compose up -d backend >/dev/null 2>&1 || true
}
trap recover EXIT INT TERM
local_compose stop backend
local_compose --profile tools run --rm migrate
local_compose --profile tools run --rm fixtures
local_compose up -d --force-recreate backend
wait_until_ready
trap - EXIT INT TERM
printf 'Interview Studio %s is ready.\n' "$APP_VERSION"
