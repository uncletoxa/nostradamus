import json
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from django.db.models import Count
from .models import ChatMessage, MessageReaction
from matches.models import Match

ALLOWED_EMOJI = {'👍', '❤️', '😂', '😮', '😢', '😡'}


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
    msg_ids = [m.id for m in chat_messages]
    reactions_qs = (MessageReaction.objects
                    .filter(message_id__in=msg_ids)
                    .values('message_id', 'emoji')
                    .annotate(count=Count('id'))
                    .order_by())
    user_reacted_qs = set(
        MessageReaction.objects
        .filter(message_id__in=msg_ids, user=request.user)
        .values_list('message_id', 'emoji'))
    reactions_by_msg = {}
    for row in reactions_qs:
        reactions_by_msg.setdefault(row['message_id'], []).append({
            'emoji': row['emoji'],
            'count': row['count'],
            'mine': (row['message_id'], row['emoji']) in user_reacted_qs,
        })
    last_ts = chat_messages[-1].created_at.isoformat() if chat_messages else timezone.now().isoformat()
    reactions_json = json.dumps({str(k): v for k, v in reactions_by_msg.items()})
    return render(request, 'chat.html', {
        'chat_messages': chat_messages,
        'reactions_json': reactions_json,
        'last_ts': last_ts,
    })


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
                          'match', 'match__home_team', 'match__guest_team'))
    try:
        limit = int(request.GET.get('limit', ''))
        msgs = list(qs.order_by('-created_at')[:limit])
        msgs.reverse()
    except (ValueError, TypeError):
        msgs = list(qs.order_by('created_at'))
    msg_ids = [m.id for m in msgs]
    reactions_qs = (MessageReaction.objects
                    .filter(message_id__in=msg_ids)
                    .values('message_id', 'emoji')
                    .annotate(count=Count('id'))
                    .order_by())
    user_reacted_qs = (MessageReaction.objects
                       .filter(message_id__in=msg_ids, user=request.user)
                       .values_list('message_id', 'emoji'))
    reactions_by_msg = {}
    for row in reactions_qs:
        reactions_by_msg.setdefault(row['message_id'], {})[row['emoji']] = row['count']
    user_reacted = set((mid, emoji) for mid, emoji in user_reacted_qs)

    data = []
    for msg in msgs:
        try:
            avatar = msg.user.profile.photo.url if msg.user.profile.photo else None
        except Exception:
            avatar = None
        msg_reactions = [
            {'emoji': e, 'count': c, 'mine': (msg.id, e) in user_reacted}
            for e, c in reactions_by_msg.get(msg.id, {}).items()]
        data.append({
            'id': msg.id,
            'user': msg.user.get_full_name() or msg.user.username,
            'username': msg.user.username,
            'text': msg.text,
            'avatar': avatar,
            'created_at': msg.created_at.isoformat(),
            'time': msg.created_at.strftime('%H:%M'),
            'match': _match_context(msg.match),
            'reactions': msg_reactions,
        })
    return JsonResponse({'messages': data})


@login_required
def chat_react(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    try:
        msg_id = int(request.POST.get('message_id', ''))
    except (ValueError, TypeError):
        return JsonResponse({'error': 'invalid'}, status=400)
    emoji = request.POST.get('emoji', '')
    if emoji not in ALLOWED_EMOJI:
        return JsonResponse({'error': 'invalid emoji'}, status=400)
    try:
        msg = ChatMessage.objects.get(pk=msg_id)
    except ChatMessage.DoesNotExist:
        return JsonResponse({'error': 'not found'}, status=404)
    obj, created = MessageReaction.objects.get_or_create(
        message=msg, user=request.user, emoji=emoji)
    if not created:
        obj.delete()
        mine = False
    else:
        mine = True
    reactions = (MessageReaction.objects
                 .filter(message=msg)
                 .values('emoji')
                 .annotate(count=Count('id'))
                 .order_by())
    user_reacted = set(
        MessageReaction.objects
        .filter(message=msg, user=request.user)
        .values_list('emoji', flat=True))
    data = [{'emoji': r['emoji'], 'count': r['count'], 'mine': r['emoji'] in user_reacted}
            for r in reactions]
    return JsonResponse({'reactions': data})
