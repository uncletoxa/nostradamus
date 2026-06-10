from django.db import models


class NewsPost(models.Model):
    title = models.CharField(max_length=255)
    body = models.TextField()
    photo = models.ImageField(upload_to='news/', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title
