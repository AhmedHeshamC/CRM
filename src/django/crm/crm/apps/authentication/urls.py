"""
Authentication App URL Configuration
Following SOLID principles and clean URL patterns
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .viewsets import UserViewSet, UserProfileViewSet, custom_token_refresh

# Create router for ViewSets
router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'profiles', UserProfileViewSet, basename='profile')

app_name = 'authentication'

urlpatterns = [
    # KISS principle: specific action URLs first to avoid router conflicts
    path('users/bulk-create/', UserViewSet.as_view({'post': 'bulk_create'}), name='user-bulk-create'),
    path('users/bulk-operations/', UserViewSet.as_view({'post': 'bulk_operations'}), name='user-bulk-operations'),
    path('users/me/', UserProfileViewSet.as_view({'get': 'me', 'patch': 'me'}), name='profile-me'),
    path('users/search/', UserViewSet.as_view({'get': 'search'}), name='user-search'),

    # Authentication endpoints (KISS principle - direct paths)
    path('register/', UserViewSet.as_view({'post': 'register'}), name='user-register'),
    path('login/', UserViewSet.as_view({'post': 'login'}), name='user-login'),
    path('logout/', UserViewSet.as_view({'post': 'logout'}), name='user-logout'),
    path('refresh/', custom_token_refresh, name='token_refresh'),
    path('password-reset/', UserViewSet.as_view({'post': 'password_reset'}), name='password-reset'),
    path('password-reset-confirm/', UserViewSet.as_view({'post': 'password_reset_confirm'}), name='password-reset-confirm'),

    # User management endpoints with ID parameters (after specific patterns)
    path('users/<int:pk>/change-password/', UserViewSet.as_view({'post': 'change_password'}), name='user-change-password'),
    path('users/<int:pk>/update-profile/', UserViewSet.as_view({'post': 'update_profile'}), name='user-update-profile'),
    path('users/<int:pk>/deactivate/', UserViewSet.as_view({'post': 'deactivate'}), name='user-deactivate'),
    path('users/<int:pk>/activate/', UserViewSet.as_view({'post': 'activate'}), name='user-activate'),
    path('users/<int:pk>/permissions/', UserViewSet.as_view({'get': 'permissions'}), name='user-permissions'),

    # ViewSet URLs (most generic patterns last)
    path('', include(router.urls)),
]