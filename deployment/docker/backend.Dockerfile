ARG FRONTEND_STAGE=frontend-empty

FROM busybox AS frontend-empty
RUN mkdir -p /build/frontend/dist

FROM node:24-alpine AS frontend-build

ENV PNPM_HOME="/pnpm" \
    PATH="/pnpm:$PATH"

RUN corepack enable && corepack prepare pnpm@11.12.0 --activate

WORKDIR /build/frontend
COPY frontend/package.json frontend/pnpm-lock.yaml frontend/pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile

COPY frontend/ ./
RUN pnpm run build

FROM ${FRONTEND_STAGE} AS frontend-source

FROM python:3.12-slim AS runtime

ARG APP_VERSION=development
ARG SOURCE_REVISION=unknown
LABEL org.opencontainers.image.title="Interview Studio backend" \
    org.opencontainers.image.version="$APP_VERSION" \
    org.opencontainers.image.revision="$SOURCE_REVISION" \
    org.opencontainers.image.source="https://github.com/obayona/interview-studio"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

RUN python -m venv /opt/venv \
    && useradd --create-home --uid 10001 --shell /usr/sbin/nologin interview-studio

WORKDIR /app

COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --requirement /tmp/requirements.txt

COPY --chown=interview-studio:interview-studio backend /app/backend

RUN apt-get update \
    && apt-get install -y --no-install-recommends nginx-light \
    && rm -rf /var/lib/apt/lists/*

COPY --from=frontend-source /build/frontend/dist /app/frontend

COPY deployment/nginx/nginx.conf /etc/nginx/nginx.conf
COPY deployment/nginx/local-default.conf /etc/nginx/conf.d/default.conf
COPY deployment/scripts/local-entrypoint.sh /usr/local/bin/interview-studio-local

RUN mkdir -p /data /secrets /backups \
    && chown interview-studio:interview-studio /data /secrets /backups \
    && chmod 0755 /usr/local/bin/interview-studio-local

USER interview-studio

EXPOSE 8000 8080

CMD ["python", "-m", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*"]
