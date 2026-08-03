#!/bin/sh
set -eu

repository_root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
cd "$repository_root"
python3 -m deployment.scripts.validate_env .env
./deployment/scripts/backup.sh
docker compose build --pull
docker compose --profile tools run --rm migrate
docker compose --profile tools run --rm fixtures
docker compose up -d --remove-orphans
docker compose exec -T backend python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=5)"
