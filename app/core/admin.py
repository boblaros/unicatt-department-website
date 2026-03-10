from django.contrib import admin

from .models import WallPost


@admin.register(WallPost)
class WallPostAdmin(admin.ModelAdmin):
    list_display = ('id', 'author', 'parent', 'soft_deleted', 'created_at')
    search_fields = ('author__email', 'author__full_name', 'body')
    list_filter = ('soft_deleted', 'created_at')
    ordering = ('-created_at',)

    def _can_manage(self, request):
        return bool(getattr(request.user, 'can_moderate_community_content', False))

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
