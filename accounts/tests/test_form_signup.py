from django.test import TestCase
from ..forms import SignUpForm


class SignUpFormTest(TestCase):
    def test_form_has_fields(self):
        form = SignUpForm()
        expected = ['username', 'first_name', 'password1', 'password2',
                    'favourite_team_1', 'favourite_team_2', 'favourite_team_3']
        actual = list(form.fields)
        self.assertSequenceEqual(expected, actual)
