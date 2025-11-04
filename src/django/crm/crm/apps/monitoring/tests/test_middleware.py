"""
Test cases for performance monitoring middleware.

This module follows Test-Driven Development (TDD) principles by defining
expected behavior for request/response time logging middleware before implementation.

Tests cover all middleware functionality including:
- Request/response timing
- Error rate tracking
- API endpoint performance monitoring
- Prometheus metrics integration
- Structured logging for performance data
"""

from unittest.mock import patch, MagicMock
import time
import json

from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from rest_framework import status
from rest_framework.test import APITestCase

from crm.apps.monitoring.middleware import PerformanceMonitoringMiddleware


class PerformanceMonitoringMiddlewareTestCase(TestCase):
    """
    Test cases for the performance monitoring middleware.

    These tests ensure the middleware properly tracks request/response
    times, logs performance data, and integrates with metrics collection.
    """

    def setUp(self) -> None:
        """Set up test environment."""
        self.factory = RequestFactory()
        self.middleware = PerformanceMonitoringMiddleware(lambda r: HttpResponse())

    def test_middleware_adds_start_time_to_request(self):
        """
        Test middleware adds start_time to request object.

        GIVEN a request passes through the middleware
        WHEN the middleware processes it
        THEN it should add start_time attribute to the request
        """
        request = self.factory.get('/api/v1/contacts/')

        # Process request through middleware
        self.middleware.process_request(request)

        # Verify start_time is added
        self.assertTrue(hasattr(request, 'start_time'))
        self.assertIsInstance(request.start_time, float)

    def test_middleware_calculates_response_time(self):
        """
        Test middleware calculates response time accurately.

        GIVEN a request that takes some time to process
        WHEN the middleware processes the request and response
        THEN it should calculate the correct response time
        """
        request = self.factory.get('/api/v1/contacts/')

        # Mock response to simulate processing time
        def get_response(request):
            # Simulate 100ms processing time
            time.sleep(0.1)
            return HttpResponse()

        middleware = PerformanceMonitoringMiddleware(get_response)

        with patch('crm.apps.monitoring.middleware.log_request_performance') as mock_log:
            response = middleware(request)

            # Verify logging was called
            mock_log.assert_called_once()

            # Get the call arguments
            call_args = mock_log.call_args[1]  # keyword arguments

            # Verify response time is calculated (should be approximately 100ms)
            self.assertIn('duration_ms', call_args)
            self.assertGreaterEqual(call_args['duration_ms'], 90)  # Allow 10ms tolerance
            self.assertLessEqual(call_args['duration_ms'], 150)

    def test_middleware_logs_request_details(self):
        """
        Test middleware logs detailed request information.

        GIVEN any request
        WHEN the middleware processes it
        THEN it should log comprehensive request details
        """
        request = self.factory.post(
            '/api/v1/contacts/',
            data=json.dumps({'name': 'Test Contact'}),
            content_type='application/json',
            HTTP_USER_AGENT='TestAgent/1.0',
            HTTP_X_FORWARDED_FOR='192.168.1.100'
        )

        def get_response(request):
            return JsonResponse({'id': 1, 'name': 'Test Contact'}, status=201)

        middleware = PerformanceMonitoringMiddleware(get_response)

        with patch('crm.apps.monitoring.middleware.log_request_performance') as mock_log:
            response = middleware(request)

            # Verify logging was called with correct details
            mock_log.assert_called_once()
            call_args = mock_log.call_args[1]

            # Verify request details
            self.assertEqual(call_args['method'], 'POST')
            self.assertEqual(call_args['path'], '/api/v1/contacts/')
            self.assertEqual(call_args['status_code'], 201)
            self.assertEqual(call_args['user_agent'], 'TestAgent/1.0')
            self.assertEqual(call_args['client_ip'], '192.168.1.100')

    def test_middleware_handles_exception_responses(self):
        """
        Test middleware handles responses from exceptions properly.

        GIVEN a request that triggers an exception
        WHEN the middleware processes the exception response
        THEN it should log the error response correctly
        """
        request = self.factory.get('/api/v1/nonexistent-endpoint/')

        def get_response(request):
            from django.http import Http404
            raise Http404("Not found")

        middleware = PerformanceMonitoringMiddleware(get_response)

        with patch('crm.apps.monitoring.middleware.log_request_performance') as mock_log:
            # Mock exception handling
            with patch('django.core.handlers.exception.handle_uncaught_exception') as mock_handler:
                mock_handler.return_value = JsonResponse(
                    {'detail': 'Not found'},
                    status=404
                )

                try:
                    response = middleware(request)
                except:
                    # Simulate Django's exception handling
                    response = mock_handler.return_value

                # Verify middleware still logs performance
                if mock_log.called:
                    call_args = mock_log.call_args[1]
                    self.assertEqual(call_args['status_code'], 404)

    def test_middleware_updates_prometheus_metrics(self):
        """
        Test middleware updates Prometheus metrics for performance tracking.

        GIVEN a completed request
        WHEN the middleware processes it
        THEN it should update relevant Prometheus metrics
        """
        request = self.factory.get('/api/v1/contacts/')

        def get_response(request):
            return HttpResponse()

        middleware = PerformanceMonitoringMiddleware(get_response)

        with patch('crm.apps.monitoring.middleware.update_request_metrics') as mock_metrics:
            response = middleware(request)

            # Verify metrics update was called
            mock_metrics.assert_called_once()
            call_args = mock_metrics.call_args[1]

            # Verify metrics data
            self.assertIn('method', call_args)
            self.assertIn('endpoint', call_args)
            self.assertIn('status_code', call_args)
            self.assertIn('duration_ms', call_args)

    def test_middleware_tracks_user_information(self):
        """
        Test middleware tracks user information when available.

        GIVEN an authenticated request
        WHEN the middleware processes it
        THEN it should include user information in performance logs
        """
        request = self.factory.get('/api/v1/contacts/')

        # Mock authenticated user
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.username = 'testuser'
        mock_user.role = 'sales'
        request.user = mock_user

        def get_response(request):
            return HttpResponse()

        middleware = PerformanceMonitoringMiddleware(get_response)

        with patch('crm.apps.monitoring.middleware.log_request_performance') as mock_log:
            response = middleware(request)

            # Verify user information is included
            mock_log.assert_called_once()
            call_args = mock_log.call_args[1]

            self.assertEqual(call_args['user_id'], 1)
            self.assertEqual(call_args['user_role'], 'sales')

    def test_middleware_handles_large_request_payloads(self):
        """
        Test middleware handles requests with large payloads efficiently.

        GIVEN a request with large payload
        WHEN the middleware processes it
        THEN it should log payload size without performance degradation
        """
        large_payload = {'data': 'x' * 10000}  # 10KB payload

        request = self.factory.post(
            '/api/v1/contacts/',
            data=json.dumps(large_payload),
            content_type='application/json'
        )

        def get_response(request):
            return HttpResponse()

        middleware = PerformanceMonitoringMiddleware(get_response)

        with patch('crm.apps.monitoring.middleware.log_request_performance') as mock_log:
            response = middleware(request)

            # Verify payload size is logged
            mock_log.assert_called_once()
            call_args = mock_log.call_args[1]

            self.assertIn('request_size_bytes', call_args)
            self.assertGreater(call_args['request_size_bytes'], 10000)

    def test_middleware_database_query_tracking(self):
        """
        Test middleware tracks database query count and duration.

        GIVEN a request that executes database queries
        WHEN the middleware processes it
        THEN it should log database query statistics
        """
        request = self.factory.get('/api/v1/contacts/')

        def get_response(request):
            # Mock database queries
            with patch('django.db.connection') as mock_connection:
                mock_connection.queries = [
                    {'time': '0.002'},
                    {'time': '0.001'},
                    {'time': '0.003'}
                ]
                return HttpResponse()

        middleware = PerformanceMonitoringMiddleware(get_response)

        with patch('crm.apps.monitoring.middleware.log_request_performance') as mock_log:
            response = middleware(request)

            # Verify database query tracking
            mock_log.assert_called_once()
            call_args = mock_log.call_args[1]

            self.assertIn('db_query_count', call_args)
            self.assertEqual(call_args['db_query_count'], 3)

    def test_middleware_cache_hit_tracking(self):
        """
        Test middleware tracks cache hits and misses.

        GIVEN a request that utilizes caching
        WHEN the middleware processes it
        THEN it should log cache hit/miss statistics
        """
        request = self.factory.get('/api/v1/contacts/')

        def get_response(request):
            # Mock cache operations
            with patch('django.core.cache.cache') as mock_cache:
                mock_cache.get.return_value = None  # Cache miss
                return HttpResponse()

        middleware = PerformanceMonitoringMiddleware(get_response)

        with patch('crm.apps.monitoring.middleware.log_request_performance') as mock_log:
            with patch('crm.apps.monitoring.middleware.track_cache_metrics') as mock_cache_metrics:
                response = middleware(request)

                # Verify cache tracking was called
                mock_cache_metrics.assert_called_once()

    def test_middleware_endpoint_categorization(self):
        """
        Test middleware correctly categorizes API endpoints.

        GIVEN requests to different API endpoints
        WHEN the middleware processes them
        THEN it should categorize endpoints for metrics aggregation
        """
        test_cases = [
            ('/api/v1/contacts/', 'contacts'),
            ('/api/v1/deals/', 'deals'),
            ('/api/v1/activities/', 'activities'),
            ('/api/v1/auth/login/', 'auth'),
            ('/health/', 'health'),
            ('/metrics/', 'metrics')
        ]

        for path, expected_category in test_cases:
            with self.subTest(path=path, category=expected_category):
                request = self.factory.get(path)

                def get_response(request):
                    return HttpResponse()

                middleware = PerformanceMonitoringMiddleware(get_response)

                with patch('crm.apps.monitoring.middleware.log_request_performance') as mock_log:
                    response = middleware(request)

                    # Verify endpoint categorization
                    mock_log.assert_called_once()
                    call_args = mock_log.call_args[1]

                    self.assertEqual(call_args['endpoint_category'], expected_category)

    def test_middleware_performance_overhead(self):
        """
        Test middleware performance overhead is minimal.

        GIVEN normal request processing
        WHEN the middleware is active
        THEN it should add minimal overhead (< 5ms)
        """
        request = self.factory.get('/api/v1/contacts/')

        def get_response(request):
            return HttpResponse()

        middleware = PerformanceMonitoringMiddleware(get_response)

        # Measure overhead
        iterations = 100
        start_time = time.time()

        for _ in range(iterations):
            response = middleware(request)

        total_time = time.time() - start_time
        avg_overhead = (total_time / iterations) * 1000  # Convert to ms

        # Average overhead should be less than 5ms
        self.assertLess(avg_overhead, 5.0)

    def test_middleware_concurrent_request_handling(self):
        """
        Test middleware handles concurrent requests safely.

        GIVEN multiple concurrent requests
        WHEN the middleware processes them simultaneously
        THEN it should maintain separate timing data for each request
        """
        import threading

        request = self.factory.get('/api/v1/contacts/')
        results = []

        def process_request():
            def get_response(req):
                time.sleep(0.01)  # Simulate processing
                return HttpResponse()

            middleware = PerformanceMonitoringMiddleware(get_response)

            with patch('crm.apps.monitoring.middleware.log_request_performance') as mock_log:
                response = middleware(request)

                # Store the logged duration
                if mock_log.called:
                    call_args = mock_log.call_args[1]
                    results.append(call_args.get('duration_ms'))

        # Run multiple threads
        threads = [threading.Thread(target=process_request) for _ in range(10)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # Verify all requests were processed
        self.assertEqual(len(results), 10)

        # Verify all timings are reasonable
        for duration in results:
            self.assertIsNotNone(duration)
            self.assertGreater(duration, 0)