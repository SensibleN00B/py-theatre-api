#!/usr/bin/env sh
set -e

python manage.py wait_for_db

echo "Applying migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

# shellcheck disable=SC2145
echo "Starting app: $@"
exec "$@"