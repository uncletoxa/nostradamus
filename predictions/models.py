from django.db import models
from django.db.models import JSONField
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from matches.models import Team


class Coefficient(models.Model):
    coef_id = models.AutoField(primary_key=True)
    match_id = models.ForeignKey('matches.Match', models.SET_NULL, null=True)
    coef_ready = models.BooleanField(default=False)
    score = JSONField()
    home_win = models.FloatField()
    tie = models.FloatField(null=True, blank=True, default=None)
    tie_home_win = models.FloatField(null=True, blank=True, default=None)
    tie_guest_win = models.FloatField(null=True, blank=True, default=None)
    guest_win = models.FloatField()
    update_time = models.DateTimeField()

    def clean(self):
        match = self.match_id
        if match is None:
            return
        if match.status == match.FINISHED:
            raise ValidationError(
                f"Cannot update odds: match '{match}' is already finished.")
        if match.start_time <= timezone.now():
            raise ValidationError(
                f"Cannot update odds: match '{match}' has already started.")
        if match.is_playoff:
            if self.tie_home_win is None or self.tie_guest_win is None:
                raise ValidationError(
                    "Playoff match requires tie_home_win and tie_guest_win odds.")
        else:
            if self.tie is None:
                raise ValidationError(
                    "Non-playoff match requires tie odds.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return '{}'.format(self.match_id)


class WinnerPredictionCoef(models.Model):
    id = models.AutoField(primary_key=True)
    team_id = models.ForeignKey(Team, models.CASCADE, related_name='winner_team')
    coef = models.FloatField(default=1.0)
    is_winner = models.BooleanField(default=None, null=True)

    def __str__(self):
        return '{}: {}'.format(self.team_id, self.coef)


class Prediction(models.Model):
    prediction_id = models.AutoField(primary_key=True)
    home_score = models.PositiveSmallIntegerField()
    guest_score = models.PositiveSmallIntegerField()
    match_id = models.ForeignKey('matches.Match', models.SET_NULL, null=True)
    user_id = models.ForeignKey(User, models.CASCADE, related_name='predictions')
    submit_time = models.DateTimeField(auto_now=True)
    home_to_advance = models.BooleanField(default=None, null=True, blank=True)

    def score(self):
        if self.home_score == self.guest_score:
            if self.home_to_advance == True:
                return '*{}:{}'.format(self.home_score, self.guest_score)
            elif self.home_to_advance == False:
                return '{}:{}*'.format(self.home_score, self.guest_score)
            else:
                return '{}:{}'.format(self.home_score, self.guest_score)
        else:
            return '{}:{}'.format(self.home_score, self.guest_score)

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
    prediction_id = models.ForeignKey(WinnerPredictionCoef, models.CASCADE, related_name='winner_team_prediction')

    def __str__(self):
        return '{}: {}'.format(self.user_id, self.prediction_id.team_id)
