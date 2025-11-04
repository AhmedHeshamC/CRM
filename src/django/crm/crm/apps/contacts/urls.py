"""
Contacts App URL Configuration
Following SOLID principles and clean URL patterns
"""

from django.urls import path
from .views import ContactListCreateView, ContactDetailView

app_name = 'contacts'

urlpatterns = [
    # Simple TDD API endpoints (KISS principle)
    path('simple/', ContactListCreateView.as_view(), name='contact-list-simple'),
    path('simple/<int:pk>/', ContactDetailView.as_view(), name='contact-detail-simple'),
]