from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from .models import ChatMessage
from matches.models import Match


def _match_context(match):
    if not match:
        return None
    return {
        'teams': '{} vs {}'.format(match.home_team.emoji_symbol, match.guest_team.emoji_symbol),
        'finished': match.status == Match.FINISHED,
    }


@login_required
def chat(request):
    if request.method == 'POST':
        text = request.POST.get('text', '').strip()
        if text:
            live_match = Match.objects.filter(
                status__in=[Match.IN_PLAY, Match.PAUSED]
            ).first()
            ChatMessage.objects.create(user=request.user, text=text, match=live_match)
        return redirect('chat')
    chat_messages = list(ChatMessage.objects
                         .select_related('user', 'user__profile',
                                         'match', 'match__home_team', 'match__guest_team')
                         .order_by('created_at')[:200])
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
          .select_related('user', 'user__profile',
                          'match', 'match__home_team', 'match__guest_team')
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
            'match': _match_context(msg.match),
        })
    return JsonResponse({'messages': data})
