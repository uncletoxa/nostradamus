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
                         match.guest_score == prediction.guest_score)
    score_bet = Decimal(str(coef.score[match_score])) if exact_score_match else Decimal(0)
    return prediction.score(), result_bet, score_bet


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
    if (match.home_score == prediction.home_score and
            match.guest_score == prediction.guest_score):
        return 5
    actual_diff = match.home_score - match.guest_score
    pred_diff = prediction.home_score - prediction.guest_score
    if actual_diff == pred_diff:
        return 3

    def sign(x):
        return 1 if x > 0 else (-1 if x < 0 else 0)
    if sign(actual_diff) == sign(pred_diff):
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
