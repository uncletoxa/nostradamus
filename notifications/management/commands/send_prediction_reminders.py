from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth.models import User
from matches.models import Match
from predictions.models import Prediction
from notifications.models import PushSubscription, PredictionReminderSent, NotificationPreferences
from notifications.utils import send_push


class Command(BaseCommand):
    help = 'Notify subscribed users who have not predicted for upcoming matches.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--hours', type=int, default=3,
            help='Send reminder when kickoff is within this many hours (default: 3)')

    def handle(self, *args, **options):
        hours = options['hours']
        now = timezone.now()
        cutoff = now + timedelta(hours=hours)

        upcoming = Match.objects.filter(
            status=Match.SCHEDULED,
            start_time__gt=now,
            start_time__lte=cutoff)

        if not upcoming.exists():
            self.stdout.write('No matches starting within {} hours.'.format(hours))
            return

        opted_out = set(
            NotificationPreferences.objects.filter(notify_predictions=False)
            .values_list('user_id', flat=True))
        subscribed_users = User.objects.filter(
            push_subscriptions__isnull=False,
            is_active=True).exclude(pk__in=opted_out).distinct()

        for match in upcoming:
            predicted_ids = set(
                Prediction.objects.filter(match_id=match)
                .values_list('user_id', flat=True))
            already_sent_ids = set(
                PredictionReminderSent.objects.filter(match=match)
                .values_list('user_id', flat=True))

            to_notify = subscribed_users.exclude(
                id__in=predicted_ids | already_sent_ids)

            for user in to_notify:
                for sub in user.push_subscriptions.all():
                    send_push(
                        sub,
                        title='Nostradamus Cup 2026',
                        body='Predict {} — {} before kickoff!'.format(
                            match.home_team, match.guest_team),
                        url='/predictions/')
                PredictionReminderSent.objects.get_or_create(user=user, match=match)
                self.stdout.write('Notified {} for {}'.format(user.username, match))
