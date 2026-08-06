#!/bin/sh
set -eu

mkdir -p /tmp/nginx

nginx -g 'daemon off;' &
nginx_pid=$!

python -m uvicorn backend.app.main:app \
  --host 127.0.0.1 --port 8000 \
  --proxy-headers --forwarded-allow-ips=* &
uvicorn_pid=$!

cleanup() {
  kill "$nginx_pid" "$uvicorn_pid" 2>/dev/null || true
  wait "$nginx_pid" 2>/dev/null || true
  wait "$uvicorn_pid" 2>/dev/null || true
}
trap cleanup TERM INT

if wait "$uvicorn_pid"; then
  status=0
else
  status=$?
fi
cleanup
exit "$status"
