from django.urls import path
from django.views.generic import TemplateView
from results import views

app_name = 'results'
urlpatterns = [
    # /results/
    path('', views.results, name='results_index'),
    # /results/simple/
    path('simple/', views.simple_results, name='results_simple'),
    # /results/champions
    path('champions', TemplateView.as_view(template_name='champions.html'), name='results_champions'),
    # /results/1/
    path('<int:user_id>/', views.user_result, name='user_results')
]
