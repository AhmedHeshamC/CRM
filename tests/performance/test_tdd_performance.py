"""
Performance Testing with TDD Approach
Test-Driven Performance Optimization
"""

import pytest
import time
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.db import connection
from django.test.utils import override_settings
from rest_framework.test import APIClient
from unittest.mock import patch
import cProfile
import pstats
from io import StringIO

User = get_user_model()


class PerformanceTestCase(TestCase):
    """
    Base class for performance tests following TDD methodology
    """

    def assert_max_response_time(self, response_func, max_time_ms, *args, **kwargs):
        """
        Assert that a function completes within specified time
        Following TDD: Write test first, then optimize
        """
        start_time = time.time()
        result = response_func(*args, **kwargs)
        end_time = time.time()

        duration_ms = (end_time - start_time) * 1000
        self.assertLessEqual(
            duration_ms, max_time_ms,
            f"Response time {duration_ms:.2f}ms exceeds maximum {max_time_ms}ms"
        )
        return result

    def assert_max_database_queries(self, query_func, max_queries, *args, **kwargs):
        """
        Assert that a function executes no more than specified number of queries
        Following TDD: Write test first, then optimize queries
        """
        initial_queries = len(connection.queries)

        with override_settings(DEBUG=True):
            result = query_func(*args, **kwargs)

        final_queries = len(connection.queries)
        query_count = final_queries - initial_queries

        self.assertLessEqual(
            query_count, max_queries,
            f"Query count {query_count} exceeds maximum {max_queries}"
        )
        return result

    def profile_function(self, func, *args, **kwargs):
        """
        Profile a function and return performance metrics
        Following TDD: Profile to identify optimization opportunities
        """
        pr = cProfile.Profile()
        pr.enable()

        result = func(*args, **kwargs)

        pr.disable()
        s = StringIO()
        ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
        ps.print_stats(10)  # Top 10 functions

        return {
            'result': result,
            'profile': s.getvalue()
        }


class APIPerformanceTests(PerformanceTestCase):
    """
    API endpoint performance tests using TDD methodology
    """

    def setUp(self):
        """Set up performance test environment"""
        self.client = APIClient()
        self.admin_user = User.objects.create_user(
            email='admin@company.com',
            password='AdminPass123!',
            first_name='Admin',
            last_name='User',
            role='admin',
            is_staff=True
        )

    def test_login_performance_tdd(self):
        """
        TDD Test: Login should complete within 500ms
        Performance requirement: < 500ms response time
        """
        def login_request():
            return self.client.post('/api/v1/auth/login/', {
                'email': 'admin@company.com',
                'password': 'AdminPass123!'
            })

        response = self.assert_max_response_time(login_request, 500)
        self.assertEqual(response.status_code, 200)

    def test_user_list_performance_tdd(self):
        """
        TDD Test: User list should complete within 200ms and use <= 3 queries
        Performance requirements: < 200ms response time, <= 3 database queries
        """
        # Create test data
        for i in range(100):
            User.objects.create_user(
                email=f'user{i}@company.com',
                password='TestPass123!',
                first_name=f'User{i}',
                last_name='Test',
                role='sales'
            )

        self.client.force_authenticate(user=self.admin_user)

        def user_list_request():
            return self.client.get('/api/v1/auth/users/')

        # Test response time
        response = self.assert_max_response_time(user_list_request, 200)
        self.assertEqual(response.status_code, 200)

        # Test query count (should be optimized)
        response = self.assert_max_database_queries(user_list_request, 3)
        self.assertEqual(response.status_code, 200)

    def test_contact_creation_performance_tdd(self):
        """
        TDD Test: Contact creation should complete within 300ms
        Performance requirement: < 300ms response time
        """
        self.client.force_authenticate(user=self.admin_user)

        def create_contact():
            return self.client.post('/api/v1/contacts/', {
                'first_name': 'Performance',
                'last_name': 'Test',
                'email': 'performance@company.com',
                'owner': self.admin_user.id
            })

        response = self.assert_max_response_time(create_contact, 300)
        self.assertEqual(response.status_code, 201)

    def test_bulk_operations_performance_tdd(self):
        """
        TDD Test: Bulk operations should scale linearly
        Performance requirement: O(n) time complexity
        """
        self.client.force_authenticate(user=self.admin_user)

        # Test different batch sizes
        batch_sizes = [10, 50, 100]
        response_times = []

        for batch_size in batch_sizes:
            contacts_data = [
                {
                    'first_name': f'User{i}',
                    'last_name': 'Test',
                    'email': f'user{i}@company.com',
                    'owner': self.admin_user.id
                }
                for i in range(batch_size)
            ]

            start_time = time.time()
            response = self.client.post('/api/v1/contacts/bulk-create/', {
                'contacts': contacts_data
            })
            end_time = time.time()

            response_times.append(end_time - start_time)
            self.assertEqual(response.status_code, 200)

        # Check linear scaling (time per item should be relatively constant)
        time_per_item_10 = response_times[0] / 10
        time_per_item_100 = response_times[2] / 100

        # Should not be more than 50% slower per item for larger batches
        self.assertLess(time_per_item_100, time_per_item_10 * 1.5)


