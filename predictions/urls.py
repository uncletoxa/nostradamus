from django.urls import path
from django.contrib.auth.decorators import login_required

from . import views

app_name = 'predictions'
urlpatterns = [
    # /predictions/
    path('', login_required(views.available_coefficients), name='predictions_index'),
    # /predictions/1
    path('<int:match_id>', login_required(views.single_coefficient), name='single_coef'),
    # /predictions/1/new
    path('<int:match_id>/details', login_required(views.new_prediction), name='details')
 ]
