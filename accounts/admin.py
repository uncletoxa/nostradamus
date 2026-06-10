from django.contrib import admin
from .models import TeamSupporter, SupportedTeam, UserProfile

admin.site.register(TeamSupporter)
admin.site.register(SupportedTeam)
admin.site.register(UserProfile)
