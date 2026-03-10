from django.urls import path

from .views import AboutView, HomeView, PrivacyView, create_wall_post, delete_wall_post

app_name = 'core'

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('about/', AboutView.as_view(), name='about'),
    path('privacy/', PrivacyView.as_view(), name='privacy'),
    path('wall/post/', create_wall_post, name='create_wall_post'),
    path('wall/post/<int:pk>/delete/', delete_wall_post, name='delete_wall_post'),
]
