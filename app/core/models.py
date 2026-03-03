from django.core.exceptions import ValidationError
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class WallPost(models.Model):
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wall_posts')
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='replies')
    body = models.TextField(max_length=800)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Wall post {self.id} by {self.author_id}'

    @property
    def depth(self):
        depth = 1
        node = self.parent
        while node is not None:
            depth += 1
            node = node.parent
        return depth

    def clean(self):
        # Only compare ids when this instance already has a primary key.
        if self.pk is not None and self.parent_id == self.pk:
            raise ValidationError(_('Wall post cannot reply to itself.'))
        if self.parent and self.parent.depth >= 5:
            raise ValidationError(_('Maximum reply depth reached.'))
