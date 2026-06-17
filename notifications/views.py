import json
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.conf import settings
from .models import PushSubscription


@login_required
@require_POST
def subscribe(request):
    try:
        data = json.loads(request.body)
        endpoint = data['endpoint']
        p256dh = data['keys']['p256dh']
        auth = data['keys']['auth']
    except (json.JSONDecodeError, KeyError):
        return JsonResponse({'error': 'invalid'}, status=400)

    PushSubscription.objects.update_or_create(
        endpoint=endpoint,
        defaults={'user': request.user, 'p256dh': p256dh, 'auth': auth})
    return JsonResponse({'ok': True})


@login_required
@require_POST
def unsubscribe(request):
    try:
        data = json.loads(request.body)
        endpoint = data['endpoint']
    except (json.JSONDecodeError, KeyError):
        return JsonResponse({'error': 'invalid'}, status=400)

    PushSubscription.objects.filter(user=request.user, endpoint=endpoint).delete()
    return JsonResponse({'ok': True})


def vapid_public_key(request):
    return HttpResponse(settings.VAPID_PUBLIC_KEY, content_type='text/plain')


def service_worker(request):
    import os
    sw_path = os.path.join(settings.BASE_DIR, 'static', 'js', 'sw.js')
    with open(sw_path, 'rb') as f:
        content = f.read()
    response = HttpResponse(content, content_type='application/javascript')
    response['Service-Worker-Allowed'] = '/'
    return response
