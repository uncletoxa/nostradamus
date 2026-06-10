import datetime


COMPETITION_START_DATE_UTC = datetime.datetime(2026, 6, 11, 19, 0, 0, tzinfo=datetime.timezone.utc)

from matches.models import Match
from predictions.models import Prediction, WinnerPrediction
from accounts.models import TeamSupporter
from django import template
from django.contrib.auth.models import User
from basic.utils import last_prediction, get_user_results_by_matches

register = template.Library()


@register.inclusion_tag('includes/champ_standings.html')
def champ_standings():
    champ_predictions = WinnerPrediction.objects.exclude(
        user_id__profile__previous_participant=True).order_by('id')
    submissions_closed = datetime.datetime.now(datetime.timezone.utc) > COMPETITION_START_DATE_UTC
    return {'champ_predictions': champ_predictions, 'submissions_closed': submissions_closed}


@register.inclusion_tag('includes/champ_supporters.html')
def champ_supporters():
    team_champ_supporters = TeamSupporter.objects.all().order_by('id')
    submissions_closed = datetime.datetime.now(datetime.timezone.utc) > COMPETITION_START_DATE_UTC
    return {'team_champ_supporters': team_champ_supporters, 'submissions_closed': submissions_closed}


@register.inclusion_tag('includes/cup_standings.html')
def cup_standings(long_standings=False, live_standings=False):
    def zero_if_none(val):
        return val if val is not None else 0

    users = User.objects.filter(is_superuser=False).exclude(profile__previous_participant=True)
    if live_standings:
        matches_queryset = Match.objects.filter(status__in=['IN_PLAY', 'PAUSED', 'FINISHED'])
    else:
        matches_queryset = Match.objects.filter(status='FINISHED')
    standings = {}

    for user in users:
        result_bet = 0
        score_bet = 0
        winner_points = 0

        user_champion = WinnerPrediction.objects.filter(user_id=user.id).first()
        if user_champion and user_champion.prediction_id.is_winner:
            winner_points = user_champion.prediction_id.coef

        results_data = get_user_results_by_matches(user.id, matches_queryset)
        for match_data in results_data.values():
            result_bet += zero_if_none(match_data['result_bet'])
            score_bet += zero_if_none(match_data['score_bet'])
        total_points = result_bet + score_bet + winner_points
        standings.update({user: {
            'total_points': total_points,
            'result_bet': result_bet,
            'score_bet': score_bet,
            'winner_points': winner_points}})

    return {'results': dict(sorted(standings.items(), key=lambda x: x[1]['total_points'], reverse=True)),
            'long_standings': long_standings}


@register.inclusion_tag('includes/next_matches.html')
def next_matches(cur_user):
    predictions = {}
    matches = Match.objects.filter(status='SCHEDULED')
    for match in matches:
        last_pred = last_prediction(
            Prediction.objects.filter(match_id_id=match.match_id,
                                      user_id=cur_user))
        predictions.update({match: next(iter(last_pred), None)})

    return {'predictions': predictions, 'cur_time': datetime.datetime.now()}


@register.inclusion_tag('includes/live_matches.html')
def live_matches():
    matches = Match.objects.filter(status__in=['IN_PLAY', 'PAUSED'])
    return {'live_matches': matches}


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)
