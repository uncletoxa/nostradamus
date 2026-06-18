import json
import logging
from django.conf import settings
from pywebpush import webpush, WebPushException

logger = logging.getLogger(__name__)


def send_push(subscription, title, body, url='/'):
    try:
        webpush(
            subscription_info={
                'endpoint': subscription.endpoint,
                'keys': {
                    'p256dh': subscription.p256dh,
                    'auth': subscription.auth,
                }},
            data=json.dumps({'title': title, 'body': body, 'url': url}),
            vapid_private_key=settings.VAPID_PRIVATE_KEY,
            vapid_claims={'sub': 'mailto:{}'.format(settings.VAPID_CONTACT_EMAIL)},
            ttl=86400)
    except WebPushException as e:
        logger.error('Push failed for subscription %s: %s', subscription.pk, e)
        if e.response is not None and e.response.status_code in (404, 410):
            subscription.delete()


def send_push_to_users(users, title, body, url='/'):
    from .models import PushSubscription
    for sub in PushSubscription.objects.filter(user__in=users):
        send_push(sub, title, body, url)
