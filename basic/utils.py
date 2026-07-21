import csv
from datetime import datetime
from decimal import Decimal

from collections import OrderedDict

from django.core.exceptions import ObjectDoesNotExist
from django.db.models.query import QuerySet
from predictions.models import Prediction, Coefficient
from matches.models import Match
from basic.poisson_odds import generate_score_odd


def get_result(home_team: int, guest_team: int) -> str:
    res = home_team - guest_team
    return 'home_win' if res > 0 else 'guest_win' if res < 0 else 'tie'


def get_playoff_result(home_team, guest_team, home_to_advance):
    res = home_team - guest_team
    if res == 0:
        if home_to_advance is None:
            return None
        return 'tie_home_win' if home_to_advance else 'tie_guest_win'
    return 'home_win' if res > 0 else 'guest_win'


def get_score(home_team, guest_team, avail_scores):
    return f'{home_team}-{guest_team}'


def last_prediction(queryset: QuerySet) -> QuerySet:
    return (queryset
            .order_by('match_id', '-submit_time')
            .distinct('match_id'))


def _ensure_score_odd(coef, home, away):
    key = f'{home}-{away}'
    if key not in coef.score:
        coef.score[key] = generate_score_odd(home, away, coef.score)
        Coefficient.objects.filter(pk=coef.pk).update(score=coef.score)


def _score_match(match, prediction, coef):
    _ensure_score_odd(coef, match.home_score, match.guest_score)
    match_score = f'{match.home_score}-{match.guest_score}'

    if match.is_playoff:
        match_result = get_playoff_result(
            match.home_score, match.guest_score, match.home_to_advance)
        prediction_result = get_playoff_result(
            prediction.home_score, prediction.guest_score, prediction.home_to_advance)
    else:
        match_result = get_result(match.home_score, match.guest_score)
        prediction_result = get_result(prediction.home_score, prediction.guest_score)

    result_bet = (Decimal(str(getattr(coef, match_result)))
                  if match_result is not None and prediction_result == match_result
                  else Decimal(0))
    exact_score_match = (match.home_score == prediction.home_score and
                         match.guest_score == prediction.guest_score and
                         prediction_result == match_result)
    score_bet = Decimal(str(coef.score[match_score])) if exact_score_match else Decimal(0)
    return prediction.score(), round(result_bet, 2), round(score_bet, 2)


def get_user_results_by_matches(user_id: int, matches: QuerySet) -> dict:
    """Get prediction results for given user for given matches."""
    match_ids = [
        m.match_id for m in matches
        if (m.home_score and m.guest_score) is not None]

    predictions = {
        p.match_id_id: p
        for p in (Prediction.objects
                  .filter(match_id__in=match_ids, user_id=user_id)
                  .order_by('match_id_id', '-submit_time')
                  .distinct('match_id_id'))}
    coefficients = {
        c.match_id_id: c
        for c in Coefficient.objects.filter(match_id__in=match_ids)}

    user_result_data = OrderedDict()
    for match in matches:
        if (match.home_score and match.guest_score) is None:
            continue
        entry = {
            'match_name': match, 'match_score': match.result,
            'result_bet': Decimal(0), 'score_bet': Decimal(0)}
        prediction = predictions.get(match.match_id)
        coef = coefficients.get(match.match_id)
        if prediction is None or coef is None:
            entry.update({'match_prediction': None, 'result_bet': None, 'score_bet': None})
        else:
            match_pred, result_bet, score_bet = _score_match(match, prediction, coef)
            entry.update({'match_prediction': match_pred, 'result_bet': result_bet, 'score_bet': score_bet})
        user_result_data[match.match_id] = entry
    return user_result_data


def get_all_users_results_for_match(match, users):
    """Get prediction results for all users for a single match. 2-3 queries total."""
    entry_base = {
        'match_name': match, 'match_score': match.result,
        'result_bet': Decimal(0), 'score_bet': Decimal(0)}

    if match.home_score is None or match.guest_score is None:
        return {user: {match.match_id: dict(entry_base)} for user in users}

    predictions = {
        p.user_id_id: p
        for p in (Prediction.objects
                  .filter(match_id=match.match_id)
                  .order_by('user_id_id', '-submit_time')
                  .distinct('user_id_id'))}
    try:
        coef = Coefficient.objects.get(match_id_id=match.match_id)
    except ObjectDoesNotExist:
        coef = None

    users_results = {}
    for user in users:
        entry = dict(entry_base)
        prediction = predictions.get(user.id)
        if prediction is None or coef is None:
            entry.update({'match_prediction': None, 'result_bet': None, 'score_bet': None})
        else:
            match_pred, result_bet, score_bet = _score_match(match, prediction, coef)
            entry.update({'match_prediction': match_pred, 'result_bet': result_bet, 'score_bet': score_bet})
        users_results[user] = {match.match_id: entry}
    return users_results


