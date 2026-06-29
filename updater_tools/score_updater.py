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

# v4 API statuses → our model statuses
STATUS_MAP = {
    'IN_PLAY': Match.IN_PLAY,
    'PAUSED': Match.PAUSED,
    'FINISHED': Match.FINISHED,
    'TIMED': Match.SCHEDULED,
    'SCHEDULED': Match.SCHEDULED,
}


def fetch_match(token, fixture_id):
    conn = http.client.HTTPSConnection(API_HOST)
    conn.request('GET', '/v4/matches/{}'.format(fixture_id),
                 headers={'X-Auth-Token': token, 'X-Api-Version': 'v4.1'})
    resp = conn.getresponse()
    if resp.status != 200:
        raise RuntimeError('API error {}: {}'.format(resp.status, resp.reason))
    return json.loads(resp.read().decode())


def main():
    token = config('FOOTBALL_DATA_API_KEY')
    current_time = now()

    # DB matches that need attention:
    #   - currently live (IN_PLAY or PAUSED)
    #   - scheduled to start within the next 5 min (catch the kickoff transition)
    #   - scheduled with start_time in the past (catches missed transitions)
    db_matches = Match.objects.select_related('home_team', 'guest_team').filter(
        Q(status__in=[Match.IN_PLAY, Match.PAUSED]) |
        Q(status=Match.SCHEDULED, start_time__lte=current_time + timedelta(minutes=5))
    ).exclude(fixture_id__isnull=True)

    if not db_matches.exists():
        logging.info('No active matches to update.')
        return

    logging.info('Checking {} match(es).'.format(db_matches.count()))

    updated = 0
    for match in db_matches:
        try:
            api_match = fetch_match(token, match.fixture_id)
        except RuntimeError as e:
            logging.error('{}: {}'.format(match, e))
            continue

        api_status = STATUS_MAP.get(api_match['status'], Match.SCHEDULED)
        score_data = api_match.get('score', {})
        duration = score_data.get('duration', 'REGULAR')
        api_minute = api_match.get('minute')
        api_injury_time = api_match.get('injuryTime')
        if api_status == Match.FINISHED:
            api_minute = None
        elif api_minute is not None and api_injury_time:
            api_minute = api_minute + api_injury_time

        # For penalty shootouts, fullTime includes penalty goals; use regularTime+extraTime instead
        if duration == 'PENALTY_SHOOTOUT':
            regular = score_data.get('regularTime', {})
            extra = score_data.get('extraTime', {})
            reg_home = regular.get('home')
            reg_away = regular.get('away')
            if reg_home is not None and reg_away is not None:
                api_home_score = reg_home + (extra.get('home') or 0)
                api_away_score = reg_away + (extra.get('away') or 0)
            else:
                api_home_score = None
                api_away_score = None
        else:
            full_time = score_data.get('fullTime', {})
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

        # Set home_to_advance for playoff matches decided by penalty shootout
        if match.is_playoff and duration == 'PENALTY_SHOOTOUT':
            winner = score_data.get('winner')
            if winner == 'HOME_TEAM':
                api_home_to_advance = True
            elif winner == 'AWAY_TEAM':
                api_home_to_advance = False
            else:
                api_home_to_advance = None
            if match.home_to_advance != api_home_to_advance:
                logging.info('{}: home_to_advance {} -> {}'.format(
                    match, match.home_to_advance, api_home_to_advance))
                match.home_to_advance = api_home_to_advance
                changed.append('home_to_advance')

        if match.current_minute != api_minute:
            match.current_minute = api_minute
            changed.append('current_minute')

        if changed:
            match.save(update_fields=changed)
            updated += 1

    logging.info('Updated {} match(es).'.format(updated))


if __name__ == '__main__':
    logging.basicConfig(
        format='%(asctime)s | %(levelname)s | %(message)s',
        level=logging.INFO)
    main()
