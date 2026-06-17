from django.urls import path
from . import views

urlpatterns = [
    path('subscribe/', views.subscribe, name='push_subscribe'),
    path('unsubscribe/', views.unsubscribe, name='push_unsubscribe'),
    path('vapid-public-key/', views.vapid_public_key, name='vapid_public_key'),
]
