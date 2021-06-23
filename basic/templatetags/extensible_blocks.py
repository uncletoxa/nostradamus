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
    users = User.objects.filter(is_superuser=False)
    if live_standings:
        matches_queryset = Match.objects.filter(status__in=['IN_PLAY', 'PAUSED', 'FINISHED'])
    else:
        matches_queryset = Match.objects.filter(status='FINISHED')
    standings = []
    for user in users:
        total_pts, result_pts, score_pts = 0, 0, 0
        results_data = get_user_results_by_matches(user.id, matches_queryset)
        for match_data in results_data.values():
            result_pts += 0 if match_data['result_bet'] is None else match_data['result_bet']
            score_pts += 0 if match_data['score_bet'] is None else match_data['score_bet']
        standings.append({'user': user,
                          'total_points': round(result_pts + score_pts, 2),
                          'result_points': round(result_pts, 2),
                          'score_points': round(score_pts, 2)})
    return {'results': sorted(standings, key=lambda item: item['total_points'], reverse=True)}


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
