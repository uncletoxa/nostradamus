from django.db import models
from django.contrib.auth.models import User
from matches.models import Team


class TeamSupporter(models.Model):
    id = models.AutoField(primary_key=True)
    team_id = models.ForeignKey(Team, models.CASCADE, related_name='supported_team')
    user_id = models.ForeignKey(User, models.CASCADE, related_name='user')

    def __str__(self):
        return '{} cheers {}'.format(self.user_id.first_name, self.team_id)
