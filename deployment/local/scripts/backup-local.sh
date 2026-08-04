#!/bin/sh
set -eu
. "$(dirname -- "$0")/common.sh"

ensure_environment
local_compose --profile tools run --rm backup
