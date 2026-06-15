from django.urls import path
from . import views

urlpatterns = [
    path('', views.chat, name='chat'),
    path('poll/', views.chat_poll, name='chat_poll'),
    path('react/', views.chat_react, name='chat_react'),
]
