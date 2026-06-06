from django.shortcuts import render
from matches.models import Match


def home(request):
    matches = (Match.objects.filter(home_score__isnull=False) |
               Match.objects.filter(guest_score__isnull=False))
    return render(request, 'home.html', {'matches_queryset': matches})
