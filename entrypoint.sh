#!/bin/sh
set -e

# Wait for PostgreSQL database connection if POSTGRES_HOST is set
if [ -n "$POSTGRES_HOST" ]; then
    echo "Waiting for PostgreSQL database at $POSTGRES_HOST:${POSTGRES_PORT:-5432}..."
    until python -c "import socket; s = socket.socket(); s.settimeout(2); s.connect(('$POSTGRES_HOST', int('${POSTGRES_PORT:-5432}'))); s.close()" 2>/dev/null; do
        echo "Postgres not ready yet, sleeping 2 seconds..."
        sleep 2
    done
    echo "PostgreSQL database is ready!"
fi

# Ensure static and media directories exist
mkdir -p /app/staticfiles /app/media

# If running gunicorn (web server), apply database migrations and collect static files
case "$1" in
    *gunicorn*)
        echo "Applying database migrations..."
        python manage.py migrate --noinput || true

        echo "Collecting static files..."
        python manage.py collectstatic --noinput --clear || python manage.py collectstatic --noinput || true
        ;;
esac

exec "$@"
