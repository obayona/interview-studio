#!/bin/sh
set -eu

staging=""
force=""
if [ "${LETSENCRYPT_STAGING:-false}" = "true" ]; then
  staging="--staging"
else
  # Replaces a staging certificate when the installer is promoted to production.
  force="--force-renewal"
fi

# Word splitting is intentional for the optional flag, which is controlled above.
# shellcheck disable=SC2086
exec certbot certonly \
  --webroot \
  --webroot-path /var/www/certbot \
  --non-interactive \
  --agree-tos \
  --keep-until-expiring \
  --email "$LETSENCRYPT_EMAIL" \
  --cert-name "$DOMAIN" \
  -d "$DOMAIN" \
  $staging \
  $force
