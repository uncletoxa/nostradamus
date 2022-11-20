import datetime


from matches.models import Match
from predictions.models import Prediction, WinnerPrediction
from django import template
from django.contrib.auth.models import User
from basic.utils import last_prediction, get_user_results_by_matches

register = template.Library()


@register.inclusion_tag('includes/champ_standings.html')
def champ_standings():
    champ_predictions = WinnerPrediction.objects.all().order_by('id')
    return {'champ_predictions': champ_predictions}


@register.inclusion_tag('includes/cup_standings.html')
def cup_standings(long_standings=False, live_standings=False):
    def zero_if_none(val):
        return val if val is not None else 0
    
    users = User.objects.filter(is_superuser=False)
    if live_standings:
        matches_queryset = Match.objects.filter(status__in=['IN_PLAY', 'PAUSED', 'FINISHED'])
    else:
        matches_queryset = Match.objects.filter(status='FINISHED')
    standings = {}

    for user in users:
        total_points = 0
        result_points = 0
        score_points = 0
        high_score_points = 0
        block_bonus_points = 0
        penalty_points = 0

        results_data = get_user_results_by_matches(user.id, matches_queryset)
        for match_data in results_data.values():
            result_points += zero_if_none(match_data['result_points'])
            score_points += zero_if_none(match_data['score_points'])
            high_score_points += zero_if_none(match_data['high_score_points'])
            block_bonus_points += zero_if_none(match_data['block_bonus_points'])
            penalty_points += zero_if_none(match_data['penalty_points'])
            total_points = sum([result_points, score_points, high_score_points, block_bonus_points, penalty_points])
        standings.update({user: {
            'total_points': total_points,
            'result_points': result_points,
            'score_points': score_points,
            'high_score_points': high_score_points,
            'block_bonus_points': block_bonus_points,
            'penalty_points': penalty_points}})
    return {'results': standings, 'long_standings': long_standings}


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
