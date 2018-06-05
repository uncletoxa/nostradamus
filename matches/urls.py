from django.urls import path
from matches import views

app_name = 'matches'
urlpatterns = [
    # /matches/
    path('', views.MatchListView.as_view(), name='matches_index'),
    # /matches/1/
    path('<int:match_id>/', views.single_match, name='single_match'),
]
