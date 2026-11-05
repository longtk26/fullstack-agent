#!/bin/sh
set -e
if [ "${1:-}" = "worker" ]; then  # Story 10.6: the job worker, from the same image (the app migrates)
  exec python -m src.worker
fi
alembic upgrade head
if [ -n "$SEED_FILE" ] && [ -f "$SEED_FILE" ]; then
  python -m scripts.seed "$SEED_FILE"
fi
exec fastapi run src/main.py --host 0.0.0.0 --port "${PORT:-8000}"
