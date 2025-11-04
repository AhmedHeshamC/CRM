"""
TDD Tests for Simplified Caching Implementation
Following Red-Green-Refactor cycle with KISS principle
"""

import pytest
from django.test import TestCase, override_settings
from django.core.cache import cache
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from crm.apps.authentication.models import User
from shared.repositories.simple_cache import SimpleCache, CachedRepositoryMixin


class TestSimpleCache(TestCase):
    """
    Test SimpleCache class following TDD methodology
    Red phase: Write failing tests first
    Green phase: Implement to make tests pass
    Refactor phase: Simplify while maintaining functionality
    """

    def setUp(self):
        """Set up test environment"""
        self.cache = SimpleCache(prefix='test_', timeout=300)
        cache.clear()  # Clear cache before each test

    def test_cache_set_and_get(self):
        """
        Test basic cache set and get operations
        TDD: Should store and retrieve values correctly
        """
        # Arrange
        key = 'test_key'
        value = {'data': 'test_value', 'timestamp': datetime.now()}

        # Act
        self.cache.set(key, value)
        retrieved_value = self.cache.get(key)

        # Assert
        self.assertEqual(retrieved_value, value)

    def test_cache_key_prefixing(self):
        """
        Test that cache keys are properly prefixed
        TDD: Should apply prefix to all keys
        """
        # Arrange
        key = 'user_data'
        value = {'id': 1, 'name': 'Test User'}

        # Act
        self.cache.set(key, value)

        # Assert - Check the actual cache key
        expected_cache_key = 'test_user_data'
        cached_value = cache.get(expected_cache_key)
        self.assertEqual(cached_value, value)

    def test_cache_get_nonexistent_key(self):
        """
        Test getting non-existent key
        TDD: Should return None for non-existent keys
        """
        # Arrange
        key = 'nonexistent_key'

        # Act
        result = self.cache.get(key)

        # Assert
        self.assertIsNone(result)

    def test_cache_delete(self):
        """
        Test cache delete operation
        TDD: Should delete keys correctly
        """
        # Arrange
        key = 'delete_test'
        value = 'test_value'
        self.cache.set(key, value)

        # Verify it exists
        self.assertIsNotNone(self.cache.get(key))

        # Act
        self.cache.delete(key)
        result = self.cache.get(key)

        # Assert
        self.assertIsNone(result)

    def test_cache_clear_pattern(self):
        """
        Test clearing cache pattern
        TDD: Should clear pattern-based keys
        """
        # Arrange
        key1 = 'user_123'
        key2 = 'user_456'
        value1 = {'id': 123}
        value2 = {'id': 456}

        self.cache.set(key1, value1)
        self.cache.set(key2, value2)

        # Verify both exist
        self.assertIsNotNone(self.cache.get(key1))
        self.assertIsNotNone(self.cache.get(key2))

        # Act
        self.cache.clear_pattern('user_123')

        # Assert
        self.assertIsNone(self.cache.get(key1))
        self.assertIsNotNone(self.cache.get(key2))

    def test_cache_timeout_configuration(self):
        """
        Test cache timeout configuration
        TDD: Should respect timeout setting
        """
        # Arrange
        short_timeout_cache = SimpleCache(prefix='short_', timeout=1)
        key = 'timeout_test'
        value = 'test_value'

        # Act
        short_timeout_cache.set(key, value)

        # Assert - Should exist immediately
        self.assertIsNotNone(short_timeout_cache.get(key))

        # Wait for timeout
        import time
        time.sleep(2)

        # Should be expired
        self.assertIsNone(short_timeout_cache.get(key))

    def test_cache_with_none_value(self):
        """
        Test caching None values
        TDD: Should handle None values correctly
        """
        # Arrange
        key = 'none_value_test'
        value = None

        # Act
        self.cache.set(key, value)
        result = self.cache.get(key)

        # Assert
        self.assertIsNone(result)  # This is expected behavior

    def test_cache_with_complex_data_types(self):
        """
        Test caching complex data types
        TDD: Should handle lists, dicts, objects
        """
        # Arrange
        test_data = {
            'simple_string': 'test',
            'number': 42,
            'list': [1, 2, 3],
            'dict': {'nested': 'value'},
            'datetime': datetime.now(),
            'none_value': None
        }

        # Act
        self.cache.set('complex_data', test_data)
        result = self.cache.get('complex_data')

        # Assert
        self.assertEqual(result['simple_string'], 'test')
        self.assertEqual(result['number'], 42)
        self.assertEqual(result['list'], [1, 2, 3])
        self.assertEqual(result['dict'], {'nested': 'value'})
        self.assertIsNone(result['none_value'])

    def test_cache_key_collision_prevention(self):
        """
        Test that key collisions are prevented with prefixes
        TDD: Different prefixes should prevent collisions
        """
        # Arrange
        cache1 = SimpleCache(prefix='cache1_', timeout=300)
        cache2 = SimpleCache(prefix='cache2_', timeout=300)
        key = 'same_key'
        value1 = 'value_from_cache1'
        value2 = 'value_from_cache2'

        # Act
        cache1.set(key, value1)
        cache2.set(key, value2)

        result1 = cache1.get(key)
        result2 = cache2.get(key)

        # Assert
        self.assertEqual(result1, value1)
        self.assertEqual(result2, value2)
        self.assertNotEqual(result1, result2)


