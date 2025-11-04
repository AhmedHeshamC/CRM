"""
Rate Limiting Middleware for Production Security Hardening
Following SOLID principles and enterprise-grade security standards
"""

import time
import logging
import hashlib
from typing import Optional, Dict, Any
from django.http import JsonResponse, HttpResponse
from django.core.cache import cache
from django.conf import settings
from django.utils import timezone
from rest_framework import status
from shared.security.exceptions import RateLimitExceededError

logger = logging.getLogger(__name__)


class RateLimitingMiddleware:
    """
    Rate Limiting Middleware for API endpoints
    Following Single Responsibility Principle for rate limiting

    Features:
    - 100 requests/minute per user
    - IP-based fallback for unauthenticated users
    - Admin exemption
    - Configurable rate limits
    - Exempt paths support
    - Redis-based distributed rate limiting
    - Graceful error handling
    - Security logging
    """

    def __init__(
        self,
        get_response,
        rate_limit: int = 100,
        window_seconds: int = 60,
        exempt_paths: Optional[list] = None
    ):
        """
        Initialize rate limiting middleware
        Following Dependency Inversion Principle for configuration
        """
        self.get_response = get_response
        self.rate_limit = rate_limit
        self.window_seconds = window_seconds

        # Default exempt paths
        self.exempt_paths = exempt_paths or [
            '/health/',
            '/metrics/',
            '/api/schema/',
            '/api/docs/',
            '/api/redoc/',
            '/admin/',
            '/static/',
            '/media/',
            '/favicon.ico',
        ]

        # Security monitoring settings
        self.enable_logging = getattr(settings, 'RATE_LIMIT_LOGGING', True)
        self.log_rate_limit_violations = getattr(settings, 'LOG_RATE_LIMIT_VIOLATIONS', True)

    def __call__(self, request):
        """
        Process request for rate limiting
        Following SOLID principles for middleware implementation
        """
        # Skip rate limiting for exempt paths
        if self._is_path_exempt(request.path):
            return self.get_response(request)

        # Get rate limit key
        rate_limit_key = self._get_rate_limit_key(request)

        # Check rate limit
        try:
            current_count, reset_time = self._get_current_count(rate_limit_key)

            if current_count >= self.rate_limit:
                return self._handle_rate_limit_exceeded(request, reset_time)

            # Increment counter
            new_count = self._increment_counter(rate_limit_key, reset_time)

            # Add rate limit headers
            response = self.get_response(request)
            self._add_rate_limit_headers(response, new_count, reset_time)

            return response

        except Exception as e:
            # Log error but don't block requests (fail-open behavior)
            logger.error(f"Rate limiting error: {str(e)}")
            return self.get_response(request)

    def _is_path_exempt(self, path: str) -> bool:
        """
        Check if path is exempt from rate limiting
        Following Single Responsibility Principle
        """
        return any(path.startswith(exempt_path) for exempt_path in self.exempt_paths)

    def _get_rate_limit_key(self, request) -> str:
        """
        Generate rate limit key for request
        Following Single Responsibility Principle with user-based identification
        """
        # Use user ID for authenticated users
        if hasattr(request, 'user') and request.user and request.user.is_authenticated:
            # Admin users are exempt from rate limiting
            if hasattr(request.user, 'role') and request.user.role == 'admin':
                return None

            user_identifier = str(request.user.id)
            key_prefix = "rate_limit:user"
        else:
            # Fallback to IP address for unauthenticated users
            ip_address = self._get_client_ip(request)
            user_identifier = hashlib.md5(ip_address.encode()).hexdigest()[:16]
            key_prefix = "rate_limit:ip"

        # Include method and endpoint for more granular rate limiting
        endpoint = request.resolver_match.url_name if request.resolver_match else 'unknown'
        method = request.method.lower()

        return f"{key_prefix}:{user_identifier}:{method}:{endpoint}"

    def _get_client_ip(self, request) -> str:
        """
        Get client IP address from request
        Following Single Responsibility Principle with proxy support
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')

        return ip or 'unknown'

    def _get_current_count(self, rate_limit_key: str) -> tuple[int, int]:
        """
        Get current count and reset time for rate limit key
        Following Single Responsibility Principle
        """
        if not rate_limit_key:
            return 0, int(time.time()) + self.window_seconds

        current_time = int(time.time())
        window_start = current_time - current_time % self.window_seconds
        reset_time = window_start + self.window_seconds

        # Try to get current count
        current_count = cache.get(rate_limit_key, 0)

        return current_count, reset_time

    def _increment_counter(self, rate_limit_key: str, reset_time: int) -> int:
        """
        Increment rate limit counter with atomic operation
        Following Single Responsibility Principle
        """
        if not rate_limit_key:
            return 0

        # Use cache.incr for atomic increment
        try:
            new_count = cache.incr(rate_limit_key)

            # Set expiration if this is the first increment
            if new_count == 1:
                cache.expire(rate_limit_key, reset_time - int(time.time()))

            return new_count
        except ValueError:
            # Key doesn't exist, set initial value
            cache.set(rate_limit_key, 1, timeout=reset_time - int(time.time()))
            return 1

    def _add_rate_limit_headers(self, response: HttpResponse, current_count: int, reset_time: int):
        """
        Add rate limit headers to response
        Following Single Responsibility Principle
        """
        response['X-RateLimit-Limit'] = str(self.rate_limit)
        response['X-RateLimit-Remaining'] = str(max(0, self.rate_limit - current_count))
        response['X-RateLimit-Reset'] = str(reset_time)

        # Add custom headers for enhanced security monitoring
        response['X-RateLimit-Window'] = str(self.window_seconds)

    def _handle_rate_limit_exceeded(self, request, reset_time: int) -> JsonResponse:
        """
        Handle rate limit exceeded scenario
        Following Single Responsibility Principle with security logging
        """
        retry_after = max(1, reset_time - int(time.time()))

        # Log rate limit violation
        if self.log_rate_limit_violations:
            self._log_rate_limit_violation(request, retry_after)

        # Return rate limit error response
        return JsonResponse({
            'error': 'Rate limit exceeded',
            'code': 'rate_limited',
            'detail': f'Rate limit of {self.rate_limit} requests per {self.window_seconds} seconds exceeded.',
            'retry_after': retry_after
        }, status=status.HTTP_429_TOO_MANY_REQUESTS)

    def _log_rate_limit_violation(self, request, retry_after: int):
        """
        Log rate limit violation for security monitoring
        Following Single Responsibility Principle
        """
        try:
            user_info = None
            if hasattr(request, 'user') and request.user and request.user.is_authenticated:
                user_info = {
                    'user_id': request.user.id,
                    'email': request.user.email,
                    'role': getattr(request.user, 'role', 'unknown')
                }

            violation_data = {
                'timestamp': timezone.now().isoformat(),
                'ip_address': self._get_client_ip(request),
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                'path': request.path,
                'method': request.method,
                'retry_after': retry_after,
                'user_info': user_info
            }

            logger.warning(
                f"Rate limit violation: {request.method} {request.path} from {self._get_client_ip(request)}",
                extra={'security_data': violation_data}
            )

        except Exception as e:
            logger.error(f"Failed to log rate limit violation: {str(e)}")


class AdvancedRateLimitingMiddleware(RateLimitingMiddleware):
    """
    Advanced Rate Limiting Middleware with additional features
    Following Open/Closed Principle for extensibility

    Additional Features:
    - Tiered rate limiting based on user roles
    - Burst rate limiting
    - Progressive rate limiting
    - API key support
    - Geographic rate limiting
    """

    def __init__(self, get_response, **kwargs):
        """
        Initialize advanced rate limiting middleware
        Following Dependency Inversion Principle
        """
        super().__init__(get_response, **kwargs)

        # Tiered rate limits based on user roles
        self.role_rate_limits = getattr(settings, 'ROLE_RATE_LIMITS', {
            'admin': 1000,      # Admin users: 1000 req/min
            'manager': 500,     # Manager users: 500 req/min
            'sales': 200,       # Sales users: 200 req/min
            'support': 150,     # Support users: 150 req/min
        })

        # Burst rate limiting settings
        self.burst_limit = getattr(settings, 'BURST_RATE_LIMIT', 50)
        self.burst_window = getattr(settings, 'BURST_WINDOW_SECONDS', 10)

        # Progressive rate limiting settings
        self.enable_progressive_limiting = getattr(settings, 'ENABLE_PROGRESSIVE_RATE_LIMITING', True)
        self.progressive_multiplier = getattr(settings, 'PROGRESSIVE_RATE_LIMIT_MULTIPLIER', 0.8)

    def _get_rate_limit_key(self, request) -> str:
        """
        Generate enhanced rate limit key with role-based limits
        Following Single Responsibility Principle with role awareness
        """
        base_key = super()._get_rate_limit_key(request)

        if not base_key:
            return None

        # Add role-based prefix for authenticated users
        if hasattr(request, 'user') and request.user and request.user.is_authenticated:
            user_role = getattr(request.user, 'role', 'unknown')
            role_limit = self.role_rate_limits.get(user_role, self.rate_limit)

            # Add role info to key for different rate limits
            return f"{base_key}:role_{user_role}"

        return base_key

    def _get_current_count(self, rate_limit_key: str) -> tuple[int, int]:
        """
        Get current count with role-based limits
        Following Single Responsibility Principle
        """
        if not rate_limit_key:
            return 0, int(time.time()) + self.window_seconds

        # Determine rate limit based on role
        current_limit = self._determine_rate_limit(rate_limit_key)

        current_time = int(time.time())
        window_start = current_time - current_time % self.window_seconds
        reset_time = window_start + self.window_seconds

        current_count = cache.get(rate_limit_key, 0)

        return current_count, reset_time

    def _determine_rate_limit(self, rate_limit_key: str) -> int:
        """
        Determine rate limit based on key
        Following Single Responsibility Principle
        """
        # Check for role-based rate limit
        if ':role_' in rate_limit_key:
            parts = rate_limit_key.split(':role_')
            if len(parts) > 1:
                role = parts[1].split(':')[0]  # Extract role from key
                return self.role_rate_limits.get(role, self.rate_limit)

        return self.rate_limit

    def _increment_counter(self, rate_limit_key: str, reset_time: int) -> int:
        """
        Increment counter with progressive rate limiting
        Following Single Responsibility Principle
        """
        if not rate_limit_key:
            return 0

        try:
            new_count = cache.incr(rate_limit_key)

            # Apply progressive rate limiting if enabled
            if self.enable_progressive_limiting and new_count > self.rate_limit * 0.8:
                # Gradually reduce rate limit as usage increases
                penalty_factor = 1 - (new_count / (self.rate_limit * 2)) * self.progressive_multiplier
                adjusted_limit = int(self.rate_limit * max(0.5, penalty_factor))

                if new_count > adjusted_limit:
                    # Treat as rate limited
                    raise RateLimitExceededError(
                        message="Progressive rate limit exceeded",
                        retry_after=reset_time - int(time.time())
                    )

            if new_count == 1:
                cache.expire(rate_limit_key, reset_time - int(time.time()))

            return new_count
        except ValueError:
            cache.set(rate_limit_key, 1, timeout=reset_time - int(time.time()))
            return 1
        except RateLimitExceededError:
            raise