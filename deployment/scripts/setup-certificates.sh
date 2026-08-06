#!/bin/sh
set -eu

repository_root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
cd "$repository_root"

COMPOSE="docker compose --project-directory . -f deployment/docker-compose.yml"

python3 -m deployment.scripts.validate_env .env --compose-file deployment/docker-compose.yml
$COMPOSE up -d backend nginx
$COMPOSE run --rm --entrypoint /bin/sh certbot -c 'certbot certonly --webroot --webroot-path /var/www/certbot --non-interactive --agree-tos --keep-until-expiring --email "$LETSENCRYPT_EMAIL" --cert-name "$DOMAIN" -d "$DOMAIN"'
$COMPOSE up -d certbot
$COMPOSE restart nginx

domain=$(python3 -c 'from pathlib import Path; from deployment.scripts.validate_env import read_env; print(read_env(Path(".env"))["DOMAIN"])')
curl -k --fail --silent --show-error "https://${domain}/health/ready" >/dev/null
printf 'Let'"'"'s Encrypt certificate active for https://%s\n' "$domain"
