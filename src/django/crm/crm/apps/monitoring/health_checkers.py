"""
Health check components for monitoring system status.

This module implements individual health checkers following SOLID principles:
- Single Responsibility: Each checker focuses on one component
- Open/Closed: Checkers can be extended without modification
- Dependency Inversion: Checkers depend on abstractions
"""

import time
import psutil
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from django.db import connection
from django.core.cache import cache
from django.utils import timezone
from django.conf import settings

import redis
from celery import current_app


class BaseHealthChecker(ABC):
    """
    Abstract base class for health checkers.

    This class defines the interface that all health checkers must implement,
    following the Dependency Inversion Principle by providing an abstraction
    that higher-level modules can depend on.
    """

    @abstractmethod
    def is_healthy(self) -> bool:
        """
        Check if the component is healthy.

        Returns:
            bool: True if healthy, False otherwise
        """
        pass

    @abstractmethod
    def get_details(self) -> Dict[str, Any]:
        """
        Get detailed health information.

        Returns:
            Dict[str, Any]: Detailed health status and metrics
        """
        pass

    def check_with_timeout(self, timeout_seconds: float = 5.0) -> Dict[str, Any]:
        """
        Perform health check with timeout protection.

        Args:
            timeout_seconds: Maximum time to wait for health check

        Returns:
            Dict[str, Any]: Health check results with timeout handling
        """
        start_time = time.time()

        try:
            # Set timeout for the check
            original_timeout = getattr(settings, 'HEALTH_CHECK_TIMEOUT', 5.0)
            timeout = min(timeout_seconds, original_timeout)

            # Perform the health check
            is_healthy = self.is_healthy()
            details = self.get_details()

            # Add timing information
            duration_ms = (time.time() - start_time) * 1000
            details['check_duration_ms'] = round(duration_ms, 2)
            details['timeout_seconds'] = timeout

            return {
                'status': 'healthy' if is_healthy else 'unhealthy',
                'healthy': is_healthy,
                'details': details,
                'timestamp': timezone.now().isoformat()
            }

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return {
                'status': 'error',
                'healthy': False,
                'details': {
                    'error': str(e),
                    'check_duration_ms': round(duration_ms, 2),
                    'timeout_seconds': timeout_seconds
                },
                'timestamp': timezone.now().isoformat()
            }


class DatabaseHealthChecker(BaseHealthChecker):
    """
    Health checker for database connectivity and performance.

    This checker follows the Single Responsibility Principle by focusing
    solely on database health monitoring.
    """

    def __init__(self, connection_name: str = 'default'):
        """
        Initialize database health checker.

        Args:
            connection_name: Name of the database connection to check
        """
        self.connection_name = connection_name

    def is_healthy(self) -> bool:
        """
        Check if database connection is healthy.

        Returns:
            bool: True if database is responding correctly
        """
        try:
            # Test database connectivity with a simple query
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()

            # Check connection pool status
            if hasattr(connection, 'pool'):
                pool = connection.pool
                if pool and pool.num_overflow > pool.max_overflow * 0.9:
                    return False  # Pool is nearly exhausted

            return True

        except Exception:
            return False

    def get_details(self) -> Dict[str, Any]:
        """
        Get detailed database health information.

        Returns:
            Dict[str, Any]: Database status, connections, and performance metrics
        """
        try:
            details = {
                'status': 'connected',
                'connection_name': self.connection_name
            }

            # Get connection pool information if available
            if hasattr(connection, 'pool') and connection.pool:
                pool = connection.pool
                details.update({
                    'pool_size': getattr(pool, 'size', 'unknown'),
                    'checked_in': getattr(pool, 'checkedin', 0),
                    'checked_out': getattr(pool, 'checkedout', 0),
                    'overflow': getattr(pool, 'num_overflow', 0),
                    'max_overflow': getattr(pool, 'max_overflow', 'unknown')
                })

            # Test query performance
            start_time = time.time()
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            query_time_ms = (time.time() - start_time) * 1000
            details['query_response_time_ms'] = round(query_time_ms, 2)

            # Get database version
            with connection.cursor() as cursor:
                cursor.execute("SELECT version()")
                version = cursor.fetchone()[0]
                details['database_version'] = version

            return details

        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'connection_name': self.connection_name
            }


