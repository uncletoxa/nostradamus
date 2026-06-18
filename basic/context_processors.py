from django.conf import settings
from predictions.models import WinnerPrediction


def winner_prediction_status(request):
    if not request.user.is_authenticated:
        return {}
    has_winner_prediction = WinnerPrediction.objects.filter(user_id=request.user).exists()
    return {'has_winner_prediction': has_winner_prediction}


def vapid_public_key(request):
    ctx = {'vapid_public_key': settings.VAPID_PUBLIC_KEY}
    if request.user.is_authenticated:
        from notifications.models import NotificationPreferences
        prefs, _ = NotificationPreferences.objects.get_or_create(user=request.user)
        ctx['notif_prefs'] = prefs
    return ctx
