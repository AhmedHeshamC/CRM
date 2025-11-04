"""
Test suite for Rate Limiting Middleware
Following SOLID principles and TDD approach
"""

import time
import redis
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.http import JsonResponse
from rest_framework import status
from shared.security.rate_limiting import RateLimitingMiddleware
from shared.security.exceptions import RateLimitExceededError

User = get_user_model()


class RateLimitingMiddlewareTest(TestCase):
    """
    Test suite for RateLimitingMiddleware
    Following SOLID principles with comprehensive test coverage
    """

    def setUp(self):
        """
        Set up test environment
        Following Single Responsibility Principle
        """
        self.factory = RequestFactory()
        self.middleware = RateLimitingMiddleware(get_response=lambda r: JsonResponse({"status": "ok"}))
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            role='sales'
        )
        cache.clear()

    def test_rate_limiting_middleware_initialization(self):
        """
        Test middleware initialization
        Following SOLID principles
        """
        self.assertIsNotNone(self.middleware)
        self.assertEqual(self.middleware.rate_limit, 100)  # 100 requests per minute
        self.assertEqual(self.middleware.window_seconds, 60)

    def test_unauthenticated_user_rate_limiting(self):
        """
        Test rate limiting for unauthenticated users
        Following Open/Closed Principle for extensibility
        """
        # Create 99 requests - should all pass
        for i in range(99):
            request = self.factory.get('/api/v1/contacts/')
            request.user = None
            response = self.middleware(request)
            self.assertEqual(response.status_code, 200)

        # 100th request should pass
        request = self.factory.get('/api/v1/contacts/')
        request.user = None
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)

        # 101st request should be rate limited
        request = self.factory.get('/api/v1/contacts/')
        request.user = None
        response = self.middleware(request)
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_authenticated_user_rate_limiting(self):
        """
        Test rate limiting for authenticated users
        Following Single Responsibility Principle
        """
        # Create 100 requests - should all pass for authenticated user
        for i in range(100):
            request = self.factory.get('/api/v1/contacts/')
            request.user = self.user
            response = self.middleware(request)
            self.assertEqual(response.status_code, 200)

        # 101st request should be rate limited
        request = self.factory.get('/api/v1/contacts/')
        request.user = self.user
        response = self.middleware(request)
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_rate_limiting_per_user_isolation(self):
        """
        Test that rate limits are isolated per user
        Following Single Responsibility Principle
        """
        user2 = User.objects.create_user(
            email='test2@example.com',
            password='testpass123',
            role='manager'
        )

        # User 1 makes 100 requests
        for i in range(100):
            request = self.factory.get('/api/v1/contacts/')
            request.user = self.user
            response = self.middleware(request)
            self.assertEqual(response.status_code, 200)

        # User 1 should be rate limited
        request = self.factory.get('/api/v1/contacts/')
        request.user = self.user
        response = self.middleware(request)
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

        # User 2 should still be able to make requests
        request = self.factory.get('/api/v1/contacts/')
        request.user = user2
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)

    def test_rate_limiting_window_reset(self):
        """
        Test rate limiting window reset after time passes
        Following SOLID principles
        """
        # Make 100 requests
        for i in range(100):
            request = self.factory.get('/api/v1/contacts/')
            request.user = self.user
            response = self.middleware(request)
            self.assertEqual(response.status_code, 200)

        # Should be rate limited
        request = self.factory.get('/api/v1/contacts/')
        request.user = self.user
        response = self.middleware(request)
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

        # Mock time passing (window reset)
        with patch('time.time', return_value=time.time() + 61):
            request = self.factory.get('/api/v1/contacts/')
            request.user = self.user
            response = self.middleware(request)
            self.assertEqual(response.status_code, 200)

    def test_rate_limiting_exempt_paths(self):
        """
        Test exempt paths are not rate limited
        Following Open/Closed Principle for extensibility
        """
        exempt_paths = [
            '/health/',
            '/metrics/',
            '/api/schema/',
            '/api/docs/',
            '/api/redoc/',
            '/admin/',
        ]

        for path in exempt_paths:
            # Make many requests to exempt path
            for i in range(150):
                request = self.factory.get(path)
                request.user = self.user
                response = self.middleware(request)
                self.assertEqual(response.status_code, 200, f"Path {path} should be exempt from rate limiting")

    def test_rate_limiting_different_methods(self):
        """
        Test rate limiting applies to different HTTP methods
        Following SOLID principles
        """
        methods = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']

        for method in methods:
            # Make 100 requests with each method
            for i in range(100):
                if method == 'GET':
                    request = self.factory.get('/api/v1/contacts/')
                elif method == 'POST':
                    request = self.factory.post('/api/v1/contacts/')
                elif method == 'PUT':
                    request = self.factory.put('/api/v1/contacts/1/')
                elif method == 'PATCH':
                    request = self.factory.patch('/api/v1/contacts/1/')
                elif method == 'DELETE':
                    request = self.factory.delete('/api/v1/contacts/1/')

                request.user = self.user
                response = self.middleware(request)
                self.assertEqual(response.status_code, 200, f"Method {method} request {i+1} should pass")

            # 101st request should be rate limited
            if method == 'GET':
                request = self.factory.get('/api/v1/contacts/')
            elif method == 'POST':
                request = self.factory.post('/api/v1/contacts/')
            elif method == 'PUT':
                request = self.factory.put('/api/v1/contacts/1/')
            elif method == 'PATCH':
                request = self.factory.patch('/api/v1/contacts/1/')
            elif method == 'DELETE':
                request = self.factory.delete('/api/v1/contacts/1/')

            request.user = self.user
            response = self.middleware(request)
            self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS, f"Method {method} should be rate limited")

            # Reset for next method
            cache.clear()

    @patch('shared.security.rate_limiting.cache')
    def test_rate_limiting_cache_error_handling(self, mock_cache):
        """
        Test graceful handling of cache errors
        Following SOLID principles for error handling
        """
        # Simulate cache error
        mock_cache.get.side_effect = redis.RedisError("Cache connection failed")
        mock_cache.set.side_effect = redis.RedisError("Cache connection failed")

        # Request should still pass (fail-open behavior)
        request = self.factory.get('/api/v1/contacts/')
        request.user = self.user
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)

    @patch('shared.security.rate_limiting.cache')
    def test_rate_limiting_with_custom_config(self, mock_cache):
        """
        Test rate limiting with custom configuration
        Following Open/Closed Principle
        """
        # Create middleware with custom rate limit
        custom_middleware = RateLimitingMiddleware(
            get_response=lambda r: JsonResponse({"status": "ok"}),
            rate_limit=50,
            window_seconds=30
        )

        # Make 50 requests - should all pass
        for i in range(50):
            request = self.factory.get('/api/v1/contacts/')
            request.user = self.user
            response = custom_middleware(request)
            self.assertEqual(response.status_code, 200)

        # 51st request should be rate limited
        request = self.factory.get('/api/v1/contacts/')
        request.user = self.user
        response = custom_middleware(request)
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_rate_limiting_response_headers(self):
        """
        Test rate limiting response headers
        Following SOLID principles
        """
        # Make some requests
        for i in range(10):
            request = self.factory.get('/api/v1/contacts/')
            request.user = self.user
            response = self.middleware(request)
            self.assertEqual(response.status_code, 200)

        # Check rate limit headers
        request = self.factory.get('/api/v1/contacts/')
        request.user = self.user
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)

        # Should have rate limit headers
        self.assertIn('X-RateLimit-Limit', response)
        self.assertIn('X-RateLimit-Remaining', response)
        self.assertIn('X-RateLimit-Reset', response)

        self.assertEqual(int(response['X-RateLimit-Limit']), 100)
        self.assertEqual(int(response['X-RateLimit-Remaining']), 89)  # 100 - 11 requests made

    def test_rate_limiting_ip_based_fallback(self):
        """
        Test IP-based rate limiting fallback for unauthenticated users
        Following Single Responsibility Principle
        """
        # Simulate requests from same IP without user
        ip_address = '192.168.1.100'

        for i in range(100):
            request = self.factory.get('/api/v1/contacts/')
            request.user = None
            request.META['REMOTE_ADDR'] = ip_address
            response = self.middleware(request)
            self.assertEqual(response.status_code, 200)

        # 101st request should be rate limited
        request = self.factory.get('/api/v1/contacts/')
        request.user = None
        request.META['REMOTE_ADDR'] = ip_address
        response = self.middleware(request)
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_rate_limiting_admin_exemption(self):
        """
        Test admin users are exempt from rate limiting
        Following Open/Closed Principle
        """
        admin_user = User.objects.create_user(
            email='admin@example.com',
            password='adminpass123',
            role='admin'
        )

        # Admin should be able to make unlimited requests
        for i in range(200):
            request = self.factory.get('/api/v1/contacts/')
            request.user = admin_user
            response = self.middleware(request)
            self.assertEqual(response.status_code, 200, f"Admin request {i+1} should pass")

    def test_rate_limiting_concurrent_requests(self):
        """
        Test rate limiting with concurrent requests
        Following SOLID principles
        """
        # Simulate concurrent requests by setting count directly
        cache_key = f"rate_limit:user:{self.user.id}"

        # Simulate 99 concurrent requests
        cache.set(cache_key, 99, timeout=60)

        # 100th request should pass
        request = self.factory.get('/api/v1/contacts/')
        request.user = self.user
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)

        # 101st request should be rate limited
        request = self.factory.get('/api/v1/contacts/')
        request.user = self.user
        response = self.middleware(request)
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_rate_limiting_error_response_format(self):
        """
        Test rate limiting error response format
        Following SOLID principles
        """
        # Make 100 requests
        for i in range(100):
            request = self.factory.get('/api/v1/contacts/')
            request.user = self.user
            response = self.middleware(request)
            self.assertEqual(response.status_code, 200)

        # Get rate limited response
        request = self.factory.get('/api/v1/contacts/')
        request.user = self.user
        response = self.middleware(request)
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

        # Check response format
        response_data = response.json()
        self.assertIn('error', response_data)
        self.assertIn('code', response_data)
        self.assertIn('detail', response_data)
        self.assertEqual(response_data['error'], 'Rate limit exceeded')
        self.assertEqual(response_data['code'], 'rate_limited')
        self.assertIn('Retry-After', response)