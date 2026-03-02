from django.conf import settings
from django.db import models


class WallPost(models.Model):
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wall_posts')
    body = models.TextField(max_length=800)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Wall post {self.id} by {self.author_id}'