def simple_score_match(match, prediction):
    """Return 5/3/1/0 points for exact score / correct diff / correct result / miss."""
    if prediction is None:
        return 0
    if match.is_playoff:
        match_result = get_playoff_result(
            match.home_score, match.guest_score, match.home_to_advance)
        prediction_result = get_playoff_result(
            prediction.home_score, prediction.guest_score, prediction.home_to_advance)
    else:
        match_result = get_result(match.home_score, match.guest_score)
        prediction_result = get_result(prediction.home_score, prediction.guest_score)
    if (match.home_score == prediction.home_score and
            match.guest_score == prediction.guest_score and
            prediction_result == match_result):
        return 5
    actual_diff = match.home_score - match.guest_score
    pred_diff = prediction.home_score - prediction.guest_score
    if actual_diff == pred_diff and prediction_result == match_result:
        return 3

    def sign(x):
        return 1 if x > 0 else (-1 if x < 0 else 0)
    if sign(actual_diff) == sign(pred_diff) and prediction_result == match_result:
        return 1
    return 0


def get_simple_standings(users, matches_queryset):
    """Compute simple 1/3/5 standings for all users."""
    match_ids = [
        m.match_id for m in matches_queryset
        if m.home_score is not None and m.guest_score is not None]
    matches = {m.match_id: m for m in matches_queryset if m.match_id in match_ids}

    all_predictions = {}
    for p in (Prediction.objects
              .filter(match_id__in=match_ids)
              .order_by('user_id_id', 'match_id_id', '-submit_time')
              .distinct('user_id_id', 'match_id_id')):
        all_predictions.setdefault(p.user_id_id, {})[p.match_id_id] = p

    standings = {}
    for user in users:
        user_preds = all_predictions.get(user.id, {})
        exact = correct_diff = correct_result = 0
        for mid, match in matches.items():
            pts = simple_score_match(match, user_preds.get(mid))
            if pts == 5:
                exact += 1
            elif pts == 3:
                correct_diff += 1
            elif pts == 1:
                correct_result += 1
        total = exact * 5 + correct_diff * 3 + correct_result
        standings[user] = {
            'total': total,
            'exact': exact,
            'correct_diff': correct_diff,
            'correct_result': correct_result}
    return dict(sorted(standings.items(), key=lambda x: x[1]['total'], reverse=True))


def _score_match_xg(match, prediction, coef):
    xg_home = round(float(match.home_xg))
    xg_guest = round(float(match.guest_xg))
    _ensure_score_odd(coef, xg_home, xg_guest)
    xg_score_key = f'{xg_home}-{xg_guest}'
    xg_result = get_result(xg_home, xg_guest)
    prediction_result = get_result(prediction.home_score, prediction.guest_score)
    odds_val = getattr(coef, xg_result, None)
    result_bet = (Decimal(str(odds_val))
                  if prediction_result == xg_result and odds_val is not None
                  else Decimal(0))
    exact_score_match = (xg_home == prediction.home_score and
                         xg_guest == prediction.guest_score)
    score_bet = Decimal(str(coef.score[xg_score_key])) if exact_score_match else Decimal(0)
    return round(result_bet, 2), round(score_bet, 2)


def get_xg_standings(users, matches_queryset):
    """Compute cup-style standings using rounded xG as the actual scores."""
    match_ids = [
        m.match_id for m in matches_queryset
        if m.home_xg is not None and m.guest_xg is not None]
    matches = {m.match_id: m for m in matches_queryset if m.match_id in match_ids}

    all_predictions = {}
    for p in (Prediction.objects
              .filter(match_id__in=match_ids)
              .order_by('user_id_id', 'match_id_id', '-submit_time')
              .distinct('user_id_id', 'match_id_id')):
        all_predictions.setdefault(p.user_id_id, {})[p.match_id_id] = p

    coefficients = {
        c.match_id_id: c
        for c in Coefficient.objects.filter(match_id__in=match_ids)}

    standings = {}
    for user in users:
        user_preds = all_predictions.get(user.id, {})
        result_bet = Decimal(0)
        score_bet = Decimal(0)
        for mid, match in matches.items():
            prediction = user_preds.get(mid)
            coef = coefficients.get(mid)
            if prediction is None or coef is None:
                continue
            rb, sb = _score_match_xg(match, prediction, coef)
            result_bet += rb
            score_bet += sb
        standings[user] = {
            'total_points': result_bet + score_bet,
            'result_bet': result_bet,
            'score_bet': score_bet}
    return dict(sorted(standings.items(), key=lambda x: x[1]['total_points'], reverse=True))


