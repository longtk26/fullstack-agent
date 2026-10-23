#!/bin/sh
set -e
alembic upgrade head
if [ -n "$SEED_FILE" ] && [ -f "$SEED_FILE" ]; then
  python -m scripts.seed "$SEED_FILE"
fi
exec fastapi run src/main.py --host 0.0.0.0 --port "${PORT:-8000}"