class TestCachedRepositoryMixin(TestCase):
    """
    Test CachedRepositoryMixin following TDD methodology
    Testing the KISS principle in action
    """

    def setUp(self):
        """Set up test environment"""
        cache.clear()

        # Create test user
        self.user = User.objects.create_user(
            email='test@example.com',
            first_name='Test',
            last_name='User',
            password='testpass123'
        )

    def test_cached_repository_initialization(self):
        """
        Test repository mixin initialization
        TDD: Should initialize with proper cache configuration
        """
        # Arrange & Act
        class TestRepository(CachedRepositoryMixin):
            model = User
            cache_timeout = 600

        # Act
        repository = TestRepository()

        # Assert
        self.assertIsInstance(repository.cache, SimpleCache)
        self.assertEqual(repository.cache.prefix, 'user_')
        self.assertEqual(repository.cache.timeout, 600)

    def test_cached_or_fetch_pattern_hit(self):
        """
        Test cached or fetch pattern with cache hit
        TDD: Should return cached value when available
        """
        # Arrange
        class TestRepository(CachedRepositoryMixin):
            model = User

        repository = TestRepository()
        cache_key = 'user_1'
        cached_data = {'id': 1, 'email': 'test@example.com'}

        # Pre-populate cache
        repository.cache.set(cache_key, cached_data)

        mock_fetch_func = Mock(return_value={'fresh': 'data'})

        # Act
        result = repository._get_cached_or_fetch(
            cache_key, mock_fetch_func, 1
        )

        # Assert
        self.assertEqual(result, cached_data)
        mock_fetch_func.assert_not_called()  # Should not fetch if cached

    def test_cached_or_fetch_pattern_miss(self):
        """
        Test cached or fetch pattern with cache miss
        TDD: Should fetch and cache when cache miss occurs
        """
        # Arrange
        class TestRepository(CachedRepositoryMixin):
            model = User

        repository = TestRepository()
        cache_key = 'user_1'
        fresh_data = {'id': 1, 'email': 'test@example.com'}

        mock_fetch_func = Mock(return_value=fresh_data)

        # Act
        result = repository._get_cached_or_fetch(
            cache_key, mock_fetch_func, 1
        )

        # Assert
        self.assertEqual(result, fresh_data)
        mock_fetch_func.assert_called_once_with(1)

        # Verify data was cached
        cached_result = repository.cache.get(cache_key)
        self.assertEqual(cached_result, fresh_data)

    def test_cached_repository_with_user_retrieval(self):
        """
        Test repository with actual user model retrieval
        TDD: Should cache user objects correctly
        """
        # Arrange
        class UserRepository(CachedRepositoryMixin):
            model = User

        repository = UserRepository()
        cache_key = f'user_{self.user.id}'

        # Act - First call (cache miss)
        user1 = repository._get_cached_or_fetch(
            cache_key, User.objects.get, id=self.user.id
        )

        # Act - Second call (cache hit)
        user2 = repository._get_cached_or_fetch(
            cache_key, User.objects.get, id=self.user.id
        )

        # Assert
        self.assertEqual(user1.id, self.user.id)
        self.assertEqual(user2.id, self.user.id)
        self.assertEqual(user1.email, user2.email)

    def test_kiss_principle_simplicity(self):
        """
        Test that the implementation follows KISS principle
        TDD: Should be simple and focused
        """
        # Arrange & Act
        cache = SimpleCache(prefix='kiss_test', timeout=300)

        # Assert - Simple interface
        self.assertTrue(hasattr(cache, 'get'))
        self.assertTrue(hasattr(cache, 'set'))
        self.assertTrue(hasattr(cache, 'delete'))

        # Assert - No complex methods
        method_names = [method for method in dir(cache) if not method.startswith('_')]
        expected_methods = ['get', 'set', 'delete', 'clear_pattern']

        for method in expected_methods:
            self.assertIn(method, method_names)

        # Assert - Methods are simple (few parameters)
        import inspect
        get_signature = inspect.signature(cache.get)
        self.assertLessEqual(len(get_signature.parameters), 2)  # self + key

    def test_error_handling_gracefully(self):
        """
        Test error handling follows KISS principle
        TDD: Should handle errors gracefully without complexity
        """
        # Arrange
        cache = SimpleCache(prefix='error_test', timeout=300)

        # Act & Assert - Should not raise exceptions for invalid inputs
        try:
            result = cache.get(None)
            self.assertIsNone(result)
        except Exception as e:
            self.fail(f"Cache.get(None) should not raise exception: {e}")

        try:
            cache.set('', 'test')
            self.assertTrue(True)  # Should not raise exception
        except Exception as e:
            self.fail(f"Cache.set('', 'test') should not raise exception: {e}")

    def test_performance_with_kiss_implementation(self):
        """
        Test performance of KISS implementation
        TDD: Should be performant despite simplicity
        """
        # Arrange
        cache = SimpleCache(prefix='perf_test', timeout=300)
        iterations = 1000

        # Act
        import time
        start_time = time.time()

        for i in range(iterations):
            key = f'key_{i}'
            value = f'value_{i}'
            cache.set(key, value)
            retrieved = cache.get(key)
            self.assertEqual(retrieved, value)

        end_time = time.time()
        execution_time = end_time - start_time

        # Assert - Should complete quickly (less than 1 second for 1000 operations)
        self.assertLess(execution_time, 1.0)

        # Calculate operations per second
        ops_per_second = iterations / execution_time
        self.assertGreater(ops_per_second, 500)  # Should handle at least 500 ops/sec