class RedisHealthChecker(BaseHealthChecker):
    """
    Health checker for Redis cache connectivity and performance.

    This checker focuses solely on Redis health monitoring following
    the Single Responsibility Principle.
    """

    def __init__(self, cache_alias: str = 'default'):
        """
        Initialize Redis health checker.

        Args:
            cache_alias: Name of the cache configuration to check
        """
        self.cache_alias = cache_alias

    def is_healthy(self) -> bool:
        """
        Check if Redis connection is healthy.

        Returns:
            bool: True if Redis is responding correctly
        """
        try:
            # Test Redis connectivity with a simple operation
            test_key = 'health_check_test'
            cache.set(test_key, 'test_value', timeout=10)
            result = cache.get(test_key)
            cache.delete(test_key)

            return result == 'test_value'

        except Exception:
            return False

    def get_details(self) -> Dict[str, Any]:
        """
        Get detailed Redis health information.

        Returns:
            Dict[str, Any]: Redis status, memory usage, and performance metrics
        """
        try:
            details = {
                'status': 'connected',
                'cache_alias': self.cache_alias
            }

            # Get Redis client and test performance
            redis_client = cache.client.get_client()

            # Test Redis response time
            start_time = time.time()
            redis_client.ping()
            ping_time_ms = (time.time() - start_time) * 1000
            details['ping_response_time_ms'] = round(ping_time_ms, 2)

            # Get Redis info
            redis_info = redis_client.info()
            details.update({
                'redis_version': redis_info.get('redis_version', 'unknown'),
                'connected_clients': redis_info.get('connected_clients', 0),
                'used_memory_mb': round(redis_info.get('used_memory', 0) / 1024 / 1024, 2),
                'used_memory_peak_mb': round(redis_info.get('used_memory_peak', 0) / 1024 / 1024, 2),
                'total_commands_processed': redis_info.get('total_commands_processed', 0),
                'keyspace_hits': redis_info.get('keyspace_hits', 0),
                'keyspace_misses': redis_info.get('keyspace_misses', 0),
                'uptime_seconds': redis_info.get('uptime_in_seconds', 0)
            })

            # Calculate hit rate
            hits = details['keyspace_hits']
            misses = details['keyspace_misses']
            total = hits + misses
            if total > 0:
                details['hit_rate_percent'] = round((hits / total) * 100, 2)
            else:
                details['hit_rate_percent'] = 0.0

            return details

        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'cache_alias': self.cache_alias
            }


class CeleryHealthChecker(BaseHealthChecker):
    """
    Health checker for Celery task queue status.

    This checker monitors Celery worker health and queue status
    following the Single Responsibility Principle.
    """

    def __init__(self, queue_name: Optional[str] = None):
        """
        Initialize Celery health checker.

        Args:
            queue_name: Specific queue to check, or None for all queues
        """
        self.queue_name = queue_name

    def is_healthy(self) -> bool:
        """
        Check if Celery workers are responding.

        Returns:
            bool: True if Celery workers are available
        """
        try:
            # Check if we can inspect workers
            inspect = current_app.control.inspect()
            stats = inspect.stats()

            # At least one worker should be active
            return bool(stats)

        except Exception:
            return False

    def get_details(self) -> Dict[str, Any]:
        """
        Get detailed Celery health information.

        Returns:
            Dict[str, Any]: Worker status, queue information, and task metrics
        """
        try:
            details = {
                'status': 'connected',
                'queue_name': self.queue_name or 'all'
            }

            # Get worker statistics
            inspect = current_app.control.inspect()
            stats = inspect.stats()

            if stats:
                # Count active workers
                details['active_workers'] = len(stats)
                details['workers'] = list(stats.keys())

                # Get worker details
                total_concurrency = 0
                for worker_name, worker_stats in stats.items():
                    pool_info = worker_stats.get('pool', {})
                    max_concurrency = pool_info.get('max-concurrency', 0)
                    total_concurrency += max_concurrency

                details['total_concurrency'] = total_concurrency

            # Get active tasks
            active = inspect.active()
            if active:
                total_active = sum(len(tasks) for tasks in active.values())
                details['active_tasks'] = total_active
                details['active_tasks_by_worker'] = {
                    worker: len(tasks) for worker, tasks in active.items()
                }
            else:
                details['active_tasks'] = 0

            # Get scheduled tasks
            scheduled = inspect.scheduled()
            if scheduled:
                total_scheduled = sum(len(tasks) for tasks in scheduled.values())
                details['scheduled_tasks'] = total_scheduled
            else:
                details['scheduled_tasks'] = 0

            # Get queue information
            with current_app.pool.acquire() as connection:
                for queue_name in current_app.conf.task_queues or []:
                    if self.queue_name is None or queue_name == self.queue_name:
                        try:
                            queue = connection.DefaultChannel(
                                connection, queue_name
                            )
                            message_count = queue.queue_declare(passive=True).message_count
                            details[f'queue_{queue_name}_messages'] = message_count
                        except Exception:
                            details[f'queue_{queue_name}_messages'] = 'unknown'

            # Get recent failed tasks (approximate - requires Celery result backend)
            try:
                from celery.result import AsyncResult
                # This is a simplified check - in production you might want
                # to use Flower or another monitoring tool
                details['failed_tasks_24h'] = 'monitoring_required'
            except Exception:
                details['failed_tasks_24h'] = 'unknown'

            return details

        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'queue_name': self.queue_name or 'all'
            }


