from django.urls import resolve, reverse
from django.test import TestCase
from matches.views import single_match
from matches.models import Match, Team


class SingleMatchTopicsTests(TestCase):
    def setUp(self):
        home_team = Team.objects.create(name='Netherlands', code='NED', emoji_symbol='🇳🇱')
        guest_team = Team.objects.create(name='Russia', code='RUS', emoji_symbol='🇷🇺')
        Match.objects.create(
            match_id=1,
            home_team=home_team,
            guest_team=guest_team,
            start_time='2008-06-21 19:45Z'
        )

    def test_single_match_view_success_status_code(self):
        url = reverse('matches:single_match', kwargs={'match_id': 1})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_single_match_view_not_found_status_code(self):
        url = reverse('matches:single_match', kwargs={'match_id': 99})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_single_match_url_resolves_single_match_view(self):
        view = resolve('/matches/1/')
        self.assertEqual(view.func, single_match)

    def test_single_match_view_contains_link_back_to_index(self):
        single_match_url = reverse('matches:single_match', kwargs={'match_id': 1})
        response = self.client.get(single_match_url)
        matches_index_url = reverse('matches:matches_index')
        self.assertContains(response, 'href="{0}"'.format(matches_index_url))
