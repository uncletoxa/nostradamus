from django.urls import path

from . import views

app_name = 'predictions'
urlpatterns = [
    # /predictions/
    path('', views.available_coefficients, name='predictions_index'),
    # /predictions/1/
    path('<int:match_id>', views.new_prediction, name='details'),
    # /predictions/winner
    path('winner', views.winner_prediction, name='winner')
 ]
