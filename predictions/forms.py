from django import forms
from matches.models import Team

CHOICES = (
    (True, 'Home Wins'),
    (False, 'Guest Wins')
)


class NewPredictionForm(forms.Form):
    home_score = forms.IntegerField()
    guest_score = forms.IntegerField()
    penalty_winner = forms.NullBooleanField(widget=forms.widgets.Select(choices=CHOICES))


class WinnerPredictionForm(forms.Form):
    team_id = forms.ModelChoiceField(queryset=Team.objects.all(), label="Your Champion")