class DatabasePerformanceTests(PerformanceTestCase):
    """
    Database performance tests using TDD methodology
    """

    def test_query_optimization_tdd(self):
        """
        TDD Test: Complex queries should be optimized
        Performance requirement: <= 5 queries for complex operations
        """
        # Create test data with relationships
        users = []
        for i in range(50):
            user = User.objects.create_user(
                email=f'user{i}@company.com',
                password='TestPass123!',
                first_name=f'User{i}',
                last_name='Test',
                role='sales'
            )
            users.append(user)

        def complex_user_query():
            """Simulate complex user query with relationships"""
            return User.objects.select_related('profile').prefetch_related(
                'api_keys'
            ).filter(
                role='sales',
                is_active=True
            ).order_by('-date_joined')[:20]

        # Test query count
        users = self.assert_max_database_queries(complex_user_query, 2)
        self.assertEqual(len(users), 20)

    def test_index_usage_tdd(self):
        """
        TDD Test: Queries should use appropriate indexes
        Performance requirement: < 50ms for indexed queries
        """
        # Create test data
        for i in range(1000):
            User.objects.create_user(
                email=f'user{i}@company.com',
                password='TestPass123!',
                first_name=f'User{i}',
                last_name='Test',
                role='sales' if i % 2 == 0 else 'admin'
            )

        def indexed_query():
            return list(User.objects.filter(role='sales', email__endswith='@company.com'))

        users = self.assert_max_response_time(indexed_query, 50)
        self.assertEqual(len(users), 500)

    def test_transaction_performance_tdd(self):
        """
        TDD Test: Database transactions should not impact performance significantly
        Performance requirement: < 100ms overhead for transactions
        """
        def transaction_operation():
            with transaction.atomic():
                user = User.objects.create_user(
                    email='transaction@company.com',
                    password='TestPass123!',
                    first_name='Transaction',
                    last_name='Test',
                    role='sales'
                )
                user.first_name = 'Updated'
                user.save()
            return user

        user = self.assert_max_response_time(transaction_operation, 100)
        self.assertEqual(user.first_name, 'Updated')


class CachePerformanceTests(PerformanceTestCase):
    """
    Cache performance tests using TDD methodology
    """

    @patch('django.core.cache.cache.get')
    @patch('django.core.cache.cache.set')
    def test_cache_hit_performance_tdd(self, mock_cache_set, mock_cache_get):
        """
        TDD Test: Cache hits should be significantly faster than database queries
        Performance requirement: < 10ms for cache hits
        """
        mock_cache_get.return_value = {'id': 1, 'name': 'Test User'}

        def cache_hit_operation():
            return User.objects.get_cached_user(1)  # Assuming cached method exists

        result = self.assert_max_response_time(cache_hit_operation, 10)
        mock_cache_get.assert_called_once()

    def test_cache_miss_performance_tdd(self):
        """
        TDD Test: Cache misses should not significantly impact performance
        Performance requirement: < 200ms for cache miss + database query
        """
        user = User.objects.create_user(
            email='cache@company.com',
            password='TestPass123!',
            first_name='Cache',
            last_name='Test',
            role='sales'
        )

        def cache_miss_operation():
            return User.objects.get_cached_user(user.id)  # Assuming cached method exists

        result = self.assert_max_response_time(cache_miss_operation, 200)
        self.assertEqual(result.id, user.id)


class LoadTestingFramework(PerformanceTestCase):
    """
    Load testing framework using TDD methodology
    """

    def test_concurrent_requests_tdd(self):
        """
        TDD Test: System should handle concurrent requests
        Performance requirement: Handle 50 concurrent requests
        """
        import threading
        import queue

        results = queue.Queue()

        def make_request():
            try:
                response = self.client.post('/api/v1/auth/login/', {
                    'email': 'admin@company.com',
                    'password': 'AdminPass123!'
                })
                results.put(response.status_code)
            except Exception as e:
                results.put(e)

        # Create 50 concurrent threads
        threads = []
        for _ in range(50):
            thread = threading.Thread(target=make_request)
            threads.append(thread)

        # Start all threads
        start_time = time.time()
        for thread in threads:
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        end_time = time.time()
        duration = end_time - start_time

        # Check results
        success_count = 0
        while not results.empty():
            result = results.get()
            if result == 200:
                success_count += 1

        # Should handle at least 80% of concurrent requests successfully
        self.assertGreaterEqual(success_count, 40)
        self.assertLess(duration, 10)  # Should complete within 10 seconds


class MemoryUsageTests(PerformanceTestCase):
    """
    Memory usage tests using TDD methodology
    """

    def test_memory_leak_detection_tdd(self):
        """
        TDD Test: Operations should not leak memory
        Performance requirement: Memory usage should not grow significantly
        """
        import gc
        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Perform many operations
        for i in range(1000):
            user = User.objects.create_user(
                email=f'memory{i}@company.com',
                password='TestPass123!',
                first_name=f'Memory{i}',
                last_name='Test',
                role='sales'
            )
            # Delete user to test cleanup
            user.delete()

        gc.collect()
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_growth = final_memory - initial_memory

        # Memory growth should be less than 50MB
        self.assertLess(memory_growth, 50)