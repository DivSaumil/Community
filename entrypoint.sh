#!/bin/bash
# ─────────────────────────────────────────────────────────────────
# entrypoint.sh — Container startup script
#
# Responsibilities:
#   1. Wait for PostgreSQL to be accepting connections
#      (docker-compose health checks should handle this, but we
#       add a guard here for safety / standalone runs)
#   2. Run Alembic database migrations
#   3. Start the Uvicorn server with the correct worker count
# ─────────────────────────────────────────────────────────────────
set -euo pipefail

echo "────────────────────────────────────────"
echo "  🚀  Community API — Starting up"
echo "────────────────────────────────────────"

# ── 1. Wait for PostgreSQL ───────────────────────────────────────
# Extract host and port from DATABASE_URL for the readiness check
DB_HOST=$(python -c "
import os, urllib.parse
url = os.environ.get('DATABASE_URL', '')
parsed = urllib.parse.urlparse(url)
print(parsed.hostname or 'db')
")
DB_PORT=$(python -c "
import os, urllib.parse
url = os.environ.get('DATABASE_URL', '')
parsed = urllib.parse.urlparse(url)
print(parsed.port or 5432)
")

echo "⏳  Waiting for PostgreSQL at ${DB_HOST}:${DB_PORT}..."

MAX_RETRIES=30
RETRY_INTERVAL=2
retries=0

until python -c "
import socket, sys
try:
    s = socket.create_connection(('${DB_HOST}', ${DB_PORT}), timeout=2)
    s.close()
    sys.exit(0)
except Exception:
    sys.exit(1)
" 2>/dev/null; do
    retries=$((retries + 1))
    if [ "$retries" -ge "$MAX_RETRIES" ]; then
        echo "❌  PostgreSQL did not become ready in time. Exiting."
        exit 1
    fi
    echo "   Attempt ${retries}/${MAX_RETRIES} — retrying in ${RETRY_INTERVAL}s..."
    sleep "$RETRY_INTERVAL"
done

echo "✅  PostgreSQL is ready."

# ── 2. Run Alembic Migrations ────────────────────────────────────
echo "⚙️   Running database migrations..."
alembic upgrade head
echo "✅  Migrations complete."

# ── 3. Start Uvicorn ─────────────────────────────────────────────
# Default to 3 workers if WORKERS is not set.
# Recommended: (2 × vCPU) + 1  →  3 for a 1-vCPU Droplet
WORKERS="${WORKERS:-3}"

echo "🌐  Starting Uvicorn with ${WORKERS} worker(s)..."
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers "$WORKERS" \
    --proxy-headers \
    --forwarded-allow-ips="*" \
    --log-level info \
    --access-log
