"""
URL configuration for monitoring app.

This module provides URL patterns for health checks and metrics endpoints
following Django best practices and SOLID principles.
"""

from django.urls import path, include
from django.conf.urls import url

from . import views

app_name = 'monitoring'

urlpatterns = [
    # Health check endpoints
    path('health/', views.HealthCheckView.as_view(), name='health-check'),
    path('health/detailed/', views.DetailedHealthView.as_view(), name='detailed-health'),

    # Metrics endpoints
    path('metrics/', views.MetricsView.as_view(), name='metrics'),

    # Legacy health check endpoint (for backward compatibility)
    url(r'^healthcheck/$', views.HealthCheckView.as_view(), name='legacy-health-check'),
]