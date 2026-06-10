from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from matches.models import Team


def _team_dropdown(label):
    return forms.ModelChoiceField(
        queryset=Team.objects.all().order_by('name'),
        widget=forms.Select,
        label=label,
        required=False,
        empty_label='—')


class SignUpForm(UserCreationForm):
    favourite_team_1 = _team_dropdown('Favourite team')
    favourite_team_2 = _team_dropdown('2nd favourite team')
    favourite_team_3 = _team_dropdown('3rd favourite team')

    class Meta:
        model = User
        fields = ('username', 'first_name', 'password1', 'password2',
                  'favourite_team_1', 'favourite_team_2', 'favourite_team_3')

    def clean(self):
        cleaned = super().clean()
        teams = [
            cleaned.get('favourite_team_1'),
            cleaned.get('favourite_team_2'),
            cleaned.get('favourite_team_3')]
        selected = [t for t in teams if t]
        if len(selected) != len(set(t.pk for t in selected)):
            raise forms.ValidationError('Please select three different teams.')
        return cleaned


class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('first_name',)


class SupportedTeamsForm(forms.Form):
    favourite_team_1 = _team_dropdown('1st team you support')
    favourite_team_2 = _team_dropdown('2nd team you support')
    favourite_team_3 = _team_dropdown('3rd team you support')

    def clean(self):
        cleaned = super().clean()
        teams = [
            cleaned.get('favourite_team_1'),
            cleaned.get('favourite_team_2'),
            cleaned.get('favourite_team_3')]
        selected = [t for t in teams if t]
        if len(selected) != len(set(t.pk for t in selected)):
            raise forms.ValidationError('Please select different teams.')
        return cleaned
