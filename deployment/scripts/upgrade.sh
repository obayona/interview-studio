#!/bin/sh
set -eu

repository_root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
cd "$repository_root"

COMPOSE="docker compose --project-directory . -f deployment/docker-compose.yml"

python3 -m deployment.scripts.validate_env .env --compose-file deployment/docker-compose.yml
./deployment/scripts/backup.sh
$COMPOSE build --pull
$COMPOSE --profile tools run --rm migrate
$COMPOSE --profile tools run --rm fixtures
$COMPOSE up -d --remove-orphans
$COMPOSE exec -T backend python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=5)"