def get_funny_stats_context():
    from collections import Counter, defaultdict
    from django.contrib.auth.models import User
    from predictions.models import WinnerPredictionCoef, WinnerPrediction

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
                          if m.is_playoff else get_result(p.home_score, p.guest_score))
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

    # Avg score distance from actual result (lower = closer)
    avg_score_dist = {}
    for uid, preds in preds_by_user.items():
        dists = [abs(p.home_score - m.home_score) + abs(p.guest_score - m.guest_score)
                 for p in preds if (m := match_by_id.get(p.match_id_id)) and m.home_score is not None]
        if dists:
            avg_score_dist[uid] = sum(dists) / len(dists)

    # Number of unique scorelines predicted
    unique_scores = {uid: len(set((p.home_score, p.guest_score) for p in preds))
                     for uid, preds in preds_by_user.items() if preds}

    def _top(d, reverse=True):
        if not d:
            return '—', None
        uid = max(d, key=lambda u: d[u]) if reverse else min(d, key=lambda u: d[u])
        return user_names[uid], d[uid]

    pess_name, pess_val = _top(zeros)
    goal_name, goal_val = _top(avg_goals)
    draw_name, draw_val = _top(draws)
    nodraw_name, nodraw_val = _top(draws, reverse=False)
    home_name, home_val = _top(home_wins_pct)
    brave_name, brave_val = _top(avg_odds)
    coward_name, coward_val = _top(avg_odds, reverse=False)
    lastmin_name, lastmin_val = _top(min_gap, reverse=False)
    early_name, early_val = _top(avg_gap_hours)
    change_name, change_val = _top(resubmits)
    nochange_names = [user_names[uid] for uid in user_ids
                      if resubmits.get(uid, 0) == 0]
    telepat_name, telepat_val = _top(avg_score_dist, reverse=False)
    artist_name, artist_val = _top(unique_scores)

    onenote_uid = (max(top_score_by_user, key=lambda uid: top_score_by_user[uid][2])
                   if top_score_by_user else None)
    if onenote_uid:
        onenote_score, onenote_cnt, onenote_pct = top_score_by_user[onenote_uid]
    else:
        onenote_score, onenote_cnt, onenote_pct = (0, 0), 0, 0

    # Triple crown: who tops all three standings (official, simple, xG)
    preds_by_user_match = {(p.user_id_id, p.match_id_id): p for p in last_preds}
    winner_preds_map = {
        wp.user_id_id: wp
        for wp in WinnerPrediction.objects.filter(user_id__in=user_ids).select_related('prediction_id')}
    official_totals = {}
    for uid in user_ids:
        total = Decimal(0)
        for m in finished_matches:
            if m.home_score is None or m.guest_score is None:
                continue
            p = preds_by_user_match.get((uid, m.match_id))
            c = coefs.get(m.match_id)
            if p and c:
                _, rb, sb = _score_match(m, p, c)
                total += rb + sb
        wp = winner_preds_map.get(uid)
        if wp and wp.prediction_id.is_winner:
            total += Decimal(str(wp.prediction_id.coef))
        official_totals[uid] = total
    official_winner_uid = max(official_totals, key=official_totals.get) if official_totals else None

    simple_std = get_simple_standings(users, finished_matches)
    simple_winner_uid = next(iter(simple_std)).id if simple_std else None

    xg_std = get_xg_standings(users, finished_matches)
    xg_winner_uid = next(iter(xg_std)).id if xg_std else None

    if official_winner_uid and official_winner_uid == simple_winner_uid == xg_winner_uid:
        triple_winner_name = user_names[official_winner_uid]
    else:
        triple_winner_name = '—'

    awards = [
        {'emoji': '👑', 'title': 'Тройная корона', 'winner': triple_winner_name,
         'stat': 'Победа во всех трёх таблицах',
         'desc': 'Лучший сразу везде: '
                 '<a href="/results/">официальная</a>, '
                 '<a href="/results/simple/">простые очки</a> '
                 'и <a href="/results/xg/">по xG</a>'},
        {'emoji': '😶', 'title': 'Пессимист', 'winner': pess_name,
         'stat': f'{pess_val} прогнозов со счётом 0:0',
         'desc': 'Чаще всех верил, что голов не будет вовсе'},
        {'emoji': '⚽', 'title': 'Голеадор', 'winner': goal_name,
         'stat': f'{goal_val:.2f} гола/матч в среднем' if goal_val else '—',
         'desc': 'Прогнозировал самые результативные матчи'},
        {'emoji': '🤝', 'title': 'Фанат ничьих', 'winner': draw_name,
         'stat': f'{draw_val} ничьих',
         'desc': 'Чаще всех ставил на равный счёт'},
        {'emoji': '🚫', 'title': 'Против ничьих', 'winner': nodraw_name,
         'stat': f'Всего {nodraw_val} ничьих за весь турнир',
         'desc': 'Для этого человека ничьих не существует'},
        {'emoji': '🏠', 'title': 'Домашний любимчик', 'winner': home_name,
         'stat': f'{home_val:.0f}% прогнозов на победу хозяев' if home_val else '—',
         'desc': 'Твёрдо верит в преимущество своего поля'},
        {'emoji': '🎵', 'title': 'Одна нота',
         'winner': user_names[onenote_uid] if onenote_uid else '—',
         'stat': f'{onenote_score[0]}:{onenote_score[1]} — {onenote_cnt} раз ({onenote_pct}%)',
         'desc': 'Один любимый счёт на все случаи жизни'},
        {'emoji': '🦁', 'title': 'Смельчак', 'winner': brave_name,
         'stat': f'Средний коэф {brave_val:.2f}' if brave_val else '—',
         'desc': 'Чаще всех ставил против фаворитов'},
        {'emoji': '🐔', 'title': 'Осторожный', 'winner': coward_name,
         'stat': f'Средний коэф {coward_val:.2f}' if coward_val else '—',
         'desc': 'Надёжно, предсказуемо, с фаворитами'},
        {'emoji': '⏰', 'title': 'Последний момент', 'winner': lastmin_name,
         'stat': f'Самая поздняя правка — за {lastmin_val:.0f} мин до матча' if lastmin_val else '—',
         'desc': 'Живёт на грани дедлайна'},
        {'emoji': '🌅', 'title': 'Ранняя пташка', 'winner': early_name,
         'stat': f'В среднем за {early_val:.0f}ч до матча' if early_val else '—',
         'desc': 'Всё сделано заранее, можно спать спокойно'},
        {'emoji': '🔄', 'title': 'Непостоянный', 'winner': change_name,
         'stat': f'{change_val} раз менял прогноз',
         'desc': 'Семь раз передумай, один раз поставь'},
        {'emoji': '🗿', 'title': 'Железное слово',
         'winner': ', '.join(nochange_names),
         'stat': '0 изменений за весь турнир',
         'desc': 'Поставил — и не оглядывался'},
        {'emoji': '📐', 'title': 'Телепат', 'winner': telepat_name,
         'stat': f'Средняя погрешность {telepat_val:.2f} гола' if telepat_val else '—',
         'desc': 'Ближе всех к реальным счётам — пусть и без точных попаданий'},
        {'emoji': '🌈', 'title': 'Художник', 'winner': artist_name,
         'stat': f'{artist_val} разных счётов за турнир' if artist_val else '—',
         'desc': 'Ни разу не повторился — каждый матч как чистый холст'},
    ]

    all_score_counter = Counter((p.home_score, p.guest_score) for p in last_preds)
    most_popular_score, most_popular_count = (all_score_counter.most_common(1)[0]
                                              if all_score_counter else ((0, 0), 0))

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
    avg_actual = (sum((m.home_score or 0) + (m.guest_score or 0) for m in finished_matches)
                  / len(finished_matches) if finished_matches else 0)

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

    # Full per-user ranking tables
    def _ranks(d, uid_list, name_map, reverse=True):
        return [{'name': name_map[uid], 'value': d.get(uid, 0)}
                for uid in sorted(uid_list, key=lambda u: d.get(u, 0), reverse=reverse)]

    # Who never predicted 0:0 / never predicted any draw
    never_zeros = sorted([user_names[uid] for uid in user_ids if zeros.get(uid, 0) == 0])
    never_draws = sorted([user_names[uid] for uid in user_ids if draws.get(uid, 0) == 0])

    # Missed matches (finished matches with no prediction submitted)
    n_finished = len(finished_matches)
    missed = {uid: n_finished - len(preds_by_user.get(uid, [])) for uid in user_ids}
    missed_matches_ranks = _ranks(missed, user_ids, user_names)

    zeros_ranks = _ranks(zeros, user_ids, user_names)
    avg_goals_ranks = _ranks(avg_goals, [u for u in user_ids if u in avg_goals], user_names)
    draws_ranks = [
        {'name': user_names[uid], 'count': draws.get(uid, 0),
         'pct': round(draws.get(uid, 0) / len(preds_by_user[uid]) * 100) if preds_by_user.get(uid) else 0}
        for uid in sorted(user_ids, key=lambda u: draws.get(u, 0), reverse=True)
        if uid in preds_by_user]
    home_wins_ranks = [
        {'name': user_names[uid], 'pct': round(home_wins_pct[uid]),
         'count': sum(1 for p in preds_by_user[uid] if p.home_score > p.guest_score)}
        for uid in sorted(home_wins_pct, key=lambda u: home_wins_pct[u], reverse=True)]
    exact_ranks = _ranks(exact, user_ids, user_names)
    onenote_ranks = sorted([
        {'name': user_names[uid],
         'score': f"{top_score_by_user[uid][0][0]}:{top_score_by_user[uid][0][1]}",
         'count': top_score_by_user[uid][1], 'pct': top_score_by_user[uid][2]}
        for uid in user_ids if uid in top_score_by_user],
        key=lambda x: -x['pct'])
    avg_odds_ranks = [{'name': user_names[uid], 'value': avg_odds[uid]}
                      for uid in sorted(avg_odds, key=lambda u: avg_odds[u], reverse=True)]
    min_gap_ranks = [{'name': user_names[uid], 'value': round(min_gap[uid])}
                     for uid in sorted(min_gap, key=lambda u: min_gap[u])]
    avg_gap_ranks = [{'name': user_names[uid], 'value': avg_gap_hours[uid]}
                     for uid in sorted(avg_gap_hours, key=lambda u: avg_gap_hours[u], reverse=True)]
    resubmits_ranks = _ranks(resubmits, user_ids, user_names)

    # Top 10 most popular scorelines
    top_scorelines = [{'score': s, 'count': c} for s, c in all_score_counter.most_common(10)]

    # Matches where nobody got exact score (all of them)
    nobody_exact_examples = [
        m for m in finished_matches
        if len(exact_by_match.get(m.match_id, set())) == 0
    ]

    # Most diverse matches (most different scorelines predicted)
    diversity = {}
    for m in finished_matches:
        preds_for = [p for p in last_preds if p.match_id_id == m.match_id]
        diversity[m.match_id] = len(set((p.home_score, p.guest_score) for p in preds_for))
    most_diverse_matches = [
        {'match': match_by_id[mid], 'unique_scores': cnt}
        for mid, cnt in sorted(diversity.items(), key=lambda x: -x[1])[:5]
    ]

    # Matches where all / nobody got result right
    n_users = len(users)
    all_got_result_matches = [
        match_by_id[mid] for mid, (h, t) in result_hits.items()
        if h == t and t == n_users
    ]
    nobody_got_result_matches = [
        match_by_id[mid] for mid, (h, t) in result_hits.items()
        if h == 0 and t > 0
    ]

    return {
        'awards': awards,
        'top_scorelines': top_scorelines,
        'most_popular_score': most_popular_score,
        'most_popular_count': most_popular_count,
        'nobody_got_exact': nobody_got_exact,
        'nobody_exact_examples': nobody_exact_examples,
        'nobody_got_result': nobody_got_result,
        'nobody_got_result_matches': nobody_got_result_matches,
        'all_got_result': all_got_result,
        'all_got_result_matches': all_got_result_matches,
        'total_matches': len(finished_matches),
        'avg_predicted': avg_predicted,
        'avg_actual': avg_actual,
        'total_result_max': total_result_max,
        'total_score_max': total_score_max,
        'winner_points': winner_points,
        'winner_team': winner_team,
        'total_max': total_max,
        'best_match': best_match_rows[0] if best_match_rows else None,
        'best_match_rows': best_match_rows[:20],
        'most_diverse_matches': most_diverse_matches,
        'never_zeros': never_zeros,
        'never_draws': never_draws,
        'missed_matches_ranks': missed_matches_ranks,
        'zeros_ranks': zeros_ranks,
        'avg_goals_ranks': avg_goals_ranks,
        'draws_ranks': draws_ranks,
        'home_wins_ranks': home_wins_ranks,
        'exact_ranks': exact_ranks,
        'onenote_ranks': onenote_ranks,
        'avg_odds_ranks': avg_odds_ranks,
        'min_gap_ranks': min_gap_ranks,
        'avg_gap_ranks': avg_gap_ranks,
        'resubmits_ranks': resubmits_ranks,
    }


def load_matches(path):
    with open(path) as f:
        reader = csv.reader(f)
        bulk = []
        for row in reader:
            bulk.append(
                Match(home_team=row[1],
                      guest_team=row[2],
                      start_time=datetime.strptime(row[0], '%d/%m/%Y %H:%M')))
    Match.objects.bulk_create(bulk)
