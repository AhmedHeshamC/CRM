"""
Enterprise-grade rate limiting middleware and utilities.

This module implements comprehensive rate limiting following enterprise security best practices:
- IP-based rate limiting for anonymous users
- User-based rate limiting for authenticated users
- API key rate limiting for external integrations
- Tiered rate limits based on user roles
- Distributed rate limiting with Redis
"""

import time
import hashlib
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
from django.core.cache import cache
from django.http import JsonResponse
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone
import structlog
import logging

logger = structlog.get_logger(__name__)


class RateLimitExceeded(Exception):
    """Custom exception for rate limit violations."""
    def __init__(self, message: str, retry_after: int = None):
        self.message = message
        self.retry_after = retry_after
        super().__init__(message)


class RateLimitConfig:
    """Rate limit configuration following enterprise standards."""

    # Rate limits per minute/hour/day
    RATE_LIMITS = {
        # Anonymous users (most restrictive)
        'anonymous': {
            'per_minute': 20,
            'per_hour': 100,
            'per_day': 500,
        },

        # Support users
        'support': {
            'per_minute': 50,
            'per_hour': 500,
            'per_day': 5000,
        },

        # Sales users
        'sales': {
            'per_minute': 100,
            'per_hour': 1000,
            'per_day': 10000,
        },

        # Manager users
        'manager': {
            'per_minute': 200,
            'per_hour': 2000,
            'per_day': 20000,
        },

        # Admin users (least restrictive)
        'admin': {
            'per_minute': 500,
            'per_hour': 5000,
            'per_day': 50000,
        },

        # API keys (external integrations)
        'api_key': {
            'per_minute': 1000,
            'per_hour': 10000,
            'per_day': 100000,
        },
    }

    # Endpoints with special rate limits
    ENDPOINT_RATE_LIMITS = {
        'login': {
            'per_minute': 5,
            'per_hour': 20,
            'per_day': 50,
        },
        'register': {
            'per_minute': 3,
            'per_hour': 10,
            'per_day': 25,
        },
        'password_reset': {
            'per_minute': 3,
            'per_hour': 5,
            'per_day': 10,
        },
        'export': {
            'per_minute': 10,
            'per_hour': 50,
            'per_day': 200,
        },
        'bulk_operations': {
            'per_minute': 20,
            'per_hour': 100,
            'per_day': 500,
        },
    }


