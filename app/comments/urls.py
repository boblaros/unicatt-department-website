from django.urls import path

from .views import create_comment_view, delete_comment_view

app_name = 'comments'

urlpatterns = [
    path('post/<slug:slug>/create/', create_comment_view, name='create'),
    path('<int:pk>/delete/', delete_comment_view, name='delete'),
]
