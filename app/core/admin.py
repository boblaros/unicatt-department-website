from django.contrib import admin

from .models import WallPost


@admin.register(WallPost)
class WallPostAdmin(admin.ModelAdmin):
    list_display = ('id', 'author', 'created_at')
    search_fields = ('author__email', 'author__full_name', 'body')
    list_filter = ('created_at',)
    ordering = ('-created_at',)
