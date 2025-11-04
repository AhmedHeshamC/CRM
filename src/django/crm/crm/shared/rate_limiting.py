"""
Simple Rate Limiting Implementation
Following KISS principle for basic rate limiting
"""

import time
from functools import wraps
from rest_framework.response import Response
from rest_framework import status

# Global rate limiter for login - KISS principle
_login_requests = []
_login_limit = 5
_login_window = 60

def rate_limit(max_requests=5, window_seconds=60):
    """
    KISS principle: Simple rate limiting decorator for login
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(self, request, *args, **kwargs):
            global _login_requests

            now = time.time()

            # Clean old requests (KISS principle: simple cleanup)
            _login_requests = [req_time for req_time in _login_requests
                             if now - req_time < window_seconds]

            # Check if rate limit exceeded
            if len(_login_requests) >= max_requests:
                return Response(
                    {'error': 'Rate limit exceeded. Please try again later.'},
                    status=status.HTTP_429_TOO_MANY_REQUESTS
                )

            # Add current request
            _login_requests.append(now)

            return view_func(self, request, *args, **kwargs)
        return wrapper
    return decorator