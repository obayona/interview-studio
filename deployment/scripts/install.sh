#!/bin/sh
set -eu

repository_root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
cd "$repository_root"

python3 -m deployment.scripts.validate_env .env --installation
docker compose build
docker compose --profile tools run --rm migrate
docker compose --profile tools run --rm fixtures
docker compose up -d backend nginx
docker compose run --rm --entrypoint /bin/sh certbot /usr/local/bin/issue-certificate
docker compose restart nginx
docker compose up -d

domain=$(python3 -c 'from pathlib import Path; from deployment.scripts.validate_env import read_env; print(read_env(Path(".env"))["DOMAIN"])')
curl --fail --silent --show-error "https://${domain}/health/ready" >/dev/null
printf 'Interview Studio is ready at https://%s\n' "$domain"
