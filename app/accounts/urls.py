from django.urls import path

from .views import (
    delete_profile_view,
    forgot_password_view,
    login_view,
    logout_view,
    profile_view,
    public_profile_view,
    register_view,
    request_password_reset_view,
    set_password_view,
    update_profile_view,
)

app_name = 'accounts'

urlpatterns = [
    path('login/', login_view, name='login'),
    path('register/', register_view, name='register'),
    path('forgot-password/', forgot_password_view, name='forgot_password'),
    path('set-password/<uidb64>/<token>/', set_password_view, name='set_password'),
    path('me/', profile_view, name='profile'),
    path('me/update/', update_profile_view, name='update_profile'),
    path('me/request-password-reset/', request_password_reset_view, name='request_password_reset'),
    path('me/delete/', delete_profile_view, name='delete_profile'),
    path('users/<int:pk>/', public_profile_view, name='public_profile'),
    path('logout/', logout_view, name='logout'),
]
