from django import forms
from matches.models import Team


class NewPredictionForm(forms.Form):
    CHOICES = (
        (None, 'No Penalty'),
        (True, 'Home Wins'),
        (False, 'Guest Wins'))
    home_score = forms.IntegerField()
    guest_score = forms.IntegerField()
    penalty_winner = forms.NullBooleanField(widget=forms.widgets.Select(choices=CHOICES), required=False)


class WinnerPredictionForm(forms.Form):
    team_id = forms.ModelChoiceField(queryset=Team.objects.all(), label="Your Champion")
