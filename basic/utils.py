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
        if (match.home_score and match.guest_score) is None:
            user_result_data.update(
                {match.match_id: {'match_name': match, 'match_score': None}})
        else:
            match_score = '{}-{}'.format(match.home_score, match.guest_score)
        match_goals_scored = match.home_score + match.guest_score
        user_result_data.update({match.match_id: {}})
        user_result_data[match.match_id].update(
            {'match_name': match, 'match_score': match_score,
             'result_points': 0, 'score_points': 0, 'high_score_points': 0,
             'block_bonus_points': 0})
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
                user_result_data[match.match_id].update({'result_points': 1})
                if predicted_score == match_score:
                    user_result_data[match.match_id].update({'score_points': 4})
                    if match_goals_scored >= 4:
                        user_result_data[match.match_id].update(
                            {'high_score_points': 3})

        except ObjectDoesNotExist:
            user_result_data[match.match_id].update(
                {'prediction': None, 'result_points': None, 'score_points': None,
                 'high_score_points': None, 'block_bonus_points': None})
    return user_result_data

