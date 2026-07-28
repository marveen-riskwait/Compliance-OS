#!/usr/bin/env bash
# Boot sequence: Fly does NOT run migrations for us, so we do it here, then seed
# the (fictitious) demo data and start the server. All steps are idempotent.
set -e
cd /app
export FLASK_APP=src/app.py PYTHONPATH=/app/src

echo "▸ Applying database migrations…"
flask db upgrade

echo "▸ Syncing RBAC (permissions + system roles)…"
flask sync-rbac || true

echo "▸ Seeding demonstration data (idempotent, fictitious only)…"
flask seed-demo || true

echo "▸ Loading sample sanctions lists for screening…"
flask ingest-watchlists --sample || true

echo "▸ Starting Compliance OS on :8080"
# SQLite is a single writer → one worker; threads give concurrency, and the
# threading async-mode of Flask-SocketIO serves WebSocket via simple-websocket.
exec gunicorn --chdir /app/src \
     --worker-class gthread --workers 1 --threads 8 \
     --bind 0.0.0.0:8080 --timeout 120 --access-logfile - \
     app:app
