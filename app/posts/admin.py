from django.contrib import admin
from django.utils import timezone

from .models import Post, PostImage


class PostImageInline(admin.TabularInline):
    model = PostImage
    extra = 1


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('title_en', 'status', 'published_at', 'updated_at')
    list_filter = ('status',)
    search_fields = ('title_en', 'title_it', 'body_en', 'body_it')
    prepopulated_fields = {'slug': ('title_en',)}
    inlines = [PostImageInline]

    def _can_manage(self, request):
        return request.user.is_superuser or request.user.is_moderator

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

    def save_model(self, request, obj, form, change):
        if obj.status == Post.Status.PUBLISHED and not obj.published_at:
            obj.published_at = timezone.now()
        super().save_model(request, obj, form, change)


@admin.register(PostImage)
class PostImageAdmin(admin.ModelAdmin):
    list_display = ('post', 'created_at')

    def _can_manage(self, request):
        return request.user.is_superuser or request.user.is_moderator

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
