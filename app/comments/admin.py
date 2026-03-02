from django.contrib import admin

from .models import Comment


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('id', 'post', 'author', 'parent', 'soft_deleted', 'created_at')
    list_filter = ('soft_deleted', 'created_at')
    search_fields = ('body', 'author__email', 'post__title_en', 'post__title_it')

    def _can_manage(self, request):
        return bool(getattr(request.user, 'is_superuser', False) or getattr(request.user, 'is_moderator', False))

    def has_module_permission(self, request):
        return self._can_manage(request)

    def has_view_permission(self, request, obj=None):
        return self._can_manage(request)

    def has_add_permission(self, request):
        return self._can_manage(request)

    def has_change_permission(self, request, obj=None):
        return self._can_manage(request)

    def has_delete_permission(self, request, obj=None):
        return self._can_manage(request)
