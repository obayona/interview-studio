#!/bin/sh
set -eu

repository_root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
cd "$repository_root"

COMPOSE="docker compose --project-directory . -f deployment/docker-compose.yml"

python3 -m deployment.scripts.validate_env .env --compose-file deployment/docker-compose.yml
$COMPOSE --profile tools run --rm backup
