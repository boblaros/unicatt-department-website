from django.urls import path

from .views import AboutView, HomeView, PrivacyView

app_name = 'core'

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('about/', AboutView.as_view(), name='about'),
    path('privacy/', PrivacyView.as_view(), name='privacy'),
]
