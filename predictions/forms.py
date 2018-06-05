from django import forms


class NewPredictionForm(forms.Form):
    home_score = forms.IntegerField()
    guest_score = forms.IntegerField()

    # def __init__(self, *args, **kwargs):
    #     self.match = kwargs.pop('match')
    #     print(self.fields)
    #     self.fields['home_score'].label = '{}'.format(self.match.home_team)
    #     self.fields['guest_score'].label = '{}'.format(self.match.guest_team)
    #     super(NewPredictionForm, self).__init__(*args, **kwargs)

