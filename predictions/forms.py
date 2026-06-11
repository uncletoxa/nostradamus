from django import forms
from django.utils.translation import gettext_lazy as _
from matches.models import Team


class NewPredictionForm(forms.Form):
    CHOICES = (
        (None, _('No Penalty')),
        (True, _('Home Wins')),
        (False, _('Guest Wins')))
    home_score = forms.IntegerField()
    guest_score = forms.IntegerField()
    penalty_winner = forms.NullBooleanField(widget=forms.widgets.Select(choices=CHOICES), required=False)


class WinnerPredictionForm(forms.Form):
    team_id = forms.ModelChoiceField(queryset=Team.objects.all(), label=_('Your Champion'))
