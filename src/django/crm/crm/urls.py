"""
URL Configuration for CRM Project
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse

# Try to import spectacular views, fall back to basic if not available
try:
    from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
    HAS_SPECTACULAR = True
except ImportError:
    HAS_SPECTACULAR = False

def api_schema_view(request):
    """Fallback API schema view"""
    return JsonResponse({
        'message': 'API Documentation',
        'version': '1.0.0',
        'status': 'Documentation available when drf-spectacular is fully configured'
    })

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

    # API Documentation (fallback)
    path('api/schema/', api_schema_view, name='schema'),

    # Simple health check
    path('health/', lambda request: JsonResponse({'status': 'healthy'}), name='health-check'),
]

# Add spectacular documentation if available
if HAS_SPECTACULAR:
    urlpatterns.insert(2, path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'))
    urlpatterns.insert(3, path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'))

# Try to include app URLs, fall back gracefully if not available
try:
    urlpatterns.append(path('api/v1/auth/', include('crm.apps.authentication.urls')))
except ImportError:
    urlpatterns.append(path('api/v1/auth/', lambda request: JsonResponse({'message': 'Authentication module not available'})))

try:
    urlpatterns.append(path('', include('crm.apps.monitoring.urls')))
except ImportError:
    pass  # Skip monitoring URLs if not available

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)