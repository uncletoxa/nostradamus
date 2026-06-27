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

    def __init__(self, *args, is_playoff=False, **kwargs):
        self.is_playoff = is_playoff
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        if self.is_playoff:
            home = cleaned_data.get('home_score')
            guest = cleaned_data.get('guest_score')
            if home is not None and guest is not None and home == guest and cleaned_data.get('penalty_winner') is None:
                raise forms.ValidationError(_('For a draw in a knockout match, you must select a penalty winner.'))
        return cleaned_data


class WinnerPredictionForm(forms.Form):
    team_id = forms.ModelChoiceField(queryset=Team.objects.all(), label=_('Your Champion'))
