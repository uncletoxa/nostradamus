#!/bin/sh
set -e

echo "Score updater starting."

while true; do
    python -m updater_tools.score_updater
    sleep 60
done
