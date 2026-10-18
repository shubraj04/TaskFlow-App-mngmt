#!/bin/sh
# Applies migrations and seeds demo data, then hands over to the given command.
set -e
python manage.py migrate --noinput
python manage.py seed_demo
exec "$@"
