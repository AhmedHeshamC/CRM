"""
Activities App URL Configuration
Following SOLID principles and clean URL patterns
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .viewsets import ActivityViewSet, ActivityCommentViewSet
from .views import ActivityListCreateView, ActivityDetailView

# Create router for ViewSets
router = DefaultRouter()
router.register(r'activities', ActivityViewSet, basename='activity')
router.register(r'comments', ActivityCommentViewSet, basename='activity-comment')

app_name = 'activities'

urlpatterns = [
    # ViewSet URLs
    path('', include(router.urls)),

    # Activity specific endpoints
    path('activities/<int:pk>/complete/', ActivityViewSet.as_view({'post': 'complete'}), name='activity-complete'),
    path('activities/<int:pk>/cancel/', ActivityViewSet.as_view({'post': 'cancel'}), name='activity-cancel'),
    path('activities/<int:pk>/reschedule/', ActivityViewSet.as_view({'post': 'reschedule'}), name='activity-reschedule'),
    path('activities/<int:pk>/add-comment/', ActivityViewSet.as_view({'post': 'add_comment'}), name='activity-add-comment'),
    path('activities/bulk-operations/', ActivityViewSet.as_view({'post': 'bulk_operations'}), name='activity-bulk-operations'),
    path('activities/upcoming/', ActivityViewSet.as_view({'get': 'upcoming'}), name='activity-upcoming'),
    path('activities/overdue/', ActivityViewSet.as_view({'get': 'overdue'}), name='activity-overdue'),
    path('activities/today/', ActivityViewSet.as_view({'get': 'today'}), name='activity-today'),
    path('activities/this-week/', ActivityViewSet.as_view({'get': 'this_week'}), name='activity-this-week'),
    path('activities/statistics/', ActivityViewSet.as_view({'get': 'statistics'}), name='activity-statistics'),
    path('activities/calendar/', ActivityViewSet.as_view({'get': 'calendar'}), name='activity-calendar'),
    path('activities/by-contact/', ActivityViewSet.as_view({'get': 'by_contact'}), name='activity-by-contact'),
    path('activities/by-deal/', ActivityViewSet.as_view({'get': 'by_deal'}), name='activity-by-deal'),

    # Simple TDD API endpoints (KISS principle)
    path('simple/', ActivityListCreateView.as_view(), name='activity-list-simple'),
    path('simple/<int:pk>/', ActivityDetailView.as_view(), name='activity-detail-simple'),
]