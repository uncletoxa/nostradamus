import csv
from datetime import datetime

from django.core.exceptions import ObjectDoesNotExist
from django.db.models.query import QuerySet
from predictions.models import Prediction, Coefficient
from matches.models import Match


def get_result(home_team: int, guest_team: int) -> str:
    res = home_team - guest_team
    return 'home_win' if res > 0 else 'guest_win' if res < 0 else 'tie'


def last_prediction(queryset: QuerySet) -> QuerySet:
    return (queryset
            .order_by('match_id', '-match_id__prediction__submit_time')
            .distinct('match_id'))


def get_user_results_by_matches(user_id: int, matches: QuerySet) -> dict:
    """Get prediction results for given user for given matches."""
    user_result_data = {}
    for match in matches:
        match_score = '{}-{}'.format(match.home_score, match.guest_score)
        user_result_data.update({match.match_id: {}})
        user_result_data[match.match_id].update(
            {'match_name': match, 'match_score': match_score})
        try:
            prediction = (Prediction.objects
                          .filter(match_id=match.match_id, user_id=user_id)
                          .latest('submit_time'))
            predicted_score = '{}-{}'.format(
                prediction.home_score, prediction.guest_score)
            user_result_data[match.match_id].update({'match_prediction': predicted_score})

            match_result = get_result(
                match.home_score, match.guest_score)
            prediction_result = get_result(
                prediction.home_score, prediction.guest_score)

            if prediction_result == match_result:
                coef = Coefficient.objects.get(coef_id=prediction.coef_id_id)
                user_result_data[match.match_id].update({'result_bet': getattr(coef, match_result)})

                match_score_cr = coef.score.get(
                    match_score, 'Any other score')
                predicted_score_cr = coef.score.get(
                    predicted_score, 'Any other score')

                if predicted_score_cr == match_score_cr:
                    user_result_data[match.match_id].update({'score_bet': coef.score[match_score]})
                else:
                    user_result_data[match.match_id].update({'score_bet': 0})
            else:
                user_result_data[match.match_id].update({'result_bet': 0, 'score_bet': 0})
        except ObjectDoesNotExist:
            user_result_data[match.match_id].update(
                {'prediction': None, 'result_bet': None, 'score_bet': None})
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
