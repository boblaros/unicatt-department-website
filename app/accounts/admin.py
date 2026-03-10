from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext_lazy as _

from .models import RateLimitRecord, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ('email',)
    list_display = ('email', 'full_name', 'role', 'is_verified_student', 'is_banned', 'is_staff')
    list_filter = ('is_verified_student', 'is_moderator', 'is_banned', 'is_staff', 'is_superuser')
    readonly_fields = ('last_login', 'date_joined')
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (
            _('Profile'),
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
        (_('Roles'), {'fields': ('is_moderator', 'is_banned', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        (_('Dates'), {'fields': ('last_login', 'date_joined')}),
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
    moderator_fieldsets = (
        (
            _('Profile'),
            {
                'fields': (
                    'email',
                    'full_name',
                    'study_program',
                    'year_of_study',
                    'country_of_origin',
                )
            },
        ),
        (_('Moderation'), {'fields': ('is_verified_student', 'is_banned')}),
        (_('Dates'), {'fields': ('date_joined', 'last_login')}),
    )
    moderator_readonly_fields = ('email', 'date_joined', 'last_login')

    def _is_privileged(self, user):
        return bool(user.is_superuser or user.is_staff or user.is_moderator)

    def _can_manage(self, request):
        return bool(getattr(request.user, 'is_superuser', False) or getattr(request.user, 'is_moderator', False))

    def _is_superuser_request(self, request):
        return bool(getattr(request.user, 'is_superuser', False))

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if self._is_superuser_request(request):
            return queryset
        if getattr(request.user, 'is_moderator', False):
            return queryset.filter(is_superuser=False, is_staff=False, is_moderator=False)
        return queryset.none()

    def get_fieldsets(self, request, obj=None):
        if self._is_superuser_request(request):
            return super().get_fieldsets(request, obj)
        return self.moderator_fieldsets

    def get_readonly_fields(self, request, obj=None):
        if self._is_superuser_request(request):
            return self.readonly_fields
        return self.moderator_readonly_fields

    def has_module_permission(self, request):
        return self._can_manage(request)

    def has_view_permission(self, request, obj=None):
        if self._is_superuser_request(request):
            return True
        if not getattr(request.user, 'is_moderator', False):
            return False
        if obj is None:
            return True
        return not self._is_privileged(obj)

    def has_add_permission(self, request):
        return self._is_superuser_request(request)

    def has_change_permission(self, request, obj=None):
        if self._is_superuser_request(request):
            return True
        if not getattr(request.user, 'is_moderator', False):
            return False
        if obj is None:
            return True
        return not self._is_privileged(obj)

    def has_delete_permission(self, request, obj=None):
        return self._is_superuser_request(request)

    def save_model(self, request, obj, form, change):
        if self._is_superuser_request(request):
            super().save_model(request, obj, form, change)
            return

        if not getattr(request.user, 'is_moderator', False):
            raise PermissionDenied

        if not change:
            raise PermissionDenied

        original = User.objects.get(pk=obj.pk)
        if self._is_privileged(original) or self._is_privileged(obj):
            raise PermissionDenied

        obj.email = original.email
        obj.is_staff = original.is_staff
        obj.is_superuser = original.is_superuser
        obj.is_moderator = original.is_moderator
        super().save_model(request, obj, form, change)


@admin.register(RateLimitRecord)
class RateLimitRecordAdmin(admin.ModelAdmin):
    list_display = ('action', 'key', 'count', 'window_started_at')
    search_fields = ('action', 'key')

    def has_module_permission(self, request):
        return bool(getattr(request.user, 'is_superuser', False))
