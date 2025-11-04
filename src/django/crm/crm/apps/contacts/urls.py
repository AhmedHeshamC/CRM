"""
Contacts App URL Configuration
Following SOLID principles and clean URL patterns
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .viewsets import ContactViewSet, ContactInteractionViewSet

# Create router for ViewSets
router = DefaultRouter()
router.register(r'contacts', ContactViewSet, basename='contact')
router.register(r'interactions', ContactInteractionViewSet, basename='contact-interaction')

app_name = 'contacts'

urlpatterns = [
    # ViewSet URLs
    path('', include(router.urls)),

    # Contact specific endpoints
    path('contacts/<int:pk>/restore/', ContactViewSet.as_view({'post': 'restore'}), name='contact-restore'),
    path('contacts/<int:pk>/deals/', ContactViewSet.as_view({'get': 'deals'}), name='contact-deals'),
    path('contacts/<int:pk>/update-tags/', ContactViewSet.as_view({'post': 'update_tags'}), name='contact-update-tags'),
    path('contacts/bulk-operations/', ContactViewSet.as_view({'post': 'bulk_operations'}), name='contact-bulk-operations'),
    path('contacts/statistics/', ContactViewSet.as_view({'get': 'statistics'}), name='contact-statistics'),
    path('contacts/recent/', ContactViewSet.as_view({'get': 'recent'}), name='contact-recent'),
    path('contacts/by-company/', ContactViewSet.as_view({'get': 'by_company'}), name='contact-by-company'),
    path('contacts/search/', ContactViewSet.as_view({'get': 'search'}), name='contact-search'),
]