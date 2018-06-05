#!/usr/bin/env bash

NAME="nostradamus"
DIR=/home/nostradamus/nostradamus
USER=az
GROUP=az
WORKERS=3
BIND=unix:/home/nostradamus/run/gunicorn.sock
DJANGO_SETTINGS_MODULE=nostradamus.settings
DJANGO_WSGI_MODULE=nostradamus.wsgi
LOG_LEVEL=error

cd $DIR
source /home/nostradamus/venv/bin/activate

export DJANGO_SETTINGS_MODULE=$DJANGO_SETTINGS_MODULE
export PYTHONPATH=$DIR:$PYTHONPATH

exec /home/az/nostradamus/venv/bin/gunicorn ${DJANGO_WSGI_MODULE}:application \
  --name $NAME \
  --workers $WORKERS \
  --user=$USER \
  --group=$GROUP \
  --bind=$BIND \
  --log-level=$LOG_LEVEL \
  --log-file=-
