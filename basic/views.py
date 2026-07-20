from collections import Counter, defaultdict
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import render, get_object_or_404

from basic.poisson_odds import generate_score_odd
from basic.utils import get_result, get_playoff_result
from matches.models import Match
from predictions.models import Prediction, Coefficient, WinnerPredictionCoef
from .models import NewsPost


@login_required
def home(request):
    latest_news = NewsPost.objects.first()
    return render(request, 'home.html', {'latest_news': latest_news})


@login_required
def news_list(request):
    posts = NewsPost.objects.all()
    return render(request, 'news_list.html', {'posts': posts})


@login_required
def news_detail(request, pk):
    post = get_object_or_404(NewsPost, pk=pk)
    return render(request, 'news_detail.html', {'post': post})


@login_required
def history(request):
    return render(request, 'history.html')


@login_required
def intro(request):
    return render(request, 'intro.html')


def install_app(request):
    return render(request, 'install_app.html')


@login_required
def how_odds_work(request):
    return render(request, 'how_odds_work.html')


@login_required
def funny_stats(request):
    users = list(User.objects.filter(is_superuser=False).exclude(profile__previous_participant=True))
    finished_matches = list(Match.objects.filter(status='FINISHED'))
    finished_ids = [m.match_id for m in finished_matches]
    match_by_id = {m.match_id: m for m in finished_matches}
    user_ids = [u.id for u in users]
    user_names = {u.id: u.first_name or u.username for u in users}

    last_preds = list(
        Prediction.objects.filter(match_id__in=finished_ids, user_id__in=user_ids)
        .order_by('user_id_id', 'match_id_id', '-submit_time')
        .distinct('user_id_id', 'match_id_id'))

    all_preds = list(
        Prediction.objects.filter(match_id__in=finished_ids, user_id__in=user_ids)
        .select_related('match_id'))

    coefs = {c.match_id_id: c for c in Coefficient.objects.filter(match_id__in=finished_ids)}

    preds_by_user = defaultdict(list)
    for p in last_preds:
        preds_by_user[p.user_id_id].append(p)

    # --- per-user stats ---
    zeros = {uid: sum(1 for p in preds if p.home_score == 0 and p.guest_score == 0)
             for uid, preds in preds_by_user.items()}

    avg_goals = {uid: sum(p.home_score + p.guest_score for p in preds) / len(preds)
                 for uid, preds in preds_by_user.items() if preds}

    draws = {uid: sum(1 for p in preds if p.home_score == p.guest_score)
             for uid, preds in preds_by_user.items()}

    home_wins_pct = {uid: sum(1 for p in preds if p.home_score > p.guest_score) / len(preds) * 100
                     for uid, preds in preds_by_user.items() if preds}

    exact = {}
    for uid, preds in preds_by_user.items():
        exact[uid] = sum(
            1 for p in preds
            if (m := match_by_id.get(p.match_id_id))
            and m.home_score == p.home_score and m.guest_score == p.guest_score)

    top_score_by_user = {}
    for uid, preds in preds_by_user.items():
        scores = Counter((p.home_score, p.guest_score) for p in preds)
        top_score, top_cnt = scores.most_common(1)[0]
        top_score_by_user[uid] = (top_score, top_cnt, round(top_cnt / len(preds) * 100))

    avg_odds = {}
    for uid, preds in preds_by_user.items():
        odds_list = []
        for p in preds:
            m = match_by_id.get(p.match_id_id)
            c = coefs.get(p.match_id_id)
            if not m or not c:
                continue
            result_key = (get_playoff_result(p.home_score, p.guest_score, p.home_to_advance)
                          if m.is_playoff
                          else get_result(p.home_score, p.guest_score))
            odds_val = getattr(c, result_key, None)
            if odds_val:
                odds_list.append(float(odds_val))
        if odds_list:
            avg_odds[uid] = sum(odds_list) / len(odds_list)

    gaps_by_user = defaultdict(list)
    for p in all_preds:
        m = match_by_id.get(p.match_id_id)
        if not m:
            continue
        gap_min = (m.start_time - p.submit_time).total_seconds() / 60
        if gap_min >= 0:
            gaps_by_user[p.user_id_id].append(gap_min)

    min_gap = {uid: min(gaps) for uid, gaps in gaps_by_user.items() if gaps}
    avg_gap_hours = {uid: sum(gaps) / len(gaps) / 60 for uid, gaps in gaps_by_user.items() if gaps}

    user_match_counts = defaultdict(lambda: defaultdict(int))
    for p in all_preds:
        user_match_counts[p.user_id_id][p.match_id_id] += 1
    resubmits = {uid: sum(1 for cnt in user_match_counts[uid].values() if cnt > 1)
                 for uid in user_ids}

    def top(d, n=1, reverse=True):
        """Return list of (uid, value) sorted by value."""
        return sorted(d.items(), key=lambda x: x[1], reverse=reverse)[:n]

    def winner_name(d, reverse=True):
        result = top(d, reverse=reverse)
        if not result:
            return '—', None
        uid, val = result[0]
        return user_names[uid], val

    # build awards list
    pess_name, pess_val = winner_name(zeros)
    goal_name, goal_val = winner_name(avg_goals)
    draw_name, draw_val = winner_name(draws)
    nodraw_name, nodraw_val = winner_name(draws, reverse=False)
    home_name, home_val = winner_name(home_wins_pct)
    oracle_name, oracle_val = winner_name(exact)
    brave_name, brave_val = winner_name(avg_odds)
    coward_name, coward_val = winner_name(avg_odds, reverse=False)
    lastmin_name, lastmin_val = winner_name(min_gap, reverse=False)
    early_name, early_val = winner_name(avg_gap_hours)
    change_name, change_val = winner_name(resubmits)
    nochange_uid, nochange_val = top(resubmits, reverse=False)[0]
    nochange_names = [user_names[uid] for uid, val in top(resubmits, n=len(resubmits), reverse=False) if val == 0]

    # one-note: pick user with highest pct
    onenote_uid = max(top_score_by_user, key=lambda uid: top_score_by_user[uid][2])
    onenote_score, onenote_cnt, onenote_pct = top_score_by_user[onenote_uid]

    awards = [
        {
            'emoji': '😶',
            'title': 'Пессимист',
            'winner': pess_name,
            'stat': f'{pess_val} прогнозов со счётом 0:0',
            'desc': 'Чаще всех верил, что голов не будет вовсе',
        },
        {
            'emoji': '⚽',
            'title': 'Голеадор',
            'winner': goal_name,
            'stat': f'{goal_val:.2f} гола/матч в среднем',
            'desc': 'Прогнозировал самые результативные матчи',
        },
        {
            'emoji': '🤝',
            'title': 'Фанат ничьих',
            'winner': draw_name,
            'stat': f'{draw_val} ничьих',
            'desc': 'Чаще всех ставил на равный счёт',
        },
        {
            'emoji': '🚫',
            'title': 'Против ничьих',
            'winner': nodraw_name,
            'stat': f'Всего {nodraw_val} ничьих за весь турнир',
            'desc': 'Для этого человека ничьих не существует',
        },
        {
            'emoji': '🏠',
            'title': 'Домашний любимчик',
            'winner': home_name,
            'stat': f'{home_val:.0f}% прогнозов на победу хозяев',
            'desc': 'Твёрдо верит в преимущество своего поля',
        },
        {
            'emoji': '🔮',
            'title': 'Оракул',
            'winner': oracle_name,
            'stat': f'{oracle_val} точных счётов',
            'desc': 'Угадал точный счёт больше всех',
        },
        {
            'emoji': '🎵',
            'title': 'Одна нота',
            'winner': user_names[onenote_uid],
            'stat': f'{onenote_score[0]}:{onenote_score[1]} — {onenote_cnt} раз ({onenote_pct}%)',
            'desc': 'Один любимый счёт на все случаи жизни',
        },
        {
            'emoji': '🦁',
            'title': 'Смельчак',
            'winner': brave_name,
            'stat': f'Средний коэф {brave_val:.2f}',
            'desc': 'Чаще всех ставил против фаворитов',
        },
        {
            'emoji': '🐔',
            'title': 'Осторожный',
            'winner': coward_name,
            'stat': f'Средний коэф {coward_val:.2f}',
            'desc': 'Надёжно, предсказуемо, с фаворитами',
        },
        {
            'emoji': '⏰',
            'title': 'Последний момент',
            'winner': lastmin_name,
            'stat': f'Самая поздняя правка — за {lastmin_val:.0f} мин до матча',
            'desc': 'Живёт на грани дедлайна',
        },
        {
            'emoji': '🌅',
            'title': 'Ранняя пташка',
            'winner': early_name,
            'stat': f'В среднем за {early_val:.0f}ч до матча',
            'desc': 'Всё сделано заранее, можно спать спокойно',
        },
        {
            'emoji': '🔄',
            'title': 'Непостоянный',
            'winner': change_name,
            'stat': f'{change_val} раз менял прогноз',
            'desc': 'Семь раз передумай, один раз поставь',
        },
        {
            'emoji': '🗿',
            'title': 'Железное слово',
            'winner': ', '.join(nochange_names),
            'stat': '0 изменений за весь турнир',
            'desc': 'Поставил — и не оглядывался',
        },
    ]

    # --- group stats ---
    all_score_counter = Counter((p.home_score, p.guest_score) for p in last_preds)
    most_popular_score, most_popular_count = all_score_counter.most_common(1)[0]

    exact_by_match = defaultdict(set)
    for p in last_preds:
        m = match_by_id.get(p.match_id_id)
        if m and m.home_score == p.home_score and m.guest_score == p.guest_score:
            exact_by_match[m.match_id].add(p.user_id_id)
    nobody_got_exact = sum(1 for m in finished_matches
                           if len(exact_by_match.get(m.match_id, set())) == 0)

    result_hits = {}
    for m in finished_matches:
        if m.home_score is None:
            continue
        actual = (get_playoff_result(m.home_score, m.guest_score, m.home_to_advance)
                  if m.is_playoff else get_result(m.home_score, m.guest_score))
        preds_for = [p for p in last_preds if p.match_id_id == m.match_id]
        hits = sum(
            1 for p in preds_for
            if (get_playoff_result(p.home_score, p.guest_score, p.home_to_advance)
                if m.is_playoff else get_result(p.home_score, p.guest_score)) == actual)
        result_hits[m.match_id] = (hits, len(preds_for))

    nobody_got_result = sum(1 for h, t in result_hits.values() if h == 0 and t > 0)
    all_got_result = sum(1 for h, t in result_hits.values() if h == t and t > 0)

    avg_predicted = (sum(p.home_score + p.guest_score for p in last_preds) / len(last_preds)
                     if last_preds else 0)
    avg_actual = (sum((m.home_score or 0) + (m.guest_score or 0) for m in finished_matches) / len(finished_matches)
                  if finished_matches else 0)

    # --- theoretical max ---
    total_result_max = Decimal(0)
    total_score_max = Decimal(0)
    for m in finished_matches:
        c = coefs.get(m.match_id)
        if not c:
            continue
        result_key = (get_playoff_result(m.home_score, m.guest_score, m.home_to_advance)
                      if m.is_playoff else get_result(m.home_score, m.guest_score))
        total_result_max += Decimal(str(getattr(c, result_key)))
        score_key = f'{m.home_score}-{m.guest_score}'
        so = c.score.get(score_key) or generate_score_odd(m.home_score, m.guest_score, c.score)
        total_score_max += Decimal(str(so))

    winner_coef = WinnerPredictionCoef.objects.filter(is_winner=True).first()
    winner_points = Decimal(str(winner_coef.coef)) if winner_coef else Decimal(0)
    winner_team = winner_coef.team_id if winner_coef else None
    total_max = total_result_max + total_score_max + winner_points

    best_match_rows = []
    for m in finished_matches:
        c = coefs.get(m.match_id)
        if not c:
            continue
        result_key = (get_playoff_result(m.home_score, m.guest_score, m.home_to_advance)
                      if m.is_playoff else get_result(m.home_score, m.guest_score))
        ro = float(getattr(c, result_key))
        score_key = f'{m.home_score}-{m.guest_score}'
        so = float(c.score.get(score_key) or generate_score_odd(m.home_score, m.guest_score, c.score))
        best_match_rows.append({'match': m, 'result_odd': ro, 'score_odd': so, 'total': ro + so})
    best_match_rows.sort(key=lambda x: -x['total'])

    return render(request, 'funny_stats.html', {
        'awards': awards,
        'most_popular_score': most_popular_score,
        'most_popular_count': most_popular_count,
        'nobody_got_exact': nobody_got_exact,
        'nobody_got_result': nobody_got_result,
        'all_got_result': all_got_result,
        'total_matches': len(finished_matches),
        'avg_predicted': avg_predicted,
        'avg_actual': avg_actual,
        'total_result_max': total_result_max,
        'total_score_max': total_score_max,
        'winner_points': winner_points,
        'winner_team': winner_team,
        'total_max': total_max,
        'best_match': best_match_rows[0] if best_match_rows else None,
    })
