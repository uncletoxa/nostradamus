import os
import sys
import urllib.request
import urllib
from bs4 import BeautifulSoup
import django

# Set up django env
sys.path.append("../../")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nostradamus.settings")
django.setup()

from predictions.models import Coefficient, OddMap
from matches.models import Match
from django.utils.timezone import localtime, now


def update_odds(odd_map) -> None:
    """Updating coefficient for single match using given odds map.
    :param odd_map: OddMap instance
    :return:
    """
    url_fabric = 'https://sports.bwin.com/en/sports/events/'
    result_part = odd_map['result_url_part']
    score_part = odd_map['score_url_part']

    url_score = url_fabric + score_part
    page = urllib.request.urlopen(url_score)
    soup = BeautifulSoup(page, 'html.parser')
    odds = soup.findAll('button', attrs={
        'class': 'no-uniform mb-option-button__button mb-option-button__button--'})

    score_odds = {}
    for odd in odds:
        score, odd_value = odd.text.strip('\n').split('\n')
        score_odds[score] = float(odd_value)
        if 'Any other score' in odd.text:
            break

    url_result = url_fabric + result_part
    page = urllib.request.urlopen(url_result)
    soup = BeautifulSoup(page, 'html.parser')
    wins = soup.findAll('td', attrs={
        'class': 'mb-option-button rounded mb-option-button--3-way'})
    draw = soup.find('td', attrs={
        'class': 'mb-option-button rounded mb-option-button--3-way-draw'})

    results = {}
    teams = {odd_map['match_id__home_team']: 'home_team',
             'X': 'tie',
             odd_map['match_id__guest_team']: 'guest_team'}

    for win in wins:
        team, odd = win.text.strip('\n').split('\n')
        results[teams[team]] = float(odd)
    team, odd = draw.text.strip('\n').split('\n')
    results[teams[team]] = float(odd)

    Coefficient.objects.create(
        match_id=Match(odd_map['match_id']),
        coef_ready=True,
        score=score_odds,
        home_win=results['home_team'],
        tie=results['tie'],
        guest_win=results['guest_team'],
        update_time=localtime(now()))


if __name__ == '__main__':
    odds = (OddMap.objects
            .filter(update_ready=True)
            .values('score_url_part',
                    'result_url_part',
                    'match_id',
                    'match_id__home_team',
                    'match_id__guest_team'))
    for odd_map in odds:
        update_odds(odd_map)
