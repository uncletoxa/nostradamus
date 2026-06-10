from django.urls import path
from . import views

urlpatterns = [
    path('', views.chat, name='chat'),
    path('poll/', views.chat_poll, name='chat_poll'),
]
