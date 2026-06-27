from django import forms
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from matches.models import Team


class NewPredictionForm(forms.Form):
    CHOICES = (
        (None, _('No Penalty')),
        (True, _('Home Wins')),
        (False, _('Guest Wins')))
    home_score = forms.IntegerField(label=_('Home score'), required=False)
    guest_score = forms.IntegerField(label=_('Guest score'), required=False)
    penalty_winner = forms.NullBooleanField(widget=forms.widgets.Select(choices=CHOICES), required=False, label=_('Penalty winner'))

    def __init__(self, *args, is_playoff=False, **kwargs):
        self.is_playoff = is_playoff
        super().__init__(*args, **kwargs)
        if is_playoff:
            tooltip = _('Score after 90 or 120 minutes, not including penalties')
            for name, base_label in (('home_score', _('Home score')), ('guest_score', _('Guest score'))):
                self.fields[name].label = format_html(
                    '{} <span tabindex="0" data-bs-toggle="tooltip" title="{}"'
                    ' class="text-muted" style="cursor:help;">?</span>',
                    base_label, tooltip)

    def clean(self):
        cleaned_data = super().clean()
        home = cleaned_data.get('home_score')
        guest = cleaned_data.get('guest_score')
        if home is None:
            self.add_error('home_score', _('This field is required.'))
        if guest is None:
            self.add_error('guest_score', _('This field is required.'))
        if self.is_playoff and home is not None and guest is not None:
            if home == guest and cleaned_data.get('penalty_winner') is None:
                raise forms.ValidationError(_('For a draw in a knockout match, you must select a penalty winner.'))
        return cleaned_data


class WinnerPredictionForm(forms.Form):
    team_id = forms.ModelChoiceField(queryset=Team.objects.all(), label=_('Your Champion'))
