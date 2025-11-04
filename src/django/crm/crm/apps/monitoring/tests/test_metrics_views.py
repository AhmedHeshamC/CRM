"""
Test cases for Prometheus metrics views.

This module follows Test-Driven Development (TDD) principles by defining
expected behavior for the Prometheus metrics endpoint before implementation.

Tests cover all metrics functionality including:
- System metrics (CPU, memory, disk)
- Database metrics (connections, query performance)
- Business metrics (user activity, conversions)
- API performance metrics
- Error rate monitoring
"""

from unittest.mock import patch, MagicMock
import time

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase


class MetricsViewTestCase(APITestCase):
    """
    Test cases for the Prometheus metrics endpoint.

    These tests ensure the metrics endpoint provides properly formatted
    Prometheus metrics with all required system and business indicators.
    """

    def setUp(self) -> None:
        """Set up test environment."""
        self.metrics_url = reverse('monitoring:metrics')

    def test_metrics_endpoint_returns_text_format(self):
        """
        Test metrics endpoint returns text/plain content type.

        GIVEN the metrics endpoint is called
        WHEN the request is processed
        THEN it should return text/plain content type for Prometheus compatibility
        """
        response = self.client.get(self.metrics_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'text/plain; version=0.0.4')

    @patch('crm.apps.monitoring.views.generate_system_metrics')
    @patch('crm.apps.monitoring.views.generate_database_metrics')
    @patch('crm.apps.monitoring.views.generate_business_metrics')
    def test_metrics_endpoint_includes_all_metric_types(self, mock_business, mock_db, mock_system):
        """
        Test metrics endpoint includes all required metric types.

        GIVEN all metric collectors are working
        WHEN the metrics endpoint is called
        THEN it should include system, database, and business metrics
        """
        # Mock system metrics
        mock_system.return_value = [
            'crm_system_uptime_seconds 3600.5',
            'crm_system_memory_usage_bytes 134217728',
            'crm_system_cpu_usage_percent 15.2',
            'crm_system_disk_usage_bytes 1073741824'
        ]

        # Mock database metrics
        mock_db.return_value = [
            'crm_database_connections_active 5',
            'crm_database_connections_idle 10',
            'crm_database_query_duration_seconds_sum 12.5',
            'crm_database_query_duration_seconds_count 100'
        ]

        # Mock business metrics
        mock_business.return_value = [
            'crm_business_users_active_total 25',
            'crm_business_registrations_total 5',
            'crm_business_deals_created_total 8',
            'crm_business_api_requests_total 15420'
        ]

        response = self.client.get(self.metrics_url)
        content = response.content.decode('utf-8')

        # Verify system metrics are included
        self.assertIn('crm_system_uptime_seconds', content)
        self.assertIn('crm_system_memory_usage_bytes', content)
        self.assertIn('crm_system_cpu_usage_percent', content)

        # Verify database metrics are included
        self.assertIn('crm_database_connections_active', content)
        self.assertIn('crm_database_query_duration_seconds_sum', content)

        # Verify business metrics are included
        self.assertIn('crm_business_users_active_total', content)
        self.assertIn('crm_business_registrations_total', content)
        self.assertIn('crm_business_deals_created_total', content)

    @patch('crm.apps.monitoring.views.generate_system_metrics')
    def test_metrics_endpoint_handles_system_metrics_error(self, mock_system):
        """
        Test metrics endpoint handles system metrics collection errors gracefully.

        GIVEN system metrics collection fails
        WHEN the metrics endpoint is called
        THEN it should still return other metrics and log the error
        """
        mock_system.side_effect = Exception("System metrics collection failed")

        # Mock other metrics to work
        with patch('crm.apps.monitoring.views.generate_database_metrics') as mock_db, \
             patch('crm.apps.monitoring.views.generate_business_metrics') as mock_business:

            mock_db.return_value = ['crm_database_connections_active 5']
            mock_business.return_value = ['crm_business_users_active_total 25']

            response = self.client.get(self.metrics_url)
            content = response.content.decode('utf-8')

            # Should still return 200 and include working metrics
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIn('crm_database_connections_active', content)
            self.assertIn('crm_business_users_active_total', content)

            # Should not include broken system metrics
            self.assertNotIn('crm_system_uptime_seconds', content)

    def test_metrics_endpoint_response_time(self):
        """
        Test metrics endpoint response time is acceptable.

        GIVEN normal system load
        WHEN the metrics endpoint is called
        THEN it should respond within acceptable time limits
        """
        start_time = time.time()

        response = self.client.get(self.metrics_url)

        response_time = time.time() - start_time

        # Metrics endpoint should be fast (< 500ms)
        self.assertLess(response_time, 0.5)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_metrics_format_validation(self):
        """
        Test metrics are properly formatted according to Prometheus format.

        GIVEN valid metric collection
        WHEN the metrics endpoint is called
        THEN the response should follow Prometheus text format specification
        """
        with patch('crm.apps.monitoring.views.generate_system_metrics') as mock_system:
            mock_system.return_value = [
                '# HELP crm_system_uptime_seconds System uptime in seconds',
                '# TYPE crm_system_uptime_seconds counter',
                'crm_system_uptime_seconds 3600.5',
                '',
                '# HELP crm_system_memory_usage_bytes System memory usage in bytes',
                '# TYPE crm_system_memory_usage_bytes gauge',
                'crm_system_memory_usage_bytes 134217728'
            ]

            response = self.client.get(self.metrics_url)
            content = response.content.decode('utf-8')

            # Verify HELP comments are present
            self.assertIn('# HELP crm_system_uptime_seconds', content)

            # Verify TYPE comments are present
            self.assertIn('# TYPE crm_system_uptime_seconds counter', content)

            # Verify metric values
            self.assertIn('crm_system_uptime_seconds 3600.5', content)

    @patch('crm.apps.monitoring.views.generate_database_metrics')
    def test_metrics_endpoint_includes_histogram_metrics(self, mock_db):
        """
        Test metrics endpoint includes histogram metrics for performance monitoring.

        GIVEN database query performance data
        WHEN the metrics endpoint is called
        THEN it should include histogram buckets for response times
        """
        mock_db.return_value = [
            '# HELP crm_api_request_duration_seconds API request duration in seconds',
            '# TYPE crm_api_request_duration_seconds histogram',
            'crm_api_request_duration_seconds_bucket{le="0.1"} 450',
            'crm_api_request_duration_seconds_bucket{le="0.5"} 480',
            'crm_api_request_duration_seconds_bucket{le="1.0"} 495',
            'crm_api_request_duration_seconds_bucket{le="+Inf"} 500',
            'crm_api_request_duration_seconds_sum 125.5',
            'crm_api_request_duration_seconds_count 500'
        ]

        response = self.client.get(self.metrics_url)
        content = response.content.decode('utf-8')

        # Verify histogram buckets are present
        self.assertIn('crm_api_request_duration_seconds_bucket{le="0.1"} 450', content)
        self.assertIn('crm_api_request_duration_seconds_bucket{le="+Inf"} 500', content)

        # Verify histogram sum and count
        self.assertIn('crm_api_request_duration_seconds_sum 125.5', content)
        self.assertIn('crm_api_request_duration_seconds_count 500', content)

    @patch('crm.apps.monitoring.views.generate_business_metrics')
    def test_metrics_endpoint_includes_labels(self, mock_business):
        """
        Test metrics include labels for better categorization.

        GIVEN business metrics with different categories
        WHEN the metrics endpoint is called
        THEN it should include properly labeled metrics
        """
        mock_business.return_value = [
            'crm_business_users_total{role="admin"} 3',
            'crm_business_users_total{role="manager"} 7',
            'crm_business_users_total{role="sales"} 15',
            'crm_business_deals_total{stage="lead"} 25',
            'crm_business_deals_total{stage="qualified"} 18',
            'crm_business_deals_total{stage="closed_won"} 12'
        ]

        response = self.client.get(self.metrics_url)
        content = response.content.decode('utf-8')

        # Verify labeled metrics are present
        self.assertIn('crm_business_users_total{role="admin"} 3', content)
        self.assertIn('crm_business_users_total{role="manager"} 7', content)
        self.assertIn('crm_business_deals_total{stage="lead"} 25', content)

    def test_metrics_endpoint_caching_headers(self):
        """
        Test metrics endpoint sets appropriate caching headers.

        GIVEN any metrics request
        WHEN the endpoint is called
        THEN it should set short cache duration to balance freshness and performance
        """
        response = self.client.get(self.metrics_url)

        # Metrics should have short cache (max-age=30) for performance
        self.assertIn('max-age=30', response.get('Cache-Control', ''))

    def test_metrics_endpoint_authentication_not_required(self):
        """
        Test metrics endpoint does not require authentication.

        GIVEN any request to metrics endpoint
        WHEN the endpoint is called without authentication
        THEN it should still return metrics
        """
        # Should work without authentication headers
        response = self.client.get(self.metrics_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch('crm.apps.monitoring.views.generate_system_metrics')
    def test_metrics_endpoint_edge_cases(self, mock_system):
        """
        Test metrics endpoint handles edge cases properly.

        GIVEN edge cases in metric values (negative numbers, special characters)
        WHEN the metrics endpoint is called
        THEN it should handle them gracefully
        """
        mock_system.return_value = [
            'crm_system_cpu_usage_percent -1',  # Edge case: negative value
            'crm_system_memory_usage_bytes inf',  # Edge case: infinite value
            'crm_system_uptime_seconds 0'  # Edge case: zero value
        ]

        response = self.client.get(self.metrics_url)
        content = response.content.decode('utf-8')

        # Edge cases should be included as-is
        self.assertIn('crm_system_cpu_usage_percent -1', content)
        self.assertIn('crm_system_memory_usage_bytes inf', content)
        self.assertIn('crm_system_uptime_seconds 0', content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class MetricsCollectorTestCase(TestCase):
    """
    Test cases for individual metrics collectors.

    These tests ensure each metrics collector generates correct
    metric data and handles errors appropriately.
    """

    def test_system_metrics_collector_structure(self):
        """
        Test system metrics collector generates proper metric structure.

        GIVEN the system metrics collector is called
        WHEN it generates metrics
        THEN it should follow Prometheus naming and structure conventions
        """
        from crm.apps.monitoring.metrics import SystemMetricsCollector

        with patch('psutil.virtual_memory') as mock_memory, \
             patch('psutil.cpu_percent') as mock_cpu, \
             patch('psutil.disk_usage') as mock_disk:

            # Mock system data
            mock_memory.return_value.available = 1073741824  # 1GB
            mock_memory.return_value.total = 4294967296     # 4GB
            mock_cpu.return_value = 25.5

            mock_disk.return_value.free = 2147483648        # 2GB
            mock_disk.return_value.total = 10737418240      # 10GB

            collector = SystemMetricsCollector()
            metrics = collector.collect()

            # Verify metrics are strings (Prometheus format)
            self.assertTrue(all(isinstance(metric, str) for metric in metrics))

            # Verify metric names follow naming convention
            metric_names = [metric.split()[0] for metric in metrics if metric and not metric.startswith('#')]
            for name in metric_names:
                self.assertTrue(name.startswith('crm_system_'))

    def test_database_metrics_collector_error_handling(self):
        """
        Test database metrics collector handles connection errors gracefully.

        GIVEN database connection issues
        WHEN the database metrics collector is called
        THEN it should return error metrics instead of raising exceptions
        """
        from crm.apps.monitoring.metrics import DatabaseMetricsCollector

        with patch('django.db.connection') as mock_connection:
            mock_connection.cursor.side_effect = Exception("Database connection failed")

            collector = DatabaseMetricsCollector()
            metrics = collector.collect()

            # Should return error metrics instead of raising
            self.assertTrue(len(metrics) > 0)

            # Should include error indicator
            error_metrics = [m for m in metrics if 'error' in m.lower()]
            self.assertTrue(len(error_metrics) > 0)

    def test_business_metrics_collector_aggregation(self):
        """
        Test business metrics collector properly aggregates data.

        GIVEN business activity data
        WHEN the business metrics collector is called
        THEN it should return properly aggregated metrics
        """
        from crm.apps.monitoring.metrics import BusinessMetricsCollector

        with patch('crm.apps.monitoring.metrics.get_user_activity_metrics') as mock_user, \
             patch('crm.apps.monitoring.metrics.get_deal_metrics') as mock_deal:

            # Mock business data
            mock_user.return_value = {
                'active_users': 25,
                'new_registrations': 5,
                'login_count': 150
            }

            mock_deal.return_value = {
                'total_deals': 50,
                'new_deals': 8,
                'conversion_rate': 0.15
            }

            collector = BusinessMetricsCollector()
            metrics = collector.collect()

            # Should convert business metrics to Prometheus format
            metric_lines = [m for m in metrics if m and not m.startswith('#')]

            # Verify metrics include business data
            self.assertTrue(any('25' in line for line in metric_lines))  # active_users
            self.assertTrue(any('5' in line for line in metric_lines))   # new_registrations
            self.assertTrue(any('50' in line for line in metric_lines))  # total_deals