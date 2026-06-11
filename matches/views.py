from django.shortcuts import get_object_or_404, render
from django.contrib.auth.models import User
from django.views.generic import ListView
from basic.utils import get_all_users_results_for_match
from matches.models import Match


class MatchListView(ListView):
    model = Match
    context_object_name = 'matches'
    template_name = 'matches_index.html'
    paginate_by = 10
    ordering = ['-start_time']


def single_match(request, match_id):
    match = get_object_or_404(Match, match_id=match_id)
    users = User.objects.filter(is_superuser=False)
    users_results = get_all_users_results_for_match(match, users)
    return render(request, 'single_match.html',
                  {'match': match,
                   'users_results': users_results})
