from django.db import models


class Match(models.Model):
    match_id = models.AutoField(primary_key=True)
    home_team = models.CharField(max_length=30)
    guest_team = models.CharField(max_length=30)
    start_time = models.DateTimeField()
    home_score = models.SmallIntegerField(default=None, null=True, blank=True)
    guest_score = models.SmallIntegerField(default=None, null=True, blank=True)

    def __str__(self):
        return '{} — {}'.format(self.home_team, self.guest_team)

    def result(self):
        if self.home_score and self.guest_score:
            return '{}:{}'.format(self.home_score, self.guest_score)
        else:
            return 'No result yet'
