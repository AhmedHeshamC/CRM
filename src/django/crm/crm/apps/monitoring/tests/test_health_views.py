"""
Test cases for health check views.

This module follows Test-Driven Development (TDD) principles by defining
expected behavior before implementation. Tests cover all health check
functionality including system components and business metrics.

Tests follow SOLID principles:
- Single Responsibility: Each test method has one clear purpose
- Open/Closed: Tests are designed for extension without modification
- Dependency Inversion: Tests mock external dependencies
"""

from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import json

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from crm.apps.monitoring.views import HealthCheckView


class HealthCheckViewTestCase(APITestCase):
    """
    Test cases for the main health check endpoint.

    These tests ensure the health check endpoint provides comprehensive
    system status information including database, cache, and background
    task processing health.
    """

    def setUp(self) -> None:
        """Set up test environment with common test data."""
        self.health_url = reverse('monitoring:health-check')

    @patch('crm.apps.monitoring.views.DatabaseHealthChecker')
    @patch('crm.apps.monitoring.views.RedisHealthChecker')
    @patch('crm.apps.monitoring.views.CeleryHealthChecker')
    def test_health_check_all_healthy(self, mock_celery, mock_redis, mock_db):
        """
        Test health check returns 200 when all components are healthy.

        GIVEN all system components (database, Redis, Celery) are healthy
        WHEN the health check endpoint is called
        THEN it should return 200 status with detailed health information
        """
        # Mock all health checkers to return healthy status
        mock_db.return_value.is_healthy.return_value = True
        mock_db.return_value.get_details.return_value = {
            'status': 'healthy',
            'connections': 5,
            'max_connections': 100,
            'response_time_ms': 2.5
        }

        mock_redis.return_value.is_healthy.return_value = True
        mock_redis.return_value.get_details.return_value = {
            'status': 'healthy',
            'connected_clients': 3,
            'used_memory_mb': 45.2,
            'response_time_ms': 1.2
        }

        mock_celery.return_value.is_healthy.return_value = True
        mock_celery.return_value.get_details.return_value = {
            'status': 'healthy',
            'active_tasks': 0,
            'pending_tasks': 2,
            'failed_tasks_24h': 0
        }

        response = self.client.get(self.health_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        # Check overall status
        self.assertEqual(data['status'], 'healthy')
        self.assertEqual(data['timestamp'], timezone.now().isoformat()[:19] + 'Z')

        # Check individual components
        self.assertEqual(data['components']['database']['status'], 'healthy')
        self.assertEqual(data['components']['redis']['status'], 'healthy')
        self.assertEqual(data['components']['celery']['status'], 'healthy')

        # Check response includes metrics
        self.assertIn('metrics', data)
        self.assertIn('uptime_seconds', data['metrics'])
        self.assertIn('version', data)

    @patch('crm.apps.monitoring.views.DatabaseHealthChecker')
    def test_health_check_database_unhealthy(self, mock_db):
        """
        Test health check returns 503 when database is unhealthy.

        GIVEN the database connection is failing
        WHEN the health check endpoint is called
        THEN it should return 503 status with error details
        """
        mock_db.return_value.is_healthy.return_value = False
        mock_db.return_value.get_details.return_value = {
            'status': 'unhealthy',
            'error': 'Connection timeout',
            'last_check': timezone.now().isoformat()
        }

        # Mock healthy Redis and Celery
        with patch('crm.apps.monitoring.views.RedisHealthChecker') as mock_redis, \
             patch('crm.apps.monitoring.views.CeleryHealthChecker') as mock_celery:

            mock_redis.return_value.is_healthy.return_value = True
            mock_celery.return_value.is_healthy.return_value = True

            response = self.client.get(self.health_url)

            self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
            data = response.json()

            self.assertEqual(data['status'], 'unhealthy')
            self.assertEqual(data['components']['database']['status'], 'unhealthy')
            self.assertIn('error', data['components']['database'])

    @patch('crm.apps.monitoring.views.DatabaseHealthChecker')
    @patch('crm.apps.monitoring.views.RedisHealthChecker')
    def test_health_check_multiple_components_unhealthy(self, mock_redis, mock_db):
        """
        Test health check returns 503 when multiple components are unhealthy.

        GIVEN both database and Redis are unhealthy
        WHEN the health check endpoint is called
        THEN it should return 503 status with all unhealthy components listed
        """
        mock_db.return_value.is_healthy.return_value = False
        mock_db.return_value.get_details.return_value = {
            'status': 'unhealthy',
            'error': 'Connection refused'
        }

        mock_redis.return_value.is_healthy.return_value = False
        mock_redis.return_value.get_details.return_value = {
            'status': 'unhealthy',
            'error': 'Redis server not responding'
        }

        # Mock healthy Celery
        with patch('crm.apps.monitoring.views.CeleryHealthChecker') as mock_celery:
            mock_celery.return_value.is_healthy.return_value = True

            response = self.client.get(self.health_url)

            self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
            data = response.json()

            self.assertEqual(data['status'], 'unhealthy')
            self.assertEqual(data['components']['database']['status'], 'unhealthy')
            self.assertEqual(data['components']['redis']['status'], 'unhealthy')
            self.assertEqual(data['components']['celery']['status'], 'healthy')

    @patch('crm.apps.monitoring.views.DatabaseHealthChecker')
    def test_health_check_database_error_handling(self, mock_db):
        """
        Test health check handles database checker exceptions gracefully.

        GIVEN the database health checker raises an exception
        WHEN the health check endpoint is called
        THEN it should return 503 status with error information
        """
        mock_db.return_value.is_healthy.side_effect = Exception("Database connection failed")
        mock_db.return_value.get_details.return_value = {
            'status': 'error',
            'error': 'Database connection failed'
        }

        # Mock healthy Redis and Celery
        with patch('crm.apps.monitoring.views.RedisHealthChecker') as mock_redis, \
             patch('crm.apps.monitoring.views.CeleryHealthChecker') as mock_celery:

            mock_redis.return_value.is_healthy.return_value = True
            mock_celery.return_value.is_healthy.return_value = True

            response = self.client.get(self.health_url)

            self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
            data = response.json()

            self.assertEqual(data['status'], 'unhealthy')
            self.assertEqual(data['components']['database']['status'], 'error')

    def test_health_check_response_structure(self):
        """
        Test health check response has the correct structure.

        GIVEN a healthy system
        WHEN the health check endpoint is called
        THEN the response should have the expected JSON structure
        """
        with patch('crm.apps.monitoring.views.DatabaseHealthChecker') as mock_db, \
             patch('crm.apps.monitoring.views.RedisHealthChecker') as mock_redis, \
             patch('crm.apps.monitoring.views.CeleryHealthChecker') as mock_celery:

            # Mock all components as healthy
            mock_db.return_value.is_healthy.return_value = True
            mock_db.return_value.get_details.return_value = {'status': 'healthy'}

            mock_redis.return_value.is_healthy.return_value = True
            mock_redis.return_value.get_details.return_value = {'status': 'healthy'}

            mock_celery.return_value.is_healthy.return_value = True
            mock_celery.return_value.get_details.return_value = {'status': 'healthy'}

            response = self.client.get(self.health_url)
            data = response.json()

            # Verify top-level structure
            required_fields = ['status', 'timestamp', 'components', 'metrics', 'version']
            for field in required_fields:
                self.assertIn(field, data, f"Missing required field: {field}")

            # Verify components structure
            required_components = ['database', 'redis', 'celery']
            for component in required_components:
                self.assertIn(component, data['components'])
                self.assertIn('status', data['components'][component])

            # Verify metrics structure
            required_metrics = ['uptime_seconds', 'memory_usage_mb', 'cpu_usage_percent']
            for metric in required_metrics:
                self.assertIn(metric, data['metrics'])

    def test_health_check_caching_headers(self):
        """
        Test health check endpoint sets appropriate caching headers.

        GIVEN any health check request
        WHEN the endpoint is called
        THEN it should set cache-control headers to prevent caching
        """
        with patch('crm.apps.monitoring.views.DatabaseHealthChecker') as mock_db, \
             patch('crm.apps.monitoring.views.RedisHealthChecker') as mock_redis, \
             patch('crm.apps.monitoring.views.CeleryHealthChecker') as mock_celery:

            # Mock all components as healthy
            mock_db.return_value.is_healthy.return_value = True
            mock_redis.return_value.is_healthy.return_value = True
            mock_celery.return_value.is_healthy.return_value = True

            response = self.client.get(self.health_url)

            # Health checks should not be cached
            self.assertEqual(
                response.get('Cache-Control'),
                'no-cache, no-store, must-revalidate'
            )
            self.assertEqual(response.get('Pragma'), 'no-cache')
            self.assertEqual(response.get('Expires'), '0')

    @patch('crm.apps.monitoring.views.start_time', timezone.now() - timedelta(hours=1))
    def test_health_check_uptime_calculation(self):
        """
        Test health check correctly calculates system uptime.

        GIVEN the system has been running for 1 hour
        WHEN the health check endpoint is called
        THEN it should report uptime close to 3600 seconds
        """
        with patch('crm.apps.monitoring.views.DatabaseHealthChecker') as mock_db, \
             patch('crm.apps.monitoring.views.RedisHealthChecker') as mock_redis, \
             patch('crm.apps.monitoring.views.CeleryHealthChecker') as mock_celery:

            # Mock all components as healthy
            mock_db.return_value.is_healthy.return_value = True
            mock_redis.return_value.is_healthy.return_value = True
            mock_celery.return_value.is_healthy.return_value = True

            response = self.client.get(self.health_url)
            data = response.json()

            uptime = data['metrics']['uptime_seconds']
            # Allow 10 seconds tolerance for test execution time
            self.assertGreaterEqual(uptime, 3590)
            self.assertLessEqual(uptime, 3610)


class HealthCheckBusinessMetricsTestCase(APITestCase):
    """
    Test cases for business metrics in health check endpoint.

    These tests ensure the health check provides relevant business
    metrics for monitoring application performance and user activity.
    """

    def setUp(self) -> None:
        """Set up test environment."""
        self.health_url = reverse('monitoring:health-check')

    @patch('crm.apps.monitoring.views.get_business_metrics')
    def test_health_check_includes_business_metrics(self, mock_get_metrics):
        """
        Test health check includes business metrics.

        GIVEN the application has business activity
        WHEN the health check endpoint is called
        THEN it should include business metrics in the response
        """
        mock_get_metrics.return_value = {
            'active_users': 25,
            'user_registrations_24h': 5,
            'deal_conversions_24h': 3,
            'api_requests_24h': 15420,
            'average_response_time_ms': 145.5
        }

        with patch('crm.apps.monitoring.views.DatabaseHealthChecker') as mock_db, \
             patch('crm.apps.monitoring.views.RedisHealthChecker') as mock_redis, \
             patch('crm.apps.monitoring.views.CeleryHealthChecker') as mock_celery:

            # Mock all components as healthy
            mock_db.return_value.is_healthy.return_value = True
            mock_redis.return_value.is_healthy.return_value = True
            mock_celery.return_value.is_healthy.return_value = True

            response = self.client.get(self.health_url)
            data = response.json()

            self.assertIn('business_metrics', data)
            business_metrics = data['business_metrics']

            self.assertEqual(business_metrics['active_users'], 25)
            self.assertEqual(business_metrics['user_registrations_24h'], 5)
            self.assertEqual(business_metrics['deal_conversions_24h'], 3)
            self.assertEqual(business_metrics['api_requests_24h'], 15420)
            self.assertEqual(business_metrics['average_response_time_ms'], 145.5)

    @patch('crm.apps.monitoring.views.get_business_metrics')
    def test_health_check_handles_business_metrics_error(self, mock_get_metrics):
        """
        Test health check handles business metrics collection errors gracefully.

        GIVEN business metrics collection fails
        WHEN the health check endpoint is called
        THEN it should return health status but indicate metrics error
        """
        mock_get_metrics.side_effect = Exception("Metrics collection failed")

        with patch('crm.apps.monitoring.views.DatabaseHealthChecker') as mock_db, \
             patch('crm.apps.monitoring.views.RedisHealthChecker') as mock_redis, \
             patch('crm.apps.monitoring.views.CeleryHealthChecker') as mock_celery:

            # Mock all components as healthy
            mock_db.return_value.is_healthy.return_value = True
            mock_redis.return_value.is_healthy.return_value = True
            mock_celery.return_value.is_healthy.return_value = True

            response = self.client.get(self.health_url)
            data = response.json()

            # System should still be healthy
            self.assertEqual(data['status'], 'healthy')

            # Business metrics should indicate error
            self.assertIn('business_metrics', data)
            self.assertEqual(data['business_metrics']['status'], 'error')
            self.assertIn('error', data['business_metrics'])