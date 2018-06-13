from django.shortcuts import render, get_object_or_404
from django.contrib.auth.models import User
from matches.models import Match
from predictions.models import WinnerPrediction
from basic.utils import get_user_results_by_matches


def results(request):
    matches = (Match.objects.filter(home_score__isnull=False) |
               Match.objects.filter(guest_score__isnull=False))
    return render(request, 'results_index.html',
                  {'matches_queryset': matches})


def user_result(request, user_id):
    user_champion = WinnerPrediction.objects.get(user_id=user_id)
    matches = (Match.objects.filter(home_score__isnull=False) |
               Match.objects.filter(guest_score__isnull=False))
    user_data = get_object_or_404(User, pk=user_id)
    user_results_data = get_user_results_by_matches(user_id, matches)
    return render(request, 'user_results.html',
                  {'user_results': user_results_data,
                   'user_data': user_data,
                   'user_champion': user_champion})
