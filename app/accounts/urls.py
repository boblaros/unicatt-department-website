from django.urls import path

from .views import forgot_password_view, login_view, logout_view, register_view, set_password_view

app_name = 'accounts'

urlpatterns = [
    path('login/', login_view, name='login'),
    path('register/', register_view, name='register'),
    path('forgot-password/', forgot_password_view, name='forgot_password'),
    path('set-password/<uidb64>/<token>/', set_password_view, name='set_password'),
    path('logout/', logout_view, name='logout'),
]
