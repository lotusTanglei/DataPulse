#!/bin/sh
set -eu

uv run --no-sync alembic -c apps/server/alembic.ini upgrade head
exec uv run --no-sync uvicorn datapulse.app:app \
    --host 0.0.0.0 \
    --port 8000 \
    --proxy-headers \
    --forwarded-allow-ips "${DATAPULSE_FORWARDED_ALLOW_IPS:-127.0.0.1}"
