#! /usr/bin/env python
import http.client
import json
import os
import django
import sys
import datetime
import logging
from decouple import config

# Set up django env
sys.path.append("../../")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nostradamus.settings")
django.setup()

from matches.models import Match
from django.utils.timezone import now


def update_scores(matches):
    LIVE_RESULTS_API_TOKEN = config('LIVE_RESULTS_API_TOKEN')
    connection = http.client.HTTPConnection('api.football-data.org')
    headers = {'X-Auth-Token': LIVE_RESULTS_API_TOKEN}

    for match in matches:
        connection.request('GET', '/v2/matches/{}'.format(match.fixture_id),
                           None, headers)
        response = connection.getresponse()
        logging.info('Running request for match {}'.format(match))
        if response.status == 200:
            resp = json.loads(response.read().decode())
            logging.info('Loading results: {}'.format(resp))
            match.status = resp['match']['status']
            match.home_score = resp['match']['score']['fullTime']['homeTeam']
            match.guest_score = resp['match']['score']['fullTime']['awayTeam']
            match.save()
        else:
            logging.error('Invalid request. Status: {}. Reason: {}.'.format(
                response.status, response.reason))


def main():
    live_matches = Match.objects.filter(
        start_time__range=(now() - datetime.timedelta(hours=4), now()))

    if len(live_matches) == 0:
        logging.info('Nothing to update.')
    else:
        update_scores(live_matches)


if __name__ == '__main__':
    logging.basicConfig(
        format='%(asctime)s | %(levelname)s | %(message)s',
        level=logging.INFO)
    main()
