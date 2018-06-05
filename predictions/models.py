from django.db import models
from django.contrib.auth.models import User
from django.contrib.postgres.fields import JSONField


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


class Prediction(models.Model):
    prediction_id = models.AutoField(primary_key=True)
    home_score = models.PositiveSmallIntegerField()
    guest_score = models.PositiveSmallIntegerField()
    match_id = models.ForeignKey('matches.Match', models.SET_NULL, null=True)
    user_id = models.ForeignKey(User, models.CASCADE, related_name='predictions')
    submit_time = models.DateTimeField(auto_now=True, auto_now_add=True)

    def score(self):
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