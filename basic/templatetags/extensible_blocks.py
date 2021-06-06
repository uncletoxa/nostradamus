import datetime
import pytz

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
def cup_standings(long_standings=False):
    def zero_if_none(val):
        return val if val is not None else 0
    users = User.objects.filter(is_staff=False)
    matches_queryset = (Match.objects.filter(home_score__isnull=False) |
                        Match.objects.filter(guest_score__isnull=False))
    standings = {}

    for user in users:
        total_points = 0
        results_data = get_user_results_by_matches(user.id, matches_queryset)
        for match_data in results_data.values():
            total_points += sum(list(filter(
                None, [match_data['result_bet'], match_data['score_bet']])))
        standings.update({user: total_points})
    return {'results': standings}


@register.inclusion_tag('includes/next_matches.html')
def next_matches(cur_user):
    predictions = {}
    matches = Match.objects.filter(start_time__range=(
        datetime.datetime.now(pytz.UTC),
        datetime.datetime.now(pytz.UTC) + datetime.timedelta(days=30)
    ))
    for match in matches:
        last_pred = last_prediction(
            Prediction.objects.filter(match_id_id=match.match_id,
                                      user_id=cur_user))
        predictions.update({match: next(iter(last_pred), None)})

    return {'predictions': predictions, 'cur_time': datetime.datetime.now()}


@register.inclusion_tag('includes/live_matches.html')
def live_matches():
    matches = Match.objects.filter(is_live=True)
    return {'live_matches': matches}