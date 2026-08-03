#!/bin/sh
set -eu

repository_root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
cd "$repository_root"
python3 -m deployment.scripts.validate_env .env
docker compose --profile tools run --rm backup
