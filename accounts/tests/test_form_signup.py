from django.test import TestCase
from ..forms import SignUpForm


class SignUpFormTest(TestCase):
    def test_form_has_fields(self):
        form = SignUpForm()
        expected = ['username', 'first_name', 'password1', 'password2', 'teams']
        actual = list(form.fields)
        self.assertSequenceEqual(expected, actual)
