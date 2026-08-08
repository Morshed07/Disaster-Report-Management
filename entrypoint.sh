#!/bin/sh
set -e

# Wait for PostgreSQL database connection if configured
if [ "$POSTGRES_HOST" ]; then
    echo "Waiting for PostgreSQL database at $POSTGRES_HOST:${POSTGRES_PORT:-5432}..."
    while ! nc -z "$POSTGRES_HOST" "${POSTGRES_PORT:-5432}"; do
        sleep 1
    done
    echo "PostgreSQL database is ready and accepting connections."
fi

# If the command is running gunicorn (web server), apply database migrations and collect static files
case "$1" in
    *gunicorn*)
        echo "Applying database migrations..."
        python manage.py migrate --noinput

        echo "Collecting static files..."
        python manage.py collectstatic --noinput
        ;;
esac

exec "$@"
