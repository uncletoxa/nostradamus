import urllib.request
import json
from datetime import datetime, timedelta, timezone

from django.core.management.base import BaseCommand

from matches.models import Match

TEAM_NAME_MAP = {
    'Bosnia and Herz.': 'Bosnia and Herzegovina',
    'Czech': 'Czech Republic',
    'Congo DR': 'DR Congo',
    'Saudi A.': 'Saudi Arabia',
    'USA': 'United States',
    'Cape Verde': 'Cape Verde',
}

API_URL = 'https://api.xgscore.io/games/xg?tournamentId=wc&seasonId=2026&gameweek={gw}&lng=en'
HEADERS = {'User-Agent': 'Mozilla/5.0'}


def normalize(name):
    return TEAM_NAME_MAP.get(name, name)


class Command(BaseCommand):
    help = 'Fetch xG data from xgscore.io and populate Match records'

    def add_arguments(self, parser):
        parser.add_argument('--gameweeks', type=int, default=8)
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        updated = 0
        skipped = 0
        unmatched = []

        for gw in range(1, options['gameweeks'] + 1):
            url = API_URL.format(gw=gw)
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req) as resp:
                games = json.loads(resp.read())

            for game in games:
                home_name = normalize(game['teams']['h']['name'])
                away_name = normalize(game['teams']['a']['name'])
                home_xg = game['xG']['h']
                away_xg = game['xG']['a']
                match_date = datetime.fromisoformat(game['datetime'].replace('Z', '+00:00'))

                # Match by team names + date (±1 day tolerance for timezone differences)
                match = Match.objects.filter(
                    home_team__name=home_name,
                    guest_team__name=away_name,
                    start_time__date__gte=(match_date - timedelta(days=1)).date(),
                    start_time__date__lte=(match_date + timedelta(days=1)).date(),
                ).first()

                if not match:
                    # Try reversed (xgscore home/away may differ from our DB)
                    match = Match.objects.filter(
                        home_team__name=away_name,
                        guest_team__name=home_name,
                        start_time__date__gte=(match_date - timedelta(days=1)).date(),
                        start_time__date__lte=(match_date + timedelta(days=1)).date(),
                    ).first()
                    if match:
                        home_xg, away_xg = away_xg, home_xg

                if not match:
                    unmatched.append(f"GW{gw}: {home_name} vs {away_name} ({match_date.date()})")
                    skipped += 1
                    continue

                if not dry_run:
                    match.home_xg = home_xg
                    match.guest_xg = away_xg
                    match.save(update_fields=['home_xg', 'guest_xg'])
                else:
                    self.stdout.write(
                        f"[dry-run] GW{gw}: {match} → home_xg={home_xg}, guest_xg={away_xg}")
                updated += 1

        self.stdout.write(self.style.SUCCESS(f"Updated: {updated}, Skipped: {skipped}"))
        for u in unmatched:
            self.stdout.write(self.style.WARNING(f"Unmatched: {u}"))
