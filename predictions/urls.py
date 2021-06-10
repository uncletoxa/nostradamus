from django.urls import path

from . import views

app_name = 'predictions'
urlpatterns = [
    # /predictions/
    path('', views.available_coefficients, name='predictions_index'),
    # /predictions/1
    path('<int:match_id>', views.single_coefficient, name='single_coef'),
    # /predictions/1/new
    path('<int:match_id>/details', views.new_prediction, name='details'),
    # /predictions/winner
    path('winner', views.winner_prediction, name='winner')
 ]
