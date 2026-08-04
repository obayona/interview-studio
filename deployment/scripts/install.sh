#!/bin/sh
set -eu

repository_root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
cd "$repository_root"

COMPOSE="docker compose --project-directory . -f deployment/docker-compose.yml"

python3 -m deployment.scripts.validate_env .env --installation --compose-file deployment/docker-compose.yml
$COMPOSE build
$COMPOSE --profile tools run --rm migrate
$COMPOSE --profile tools run --rm fixtures
$COMPOSE up -d backend nginx
$COMPOSE run --rm --entrypoint /bin/sh certbot /usr/local/bin/issue-certificate
$COMPOSE restart nginx
$COMPOSE up -d

domain=$(python3 -c 'from pathlib import Path; from deployment.scripts.validate_env import read_env; print(read_env(Path(".env"))["DOMAIN"])')
curl --fail --silent --show-error "https://${domain}/health/ready" >/dev/null
printf 'Interview Studio is ready at https://%s\n' "$domain"
