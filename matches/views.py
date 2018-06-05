from django.shortcuts import get_object_or_404, render
from django.contrib.auth.models import User
from django.views.generic import ListView
from basic.utils import get_user_results_by_matches
from .models import Match


class MatchListView(ListView):
    model = Match
    context_object_name = 'matches'
    template_name = 'matches_index.html'
    paginate_by = 3


def single_match(request, match_id):
    match = get_object_or_404(Match, match_id=match_id)
    match_queryset = Match.objects.filter(match_id=match_id)
    users = User.objects.filter(is_staff=False)
    users_results = {}
    for user in users:
        users_results.update({user: get_user_results_by_matches(
            user.id, match_queryset)})
    return render(request, 'single_match.html',
                  {'match': match,
                   'users_results': users_results})
