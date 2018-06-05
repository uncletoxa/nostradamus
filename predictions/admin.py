from django.contrib import admin
from .models import Coefficient, Prediction, OddMap


class PredictionAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'user_id', 'submit_time')


admin.site.register(Prediction, PredictionAdmin)
admin.site.register(Coefficient)
admin.site.register(OddMap)
