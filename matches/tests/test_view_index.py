from django.urls import resolve, reverse
from django.test import TestCase
from matches.views import MatchListView
from matches.models import Match, Team


class AllMatchesTests(TestCase):
    def setUp(self):
        home_team = Team.objects.create(name='Netherlands', code='NED', emoji_symbol='🇳🇱')
        guest_team = Team.objects.create(name='Russia', code='RUS', emoji_symbol='🇷🇺')
        self.match = Match.objects.create(
            match_id=1,
            home_team=home_team,
            guest_team=guest_team,
            start_time='2008-06-21 19:45Z'
        )
        url = reverse('matches:matches_index')
        self.response = self.client.get(url)

    def test_index_view_status_code(self):
        self.assertEqual(self.response.status_code, 200)

    def test_index_url_resolves_index_view(self):
        view = resolve('/matches/')
        self.assertEqual(view.func.view_class, MatchListView)

    def test_index_view_contains_link_to_single_match_page(self):
        single_match_url = reverse(
            'matches:single_match', kwargs={'match_id': self.match.match_id})
        self.assertContains(
            self.response, 'href="{0}"'.format(single_match_url))
