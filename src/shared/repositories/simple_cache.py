"""
Simplified Caching Implementation - KISS Principle
Extracting complex caching to focused, simple components
"""

from django.core.cache import cache
from typing import Any, Optional
import logging

logger = logging.getLogger(__name__)


class SimpleCache:
    """
    Simple cache wrapper following KISS principle
    Focused on single responsibility: caching
    """

    def __init__(self, prefix: str, timeout: int = 300):
        self.prefix = prefix
        self.timeout = timeout

    def _make_key(self, key: str) -> str:
        """Generate cache key with prefix"""
        return f"{self.prefix}{key}"

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        cache_key = self._make_key(key)
        value = cache.get(cache_key)
        if value:
            logger.debug(f"Cache hit: {cache_key}")
        return value

    def set(self, key: str, value: Any) -> None:
        """Set value in cache"""
        cache_key = self._make_key(key)
        cache.set(cache_key, value, self.timeout)

    def delete(self, key: str) -> None:
        """Delete value from cache"""
        cache_key = self._make_key(key)
        cache.delete(cache_key)

    def clear_pattern(self, pattern: str) -> None:
        """Clear cache keys matching pattern"""
        cache_key = self._make_key(pattern)
        cache.delete(cache_key)


class CachedRepositoryMixin:
    """
    Simple caching mixin for repositories
    Following KISS principle
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cache = SimpleCache(
            prefix=f"{self.model._meta.model_name}_",
            timeout=getattr(self, 'cache_timeout', 300)
        )

    def _get_cached_or_fetch(self, cache_key: str, fetch_func, *args, **kwargs):
        """Generic cached or fetch pattern"""
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        result = fetch_func(*args, **kwargs)
        self.cache.set(cache_key, result)
        return result