"""
Deals App URL Configuration
Following SOLID principles and clean URL patterns
"""

from django.urls import path
from .views import DealListCreateView, DealDetailView

app_name = 'deals'

urlpatterns = [
    # Simple TDD API endpoints (KISS principle)
    path('', DealListCreateView.as_view(), name='deal-list-simple'),
    path('<int:pk>/', DealDetailView.as_view(), name='deal-detail-simple'),
]