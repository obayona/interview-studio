#!/bin/sh
set -eu
. "$(dirname -- "$0")/common.sh"

ensure_environment
if [ "${1:-}" != "--delete-data" ]; then
  local_compose down --remove-orphans --rmi all
  printf 'Interview Studio containers and images were removed. Local data was retained.\n'
  exit 0
fi

printf 'This permanently deletes every local profile, process, interview, report, and setting.\n'
printf 'Type DELETE to continue: '
read -r confirmation
if [ "$confirmation" != "DELETE" ]; then
  printf 'Data deletion cancelled.\n'
  exit 1
fi
local_compose down --volumes --remove-orphans --rmi all
printf 'Interview Studio and its local data were removed. This cannot be undone.\n'
