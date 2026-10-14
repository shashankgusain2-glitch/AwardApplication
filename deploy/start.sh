#!/bin/sh
# Container start-up for Render, Railway or any Docker host.
#  - PORT: set by the platform (default 8000)
#  - RUN_MIGRATIONS_ON_START=true: apply database migrations before starting (works on free plans
#    that have no separate release step; safe to run on every start)
set -e
if [ "${RUN_MIGRATIONS_ON_START:-false}" = "true" ]; then
    python manage.py migrate --noinput
fi
exec gunicorn config.wsgi:application \
    --bind "0.0.0.0:${PORT:-8000}" \
    --workers "${WEB_CONCURRENCY:-3}" \
    --timeout 60 \
    --access-logfile - --error-logfile -
