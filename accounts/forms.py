from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from matches.models import Team

SUPPORTED_TEAMS_LIMIT = 3


def supported_teams_field():
    return forms.ModelMultipleChoiceField(
        queryset=Team.objects.all().order_by('name'),
        widget=forms.SelectMultiple,
        label='Teams you support',
        help_text='Hold Ctrl (Cmd on Mac) to select up to three teams you support — just for fun, not tied to predictions.',
        required=False)


def clean_supported_teams(teams):
    if len(teams) > SUPPORTED_TEAMS_LIMIT:
        raise forms.ValidationError(
            'You can support up to {} teams.'.format(SUPPORTED_TEAMS_LIMIT))
    return teams


class SignUpForm(UserCreationForm):
    teams = supported_teams_field()

    class Meta:
        model = User
        fields = ('username', 'first_name', 'password1', 'password2')

    def clean_teams(self):
        return clean_supported_teams(self.cleaned_data['teams'])


class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('first_name',)


class SupportedTeamsForm(forms.Form):
    teams = supported_teams_field()

    def clean_teams(self):
        return clean_supported_teams(self.cleaned_data['teams'])
