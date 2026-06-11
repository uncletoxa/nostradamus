from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from .models import ChatMessage


@login_required
def chat(request):
    if request.method == 'POST':
        text = request.POST.get('text', '').strip()
        if text:
            ChatMessage.objects.create(user=request.user, text=text)
        return redirect('chat')
    chat_messages = list(ChatMessage.objects.select_related('user', 'user__profile').order_by('created_at')[:200])
    last_ts = chat_messages[-1].created_at.isoformat() if chat_messages else timezone.now().isoformat()
    return render(request, 'chat.html', {'chat_messages': chat_messages, 'last_ts': last_ts})


@login_required
def chat_poll(request):
    since_str = request.GET.get('since', '')
    if not since_str:
        return JsonResponse({'messages': []})
    since = parse_datetime(since_str)
    if since is None:
        return JsonResponse({'messages': []})
    qs = (ChatMessage.objects
          .filter(created_at__gt=since)
          .select_related('user', 'user__profile')
          .order_by('created_at'))
    data = []
    for msg in qs:
        try:
            avatar = msg.user.profile.photo.url if msg.user.profile.photo else None
        except Exception:
            avatar = None
        data.append({
            'user': msg.user.get_full_name() or msg.user.username,
            'text': msg.text,
            'avatar': avatar,
            'created_at': msg.created_at.isoformat(),
            'time': msg.created_at.strftime('%H:%M'),
        })
    return JsonResponse({'messages': data})
