from django.contrib.auth import login
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.utils import timezone
from matches.models import Match, Team
from .forms import SignUpForm, UserUpdateForm, SupportedTeamsForm
from .models import SupportedTeam, UserProfile


def _cup_started():
    first_match = Match.objects.order_by('start_time').values('start_time').first()
    return first_match is not None and first_match['start_time'] <= timezone.now()


def _supported_teams(user):
    return list(Team.objects.filter(supporters__user_id=user).order_by('supporters__id'))


def _supported_teams_initial(teams):
    return {
        'favourite_team_1': teams[0] if len(teams) > 0 else None,
        'favourite_team_2': teams[1] if len(teams) > 1 else None,
        'favourite_team_3': teams[2] if len(teams) > 2 else None}


@login_required
def my_account(request):
    cup_started = _cup_started()
    account_form = UserUpdateForm(instance=request.user)
    current_teams = _supported_teams(request.user)
    supported_teams_form = SupportedTeamsForm(initial=_supported_teams_initial(current_teams))

    if request.method == 'POST':
        if 'update_account' in request.POST:
            account_form = UserUpdateForm(request.POST, instance=request.user)
            if account_form.is_valid():
                account_form.save()
                return redirect('my_account')
        elif 'update_supported_teams' in request.POST and not cup_started:
            supported_teams_form = SupportedTeamsForm(request.POST)
            if supported_teams_form.is_valid():
                cd = supported_teams_form.cleaned_data
                teams = [cd.get('favourite_team_1'), cd.get('favourite_team_2'), cd.get('favourite_team_3')]
                SupportedTeam.objects.filter(user_id=request.user).delete()
                SupportedTeam.objects.bulk_create(
                    SupportedTeam(user_id=request.user, team_id=team)
                    for team in teams if team)
                return redirect('my_account')

    return render(request, 'my_account.html',
                  {'form': account_form, 'supported_teams_form': supported_teams_form,
                   'cup_started': cup_started, 'current_teams': current_teams})


@login_required
def participants(request):
    profiles = (UserProfile.objects
                .filter(previous_participant=True)
                .select_related('user')
                .order_by('user__first_name', 'user__username'))
    return render(request, 'participants.html', {'profiles': profiles})


def signup(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            teams = [
                form.cleaned_data.get('favourite_team_1'),
                form.cleaned_data.get('favourite_team_2'),
                form.cleaned_data.get('favourite_team_3')]
            SupportedTeam.objects.bulk_create(
                SupportedTeam(user_id=user, team_id=team)
                for team in teams if team)
            login(request, user)
            return redirect('home')
    else:
        form = SignUpForm()
    return render(request, 'signup.html', {'form': form})
