import datetime


COMPETITION_START_DATE_UTC = datetime.datetime(2026, 6, 11, 19, 0, 0, tzinfo=datetime.timezone.utc)

from decimal import Decimal
from matches.models import Match
from predictions.models import Prediction, WinnerPrediction
from django import template
from django.contrib.auth.models import User
from basic.utils import last_prediction, get_user_results_by_matches, get_funny_stats_context

register = template.Library()


@register.inclusion_tag('includes/champ_standings.html', takes_context=True)
def champ_standings(context):
    champ_predictions = WinnerPrediction.objects.exclude(
        user_id__profile__previous_participant=True).order_by('id')
    submissions_closed = datetime.datetime.now(datetime.timezone.utc) > COMPETITION_START_DATE_UTC
    request = context.get('request')
    current_user = request.user if request else None
    return {'champ_predictions': champ_predictions, 'submissions_closed': submissions_closed,
            'current_user': current_user}


@register.inclusion_tag('includes/cup_standings.html', takes_context=True)
def cup_standings(context, long_standings=False, live_standings=False):
    def zero_if_none(val):
        return val if val is not None else Decimal(0)

    users = User.objects.filter(is_superuser=False).exclude(profile__previous_participant=True)
    if live_standings:
        matches_queryset = Match.objects.filter(status__in=['IN_PLAY', 'PAUSED', 'FINISHED'])
    else:
        matches_queryset = Match.objects.filter(status='FINISHED')
    standings = {}

    for user in users:
        result_bet = Decimal(0)
        score_bet = Decimal(0)
        winner_points = Decimal(0)

        user_champion = WinnerPrediction.objects.filter(user_id=user.id).first()
        if user_champion and user_champion.prediction_id.is_winner:
            winner_points = Decimal(str(user_champion.prediction_id.coef))

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

    request = context.get('request')
    current_user = request.user if request else None
    return {'results': dict(sorted(standings.items(), key=lambda x: x[1]['total_points'], reverse=True)),
            'long_standings': long_standings,
            'current_user': current_user}


@register.inclusion_tag('includes/next_matches.html')
def next_matches(cur_user):
    predictions = {}
    matches = Match.objects.filter(status='SCHEDULED').order_by('start_time')[:10]
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


@register.inclusion_tag('includes/funny_stats_panel.html')
def funny_stats_panel():
    return get_funny_stats_context()


@register.simple_tag
def get_live_matches():
    return Match.objects.filter(status__in=['IN_PLAY', 'PAUSED'])


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)
