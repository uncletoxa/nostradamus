from django.urls import resolve, reverse
from django.test import TestCase
from matches.views import single_match
from matches.models import Match


class SingleMatchTopicsTests(TestCase):
    def setUp(self):
        Match.objects.create(
            match_id=1,
            home_team='Netherlands',
            guest_team='Russia',
            start_time='2008-06-21 19:45Z'
        )

    def test_single_match_view_success_status_code(self):
        url = reverse('matches:single_match', kwargs={'match_id': 1})
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)

    def test_single_match_view_not_found_status_code(self):
        url = reverse('matches:single_match', kwargs={'match_id': 99})
        response = self.client.get(url)
        self.assertEquals(response.status_code, 404)

    def test_single_match_url_resolves_single_match_view(self):
        view = resolve('/matches/1/')
        self.assertEquals(view.func, single_match)

    def test_single_match_view_contains_link_back_to_index(self):
        single_match_url = reverse('matches:single_match', kwargs={'match_id': 1})
        response = self.client.get(single_match_url)
        matches_index_url = reverse('matches:matches_index')
        self.assertContains(response, 'href="{0}"'.format(matches_index_url))
