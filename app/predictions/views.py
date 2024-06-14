from datetime import datetime
import pytz

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils.timezone import localtime, now

from basic.utils import last_prediction
from predictions.models import Prediction, Coefficient, WinnerPrediction, WinnerPredictionCoef
from matches.models import Match, Team
from predictions.forms import NewPredictionForm, WinnerPredictionForm

COMPETITION_START_DATE_UTC = datetime(2021, 5, 11, 19, 0, 0, tzinfo=pytz.utc)


def available_coefficients(request):
    user_preds = {}
    avail_coefs = last_prediction(
        Coefficient.objects
        .filter(coef_ready=True, match_id__status='SCHEDULED'))
    not_avail_coefs = last_prediction(
        Coefficient.objects
        .filter(coef_ready=True)
        .exclude(match_id__status='SCHEDULED'))

    preds_q = Prediction.objects.filter(user_id=request.user.id).order_by('match_id_id', '-submit_time').distinct('match_id_id')
    for i in preds_q:
        user_preds[i.match_id.match_id] = f'{i.home_score} - {i.guest_score}'
    return render(request, 'index.html', {'avail_coefs': avail_coefs,
                                          'not_avail_coefs': not_avail_coefs,
                                          'user_preds': user_preds})


@login_required
def new_prediction(request, match_id):
    match_data = Match.objects.get(match_id=match_id)
    score_coef_data = Coefficient.objects.get(match_id=match_id)
    score_coef_win, score_coef_tie, score_coef_lose = {}, {}, {}
    for score, coef in score_coef_data.score.items():
        if score != 'Any other score':
            home, guest = score.split('-')
            if home > guest:
                score_coef_win[score] = coef
            if home == guest:
                score_coef_tie[score] = coef
            if home < guest:
                score_coef_lose[score] = coef
        else:
            any_other_score = coef
    curr_prediction = (Prediction.objects
                       .filter(match_id=match_data, user_id=request.user.id)
                       .order_by('-submit_time')
                       .first())
    if request.method == 'POST':
        frm = NewPredictionForm(
            request.POST, initial={'home_score': 0, 'guest_score': 0})
        home_score = request.POST['home_score']
        guest_score = request.POST['guest_score']
        is_home_advance = request.POST['penalty_winner']
        if frm.is_valid():
            Prediction.objects.create(
                home_score=home_score,
                guest_score=guest_score,
                user_id=request.user,
                match_id=match_data,
                home_to_advance=is_home_advance,
                submit_time=localtime(now()))
            return redirect('predictions:details', match_id)
    else:
        frm = NewPredictionForm()
    return render(request, 'details.html',
                  {'form': frm, 'match': match_data, 'cur_time': now(),
                   'curr_prediction': curr_prediction,
                   'score_coef': score_coef_data,
                   'score_coef_win': score_coef_win,
                   'score_coef_tie': score_coef_tie,
                   'score_coef_lose': score_coef_lose,
                   'any_other_score': any_other_score})


@login_required
def winner_prediction(request):
    winner_coef_data = WinnerPredictionCoef.objects.all().select_related('team_id').order_by('coef')
    curr_prediction = WinnerPrediction.objects.filter(user_id=request.user.id).first()
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
                   'submissions_closed': datetime.now(pytz.UTC) > COMPETITION_START_DATE_UTC,
                   'form': frm})
