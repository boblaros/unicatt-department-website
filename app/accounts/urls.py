from django.urls import path

from .views import forgot_password_view, login_view, logout_view, register_view

app_name = 'accounts'

urlpatterns = [
    path('login/', login_view, name='login'),
    path('register/', register_view, name='register'),
    path('forgot-password/', forgot_password_view, name='forgot_password'),
    path('logout/', logout_view, name='logout'),
]
