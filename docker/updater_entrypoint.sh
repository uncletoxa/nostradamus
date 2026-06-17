#!/bin/sh
set -e

echo "Score updater starting."

while true; do
    python -m updater_tools.score_updater
    python manage.py send_prediction_reminders --hours 3
    sleep 60
done
