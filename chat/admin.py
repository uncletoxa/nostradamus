from django.contrib import admin
from .models import ChatMessage


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ['user', 'text', 'created_at']
    list_filter = ['user']
    ordering = ['-created_at']
