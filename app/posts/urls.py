from django.urls import path

from .views import PostListView, post_detail_view

app_name = 'posts'

urlpatterns = [
    path('', PostListView.as_view(), name='list'),
    path('<slug:slug>/', post_detail_view, name='detail'),
]
