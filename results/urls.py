from django.urls import path
from django.contrib.auth.decorators import login_required

from results import views

app_name = 'results'
urlpatterns = [
    # /results/
    path('', login_required(views.results), name='results_index'),
    # /results/1/
    path('<int:user_id>/', login_required(views.user_result), name='user_results')
]
