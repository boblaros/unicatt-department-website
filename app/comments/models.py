from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Comment(models.Model):
    post = models.ForeignKey('posts.Post', on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='comments')
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='replies')
    body = models.TextField(max_length=2000)
    soft_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='deleted_comments',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'Comment {self.id} on post {self.post_id}'

    @property
    def depth(self):
        depth = 1
        node = self.parent
        while node is not None:
            depth += 1
            node = node.parent
        return depth

    def clean(self):
        if self.parent and self.parent.post_id != self.post_id:
            raise ValidationError('Parent comment must belong to the same post.')
        if self.parent and self.parent.depth >= 5:
            raise ValidationError('Maximum reply depth reached.')

    def soft_delete(self, actor):
        self.soft_deleted = True
        self.deleted_at = timezone.now()
        self.deleted_by = actor
        self.body = '[deleted]'
        self.save(update_fields=['soft_deleted', 'deleted_at', 'deleted_by', 'body'])
