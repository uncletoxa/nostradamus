from django.urls import path
from django.contrib.auth.decorators import login_required
from matches import views

app_name = 'matches'
urlpatterns = [
    # /matches/
    path('', login_required(views.MatchListView.as_view()), name='matches_index'),
    # /matches/1/
    path('<int:match_id>/', login_required(views.single_match), name='single_match'),
]