class RateLimitMiddleware(MiddlewareMixin):
    """
    Enterprise-grade rate limiting middleware.

    This middleware implements comprehensive rate limiting with the following features:
    - Multiple rate limit periods (minute, hour, day)
    - Role-based rate limiting
    - IP-based limiting for anonymous users
    - API key rate limiting
    - Distributed rate limiting with Redis
    - Detailed logging and monitoring
    """

    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)

        # Configure structured logger for rate limiting
        self.rate_limit_logger = structlog.get_logger('rate_limiting')

        # Cache configuration
        self.cache_timeout = 86400  # 24 hours
        self.burst_window = 60  # 1 minute

    def process_request(self, request):
        """
        Process incoming request for rate limiting.

        Args:
            request: Django request object

        Returns:
            JsonResponse if rate limited, None otherwise
        """
        try:
            # Skip rate limiting for health checks and admin
            if self._should_skip_rate_limiting(request):
                return None

            # Get rate limit key and check limits
            rate_limit_key = self._get_rate_limit_key(request)
            limits = self._get_applicable_limits(request)

            # Check rate limits
            if self._is_rate_limited(rate_limit_key, limits, request):
                return self._create_rate_limit_response(request, rate_limit_key)

            # Log successful request
            self._log_request(request, rate_limit_key)

        except Exception as e:
            # Log error but don't block requests
            self.rate_limit_logger.error(
                'rate_limiting_error',
                error=str(e),
                path=request.path,
                method=request.method,
                user_id=getattr(request.user, 'id', None) if hasattr(request, 'user') else None
            )

        return None

    def _should_skip_rate_limiting(self, request) -> bool:
        """Check if request should skip rate limiting."""
        skip_paths = [
            '/health/',
            '/api/v1/monitoring/',
            '/admin/',
            '/static/',
            '/media/',
        ]

        # Skip health checks and static files
        if any(request.path.startswith(path) for path in skip_paths):
            return True

        # Skip internal requests (e.g., from load balancer)
        if request.META.get('HTTP_X_FORWARDED_FOR') in ['127.0.0.1', '::1']:
            return True

        return False

    def _get_rate_limit_key(self, request) -> str:
        """
        Generate rate limit key for the request.

        Returns:
            Rate limit key string
        """
        # Check for API key first
        api_key = self._extract_api_key(request)
        if api_key:
            return f"api_key:{hashlib.sha256(api_key.encode()).hexdigest()[:16]}"

        # Use user ID for authenticated users
        if hasattr(request, 'user') and request.user.is_authenticated:
            return f"user:{request.user.id}"

        # Use IP address for anonymous users
        ip = self._get_client_ip(request)
        return f"ip:{hashlib.sha256(ip.encode()).hexdigest()[:16]}"

    def _get_applicable_limits(self, request) -> Dict[str, int]:
        """
        Get applicable rate limits for the request.

        Returns:
            Dictionary of rate limits per period
        """
        # Check endpoint-specific limits first
        endpoint_type = self._get_endpoint_type(request)
        if endpoint_type in RateLimitConfig.ENDPOINT_RATE_LIMITS:
            return RateLimitConfig.ENDPOINT_RATE_LIMITS[endpoint_type]

        # Get user role-based limits
        if hasattr(request, 'user') and request.user.is_authenticated:
            role = getattr(request.user, 'role', 'sales')
            return RateLimitConfig.RATE_LIMITS.get(role, RateLimitConfig.RATE_LIMITS['sales'])

        # Check for API key
        if self._extract_api_key(request):
            return RateLimitConfig.RATE_LIMITS['api_key']

        # Default to anonymous limits
        return RateLimitConfig.RATE_LIMITS['anonymous']

    def _get_endpoint_type(self, request) -> Optional[str]:
        """Determine endpoint type for special rate limiting."""
        path = request.path.lower()

        if 'login' in path or 'auth/token' in path:
            return 'login'
        elif 'register' in path or 'signup' in path:
            return 'register'
        elif 'password' in path and 'reset' in path:
            return 'password_reset'
        elif 'export' in path:
            return 'export'
        elif 'bulk' in path:
            return 'bulk_operations'

        return None

    def _extract_api_key(self, request) -> Optional[str]:
        """Extract API key from request headers."""
        # Check Authorization header for Bearer token
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]  # Remove 'Bearer ' prefix
            # Check if it's an API key (longer than JWT)
            if len(token) > 100:
                return token

        # Check X-API-Key header
        return request.META.get('HTTP_X_API_KEY')

    def _get_client_ip(self, request) -> str:
        """Get client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '0.0.0.0')
        return ip

    def _is_rate_limited(self, key: str, limits: Dict[str, int], request) -> bool:
        """
        Check if request is rate limited.

        Args:
            key: Rate limit key
            limits: Rate limits per period
            request: Django request object

        Returns:
            True if rate limited, False otherwise
        """
        now = timezone.now()

        for period, max_requests in limits.items():
            cache_key = f"rate_limit:{key}:{period}"

            # Get current request count
            current_count = cache.get(cache_key, 0)

            # Check if limit exceeded
            if current_count >= max_requests:
                self.rate_limit_logger.warning(
                    'rate_limit_exceeded',
                    key=key,
                    period=period,
                    current_count=current_count,
                    max_requests=max_requests,
                    path=request.path,
                    method=request.method,
                    ip=self._get_client_ip(request),
                    user_id=getattr(request.user, 'id', None) if hasattr(request, 'user') else None
                )
                return True

            # Increment counter
            cache.set(cache_key, current_count + 1, self._get_cache_ttl(period))

        return False

    def _get_cache_ttl(self, period: str) -> int:
        """Get cache TTL for rate limit period."""
        ttl_map = {
            'per_minute': 60,
            'per_hour': 3600,
            'per_day': 86400,
        }
        return ttl_map.get(period, 3600)

    def _create_rate_limit_response(self, request, rate_limit_key: str) -> JsonResponse:
        """
        Create rate limit exceeded response.

        Args:
            request: Django request object
            rate_limit_key: Rate limit key that exceeded limits

        Returns:
            JsonResponse with rate limit information
        """
        # Get retry after time (in seconds)
        retry_after = self._get_retry_after(rate_limit_key)

        response = JsonResponse({
            'error': 'Rate limit exceeded',
            'message': 'Too many requests. Please try again later.',
            'retry_after': retry_after,
            'rate_limit_key': rate_limit_key[:8] + '...',  # Partial key for debugging
        }, status=429)

        # Add rate limit headers
        response['Retry-After'] = str(retry_after)
        response['X-RateLimit-Limit'] = str(self._get_rate_limit_total())
        response['X-RateLimit-Remaining'] = '0'
        response['X-RateLimit-Reset'] = str(int(time.time()) + retry_after)

        # Log rate limit violation
        self.rate_limit_logger.warning(
            'rate_limit_blocked_request',
            key=rate_limit_key,
            retry_after=retry_after,
            path=request.path,
            method=request.method,
            ip=self._get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:200],
            user_id=getattr(request.user, 'id', None) if hasattr(request, 'user') else None
        )

        return response

    def _get_retry_after(self, rate_limit_key: str) -> int:
        """Calculate retry after time in seconds."""
        # For simplicity, return 60 seconds (can be enhanced with actual window calculation)
        return 60

    def _get_rate_limit_total(self) -> int:
        """Get total rate limit for the current user."""
        # This would depend on the user's role and current context
        return 1000  # Default value

    def _log_request(self, request, rate_limit_key: str):
        """Log successful request for monitoring."""
        self.rate_limit_logger.info(
            'request_allowed',
            key=rate_limit_key,
            path=request.path,
            method=request.method,
            ip=self._get_client_ip(request),
            user_id=getattr(request.user, 'id', None) if hasattr(request, 'user') else None
        )


# Rate limiting decorator for views
def rate_limit(scope: str, **kwargs):
    """
    Decorator for rate limiting specific views.

    Args:
        scope: Rate limit scope (e.g., 'login', 'export')
        **kwargs: Additional rate limit parameters
    """
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            # Implement view-level rate limiting here
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


# Utility functions for rate limit management
def get_rate_limit_status(user=None, ip_address=None, api_key=None) -> Dict[str, Any]:
    """
    Get current rate limit status for a user/IP/API key.

    Returns:
        Dictionary with rate limit information
    """
    status = {
        'limits': {},
        'current_usage': {},
        'reset_times': {},
    }

    # Implementation would query Redis/cache for current usage
    return status


def clear_rate_limits(user=None, ip_address=None, api_key=None):
    """
    Clear rate limits for a user/IP/API key.

    Used for admin purposes or when lifting restrictions.
    """
    # Implementation would clear relevant cache keys
    pass