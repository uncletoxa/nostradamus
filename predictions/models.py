from django.db import models
from django.contrib.auth.models import User
from django.contrib.postgres.fields import JSONField
from matches.models import Team


class Coefficient(models.Model):
    coef_id = models.AutoField(primary_key=True)
    match_id = models.ForeignKey('matches.Match', models.SET_NULL, null=True)
    coef_ready = models.BooleanField(default=False)
    score = JSONField()
    home_win = models.FloatField()
    tie = models.FloatField()
    guest_win = models.FloatField()
    update_time = models.DateTimeField()

    def __str__(self):
        return '{}'.format(self.match_id)


class WinnerPredictionCoef(models.Model):
    team_id = models.ForeignKey(Team, models.CASCADE, related_name='winner_team')
    coef = models.FloatField(default=1.0)

    def __str__(self):
        return '{}: {}'.format(self.team_id, self.coef)


class Prediction(models.Model):
    prediction_id = models.AutoField(primary_key=True)
    home_score = models.PositiveSmallIntegerField()
    guest_score = models.PositiveSmallIntegerField()
    match_id = models.ForeignKey('matches.Match', models.SET_NULL, null=True)
    user_id = models.ForeignKey(User, models.CASCADE, related_name='predictions')
    submit_time = models.DateTimeField(auto_now=True)
    penalty_winner = models.ForeignKey(Team, models.CASCADE, related_name='pred_penalty_winner_team',
                                       default=None, null=True, blank=True)
    penalty_home_winner = models.NullBooleanField(default=None, null=True, blank=True)

    def score(self):
        if self.penalty_home_winner is None:
            return '{}:{}'.format(self.home_score, self.guest_score)
        else:
            if self.penalty_home_winner:
                return '*{}:{}'.format(self.home_score, self.guest_score)
            else:
                return '{}:{}*'.format(self.home_score, self.guest_score)

    def __str__(self):
        return '{} {}'.format(self.match_id, self.score())


class OddMap(models.Model):
    match_id = models.ForeignKey('matches.Match', models.CASCADE)
    result_url_part = models.CharField(max_length=100)
    score_url_part = models.CharField(max_length=100)
    update_ready = models.BooleanField(default=False)

    def __str__(self):
        return '{}'.format(self.match_id)


class WinnerPrediction(models.Model):
    user_id = models.OneToOneField(User, models.CASCADE, related_name='winner_prediction', unique=True)
    team_id = models.ForeignKey(Team, models.CASCADE, related_name='winner_team_prediction')

    def __str__(self):
        return '{}: {}'.format(self.user_id, self.team_id)
