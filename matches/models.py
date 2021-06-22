from django.db import models


class Team(models.Model):
    team_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=30)
    code = models.CharField(max_length=3)
    emoji_symbol = models.CharField(max_length=30)

    def __str__(self):
        return '{} {}'.format(self.emoji_symbol, self.name)


class Match(models.Model):
    FINISHED = 'FINISHED'
    SCHEDULED = 'SCHEDULED'
    IN_PLAY = 'IN_PLAY'
    PAUSED = 'PAUSED'
    STATUS_CHOICES = [(FINISHED, 'FINISHED'), (SCHEDULED, 'SCHEDULED'),
                      (IN_PLAY, 'IN_PLAY'), (PAUSED, 'PAUSED')]

    match_id = models.AutoField(primary_key=True)
    home_team = models.ForeignKey(Team, models.CASCADE, related_name='match_home_team')
    guest_team = models.ForeignKey(Team, models.CASCADE, related_name='match_guest_team')
    start_time = models.DateTimeField()
    home_score = models.SmallIntegerField(default=None, null=True, blank=True)
    guest_score = models.SmallIntegerField(default=None, null=True, blank=True)
    fixture_id = models.IntegerField(default=None, null=True, blank=True)
    is_playoff = models.BooleanField(default=False)
    penalty_home_winner = models.NullBooleanField(default=None, null=True, blank=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default=SCHEDULED)

    def __str__(self):
        return '{} — {}'.format(self.home_team, self.guest_team)

    def result(self):
        if (self.home_score and self.guest_score) is not None:
            if self.penalty_home_winner is None:
                return '{}:{}'.format(self.home_score, self.guest_score)
            else:
                if self.penalty_home_winner:
                    return '*{}:{}'.format(self.home_score, self.guest_score)
                else:
                    return '{}:{}*'.format(self.home_score, self.guest_score)
        else:
            return None
