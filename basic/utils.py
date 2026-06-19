import csv
from datetime import datetime
from decimal import Decimal

from collections import OrderedDict

from django.core.exceptions import ObjectDoesNotExist
from django.db.models.query import QuerySet
from predictions.models import Prediction, Coefficient
from matches.models import Match


def get_result(home_team: int, guest_team: int) -> str:
    res = home_team - guest_team
    return 'home_win' if res > 0 else 'guest_win' if res < 0 else 'tie'


def get_playoff_result(home_team, guest_team, home_to_advance):
    res = home_team - guest_team
    if res == 0:
        return 'tie_home_win' if home_to_advance else 'tie_guest_win'
    return 'home_win' if res > 0 else 'guest_win'


def get_score(home_team, guest_team, avail_scores):
    if f'{home_team}-{guest_team}' in avail_scores:
        return f'{home_team}-{guest_team}'
    else:
        return 'Any other score'


def last_prediction(queryset: QuerySet) -> QuerySet:
    return (queryset
            .order_by('match_id', '-submit_time')
            .distinct('match_id'))


def _score_match(match, prediction, coef):
    match_score_cr = get_score(match.home_score, match.guest_score, coef.score)
    predicted_score_cr = get_score(prediction.home_score, prediction.guest_score, coef.score)

    if match.is_playoff:
        match_result = get_playoff_result(
            match.home_score, match.guest_score, match.home_to_advance)
        prediction_result = get_playoff_result(
            prediction.home_score, prediction.guest_score, prediction.home_to_advance)
    else:
        match_result = get_result(match.home_score, match.guest_score)
        prediction_result = get_result(prediction.home_score, prediction.guest_score)

    result_bet = Decimal(str(getattr(coef, match_result))) if prediction_result == match_result else Decimal(0)
    exact_score_match = (match.home_score == prediction.home_score and
                         match.guest_score == prediction.guest_score)
    score_correct = (predicted_score_cr == match_score_cr and
                     (match_score_cr != 'Any other score' or exact_score_match))
    score_bet = Decimal(str(coef.score[match_score_cr])) if score_correct else Decimal(0)
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
