"""
Performance monitoring middleware.

This middleware implements request/response time tracking and performance metrics
following SOLID principles:
- Single Responsibility: Focuses solely on performance monitoring
- Open/Closed: Can be extended without modification
- Dependency Inversion: Depends on logging and metrics abstractions
"""

import time
import uuid
import json
import logging
from typing import Dict, Any, Optional

from django.http import HttpResponse
from django.utils.deprecation import MiddlewareMixin
from django.utils import timezone
from django.conf import settings

import structlog

logger = structlog.get_logger(__name__)


class PerformanceMonitoringMiddleware(MiddlewareMixin):
    """
    Middleware for monitoring API performance and logging request metrics.

    This middleware tracks request/response times, error rates, and other
    performance metrics for all API requests. It follows the Single
    Responsibility Principle by focusing solely on performance monitoring.
    """

    def __init__(self, get_response):
        """
        Initialize the performance monitoring middleware.

        Args:
            get_response: Django's get_response callable
        """
        self.get_response = get_response
        super().__init__(get_response)

        # Configure structured logger for performance data
        self.performance_logger = structlog.get_logger('performance')

        # Initialize metrics collector if available
        try:
            from .metrics import MetricsCollector
            self.metrics_collector = MetricsCollector()
        except ImportError:
            self.metrics_collector = None

    def process_request(self, request):
        """
        Process incoming request and start timing.

        Args:
            request: Django request object
        """
        # Add unique request ID for tracing
        request.request_id = str(uuid.uuid4())

        # Record start time
        request.start_time = time.time()

        # Get client IP address (considering proxy headers)
        request.client_ip = self._get_client_ip(request)

        # Log request start
        if self._should_log_request(request):
            self.performance_logger.info(
                'request_started',
                request_id=request.request_id,
                method=request.method,
                path=request.path,
                client_ip=request.client_ip,
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                content_type=request.content_type,
                timestamp=timezone.now().isoformat()
            )

    def process_response(self, request, response):
        """
        Process response and log performance metrics.

        Args:
            request: Django request object
            response: Django response object

        Returns:
            HttpResponse: The processed response
        """
        try:
            # Calculate duration
            if hasattr(request, 'start_time'):
                duration_ms = (time.time() - request.start_time) * 1000
                request.duration_ms = duration_ms
            else:
                duration_ms = 0

            # Log performance data
            if self._should_log_request(request):
                self._log_request_performance(request, response, duration_ms)

            # Update metrics
            if self.metrics_collector:
                self._update_metrics(request, response, duration_ms)

            # Add performance headers (useful for debugging)
            response['X-Request-ID'] = getattr(request, 'request_id', 'unknown')
            response['X-Response-Time-MS'] = f"{duration_ms:.2f}"

        except Exception as e:
            # Middleware should never break the request
            logger.error(
                'performance_monitoring_error',
                error=str(e),
                path=getattr(request, 'path', 'unknown'),
                method=getattr(request, 'method', 'unknown')
            )

        return response


