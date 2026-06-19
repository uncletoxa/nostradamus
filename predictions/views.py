from datetime import datetime, timezone

from django.db.models import Q
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils.timezone import localtime, now

from predictions.models import Prediction, Coefficient, WinnerPrediction, WinnerPredictionCoef
from matches.models import Match, Team
from predictions.forms import NewPredictionForm, WinnerPredictionForm

COMPETITION_START_DATE_UTC = datetime(2026, 6, 11, 19, 0, 0, tzinfo=timezone.utc)


def available_coefficients(request):
    user_preds = {}
    avail_coef_ids = (Coefficient.objects
        .filter(coef_ready=True, match_id__status='SCHEDULED')
        .order_by('match_id', '-update_time')
        .distinct('match_id')
        .values_list('coef_id', flat=True))
    avail_coefs = (Coefficient.objects
        .filter(coef_id__in=avail_coef_ids)
        .order_by('match_id__start_time'))

    not_avail_coef_ids = (Coefficient.objects
        .filter(coef_ready=True)
        .exclude(match_id__status='SCHEDULED')
        .order_by('match_id', '-update_time')
        .distinct('match_id')
        .values_list('coef_id', flat=True))
    not_avail_coefs = (Coefficient.objects
        .filter(coef_id__in=not_avail_coef_ids)
        .order_by('match_id__start_time'))

    preds_q = Prediction.objects.filter(user_id=request.user.id).order_by('match_id_id', '-submit_time').distinct('match_id_id')
    for i in preds_q:
        user_preds[i.match_id.match_id] = f'{i.home_score} - {i.guest_score}'
    return render(request, 'index.html', {'avail_coefs': avail_coefs,
                                          'not_avail_coefs': not_avail_coefs,
                                          'user_preds': user_preds})


@login_required
def new_prediction(request, match_id):
    match_data = Match.objects.get(match_id=match_id)
    # score_coef_data = Coefficient.objects.get(match_id=match_id)
    # score_coef_win, score_coef_tie, score_coef_lose = {}, {}, {}
    # for score, coef in score_coef_data.score.items():
    #     if score != 'Any other score':
    #         home, guest = score.split('-')
    #         if home > guest:
    #             score_coef_win[score] = coef
    #         if home == guest:
    #             score_coef_tie[score] = coef
    #         if home < guest:
    #             score_coef_lose[score] = coef
    #     else:
    #         any_other_score = coef
    curr_prediction = (Prediction.objects
                       .filter(match_id=match_data, user_id=request.user.id)
                       .order_by('-submit_time')
                       .first())
    coef = (Coefficient.objects
            .filter(match_id=match_data, coef_ready=True)
            .order_by('-update_time')
            .first())
    score_coefs = {'home': {}, 'draw': {}, 'away': {}, 'other': None}
    if coef:
        for score, odd in coef.score.items():
            if score == 'Any other score':
                score_coefs['other'] = odd
            else:
                h, g = map(int, score.split('-'))
                if h > g:
                    score_coefs['home'][score] = odd
                elif h == g:
                    score_coefs['draw'][score] = odd
                else:
                    score_coefs['away'][score] = odd
    if request.method == 'POST':
        if not coef:
            return redirect('predictions:details', match_id)
        frm = NewPredictionForm(
            request.POST, initial={'home_score': 0, 'guest_score': 0})
        home_score = request.POST['home_score']
        guest_score = request.POST['guest_score']
        is_home_advance = request.POST.get('penalty_winner') if match_data.is_playoff else None
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
    team_matches = (Match.objects
        .filter(Q(home_team=match_data.home_team) | Q(guest_team=match_data.home_team) |
                Q(home_team=match_data.guest_team) | Q(guest_team=match_data.guest_team))
        .exclude(match_id=match_data.match_id)
        .exclude(status='SCHEDULED')
        .order_by('-start_time'))
    home_matches = [m for m in team_matches
                    if m.home_team_id == match_data.home_team_id or m.guest_team_id == match_data.home_team_id]
    guest_matches = [m for m in team_matches
                     if m.home_team_id == match_data.guest_team_id or m.guest_team_id == match_data.guest_team_id]
    return render(request, 'details.html',
                  {'form': frm, 'match': match_data, 'cur_time': now(),
                   'curr_prediction': curr_prediction, 'coef': coef,
                   'score_coefs': score_coefs,
                   'home_matches': home_matches, 'guest_matches': guest_matches})


@login_required
def winner_prediction(request):
    winner_coef_data = WinnerPredictionCoef.objects.all().select_related('team_id').order_by('coef')
    curr_prediction = WinnerPrediction.objects.filter(user_id=request.user.id).first()
    if request.method == 'POST':
        frm = WinnerPredictionForm(request.POST)
        team_id = request.POST['team_id']
        if frm.is_valid():
            coef_record = WinnerPredictionCoef.objects.get(team_id=team_id)
            WinnerPrediction.objects.update_or_create(
                user_id=request.user,
                defaults={'prediction_id': coef_record}
            )
            return redirect('home')
    else:
        frm = WinnerPredictionForm()
    return render(request, 'winner.html',
                  {'winner_coef': winner_coef_data,
                   'curr_prediction': curr_prediction,
                   'submissions_closed': datetime.now(timezone.utc) > COMPETITION_START_DATE_UTC,
                   'form': frm})
