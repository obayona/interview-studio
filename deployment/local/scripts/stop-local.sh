#!/bin/sh
set -eu
. "$(dirname -- "$0")/common.sh"

ensure_environment
local_compose down
printf 'Interview Studio stopped. Local data was retained.\n'