class SecurityMiddleware(MiddlewareMixin):
    """
    Simple security middleware following KISS principles.

    Provides basic security features without over-engineering.
    Focuses on essential security headers only.
    """

    def __init__(self, get_response):
        """Initialize security middleware."""
        self.get_response = get_response
        super().__init__(get_response)

    def process_response(self, request, response):
        """
        Add security headers to response.

        Args:
            request: Django request object
            response: Django response object

        Returns:
            HttpResponse: Response with security headers
        """
        # Add security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'

        return response

    def process_exception(self, request, exception):
        """
        Process unhandled exceptions and log as errors.

        Args:
            request: Django request object
            exception: The exception that was raised
        """
        try:
            # Calculate duration for failed request
            if hasattr(request, 'start_time'):
                duration_ms = (time.time() - request.start_time) * 1000
            else:
                duration_ms = 0

            # Log exception as performance event
            self.performance_logger.error(
                'request_exception',
                request_id=getattr(request, 'request_id', 'unknown'),
                method=getattr(request, 'method', 'unknown'),
                path=getattr(request, 'path', 'unknown'),
                client_ip=getattr(request, 'client_ip', 'unknown'),
                exception_type=type(exception).__name__,
                exception_message=str(exception),
                duration_ms=duration_ms,
                timestamp=timezone.now().isoformat()
            )

            # Update error metrics
            if self.metrics_collector:
                self._update_error_metrics(request, exception, duration_ms)

        except Exception as e:
            # Don't let logging errors break exception handling
            logger.error(
                'performance_exception_logging_error',
                logging_error=str(e),
                original_exception=str(exception)
            )

        # Don't handle the exception, let Django's normal exception handling proceed
        return None

    def _should_log_request(self, request) -> bool:
        """
        Determine if request should be logged.

        Args:
            request: Django request object

        Returns:
            bool: True if request should be logged
        """
        # Skip health check and metrics endpoints to avoid log spam
        skip_paths = getattr(settings, 'PERFORMANCE_LOG_SKIP_PATHS', [
            '/health/',
            '/metrics/',
            '/api/schema/',
            '/static/',
            '/media/'
        ])

        return not any(request.path.startswith(path) for path in skip_paths)

    def _log_request_performance(self, request, response, duration_ms: float):
        """
        Log detailed request performance information.

        Args:
            request: Django request object
            response: Django response object
            duration_ms: Request duration in milliseconds
        """
        # Get endpoint category for grouping
        endpoint_category = self._get_endpoint_category(request.path)

        # Build performance log data
        log_data = {
            'request_id': getattr(request, 'request_id', 'unknown'),
            'method': request.method,
            'path': request.path,
            'endpoint_category': endpoint_category,
            'status_code': response.status_code,
            'duration_ms': round(duration_ms, 2),
            'client_ip': getattr(request, 'client_ip', 'unknown'),
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            'timestamp': timezone.now().isoformat()
        }

        # Add user information if available
        if hasattr(request, 'user') and request.user.is_authenticated:
            log_data.update({
                'user_id': request.user.id,
                'user_role': getattr(request.user, 'role', 'unknown'),
                'username': request.user.username
            })

        # Add request size if available
        if hasattr(request, 'body') and request.body:
            log_data['request_size_bytes'] = len(request.body)

        # Add response size if available
        if hasattr(response, 'content') and response.content:
            log_data['response_size_bytes'] = len(response.content)

        # Add database query information
        if hasattr(request, 'queries_logged'):
            log_data['db_query_count'] = len(getattr(request, 'queries_logged', []))

        # Determine log level based on performance
        log_level = 'info'
        if duration_ms > getattr(settings, 'SLOW_REQUEST_THRESHOLD_MS', 1000):
            log_level = 'warning'
            log_data['performance_issue'] = 'slow_request'
        elif response.status_code >= 400:
            log_level = 'warning'
            log_data['performance_issue'] = 'error_response'

        # Log the performance data
        getattr(self.performance_logger, log_level)(
            'request_completed',
            **log_data
        )

        # Log additional details for slow requests
        if duration_ms > getattr(settings, 'VERY_SLOW_REQUEST_THRESHOLD_MS', 5000):
            self.performance_logger.error(
                'very_slow_request',
                **log_data,
                query_details=getattr(request, 'queries_logged', [])
            )

    def _update_metrics(self, request, response, duration_ms: float):
        """
        Update Prometheus metrics for request performance.

        Args:
            request: Django request object
            response: Django response object
            duration_ms: Request duration in milliseconds
        """
        try:
            # Get endpoint category for metrics
            endpoint_category = self._get_endpoint_category(request.path)

            # Update request duration histogram
            self.metrics_collector.record_request_duration(
                method=request.method,
                endpoint=endpoint_category,
                status_code=response.status_code,
                duration_ms=duration_ms
            )

            # Update request count
            self.metrics_collector.increment_request_count(
                method=request.method,
                endpoint=endpoint_category,
                status_code=response.status_code
            )

            # Track slow requests
            if duration_ms > getattr(settings, 'SLOW_REQUEST_THRESHOLD_MS', 1000):
                self.metrics_collector.increment_slow_request_count(
                    method=request.method,
                    endpoint=endpoint_category
                )

            # Track error responses
            if response.status_code >= 400:
                self.metrics_collector.increment_error_count(
                    method=request.method,
                    endpoint=endpoint_category,
                    status_code=response.status_code
                )

        except Exception as e:
            logger.error(
                'metrics_update_error',
                error=str(e),
                path=getattr(request, 'path', 'unknown')
            )

    def _update_error_metrics(self, request, exception, duration_ms: float):
        """
        Update metrics for unhandled exceptions.

        Args:
            request: Django request object
            exception: The exception that occurred
            duration_ms: Request duration in milliseconds
        """
        try:
            endpoint_category = self._get_endpoint_category(request.path)

            # Track exceptions
            self.metrics_collector.record_exception(
                method=getattr(request, 'method', 'unknown'),
                endpoint=endpoint_category,
                exception_type=type(exception).__name__,
                duration_ms=duration_ms
            )

        except Exception as e:
            logger.error(
                'error_metrics_update_error',
                error=str(e)
            )

    def _get_client_ip(self, request) -> str:
        """
        Get client IP address considering proxy headers.

        Args:
            request: Django request object

        Returns:
            str: Client IP address
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', 'unknown')
        return ip

    def _get_endpoint_category(self, path: str) -> str:
        """
        Categorize endpoint for metrics grouping.

        Args:
            path: Request path

        Returns:
            str: Endpoint category
        """
        # Define path patterns and their categories
        path_patterns = {
            '/api/v1/contacts/': 'contacts',
            '/api/v1/deals/': 'deals',
            '/api/v1/activities/': 'activities',
            '/api/v1/auth/': 'auth',
            '/admin/': 'admin',
            '/health/': 'health',
            '/metrics/': 'metrics',
            '/api/schema/': 'documentation',
        }

        for pattern, category in path_patterns.items():
            if path.startswith(pattern):
                return category

        return 'other'


class DatabaseQueryLoggingMiddleware(MiddlewareMixin):
    """
    Middleware for logging database query performance.

    This middleware tracks database queries and their performance,
    helping identify slow queries and N+1 problems.
    """

    def __init__(self, get_response):
        """Initialize database query logging middleware."""
        self.get_response = get_response
        self.query_logger = structlog.get_logger('database_queries')

        # Configuration
        self.log_queries = getattr(settings, 'LOG_DATABASE_QUERIES', False)
        self.slow_query_threshold = getattr(settings, 'SLOW_QUERY_THRESHOLD_MS', 100)

        super().__init__(get_response)

    def process_request(self, request):
        """Initialize query tracking for request."""
        if self.log_queries:
            request.query_count = 0
            request.slow_queries = []
            from django.db import connection
            connection.use_debug_cursor = True
            connection.queries_log.clear()

    def process_response(self, request, response):
        """Log query performance for completed request."""
        if not self.log_queries:
            return response


class SecurityMiddleware(MiddlewareMixin):
    """
    Simple security middleware following KISS principles.

    Provides basic security features without over-engineering.
    Focuses on essential security headers only.
    """

    def __init__(self, get_response):
        """Initialize security middleware."""
        self.get_response = get_response
        super().__init__(get_response)

    def process_response(self, request, response):
        """
        Add security headers to response.

        Args:
            request: Django request object
            response: Django response object

        Returns:
            HttpResponse: Response with security headers
        """
        # Add security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'

        return response

        try:
            from django.db import connection

            # Get query information
            queries = getattr(connection, 'queries', [])
            if queries:
                query_count = len(queries)
                total_time = sum(float(q['time']) for q in queries)
                total_time_ms = total_time * 1000

                # Find slow queries
                slow_queries = [
                    {
                        'sql': q['sql'],
                        'time_ms': float(q['time']) * 1000
                    }
                    for q in queries
                    if float(q['time']) * 1000 > self.slow_query_threshold
                ]

                # Log query performance
                self.query_logger.info(
                    'database_queries_completed',
                    request_id=getattr(request, 'request_id', 'unknown'),
                    path=request.path,
                    method=request.method,
                    query_count=query_count,
                    total_time_ms=round(total_time_ms, 2),
                    slow_query_count=len(slow_queries),
                    avg_time_ms=round(total_time_ms / query_count, 2) if query_count > 0 else 0
                )

                # Log slow queries in detail
                for slow_query in slow_queries:
                    self.query_logger.warning(
                        'slow_database_query',
                        request_id=getattr(request, 'request_id', 'unknown'),
                        path=request.path,
                        sql=slow_query['sql'][:500],  # Truncate long queries
                        time_ms=round(slow_query['time_ms'], 2)
                    )

        except Exception as e:
            self.query_logger.error(
                'database_query_logging_error',
                error=str(e),
                path=getattr(request, 'path', 'unknown')
            )

        return response


class SecurityMiddleware(MiddlewareMixin):
    """
    Simple security middleware following KISS principles.

    Provides basic security features without over-engineering.
    Focuses on essential security headers only.
    """

    def __init__(self, get_response):
        """Initialize security middleware."""
        self.get_response = get_response
        super().__init__(get_response)

    def process_response(self, request, response):
        """
        Add security headers to response.

        Args:
            request: Django request object
            response: Django response object

        Returns:
            HttpResponse: Response with security headers
        """
        # Add security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'

        return response