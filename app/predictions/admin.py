from django.contrib import admin
from .models import Coefficient, Prediction, OddMap, WinnerPrediction, WinnerPredictionCoef


class PredictionAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'user_id', 'submit_time')


admin.site.register(Prediction, PredictionAdmin)
admin.site.register(Coefficient)
admin.site.register(OddMap)
admin.site.register(WinnerPrediction)
admin.site.register(WinnerPredictionCoef)
