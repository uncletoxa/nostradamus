from django.shortcuts import render
from matches.models import Match
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from predictions.models import WinnerPrediction


@login_required
def home(request):
    curr_prediction = WinnerPrediction.objects.filter(user_id=request.user).first()
    if curr_prediction:
        matches = (Match.objects.filter(home_score__isnull=False) |
                   Match.objects.filter(guest_score__isnull=False))
        return render(request, 'home.html', {'matches_queryset': matches})
    else:
        return HttpResponseRedirect("predictions/winner")
