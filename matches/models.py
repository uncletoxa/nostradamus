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
    home_to_advance = models.NullBooleanField(default=None, null=True, blank=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default=SCHEDULED)

    def __str__(self):
        return '{} — {}'.format(self.home_team, self.guest_team)

    @property
    def result(self):
        if self.home_score == self.guest_score:
            if self.home_to_advance == True:
                return '*{}:{}'.format(self.home_score, self.guest_score)
            elif self.home_to_advance == False:
                return '{}:{}*'.format(self.home_score, self.guest_score)
            else:
                return '{}:{}'.format(self.home_score, self.guest_score)
        else:
            return '{}:{}'.format(self.home_score, self.guest_score)

    @property
    def teams(self):
        return '{} — {}'.format(self.home_team, self.guest_team)
