from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class Comment(models.Model):
    MAX_DEPTH = 5

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
        return self._compute_depth()

    def _compute_depth(self, strict=False):
        depth = 1
        node = self.parent
        current_key = self.pk if self.pk is not None else id(self)
        seen = {current_key}

        while node is not None:
            node_key = node.pk if node.pk is not None else id(node)
            if node_key in seen:
                if strict:
                    raise ValidationError(_('Comment tree cannot contain cycles.'))
                break
            seen.add(node_key)

            if self.post_id is None or node.post_id != self.post_id:
                if strict:
                    raise ValidationError(_('Parent comment must belong to the same post.'))
                break

            depth += 1
            if depth > self.MAX_DEPTH:
                if strict:
                    raise ValidationError(_('Maximum reply depth reached.'))
                return self.MAX_DEPTH

            node = node.parent

        return depth

    def clean(self):
        if not self.parent:
            return
        if self.parent is self or (self.pk is not None and self.parent_id == self.pk):
            raise ValidationError(_('Comment cannot reply to itself.'))
        self._compute_depth(strict=True)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def soft_delete(self, actor):
        self.soft_deleted = True
        self.deleted_at = timezone.now()
        self.deleted_by = actor
        self.body = _('[deleted]')
        self.save(update_fields=['soft_deleted', 'deleted_at', 'deleted_by', 'body'])
