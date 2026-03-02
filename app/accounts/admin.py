from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import RateLimitRecord, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ('email',)
    list_display = ('email', 'full_name', 'role', 'is_verified_student', 'is_banned', 'is_staff')
    list_filter = ('is_verified_student', 'is_moderator', 'is_banned', 'is_staff', 'is_superuser')
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (
            'Profile',
            {
                'fields': (
                    'full_name',
                    'study_program',
                    'year_of_study',
                    'country_of_origin',
                    'is_verified_student',
                )
            },
        ),
        ('Roles', {'fields': ('is_moderator', 'is_banned', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (
            None,
            {
                'classes': ('wide',),
                'fields': (
                    'email',
                    'password1',
                    'password2',
                    'full_name',
                    'study_program',
                    'year_of_study',
                    'country_of_origin',
                    'is_verified_student',
                    'is_moderator',
                    'is_banned',
                    'is_staff',
                    'is_superuser',
                ),
            },
        ),
    )
    search_fields = ('email', 'full_name')

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
        return bool(getattr(request.user, 'is_superuser', False))


@admin.register(RateLimitRecord)
class RateLimitRecordAdmin(admin.ModelAdmin):
    list_display = ('action', 'key', 'count', 'window_started_at')
    search_fields = ('action', 'key')

    def has_module_permission(self, request):
        return bool(getattr(request.user, 'is_superuser', False))
