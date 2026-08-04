#!/bin/sh
set -eu
. "$(dirname -- "$0")/common.sh"

ensure_environment
local_compose pull backend web
if [ -z "$(local_compose ps -q web)" ]; then
  if ! local_compose --profile tools run --rm --service-ports port-check; then
    printf 'LOCAL_PORT %s is already in use. Change it in .env.local.\n' "$LOCAL_PORT" >&2
    exit 2
  fi
fi
local_compose --profile tools run --rm migrate
local_compose --profile tools run --rm fixtures
local_compose up -d backend web
wait_until_ready
open_local_browser
