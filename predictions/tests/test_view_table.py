from django.contrib.auth.models import User
from django.urls import reverse
from django.test import TestCase
from matches.models import Match, Team
from predictions.models import Coefficient


class PredictionsIndexTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='john', password='abcdef123456')
        self.client.login(username='john', password='abcdef123456')

        home_team = Team.objects.create(name='Netherlands', code='NED', emoji_symbol='🇳🇱')
        guest_team = Team.objects.create(name='Russia', code='RUS', emoji_symbol='🇷🇺')
        self.match = Match.objects.create(
            match_id=1,
            home_team=home_team,
            guest_team=guest_team,
            start_time='2008-06-21 19:45Z',
            status=Match.SCHEDULED
        )
        Coefficient.objects.create(
            coef_ready=True,
            score={'0-0': 2, '1-0': 1.2, '1-1': 1.8, 'Any other score': 4},
            home_win=1.4,
            tie=2,
            guest_win=3.2,
            update_time='2008-06-10 00:00Z',
            match_id=self.match
        )

        url = reverse('predictions:predictions_index')
        self.response = self.client.get(url)

    def test_index_view_status_code(self):
        self.assertEqual(self.response.status_code, 200)

    def test_index_view_contains_link_to_prediction_details(self):
        details_url = reverse(
            'predictions:details', kwargs={'match_id': self.match.match_id})
        self.assertContains(
            self.response, 'href="{0}"'.format(details_url))
