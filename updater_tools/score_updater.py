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


logging.basicConfig(format='%(asctime)s | %(levelname)s | %(message)s', level=logging.INFO)

LIVE_RESULTS_API_TOKEN = config('LIVE_RESULTS_API_TOKEN')
connection = http.client.HTTPConnection('api.football-data.org')
headers = {'X-Auth-Token': LIVE_RESULTS_API_TOKEN, 'X-Response-Control': 'minified' }

live_matches = Match.objects.filter(
    start_time__range=(now() - datetime.timedelta(hours=2), now()))

for match in live_matches:
    connection.request('GET', '/v1/fixtures/{}'.format(match.fixture_id),
                       None, headers)
    response = connection.getresponse()
    logging.info('Running request for match {}'.format(match))
    if response.status == 200:
        resp = json.loads(response.read().decode())
        logging.info('Loading results: {}'.format(resp))
        match.home_score = resp['fixture']['result']['goalsHomeTeam']
        match.guest_score = resp['fixture']['result']['goalsAwayTeam']
        match.save()
    else:
        logging.warning('Invalid request. Status: {}. Reason: {}.'.format(
            response.status, response.reason))
