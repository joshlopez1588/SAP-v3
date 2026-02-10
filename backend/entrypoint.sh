#!/usr/bin/env sh
set -e

cd /app/backend

echo "[entrypoint] Running database migrations (alembic upgrade head)..."

attempt=0
max_attempts="${DB_MIGRATION_MAX_ATTEMPTS:-30}"
sleep_seconds="${DB_MIGRATION_SLEEP_SECONDS:-2}"

until alembic upgrade head; do
  attempt=$((attempt + 1))
  if [ "$attempt" -ge "$max_attempts" ]; then
    echo "[entrypoint] Migration failed after $attempt attempts; exiting."
    exit 1
  fi
  echo "[entrypoint] Migration failed; retrying in ${sleep_seconds}s ($attempt/$max_attempts)..."
  sleep "$sleep_seconds"
done

echo "[entrypoint] Migrations complete."

# Optional seed hooks (idempotent). Keep disabled by default.
if [ "${SEED_FEDLINK_STARTER:-0}" = "1" ]; then
  echo "[entrypoint] Seeding Fedlink starter data..."
  python -m app.scripts.seed_fedlink_starter || true
fi

echo "[entrypoint] Starting server..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"

