"""
User API URLs
Following KISS principle - simple, clear URL patterns
"""

from django.urls import path
from .views import UserRegistrationView, user_login_view, UserProfileView

urlpatterns = [
    path('register/', UserRegistrationView.as_view(), name='user-register'),
    path('login/', user_login_view, name='user-login'),
    path('profile/', UserProfileView.as_view(), name='user-profile'),
]