#!/bin/bash
set -e

echo "Running Database migrations if any"
cd /app/models/db_schemes/minirag/
alembic upgrade head
cd /app
exec "$@"

