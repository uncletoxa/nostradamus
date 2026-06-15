from django.db import models
from django.contrib.auth.models import User


class ChatMessage(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_messages')
    text = models.TextField(max_length=1000, blank=True)
    image = models.ImageField(upload_to='chat/images/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    match = models.ForeignKey(
        'matches.Match', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='chat_messages')

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.user.username}: {self.text[:50]}'


class MessageReaction(models.Model):
    message = models.ForeignKey(ChatMessage, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_reactions')
    emoji = models.CharField(max_length=10)

    class Meta:
        unique_together = ('message', 'user', 'emoji')
