"""
Activities App URL Configuration
Following SOLID principles and clean URL patterns
"""

from django.urls import path
from .views import ActivityListCreateView, ActivityDetailView

app_name = 'activities'

urlpatterns = [
    # Simple TDD API endpoints (KISS principle)
    path('', ActivityListCreateView.as_view(), name='activity-list-simple'),
    path('<int:pk>/', ActivityDetailView.as_view(), name='activity-detail-simple'),
]