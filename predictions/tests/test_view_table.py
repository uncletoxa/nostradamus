from django.urls import resolve, reverse
from django.test import TestCase
from matches.models import Match
from predictions.models import Prediction, Coefficient


class AllMatchesTests(TestCase):
    def setUp(self):
        self.match = Match.objects.create(
            match_id=1,
            home_team='Netherlands',
            guest_team='Russia',
            start_time='2008-06-21 19:45Z'
        )
        self.coef = Coefficient.objects.create(
            coef_ready=True,
            score={'0-0': 2, '1-0': 1.2, '1-1': 1.8, 'Any other score': 4},
            home_win=1.4,
            tie=2,
            guest_win=3.2,
            update_time='2008-06-10 00:00Z',
            match_id=Match(1)
        )
        self.prediction = Prediction.objects.create(
            home_score=4,
            guest_score=0,
            match_id=Match(1),
            submit_time='2008-06-20 20:00Z',
            user_id=1,

        )

    def test_index_view_status_code(self):
        self.assertEquals(self.response.status_code, 200)

    # def test_index_url_resolves_index_view(self):
    #     view = resolve('/matches/')
    #     self.assertEquals(view.func, matches_index)

    def test_index_view_contains_link_to_single_match_page(self):
        single_match_url = reverse(
            'matches:single_match', kwargs={'match_id': self.match.match_id})
        self.assertContains(
            self.response, 'href="{0}"'.format(single_match_url))