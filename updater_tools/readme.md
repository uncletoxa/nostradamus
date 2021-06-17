# Score Updater

Live score updater for [live score widget](../templates/includes/live_matches.html) support.

## Deployment

0. Get the [foolball-data.org](https://www.football-data.org) token. 10 calls/minute in free tier is enough.
1. Add ```LIVE_RESULTS_API_TOKEN=<your token>``` to `.env` file containing 
2. Setup cron minutely update job in cron:
	* open cron `$ crontab -e`
	* add `* * * * * cd /<path to project folder root>/ && venv/bin/python -m updater_tools.score_updater > /<path to logs folder>/score_updater.log 2>&1`
