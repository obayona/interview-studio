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

ARG APP_VERSION=development
ARG SOURCE_REVISION=unknown
LABEL org.opencontainers.image.title="Interview Studio local web" \
    org.opencontainers.image.version="$APP_VERSION" \
    org.opencontainers.image.revision="$SOURCE_REVISION" \
    org.opencontainers.image.source="https://github.com/obayona/interview-studio"

COPY --from=frontend-build /build/frontend/dist /usr/share/nginx/html
COPY deployment/local/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 8080