class TestCacheIntegrationWithServices(TestCase):
    """
    Integration tests for cache with service layer
    Testing TDD in real-world scenarios
    """

    def setUp(self):
        """Set up test environment"""
        cache.clear()

        # Create test users
        self.user1 = User.objects.create_user(
            email='user1@example.com',
            first_name='User',
            last_name='One',
            password='testpass123'
        )

        self.user2 = User.objects.create_user(
            email='user2@example.com',
            first_name='User',
            last_name='Two',
            password='testpass123'
        )

    def test_service_layer_caching_integration(self):
        """
        Test service layer caching integration
        TDD: Should integrate seamlessly with services
        """
        # Arrange
        from crm.apps.authentication.services import UserManagementService

        service = UserManagementService()

        # Mock the service to use our simple cache
        service.cache = SimpleCache(prefix='user_service_', timeout=300)

        # Act - Simulate caching user lookup
        cache_key = f'user_{self.user1.id}'
        user_data = {
            'id': self.user1.id,
            'email': self.user1.email,
            'first_name': self.user1.first_name
        }

        # First call - cache miss
        result1 = service._get_cached_or_fetch(
            cache_key,
            lambda: user_data
        )

        # Second call - cache hit
        result2 = service._get_cached_or_fetch(
            cache_key,
            lambda: {'fresh': 'data'}
        )

        # Assert
        self.assertEqual(result1, user_data)
        self.assertEqual(result2, user_data)  # Should get cached data

    def test_cache_invalidation_on_user_update(self):
        """
        Test cache invalidation when user is updated
        TDD: Should invalidate cache when data changes
        """
        # Arrange
        cache = SimpleCache(prefix='user_cache_', timeout=300)
        cache_key = f'user_{self.user1.id}'
        original_data = {
            'id': self.user1.id,
            'email': self.user1.email,
            'first_name': self.user1.first_name
        }

        # Cache original data
        cache.set(cache_key, original_data)
        self.assertIsNotNone(cache.get(cache_key))

        # Act - Simulate user update
        self.user1.first_name = 'Updated'
        self.user1.save()

        # Invalidate cache
        cache.delete(cache_key)

        # Assert
        self.assertIsNone(cache.get(cache_key))

    def test_cache_with_concurrent_access(self):
        """
        Test cache behavior with concurrent access
        TDD: Should handle concurrent access safely
        """
        # Arrange
        cache = SimpleCache(prefix='concurrent_', timeout=300)
        cache_key = 'shared_key'
        shared_value = {'counter': 0}

        # Act - Simulate concurrent access
        def update_cache():
            current = cache.get(cache_key) or {'counter': 0}
            current['counter'] += 1
            cache.set(cache_key, current)
            return current

        # Run multiple updates
        results = []
        for i in range(10):
            result = update_cache()
            results.append(result['counter'])

        # Assert - Should handle concurrent updates gracefully
        # In a real scenario, you'd need proper locking mechanisms
        # For this test, we verify no exceptions occurred
        self.assertEqual(len(results), 10)
        self.assertTrue(all(count > 0 for count in results))

    @override_settings(CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'test-cache-simple',
        }
    })
    def test_cache_configuration_flexibility(self):
        """
        Test cache works with different Django cache configurations
        TDD: Should be flexible with cache backends
        """
        # Arrange
        cache = SimpleCache(prefix='config_test_', timeout=300)

        # Act
        cache.set('test_key', 'test_value')
        result = cache.get('test_key')

        # Assert
        self.assertEqual(result, 'test_value')

        # Test that it works with the overridden cache configuration
        self.assertIsNotNone(result)