#! /usr/bin/env python
import http.client
import json
import os
import django
import sys
import logging
from datetime import timedelta
from decouple import config

sys.path.append("../../")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nostradamus.settings")
django.setup()

from django.db.models import Q
from django.utils.timezone import now
from matches.models import Match

API_HOST = 'api.football-data.org'
COMPETITION = 'WC'

# football-data.org v4 team names → our DB names
NAME_MAP = {
    'Bosnia-Herzegovina': 'Bosnia and Herzegovina',
    'Cape Verde Islands': 'Cape Verde',
    'Congo DR': 'DR Congo',
    'Czechia': 'Czech Republic',
}

# v4 API statuses → our model statuses
STATUS_MAP = {
    'IN_PLAY': Match.IN_PLAY,
    'PAUSED': Match.PAUSED,
    'FINISHED': Match.FINISHED,
    'TIMED': Match.SCHEDULED,
    'SCHEDULED': Match.SCHEDULED,
}


def fetch_competition_matches(token, date_from, date_to):
    conn = http.client.HTTPSConnection(API_HOST)
    path = '/v4/competitions/{}/matches?dateFrom={}&dateTo={}'.format(
        COMPETITION, date_from, date_to)
    conn.request('GET', path, headers={'X-Auth-Token': token})
    resp = conn.getresponse()
    if resp.status != 200:
        raise RuntimeError('API error {}: {}'.format(resp.status, resp.reason))
    return json.loads(resp.read().decode())['matches']


def main():
    token = config('FOOTBALL_DATA_API_KEY')
    current_time = now()

    # Fetch matches for yesterday–tomorrow to cover all timezones and late-running games
    date_from = (current_time - timedelta(days=1)).date().isoformat()
    date_to = (current_time + timedelta(days=1)).date().isoformat()

    api_matches = fetch_competition_matches(token, date_from, date_to)
    logging.info('Fetched {} matches from API ({} to {})'.format(
        len(api_matches), date_from, date_to))

    # Build lookup by normalised team name pair
    api_lookup = {}
    for m in api_matches:
        home = NAME_MAP.get(m['homeTeam']['name'], m['homeTeam']['name'])
        away = NAME_MAP.get(m['awayTeam']['name'], m['awayTeam']['name'])
        api_lookup[(home, away)] = m

    # DB matches that need attention:
    #   - currently live (IN_PLAY or PAUSED)
    #   - scheduled to start within the next 5 min (catch the kickoff transition)
    #   - started up to 3h ago and still not FINISHED (handles restarts / delays)
    window_start = current_time - timedelta(hours=3)
    window_end = current_time + timedelta(minutes=5)

    db_matches = Match.objects.select_related('home_team', 'guest_team').filter(
        Q(status__in=[Match.IN_PLAY, Match.PAUSED]) |
        Q(status=Match.SCHEDULED, start_time__range=(window_start, window_end)))

    if not db_matches.exists():
        logging.info('No active matches to update.')
        return

    updated = 0
    for match in db_matches:
        key = (match.home_team.name, match.guest_team.name)
        api_match = api_lookup.get(key)
        if not api_match:
            logging.warning('No API data for {}'.format(key))
            continue

        api_status = STATUS_MAP.get(api_match['status'], Match.SCHEDULED)
        full_time = api_match.get('score', {}).get('fullTime', {})
        api_home_score = full_time.get('home')
        api_away_score = full_time.get('away')

        changed = []

        if match.status != api_status:
            logging.info('{}: status {} -> {}'.format(match, match.status, api_status))
            match.status = api_status
            changed.append('status')

        # Update score whenever the API provides it (live or final)
        if api_home_score is not None and api_away_score is not None:
            if match.home_score != api_home_score or match.guest_score != api_away_score:
                logging.info('{}: score {}:{}'.format(match, api_home_score, api_away_score))
                match.home_score = api_home_score
                match.guest_score = api_away_score
                changed.extend(['home_score', 'guest_score'])

        if changed:
            match.save(update_fields=changed)
            updated += 1

    logging.info('Updated {} match(es).'.format(updated))


if __name__ == '__main__':
    logging.basicConfig(
        format='%(asctime)s | %(levelname)s | %(message)s',
        level=logging.INFO)
    main()
