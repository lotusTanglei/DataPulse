FROM node:22-slim AS web

WORKDIR /src
RUN corepack enable

COPY package.json pnpm-workspace.yaml pnpm-lock.yaml ./
COPY apps/web/package.json apps/web/package.json
COPY packages/schema/package.json packages/schema/package.json
RUN pnpm install --frozen-lockfile

COPY apps/web apps/web
COPY packages/schema packages/schema
RUN pnpm build:web

FROM python:3.13-slim AS runtime

WORKDIR /app
RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
COPY apps/server apps/server
RUN apt-get update \
    && apt-get install --yes --no-install-recommends build-essential \
    && uv sync --frozen --no-dev --package datapulse-server \
    && apt-get purge --yes --auto-remove build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY --from=web /src/apps/web/dist /app/static
RUN useradd --create-home --uid 10001 datapulse \
    && mkdir -p /data/sources \
    && chown -R datapulse:datapulse /data
COPY --chown=datapulse:datapulse apps/server/docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod 0555 /app/docker-entrypoint.sh

USER datapulse
ENV DATAPULSE_ENVIRONMENT=production \
    DATAPULSE_STATIC_DIR=/app/static \
    DATAPULSE_DATA_DIR=/data

EXPOSE 8000
VOLUME ["/data"]

ENTRYPOINT ["/app/docker-entrypoint.sh"]
