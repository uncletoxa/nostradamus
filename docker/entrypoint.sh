#!/bin/sh
set -e
python manage.py compilemessages
python manage.py collectstatic --noinput
exec gunicorn nostradamus.wsgi:application --bind 0.0.0.0:8000 --workers 2 --log-file -
