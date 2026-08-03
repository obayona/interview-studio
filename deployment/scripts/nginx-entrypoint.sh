#!/bin/sh
set -eu

runtime_dir=/var/run/interview-studio-tls
live_dir="/etc/letsencrypt/live/${DOMAIN}"
mkdir -p "$runtime_dir" /etc/nginx/conf.d
rm -f /var/log/nginx/access.log /var/log/nginx/error.log
touch /var/log/nginx/access.log /var/log/nginx/error.log
chown -R nginx:nginx "$runtime_dir" /etc/nginx/conf.d /var/log/nginx
tail -F /var/log/nginx/access.log /var/log/nginx/error.log &

if [ ! -s "$runtime_dir/fullchain.pem" ] || [ ! -s "$runtime_dir/privkey.pem" ]; then
  openssl req -x509 -nodes -newkey rsa:2048 -days 1 \
    -subj "/CN=${DOMAIN}" \
    -keyout "$runtime_dir/privkey.pem" \
    -out "$runtime_dir/fullchain.pem" >/dev/null 2>&1
fi
chown nginx:nginx "$runtime_dir"/*.pem
chmod 0600 "$runtime_dir/privkey.pem"

envsubst '${DOMAIN}' \
  < /etc/nginx/templates/default.conf.template \
  > /etc/nginx/conf.d/default.conf

certificate_fingerprint() {
  if [ -s "$live_dir/fullchain.pem" ] && [ -s "$live_dir/privkey.pem" ]; then
    sha256sum "$live_dir/fullchain.pem" "$live_dir/privkey.pem" | sha256sum | cut -d ' ' -f 1
  fi
}

watch_certificates() {
  current=""
  while sleep 300; do
    next="$(certificate_fingerprint || true)"
    if [ -n "$next" ] && [ "$next" != "$current" ]; then
      cp -L "$live_dir/fullchain.pem" "$runtime_dir/fullchain.pem.new"
      cp -L "$live_dir/privkey.pem" "$runtime_dir/privkey.pem.new"
      mv "$runtime_dir/fullchain.pem.new" "$runtime_dir/fullchain.pem"
      mv "$runtime_dir/privkey.pem.new" "$runtime_dir/privkey.pem"
      chmod 0600 "$runtime_dir/privkey.pem"
      current="$next"
      nginx -s reload
    fi
  done
}

if [ -s "$live_dir/fullchain.pem" ] && [ -s "$live_dir/privkey.pem" ]; then
  cp -L "$live_dir/fullchain.pem" "$runtime_dir/fullchain.pem"
  cp -L "$live_dir/privkey.pem" "$runtime_dir/privkey.pem"
  chown nginx:nginx "$runtime_dir"/*.pem
  chmod 0600 "$runtime_dir/privkey.pem"
fi

watch_certificates &
exec su-exec nginx nginx -g 'daemon off;'
