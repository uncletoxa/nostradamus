from django.shortcuts import get_object_or_404, render
from django.contrib.auth.models import User
from django.views.generic import ListView
from basic.utils import get_all_users_results_for_match
from matches.models import Match


class MatchListView(ListView):
    model = Match
    context_object_name = 'matches'
    template_name = 'matches_index.html'
    ordering = ['-start_time']

    ALLOWED_PAGE_SIZES = [10, 25, 50, 100]

    def get_paginate_by(self, queryset):
        try:
            size = int(self.request.GET.get('per_page', 10))
        except (ValueError, TypeError):
            size = 10
        return size if size in self.ALLOWED_PAGE_SIZES else 10

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        per_page = self.get_paginate_by(None)
        ctx['per_page'] = per_page
        ctx['allowed_page_sizes'] = self.ALLOWED_PAGE_SIZES
        ctx['page_suffix'] = f'&per_page={per_page}' if per_page != 10 else ''
        return ctx


def single_match(request, match_id):
    match = get_object_or_404(Match, match_id=match_id)
    users = User.objects.filter(is_superuser=False, is_active=True)
    users_results = get_all_users_results_for_match(match, users)
    return render(request, 'single_match.html',
                  {'match': match,
                   'users_results': users_results})