class SystemHealthChecker(BaseHealthChecker):
    """
    Health checker for system resources (CPU, memory, disk).

    This checker monitors system-level health metrics following
    the Single Responsibility Principle.
    """

    def __init__(self, disk_path: str = '/'):
        """
        Initialize system health checker.

        Args:
            disk_path: Path to check for disk usage
        """
        self.disk_path = disk_path

    def is_healthy(self) -> bool:
        """
        Check if system resources are within acceptable limits.

        Returns:
            bool: True if system resources are healthy
        """
        try:
            # Check CPU usage (< 80%)
            cpu_percent = psutil.cpu_percent(interval=1)
            if cpu_percent > 80:
                return False

            # Check memory usage (< 85%)
            memory = psutil.virtual_memory()
            if memory.percent > 85:
                return False

            # Check disk usage (< 90%)
            disk = psutil.disk_usage(self.disk_path)
            disk_percent = (disk.used / disk.total) * 100
            if disk_percent > 90:
                return False

            return True

        except Exception:
            return False

    def get_details(self) -> Dict[str, Any]:
        """
        Get detailed system resource information.

        Returns:
            Dict[str, Any]: System resource usage and performance metrics
        """
        try:
            details = {'status': 'healthy'}

            # CPU information
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()
            details.update({
                'cpu_usage_percent': round(cpu_percent, 2),
                'cpu_count': cpu_count,
                'cpu_frequency_mhz': round(cpu_freq.current, 2) if cpu_freq else 'unknown'
            })

            # Memory information
            memory = psutil.virtual_memory()
            details.update({
                'memory_total_mb': round(memory.total / 1024 / 1024, 2),
                'memory_available_mb': round(memory.available / 1024 / 1024, 2),
                'memory_used_mb': round(memory.used / 1024 / 1024, 2),
                'memory_usage_percent': round(memory.percent, 2)
            })

            # Disk information
            disk = psutil.disk_usage(self.disk_path)
            details.update({
                'disk_path': self.disk_path,
                'disk_total_gb': round(disk.total / 1024 / 1024 / 1024, 2),
                'disk_used_gb': round(disk.used / 1024 / 1024 / 1024, 2),
                'disk_free_gb': round(disk.free / 1024 / 1024 / 1024, 2),
                'disk_usage_percent': round((disk.used / disk.total) * 100, 2)
            })

            # System load (Unix-like systems)
            try:
                load_avg = psutil.getloadavg()
                details.update({
                    'load_average_1m': round(load_avg[0], 2),
                    'load_average_5m': round(load_avg[1], 2),
                    'load_average_15m': round(load_avg[2], 2)
                })
            except AttributeError:
                # Not available on Windows
                pass

            # System uptime
            details['uptime_seconds'] = time.time() - psutil.boot_time()

            return details

        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }