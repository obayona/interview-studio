FROM node:24-alpine AS frontend-build

ENV PNPM_HOME="/pnpm" \
    PATH="/pnpm:$PATH"

RUN corepack enable && corepack prepare pnpm@11.12.0 --activate

WORKDIR /build/frontend
COPY frontend/package.json frontend/pnpm-lock.yaml frontend/pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile

COPY frontend/ ./
RUN pnpm run build

FROM nginxinc/nginx-unprivileged:1.29-alpine AS runtime

USER root
RUN apk add --no-cache gettext openssl su-exec

COPY --from=frontend-build /build/frontend/dist /usr/share/nginx/html
COPY deployment/nginx/default.conf.template /etc/nginx/templates/default.conf.template
COPY deployment/scripts/nginx-entrypoint.sh /usr/local/bin/interview-studio-nginx

RUN chmod 0755 /usr/local/bin/interview-studio-nginx \
    && rm -f /etc/nginx/conf.d/default.conf

EXPOSE 8080 8443

ENTRYPOINT ["/usr/local/bin/interview-studio-nginx"]
