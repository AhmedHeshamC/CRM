"""
Deals App URL Configuration
Following SOLID principles and clean URL patterns
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .viewsets import DealViewSet, DealStageHistoryViewSet
from .views import DealListCreateView, DealDetailView

# Create router for ViewSets
router = DefaultRouter()
router.register(r'deals', DealViewSet, basename='deal')
router.register(r'stage-history', DealStageHistoryViewSet, basename='deal-stage-history')

app_name = 'deals'

urlpatterns = [
    # ViewSet URLs
    path('', include(router.urls)),

    # Deal specific endpoints
    path('deals/<int:pk>/change-stage/', DealViewSet.as_view({'post': 'change_stage'}), name='deal-change-stage'),
    path('deals/<int:pk>/close/', DealViewSet.as_view({'post': 'close'}), name='deal-close'),
    path('deals/bulk-operations/', DealViewSet.as_view({'post': 'bulk_operations'}), name='deal-bulk-operations'),
    path('deals/pipeline-statistics/', DealViewSet.as_view({'get': 'pipeline_statistics'}), name='deal-pipeline-statistics'),
    path('deals/forecast/', DealViewSet.as_view({'get': 'forecast'}), name='deal-forecast'),
    path('deals/<int:pk>/activities/', DealViewSet.as_view({'get': 'activities'}), name='deal-activities'),
    path('deals/closing-soon/', DealViewSet.as_view({'get': 'closing_soon'}), name='deal-closing-soon'),
    path('deals/stalled/', DealViewSet.as_view({'get': 'stalled'}), name='deal-stalled'),

    # Simple TDD API endpoints (KISS principle)
    path('simple/', DealListCreateView.as_view(), name='deal-list-simple'),
    path('simple/<int:pk>/', DealDetailView.as_view(), name='deal-detail-simple'),
]