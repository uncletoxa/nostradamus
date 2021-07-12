import csv
from datetime import datetime

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
            .order_by('match_id', '-match_id__prediction__submit_time')
            .distinct('match_id'))


def get_user_results_by_matches(user_id: int, matches: QuerySet) -> dict:
    """Get prediction results for given user for given matches."""
    user_result_data = {}
    for match in matches:
        if (match.home_score and match.guest_score) is None:
            continue
        match_score = '{}-{}'.format(match.home_score, match.guest_score)
        user_result_data.update({match.match_id: {}})
        user_result_data[match.match_id].update(
            {'match_name': match, 'match_score': match_score})
        try:
            prediction = (Prediction.objects
                          .filter(match_id=match.match_id, user_id=user_id)
                          .latest('submit_time'))
            user_result_data[match.match_id].update({'match_prediction': prediction.score()})

            if match.is_playoff:
                match_result = get_playoff_result(
                    match.home_score, match.guest_score, match.home_to_advance)
                prediction_result = get_playoff_result(
                    prediction.home_score, prediction.guest_score, prediction.home_to_advance)
            else:
                match_result = get_result(
                    match.home_score, match.guest_score)
                prediction_result = get_result(
                    prediction.home_score, prediction.guest_score)

            coef = Coefficient.objects.get(match_id_id=prediction.match_id_id)
            match_score_cr = get_score(match.home_score, match.guest_score, coef.score)
            predicted_score_cr = get_score(prediction.home_score, prediction.guest_score, coef.score)

            if predicted_score_cr == match_score_cr:
                user_result_data[match.match_id].update({'score_bet': coef.score[match_score]})
            else:
                user_result_data[match.match_id].update({'score_bet': 0})

            if prediction_result == match_result:
                user_result_data[match.match_id].update({'result_bet': getattr(coef, match_result)})
            else:
                user_result_data[match.match_id].update({'result_bet': 0})

        except ObjectDoesNotExist:
            user_result_data[match.match_id].update(
                {'match_prediction': None, 'result_bet': None, 'score_bet': None})
    return user_result_data


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
