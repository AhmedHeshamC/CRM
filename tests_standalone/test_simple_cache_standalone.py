"""
Standalone Simple Cache Tests - No Django Dependencies
Tests KISS principle implementation without external dependencies
"""

import unittest
import time
from unittest.mock import Mock, patch
import sys
import os

# Add the project to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


class MockDjangoCache:
    """Mock Django cache for testing without Django"""
    def __init__(self):
        self.data = {}
        self.expirations = {}

    def get(self, key):
        import time
        if key in self.expirations and self.expirations[key] < time.time():
            del self.data[key]
            del self.expirations[key]
            return None
        return self.data.get(key)

    def set(self, key, value, timeout=None):
        import time
        self.data[key] = value
        if timeout:
            self.expirations[key] = time.time() + timeout

    def delete(self, key):
        self.data.pop(key, None)
        self.expirations.pop(key, None)


class TestSimpleCacheStandalone(unittest.TestCase):
    """Test SimpleCache implementation without Django dependencies"""

    def setUp(self):
        """Set up test environment"""
        # Mock Django cache
        self.mock_django_cache = MockDjangoCache()

        # Mock the Django cache import
        cache_patch = patch('shared.repositories.simple_cache.cache', self.mock_django_cache)
        cache_patch.start()

        # Import after mocking
        from shared.repositories.simple_cache import SimpleCache
        self.cache = SimpleCache(prefix='test_', timeout=300)

    def test_cache_set_and_get(self):
        """Test basic cache set and get operations"""
        # Arrange
        key = 'test_key'
        value = {'data': 'test_value', 'timestamp': '2024-01-01'}

        # Act
        self.cache.set(key, value)
        retrieved_value = self.cache.get(key)

        # Assert
        self.assertEqual(retrieved_value, value)
        self.assertEqual(self.mock_django_cache.data['test_test_key'], value)

    def test_cache_key_prefixing(self):
        """Test that cache keys are properly prefixed"""
        # Arrange
        key = 'user_data'
        value = {'id': 1, 'name': 'Test User'}

        # Act
        self.cache.set(key, value)

        # Assert - Check the actual cache key
        expected_cache_key = 'test_user_data'
        self.assertIn(expected_cache_key, self.mock_django_cache.data)
        self.assertEqual(self.mock_django_cache.data[expected_cache_key], value)

    def test_cache_get_nonexistent_key(self):
        """Test getting non-existent key returns None"""
        # Arrange
        key = 'nonexistent_key'

        # Act
        result = self.cache.get(key)

        # Assert
        self.assertIsNone(result)

    def test_cache_delete(self):
        """Test cache delete operation"""
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
        self.assertNotIn('test_delete_test', self.mock_django_cache.data)

    def test_cache_clear_pattern(self):
        """Test clearing cache pattern"""
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
        """Test cache timeout configuration"""
        # Arrange - Create a simple cache instance with different timeout
        short_timeout_cache_instance = self.cache.__class__(prefix='short_', timeout=1)

        # Act
        short_timeout_cache_instance.set('timeout_test', 'test_value')
        result = short_timeout_cache_instance.get('timeout_test')

        # Assert - Should still work with different timeout
        self.assertEqual(result, 'test_value')

    def test_cache_with_none_value(self):
        """Test caching None values"""
        # Arrange
        key = 'none_value_test'
        value = None

        # Act
        self.cache.set(key, value)
        result = self.cache.get(key)

        # Assert
        self.assertIsNone(result)  # This is expected behavior

    def test_cache_with_complex_data_types(self):
        """Test caching complex data types"""
        # Arrange
        import datetime
        test_data = {
            'simple_string': 'test',
            'number': 42,
            'list': [1, 2, 3],
            'dict': {'nested': 'value'},
            'datetime': datetime.datetime.now(),
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
        """Test that key collisions are prevented with prefixes"""
        # Arrange
        from shared.repositories.simple_cache import SimpleCache

        cache1 = SimpleCache(prefix='cache1_', timeout=300)
        cache2 = SimpleCache(prefix='cache2_', timeout=300)

        # Mock both caches
        cache1._cache_backend = MockDjangoCache()
        cache2._cache_backend = MockDjangoCache()

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

    def test_cache_performance_with_many_operations(self):
        """Test cache performance with many operations"""
        # Arrange
        import time

        iterations = 100

        # Act
        start_time = time.time()

        for i in range(iterations):
            key = f'perf_key_{i}'
            value = f'perf_value_{i}'
            self.cache.set(key, value)
            retrieved = self.cache.get(key)
            self.assertEqual(retrieved, value)

        end_time = time.time()
        execution_time = end_time - start_time

        # Assert - Should complete quickly (less than 1 second for 100 operations)
        self.assertLess(execution_time, 1.0)

        # Calculate operations per second
        ops_per_second = iterations / execution_time
        self.assertGreater(ops_per_second, 50)  # Should handle at least 50 ops/sec

    def test_cache_error_handling(self):
        """Test error handling follows KISS principle"""
        # Arrange & Act
        try:
            result = self.cache.get(None)
            self.assertIsNone(result)  # Should handle None gracefully
        except Exception:
            self.fail("Cache.get(None) should not raise exception")

        try:
            self.cache.set('', 'test')
            self.assertTrue(True)  # Should not raise exception
        except Exception:
            self.fail("Cache.set('', 'test') should not raise exception")

    def test_cache_interface_simplicity(self):
        """Test that cache interface follows KISS principle"""
        # Arrange & Act
        # Test interface simplicity
        self.assertTrue(hasattr(self.cache, 'get'))
        self.assertTrue(hasattr(self.cache, 'set'))
        self.assertTrue(hasattr(self.cache, 'delete'))
        self.assertTrue(hasattr(self.cache, 'clear_pattern'))

        # Assert - No complex methods
        method_names = [method for method in dir(self.cache) if not method.startswith('_')]
        expected_methods = ['get', 'set', 'delete', 'clear_pattern']

        for method in expected_methods:
            self.assertIn(method, method_names)

        # Assert - Methods are simple (few parameters)
        import inspect
        get_signature = inspect.signature(self.cache.get)
        self.assertLessEqual(len(get_signature.parameters), 2)  # self + key

    def test_cache_builder_pattern_integration(self):
        """Test cache integration with builder pattern"""
        from shared.repositories.simple_cache import CachedRepositoryMixin

        # Arrange
        class TestRepository(CachedRepositoryMixin):
            model = Mock()
            model._meta = Mock()
            model._meta.model_name = 'testmodel'
            cache_timeout = 600

        repository = TestRepository()

        # Assert
        self.assertIsInstance(repository.cache, type(self.cache))
        self.assertEqual(repository.cache.prefix, 'testmodel_')
        self.assertEqual(repository.cache.timeout, 600)


class TestCachedRepositoryMixinStandalone(unittest.TestCase):
    """Test CachedRepositoryMixin without Django dependencies"""

    def setUp(self):
        """Set up test environment"""
        self.mock_cache = MockDjangoCache()
        cache_patch = patch('shared.repositories.simple_cache.cache', self.mock_cache)
        cache_patch.start()

    def test_cached_repository_initialization(self):
        """Test repository mixin initialization"""
        # Arrange
        from shared.repositories.simple_cache import CachedRepositoryMixin

        class TestRepository(CachedRepositoryMixin):
            model = Mock()
            model._meta = Mock()
            model._meta.model_name = 'user'
            cache_timeout = 600

        # Act
        repository = TestRepository()

        # Assert - Check that repository was initialized
        self.assertIsInstance(repository, TestRepository)
        self.assertTrue(hasattr(repository, 'cache'))

    def test_cached_or_fetch_pattern_hit(self):
        """Test cached or fetch pattern with cache hit"""
        # Arrange
        from shared.repositories.simple_cache import CachedRepositoryMixin

        class TestRepository(CachedRepositoryMixin):
            model = Mock()
            model._meta = Mock()
            model._meta.model_name = 'test'

        repository = TestRepository()
        cache_key = 'test_1'
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
        """Test cached or fetch pattern with cache miss"""
        # Arrange
        from shared.repositories.simple_cache import CachedRepositoryMixin

        class TestRepository(CachedRepositoryMixin):
            model = Mock()
            model._meta = Mock()
            model._meta.model_name = 'test'

        repository = TestRepository()
        cache_key = 'test_1'
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


if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2)