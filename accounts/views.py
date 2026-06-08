from django.contrib.auth import login
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from matches.models import Team
from .forms import SignUpForm, UserUpdateForm, SupportedTeamsForm
from .models import SupportedTeam


def _supported_teams_initial(user):
    return {'teams': Team.objects.filter(supporters__user_id=user)}


@login_required
def my_account(request):
    account_form = UserUpdateForm(instance=request.user)
    supported_teams_form = SupportedTeamsForm(initial=_supported_teams_initial(request.user))

    if request.method == 'POST':
        if 'update_account' in request.POST:
            account_form = UserUpdateForm(request.POST, instance=request.user)
            if account_form.is_valid():
                account_form.save()
                return redirect('my_account')
        elif 'update_supported_teams' in request.POST:
            supported_teams_form = SupportedTeamsForm(request.POST)
            if supported_teams_form.is_valid():
                SupportedTeam.objects.filter(user_id=request.user).delete()
                SupportedTeam.objects.bulk_create(
                    SupportedTeam(user_id=request.user, team_id=team)
                    for team in supported_teams_form.cleaned_data['teams'])
                return redirect('my_account')

    return render(request, 'my_account.html',
                  {'form': account_form, 'supported_teams_form': supported_teams_form})


def signup(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            SupportedTeam.objects.bulk_create(
                SupportedTeam(user_id=user, team_id=team) for team in form.cleaned_data['teams'])
            login(request, user)
            return redirect('home')
    else:
        form = SignUpForm()
    return render(request, 'signup.html', {'form': form})
