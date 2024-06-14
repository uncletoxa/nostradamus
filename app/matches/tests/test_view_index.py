from django.urls import resolve, reverse
from django.test import TestCase
from matches.views import matches_index
from matches.models import Match


class AllMatchesTests(TestCase):
    def setUp(self):
        self.match = Match.objects.create(
            match_id=1,
            home_team='Netherlands',
            guest_team='Russia',
            start_time='2008-06-21 19:45Z'
        )
        url = reverse('matches:matches_index')
        self.response = self.client.get(url)

    def test_index_view_status_code(self):
        self.assertEquals(self.response.status_code, 200)

    def test_index_url_resolves_index_view(self):
        view = resolve('/matches/')
        self.assertEquals(view.func, matches_index)

    def test_index_view_contains_link_to_single_match_page(self):
        single_match_url = reverse(
            'matches:single_match', kwargs={'match_id': self.match.match_id})
        self.assertContains(
            self.response, 'href="{0}"'.format(single_match_url))
