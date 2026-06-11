# Score Updater

Live score updater using [football-data.org](https://www.football-data.org) v4 API.

Makes a **single batch API call** per run (fetches all competition matches for yesterday–tomorrow),
then updates only the matches that are currently active in the DB.

## What it does

- `SCHEDULED → IN_PLAY` when the API reports the match has kicked off
- `IN_PLAY → PAUSED` at half-time
- `PAUSED → IN_PLAY` for second half
- `IN_PLAY / PAUSED → FINISHED` at full time
- Updates `home_score` / `guest_score` whenever the API provides them (live + final)

## Deployment

1. Ensure `FOOTBALL_DATA_API_KEY=<token>` is in `.env` (10 calls/minute on free tier — fine for 1/min cron)
2. Add a minutely cron job:
   ```
   * * * * * cd /<path to project>/ && venv/bin/python -m updater_tools.score_updater >> /<path to logs>/score_updater.log 2>&1
   ```
