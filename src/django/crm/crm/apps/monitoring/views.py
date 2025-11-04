"""
Health check and monitoring views.

This module implements views for health checks and metrics following SOLID principles:
- Single Responsibility: Each view has one clear purpose
- Open/Closed: Views can be extended without modification
- Dependency Inversion: Views depend on health checker abstractions
"""

import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from django.http import JsonResponse, HttpResponse
from django.views import View
from django.utils import timezone
from django.conf import settings

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

from .health_checkers import (
    DatabaseHealthChecker,
    RedisHealthChecker,
    CeleryHealthChecker,
    SystemHealthChecker
)


# Application start time for uptime calculation
start_time = time.time()


class HealthCheckView(APIView):
    """
    Main health check endpoint providing comprehensive system status.

    This view follows the Single Responsibility Principle by focusing solely
    on providing health check information for all system components.
    """

    permission_classes = []  # No authentication required for health checks

    def __init__(self, **kwargs):
        """Initialize health check components."""
        super().__init__(**kwargs)

        # Initialize health checkers with dependency injection for testability
        self.health_checkers = {
            'database': DatabaseHealthChecker(),
            'redis': RedisHealthChecker(),
            'celery': CeleryHealthChecker(),
            'system': SystemHealthChecker()
        }

    def get(self, request, *args, **kwargs) -> Response:
        """
        Perform comprehensive health check of all system components.

        Returns:
            Response: JSON response with health status for all components
        """
        try:
            # Check all components
            components = {}
            overall_healthy = True

            for component_name, checker in self.health_checkers.items():
                try:
                    health_result = checker.check_with_timeout()
                    components[component_name] = health_result

                    if not health_result['healthy']:
                        overall_healthy = False

                except Exception as e:
                    components[component_name] = {
                        'status': 'error',
                        'healthy': False,
                        'error': str(e),
                        'timestamp': timezone.now().isoformat()
                    }
                    overall_healthy = False

            # Determine overall status and HTTP status code
            if overall_healthy:
                http_status = status.HTTP_200_OK
                overall_status = 'healthy'
            else:
                http_status = status.HTTP_503_SERVICE_UNAVAILABLE
                overall_status = 'unhealthy'

            # Build response data
            response_data = {
                'status': overall_status,
                'timestamp': timezone.now().isoformat(),
                'components': components,
                'metrics': self._get_system_metrics(),
                'version': getattr(settings, 'APP_VERSION', '1.0.0')
            }

            # Add business metrics if available
            try:
                business_metrics = get_business_metrics()
                if business_metrics:
                    response_data['business_metrics'] = business_metrics
            except Exception:
                # Business metrics should not fail the health check
                response_data['business_metrics'] = {
                    'status': 'error',
                    'error': 'Business metrics collection failed'
                }

            # Add HTTP headers to prevent caching
            response = Response(response_data, status=http_status)
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'

            return response

        except Exception as e:
            # Last-resort error handling
            return Response({
                'status': 'error',
                'timestamp': timezone.now().isoformat(),
                'error': str(e),
                'components': {},
                'version': getattr(settings, 'APP_VERSION', '1.0.0')
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _get_system_metrics(self) -> Dict[str, Any]:
        """
        Get basic system metrics for health check response.

        Returns:
            Dict[str, Any]: System metrics including uptime and basic stats
        """
        try:
            uptime_seconds = time.time() - start_time

            return {
                'uptime_seconds': round(uptime_seconds, 2),
                'uptime_human': str(timedelta(seconds=int(uptime_seconds))),
                'timestamp': timezone.now().isoformat(),
                'timezone': str(timezone.get_current_timezone()),
            }

        except Exception:
            return {
                'uptime_seconds': 'unknown',
                'timestamp': timezone.now().isoformat(),
                'timezone': 'unknown'
            }


class MetricsView(View):
    """
    Prometheus metrics endpoint.

    This view follows the Single Responsibility Principle by focusing
    solely on providing Prometheus-formatted metrics.
    """

    def __init__(self, **kwargs):
        """Initialize metrics collection."""
        super().__init__(**kwargs)

    def get(self, request, *args, **kwargs) -> HttpResponse:
        """
        Generate Prometheus-formatted metrics.

        Returns:
            HttpResponse: Text response with Prometheus metrics
        """
        try:
            # Collect metrics from all sources
            metrics_lines = []

            # Add system metrics
            try:
                system_metrics = generate_system_metrics()
                metrics_lines.extend(system_metrics)
            except Exception as e:
                metrics_lines.append(f"# System metrics error: {e}")

            # Add database metrics
            try:
                db_metrics = generate_database_metrics()
                metrics_lines.extend(db_metrics)
            except Exception as e:
                metrics_lines.append(f"# Database metrics error: {e}")

            # Add business metrics
            try:
                business_metrics = generate_business_metrics()
                metrics_lines.extend(business_metrics)
            except Exception as e:
                metrics_lines.append(f"# Business metrics error: {e}")

            # Build response
            metrics_content = '\n'.join(metrics_lines)

            response = HttpResponse(
                metrics_content,
                content_type='text/plain; version=0.0.4; charset=utf-8'
            )

            # Set caching headers for performance
            response['Cache-Control'] = 'max-age=30'  # Cache for 30 seconds

            return response

        except Exception as e:
            # Return error metrics instead of failing
            error_metrics = [
                f"# Metrics collection error: {e}",
                "# HELP crm_metrics_collection_failed Indicates metrics collection failure",
                "# TYPE crm_metrics_collection_failed gauge",
                f"crm_metrics_collection_failed 1"
            ]

            return HttpResponse(
                '\n'.join(error_metrics),
                content_type='text/plain; version=0.0.4; charset=utf-8',
                status=500
            )


class DetailedHealthView(APIView):
    """
    Detailed health check endpoint with comprehensive diagnostics.

    This view provides more detailed health information suitable for
    debugging and monitoring tools.
    """

    permission_classes = []  # No authentication required

    def get(self, request, *args, **kwargs) -> Response:
        """
        Get detailed health diagnostics.

        Returns:
            Response: Comprehensive health and diagnostic information
        """
        try:
            # Use the main health check to get basic status
            health_view = HealthCheckView()
            basic_health = health_view.get(request)

            # Add additional diagnostic information
            diagnostics = self._get_diagnostics()

            # Merge with basic health data
            response_data = basic_health.data
            response_data['diagnostics'] = diagnostics

            return Response(response_data)

        except Exception as e:
            return Response({
                'status': 'error',
                'timestamp': timezone.now().isoformat(),
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _get_diagnostics(self) -> Dict[str, Any]:
        """
        Get diagnostic information for troubleshooting.

        Returns:
            Dict[str, Any]: Diagnostic information
        """
        try:
            import django
            import sys

            return {
                'python_version': sys.version,
                'django_version': django.get_version(),
                'settings_module': settings.SETTINGS_MODULE,
                'debug_mode': settings.DEBUG,
                'database_engine': settings.DATABASES['default']['ENGINE'],
                'cache_backend': settings.CACHES['default']['BACKEND'],
                'installed_apps_count': len(settings.INSTALLED_APPS),
                'middleware_count': len(settings.MIDDLEWARE),
                'timezone': str(timezone.get_current_timezone()),
            }

        except Exception as e:
            return {
                'error': f'Diagnostics collection failed: {e}'
            }


# Helper functions for metrics collection

def generate_system_metrics() -> list:
    """
    Generate system-level metrics in Prometheus format.

    Returns:
        list: List of Prometheus-formatted metric lines
    """
    try:
        import psutil

        metrics = []

        # Uptime metric
        uptime_seconds = time.time() - start_time
        metrics.extend([
            '# HELP crm_system_uptime_seconds System uptime in seconds',
            '# TYPE crm_system_uptime_seconds counter',
            f'crm_system_uptime_seconds {uptime_seconds:.2f}',
            ''
        ])

        # Memory metrics
        memory = psutil.virtual_memory()
        metrics.extend([
            '# HELP crm_system_memory_usage_bytes System memory usage in bytes',
            '# TYPE crm_system_memory_usage_bytes gauge',
            f'crm_system_memory_usage_bytes {memory.used}',
            f'crm_system_memory_available_bytes {memory.available}',
            f'crm_system_memory_total_bytes {memory.total}',
            ''
        ])

        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        metrics.extend([
            '# HELP crm_system_cpu_usage_percent System CPU usage percentage',
            '# TYPE crm_system_cpu_usage_percent gauge',
            f'crm_system_cpu_usage_percent {cpu_percent:.2f}',
            ''
        ])

        # Disk metrics
        disk = psutil.disk_usage('/')
        metrics.extend([
            '# HELP crm_system_disk_usage_bytes System disk usage in bytes',
            '# TYPE crm_system_disk_usage_bytes gauge',
            f'crm_system_disk_usage_bytes {disk.used}',
            f'crm_system_disk_free_bytes {disk.free}',
            f'crm_system_disk_total_bytes {disk.total}',
            ''
        ])

        return metrics

    except Exception as e:
        return [f"# System metrics generation failed: {e}"]


def generate_database_metrics() -> list:
    """
    Generate database metrics in Prometheus format.

    Returns:
        list: List of Prometheus-formatted metric lines
    """
    try:
        from django.db import connection

        metrics = []

        # Test database performance
        start_time = time.time()
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        query_time = time.time() - start_time

        metrics.extend([
            '# HELP crm_database_query_duration_seconds Database query duration in seconds',
            '# TYPE crm_database_query_duration_seconds gauge',
            f'crm_database_query_duration_seconds {query_time:.4f}',
            ''
        ])

        # Connection pool metrics (if available)
        if hasattr(connection, 'pool') and connection.pool:
            pool = connection.pool
            metrics.extend([
                '# HELP crm_database_connections_active Number of active database connections',
                '# TYPE crm_database_connections_active gauge',
                f'crm_database_connections_active {getattr(pool, "checkedout", 0)}',
                '',
                '# HELP crm_database_connections_idle Number of idle database connections',
                '# TYPE crm_database_connections_idle gauge',
                f'crm_database_connections_idle {getattr(pool, "checkedin", 0)}',
                ''
            ])

        return metrics

    except Exception as e:
        return [f"# Database metrics generation failed: {e}"]


def generate_business_metrics() -> list:
    """
    Generate business metrics in Prometheus format.

    Returns:
        list: List of Prometheus-formatted metric lines
    """
    try:
        from crm.apps.authentication.models import User
        from crm.apps.contacts.models import Contact
        from crm.apps.deals.models import Deal
        from django.utils import timezone
        from datetime import timedelta

        metrics = []

        # User metrics
        total_users = User.objects.count()
        active_users_24h = User.objects.filter(
            last_login__gte=timezone.now() - timedelta(hours=24)
        ).count()

        metrics.extend([
            '# HELP crm_business_users_total Total number of users',
            '# TYPE crm_business_users_total gauge',
            f'crm_business_users_total {total_users}',
            '',
            '# HELP crm_business_users_active_24h Users active in last 24 hours',
            '# TYPE crm_business_users_active_24h gauge',
            f'crm_business_users_active_24h {active_users_24h}',
            ''
        ])

        # Contact metrics
        total_contacts = Contact.objects.count()
        new_contacts_24h = Contact.objects.filter(
            created_at__gte=timezone.now() - timedelta(hours=24)
        ).count()

        metrics.extend([
            '# HELP crm_business_contacts_total Total number of contacts',
            '# TYPE crm_business_contacts_total gauge',
            f'crm_business_contacts_total {total_contacts}',
            '',
            '# HELP crm_business_contacts_created_24h Contacts created in last 24 hours',
            '# TYPE crm_business_contacts_created_24h gauge',
            f'crm_business_contacts_created_24h {new_contacts_24h}',
            ''
        ])

        # Deal metrics
        total_deals = Deal.objects.count()
        new_deals_24h = Deal.objects.filter(
            created_at__gte=timezone.now() - timedelta(hours=24)
        ).count()
        won_deals_24h = Deal.objects.filter(
            stage='closed_won',
            updated_at__gte=timezone.now() - timedelta(hours=24)
        ).count()

        metrics.extend([
            '# HELP crm_business_deals_total Total number of deals',
            '# TYPE crm_business_deals_total gauge',
            f'crm_business_deals_total {total_deals}',
            '',
            '# HELP crm_business_deals_created_24h Deals created in last 24 hours',
            '# TYPE crm_business_deals_created_24h gauge',
            f'crm_business_deals_created_24h {new_deals_24h}',
            '',
            '# HELP crm_business_deals_won_24h Deals won in last 24 hours',
            '# TYPE crm_business_deals_won_24h gauge',
            f'crm_business_deals_won_24h {won_deals_24h}',
            ''
        ])

        return metrics

    except Exception as e:
        return [f"# Business metrics generation failed: {e}"]


def get_business_metrics() -> Optional[Dict[str, Any]]:
    """
    Get business metrics for health check response.

    Returns:
        Optional[Dict[str, Any]]: Business metrics or None if unavailable
    """
    try:
        from crm.apps.authentication.models import User
        from crm.apps.contacts.models import Contact
        from crm.apps.deals.models import Deal
        from django.utils import timezone
        from datetime import timedelta

        now_24h_ago = timezone.now() - timedelta(hours=24)

        return {
            'active_users': User.objects.filter(
                last_login__gte=now_24h_ago
            ).count(),
            'user_registrations_24h': User.objects.filter(
                date_joined__gte=now_24h_ago
            ).count(),
            'total_contacts': Contact.objects.count(),
            'new_contacts_24h': Contact.objects.filter(
                created_at__gte=now_24h_ago
            ).count(),
            'total_deals': Deal.objects.count(),
            'new_deals_24h': Deal.objects.filter(
                created_at__gte=now_24h_ago
            ).count(),
            'deal_conversions_24h': Deal.objects.filter(
                stage='closed_won',
                updated_at__gte=now_24h_ago
            ).count(),
        }

    except Exception:
        return None