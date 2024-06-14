from django.urls import path
from results import views
from django.views.generic import TemplateView

app_name = 'results'
urlpatterns = [
    # /results/
    path('', views.results, name='results_index'),
    # /results/champions
    path('champions', TemplateView.as_view(template_name='champions.html'), name='results_champions'),
    # /results/table
    path('table', TemplateView.as_view(template_name='points_table.html'), name='points_table'),
    # /results/1/
    path('<int:user_id>/', views.user_result, name='user_results')
]
