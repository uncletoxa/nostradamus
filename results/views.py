from django.shortcuts import render, get_object_or_404
from django.contrib.auth.models import User
from matches.models import Match
from basic.utils import get_user_results_by_matches


def results(request):
    return render(request, 'results_index.html')


def user_result(request, user_id):
    matches = (Match.objects.filter(home_score__isnull=False) |
               Match.objects.filter(guest_score__isnull=False)).order_by('-start_time')
    user_data = get_object_or_404(User, pk=user_id)
    user_results_data = get_user_results_by_matches(user_id, matches)
    return render(request, 'user_results.html',
                  {'user_results': user_results_data,
                   'user_data': user_data})
