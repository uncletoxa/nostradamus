from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from predictions.models import WinnerPrediction


@login_required
def home(request):
    curr_prediction = WinnerPrediction.objects.filter(user_id=request.user).first()
    if curr_prediction:
        return render(request, 'home.html')
    else:
        return HttpResponseRedirect("predictions/winner")
