from django.urls import path
from results import views

app_name = 'results'
urlpatterns = [
    # /results/
    path('', views.results, name='results_index'),
    # /results/1/
    path('<int:user_id>/', views.user_result, name='user_results')
]
