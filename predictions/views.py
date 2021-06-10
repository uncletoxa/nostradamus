from datetime import datetime
import pytz

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils.timezone import localtime, now

from basic.utils import get_result, last_prediction
from predictions.models import Prediction, Coefficient, WinnerPrediction, WinnerPredictionCoef
from matches.models import Match, Team
from predictions.forms import NewPredictionForm, WinnerPredictionForm

COMPETITION_START_DATE_UTC = datetime(2021, 5, 11, 19, 0, 0, tzinfo=pytz.utc)

def available_coefficients(request):
    avail_coefs = last_prediction(
        Coefficient.objects
        .filter(coef_ready=True,
                match_id__start_time__gt=datetime.now(pytz.UTC))
        .values('match_id',
                'match_id__home_team',
                'match_id__guest_team',
                'match_id__prediction__home_score',
                'match_id__prediction__guest_score',
                'match_id__prediction__submit_time',
                'match_id__prediction__user_id'))
    not_avail_coefs = last_prediction(
        Coefficient.objects
            .filter(coef_ready=True,
                    match_id__start_time__lte=datetime.now(pytz.UTC))
            .values('match_id',
                    'match_id__home_team',
                    'match_id__guest_team',
                    'match_id__prediction__home_score',
                    'match_id__prediction__guest_score',
                    'match_id__prediction__submit_time',
                    'match_id__prediction__user_id'))
    return render(request, 'index.html', {
        'avail_coefs': avail_coefs, 'not_avail_coefs': not_avail_coefs})


def single_coefficient(request, match_id):
    coef = (Coefficient.objects.filter(match_id=match_id).latest('update_time'))
    match = Match.objects.get(match_id=match_id)
    try:
        prediction = Prediction.objects.filter(match_id=match_id).latest('submit_time')
        match_result = get_result(prediction.home_score, prediction.guest_score)
        result = {'match_result': match_result,
                  'match_bet': coef.serializable_value(match_result)}
    except Prediction.DoesNotExist:
        result = None
    return render(request, 'single_prediction.html',
                  {'coef': coef, 'result': result, 'match': match,
                   'cur_time': now()})


@login_required
def new_prediction(request, match_id):
    match_data = Match.objects.get(match_id=match_id)
    score_coef_data = Coefficient.objects.get(match_id=match_id)
    user_predictions = (Prediction.objects
                        .filter(match_id=match_id, user_id=request.user.id)
                        .order_by('-submit_time'))
    coef = Coefficient.objects.filter(match_id=match_id).latest('update_time')
    if request.method == 'POST':
        frm = NewPredictionForm(request.POST)
        home_score = request.POST['home_score']
        guest_score = request.POST['guest_score']
        if frm.is_valid():
            Prediction.objects.create(
                home_score=home_score,
                guest_score=guest_score,
                user_id=request.user,
                match_id=match_data,
                submit_time=localtime(now()),
                coef_id=coef)
            return redirect('predictions:predictions_index')
    else:
        frm = NewPredictionForm()
    return render(request, 'details.html',
                  {'form': frm, 'match': match_data, 'user_predictions': user_predictions,
                   'score_coef': score_coef_data, 'cur_time': now()})


@login_required
def winner_prediction(request):
    winner_coef_data = WinnerPredictionCoef.objects.all().select_related('team_id')
    curr_prediction = WinnerPrediction.objects.select_related('team_id').filter(user_id=request.user).first()
    if request.method == 'POST':
        frm = WinnerPredictionForm(request.POST)
        team_id = request.POST['team_id']
        if frm.is_valid():
            WinnerPrediction.objects.update_or_create(
                user_id=request.user,
                defaults={'team_id': Team(team_id=team_id)}
            )
            return redirect('home')
    else:
        frm = WinnerPredictionForm()
    return render(request, 'winner.html',
                  {'winner_coef': winner_coef_data,
                   'curr_prediction': curr_prediction,
                   'submissions_closed': datetime.now(pytz.UTC) < COMPETITION_START_DATE_UTC,
                   'form': frm})
