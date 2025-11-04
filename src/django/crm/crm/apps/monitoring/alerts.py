"""
System alerts and monitoring for critical conditions.

This module implements alerting functionality following SOLID principles:
- Single Responsibility: Each alert type focuses on one condition
- Open/Closed: New alert types can be added without modification
- Dependency Inversion: Depends on logging and notification abstractions
"""

import time
import threading
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass

from django.utils import timezone
from django.conf import settings
from django.core.cache import cache

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class Alert:
    """
    Data class representing an alert.

    This class follows the Single Responsibility Principle by focusing
    solely on representing alert data.
    """
    alert_type: str
    severity: str  # 'critical', 'warning', 'info'
    title: str
    description: str
    source: str
    timestamp: datetime
    metadata: Dict[str, Any]
    resolved: bool = False
    resolved_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary format."""
        return {
            'alert_type': self.alert_type,
            'severity': self.severity,
            'title': self.title,
            'description': self.description,
            'source': self.source,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata,
            'resolved': self.resolved,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
        }


class BaseAlertChecker(ABC):
    """
    Abstract base class for alert checkers.

    This class defines the interface that all alert checkers must implement,
    following the Dependency Inversion Principle.
    """

    @abstractmethod
    def check(self) -> Optional[Alert]:
        """
        Check for alert conditions.

        Returns:
            Optional[Alert]: Alert if condition detected, None otherwise
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """
        Get the name of this alert checker.

        Returns:
            str: Name of the alert checker
        """
        pass


class CpuUsageAlertChecker(BaseAlertChecker):
    """
    Alert checker for high CPU usage.

    This checker follows the Single Responsibility Principle by focusing
    solely on CPU usage monitoring.
    """

    def __init__(self, threshold_percent: float = 80.0):
        """
        Initialize CPU usage alert checker.

        Args:
            threshold_percent: CPU usage threshold for alerts
        """
        self.threshold_percent = threshold_percent

    def check(self) -> Optional[Alert]:
        """Check for high CPU usage."""
        try:
            import psutil
            cpu_percent = psutil.cpu_percent(interval=1)

            if cpu_percent >= self.threshold_percent:
                return Alert(
                    alert_type='cpu_usage_high',
                    severity='critical' if cpu_percent >= 90 else 'warning',
                    title=f'High CPU Usage: {cpu_percent:.1f}%',
                    description=f'CPU usage has exceeded {self.threshold_percent}% threshold',
                    source='system_monitor',
                    timestamp=timezone.now(),
                    metadata={
                        'cpu_percent': cpu_percent,
                        'threshold_percent': self.threshold_percent,
                        'cpu_count': psutil.cpu_count(),
                    }
                )

        except Exception as e:
            logger.error(f"CPU usage check failed: {e}")

        return None

    def get_name(self) -> str:
        return "CPU Usage Alert Checker"


class MemoryUsageAlertChecker(BaseAlertChecker):
    """
    Alert checker for high memory usage.

    This checker follows the Single Responsibility Principle by focusing
    solely on memory usage monitoring.
    """

    def __init__(self, threshold_percent: float = 85.0):
        """
        Initialize memory usage alert checker.

        Args:
            threshold_percent: Memory usage threshold for alerts
        """
        self.threshold_percent = threshold_percent

    def check(self) -> Optional[Alert]:
        """Check for high memory usage."""
        try:
            import psutil
            memory = psutil.virtual_memory()
            memory_percent = memory.percent

            if memory_percent >= self.threshold_percent:
                return Alert(
                    alert_type='memory_usage_high',
                    severity='critical' if memory_percent >= 95 else 'warning',
                    title=f'High Memory Usage: {memory_percent:.1f}%',
                    description=f'Memory usage has exceeded {self.threshold_percent}% threshold',
                    source='system_monitor',
                    timestamp=timezone.now(),
                    metadata={
                        'memory_percent': memory_percent,
                        'threshold_percent': self.threshold_percent,
                        'used_gb': round(memory.used / 1024 / 1024 / 1024, 2),
                        'total_gb': round(memory.total / 1024 / 1024 / 1024, 2),
                        'available_gb': round(memory.available / 1024 / 1024 / 1024, 2),
                    }
                )

        except Exception as e:
            logger.error(f"Memory usage check failed: {e}")

        return None

    def get_name(self) -> str:
        return "Memory Usage Alert Checker"


class DiskUsageAlertChecker(BaseAlertChecker):
    """
    Alert checker for high disk usage.

    This checker follows the Single Responsibility Principle by focusing
    solely on disk usage monitoring.
    """

    def __init__(self, threshold_percent: float = 90.0, disk_path: str = '/'):
        """
        Initialize disk usage alert checker.

        Args:
            threshold_percent: Disk usage threshold for alerts
            disk_path: Path to check for disk usage
        """
        self.threshold_percent = threshold_percent
        self.disk_path = disk_path

    def check(self) -> Optional[Alert]:
        """Check for high disk usage."""
        try:
            import psutil
            disk = psutil.disk_usage(self.disk_path)
            disk_percent = (disk.used / disk.total) * 100

            if disk_percent >= self.threshold_percent:
                return Alert(
                    alert_type='disk_usage_high',
                    severity='critical' if disk_percent >= 95 else 'warning',
                    title=f'High Disk Usage: {disk_percent:.1f}% on {self.disk_path}',
                    description=f'Disk usage has exceeded {self.threshold_percent}% threshold',
                    source='system_monitor',
                    timestamp=timezone.now(),
                    metadata={
                        'disk_path': self.disk_path,
                        'disk_percent': disk_percent,
                        'threshold_percent': self.threshold_percent,
                        'used_gb': round(disk.used / 1024 / 1024 / 1024, 2),
                        'total_gb': round(disk.total / 1024 / 1024 / 1024, 2),
                        'free_gb': round(disk.free / 1024 / 1024 / 1024, 2),
                    }
                )

        except Exception as e:
            logger.error(f"Disk usage check failed: {e}")

        return None

    def get_name(self) -> str:
        return "Disk Usage Alert Checker"


class DatabaseConnectionAlertChecker(BaseAlertChecker):
    """
    Alert checker for database connection issues.

    This checker follows the Single Responsibility Principle by focusing
    solely on database connectivity monitoring.
    """

    def __init__(self, max_response_time_ms: float = 1000.0):
        """
        Initialize database connection alert checker.

        Args:
            max_response_time_ms: Maximum acceptable response time in milliseconds
        """
        self.max_response_time_ms = max_response_time_ms

    def check(self) -> Optional[Alert]:
        """Check for database connection issues."""
        try:
            from django.db import connection

            start_time = time.time()
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()

            response_time_ms = (time.time() - start_time) * 1000

            if response_time_ms >= self.max_response_time_ms:
                return Alert(
                    alert_type='database_slow_response',
                    severity='warning',
                    title=f'Database Slow Response: {response_time_ms:.1f}ms',
                    description=f'Database response time has exceeded {self.max_response_time_ms}ms threshold',
                    source='database_monitor',
                    timestamp=timezone.now(),
                    metadata={
                        'response_time_ms': response_time_ms,
                        'threshold_ms': self.max_response_time_ms,
                    }
                )

        except Exception as e:
            return Alert(
                alert_type='database_connection_failed',
                severity='critical',
                title='Database Connection Failed',
                description=f'Database connection failed: {str(e)}',
                source='database_monitor',
                timestamp=timezone.now(),
                metadata={
                    'error': str(e),
                }
            )

        return None

    def get_name(self) -> str:
        return "Database Connection Alert Checker"


class RedisConnectionAlertChecker(BaseAlertChecker):
    """
    Alert checker for Redis connection issues.

    This checker follows the Single Responsibility Principle by focusing
    solely on Redis connectivity monitoring.
    """

    def __init__(self, max_response_time_ms: float = 500.0):
        """
        Initialize Redis connection alert checker.

        Args:
            max_response_time_ms: Maximum acceptable response time in milliseconds
        """
        self.max_response_time_ms = max_response_time_ms

    def check(self) -> Optional[Alert]:
        """Check for Redis connection issues."""
        try:
            from django.core.cache import cache

            start_time = time.time()
            test_key = 'health_check_test'
            cache.set(test_key, 'test_value', timeout=10)
            result = cache.get(test_key)
            cache.delete(test_key)

            response_time_ms = (time.time() - start_time) * 1000

            if response_time_ms >= self.max_response_time_ms:
                return Alert(
                    alert_type='redis_slow_response',
                    severity='warning',
                    title=f'Redis Slow Response: {response_time_ms:.1f}ms',
                    description=f'Redis response time has exceeded {self.max_response_time_ms}ms threshold',
                    source='cache_monitor',
                    timestamp=timezone.now(),
                    metadata={
                        'response_time_ms': response_time_ms,
                        'threshold_ms': self.max_response_time_ms,
                    }
                )

            if result != 'test_value':
                return Alert(
                    alert_type='redis_data_corruption',
                    severity='critical',
                    title='Redis Data Integrity Issue',
                    description='Redis cache returned unexpected data',
                    source='cache_monitor',
                    timestamp=timezone.now(),
                    metadata={
                        'expected': 'test_value',
                        'received': str(result),
                    }
                )

        except Exception as e:
            return Alert(
                alert_type='redis_connection_failed',
                severity='critical',
                title='Redis Connection Failed',
                description=f'Redis connection failed: {str(e)}',
                source='cache_monitor',
                timestamp=timezone.now(),
                metadata={
                    'error': str(e),
                }
            )

        return None

    def get_name(self) -> str:
        return "Redis Connection Alert Checker"


class ApiErrorRateAlertChecker(BaseAlertChecker):
    """
    Alert checker for high API error rates.

    This checker follows the Single Responsibility Principle by focusing
    solely on API error rate monitoring.
    """

    def __init__(self, error_rate_threshold: float = 5.0, window_minutes: int = 5):
        """
        Initialize API error rate alert checker.

        Args:
            error_rate_threshold: Error rate threshold as percentage
            window_minutes: Time window for error rate calculation
        """
        self.error_rate_threshold = error_rate_threshold
        self.window_minutes = window_minutes

    def check(self) -> Optional[Alert]:
        """Check for high API error rates."""
        try:
            # This would typically use actual metrics data
            # For now, we'll check cache-based error tracking
            cache_key = 'api_error_rate_5m'
            error_data = cache.get(cache_key, {})

            if error_data:
                total_requests = error_data.get('total_requests', 0)
                error_requests = error_data.get('error_requests', 0)

                if total_requests > 0:
                    error_rate = (error_requests / total_requests) * 100

                    if error_rate >= self.error_rate_threshold:
                        return Alert(
                            alert_type='api_error_rate_high',
                            severity='warning',
                            title=f'High API Error Rate: {error_rate:.1f}%',
                            description=f'API error rate has exceeded {self.error_rate_threshold}% threshold over {self.window_minutes} minutes',
                            source='api_monitor',
                            timestamp=timezone.now(),
                            metadata={
                                'error_rate': error_rate,
                                'threshold_percent': self.error_rate_threshold,
                                'window_minutes': self.window_minutes,
                                'total_requests': total_requests,
                                'error_requests': error_requests,
                            }
                        )

        except Exception as e:
            logger.error(f"API error rate check failed: {e}")

        return None

    def get_name(self) -> str:
        return "API Error Rate Alert Checker"


class AlertManager:
    """
    Main alert management system.

    This class follows the Single Responsibility Principle by focusing
    on coordinating all alert checking and notification.
    """

    def __init__(self):
        """Initialize alert manager with all alert checkers."""
        self.alert_checkers = self._initialize_checkers()
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_handlers = []
        self.alert_logger = structlog.get_logger('alerts')

        # Configuration
        self.check_interval_seconds = getattr(settings, 'ALERT_CHECK_INTERVAL_SECONDS', 60)
        self.alert_cooldown_minutes = getattr(settings, 'ALERT_COOLDOWN_MINUTES', 5)

    def _initialize_checkers(self) -> List[BaseAlertChecker]:
        """Initialize all alert checkers with configuration from settings."""
        return [
            CpuUsageAlertChecker(
                threshold_percent=getattr(settings, 'ALERT_CPU_USAGE_PERCENT', 80.0)
            ),
            MemoryUsageAlertChecker(
                threshold_percent=getattr(settings, 'ALERT_MEMORY_USAGE_PERCENT', 85.0)
            ),
            DiskUsageAlertChecker(
                threshold_percent=getattr(settings, 'ALERT_DISK_USAGE_PERCENT', 90.0)
            ),
            DatabaseConnectionAlertChecker(
                max_response_time_ms=getattr(settings, 'ALERT_RESPONSE_TIME_MS', 2000.0)
            ),
            RedisConnectionAlertChecker(),
            ApiErrorRateAlertChecker(
                error_rate_threshold=getattr(settings, 'ALERT_ERROR_RATE_PERCENT', 5.0)
            ),
        ]

    def add_alert_handler(self, handler: Callable[[Alert], None]):
        """
        Add an alert handler function.

        Args:
            handler: Function that accepts an Alert and processes it
        """
        self.alert_handlers.append(handler)

    def check_all_alerts(self) -> List[Alert]:
        """
        Run all alert checkers and return triggered alerts.

        Returns:
            List[Alert]: List of triggered alerts
        """
        triggered_alerts = []

        for checker in self.alert_checkers:
            try:
                alert = checker.check()
                if alert:
                    alert_key = f"{alert.alert_type}_{alert.source}"

                    # Check if we should suppress this alert due to cooldown
                    if self._should_suppress_alert(alert_key):
                        continue

                    # Add to active alerts
                    self.active_alerts[alert_key] = alert
                    triggered_alerts.append(alert)

                    # Log the alert
                    self.alert_logger.warning(
                        'alert_triggered',
                        alert_type=alert.alert_type,
                        severity=alert.severity,
                        title=alert.title,
                        description=alert.description,
                        source=alert.source,
                        metadata=alert.metadata,
                    )

                    # Notify handlers
                    self._notify_handlers(alert)

            except Exception as e:
                self.alert_logger.error(
                    'alert_checker_error',
                    checker_name=checker.get_name(),
                    error=str(e)
                )

        # Check for resolved alerts
        self._check_resolved_alerts()

        return triggered_alerts

    def _should_suppress_alert(self, alert_key: str) -> bool:
        """
        Check if an alert should be suppressed due to cooldown.

        Args:
            alert_key: Unique key for the alert

        Returns:
            bool: True if alert should be suppressed
        """
        if alert_key not in self.active_alerts:
            return False

        last_alert = self.active_alerts[alert_key]
        cooldown_seconds = self.alert_cooldown_minutes * 60

        return (timezone.now() - last_alert.timestamp).total_seconds() < cooldown_seconds

    def _check_resolved_alerts(self):
        """Check if any active alerts have been resolved."""
        for alert_key, alert in list(self.active_alerts.items()):
            # For simplicity, we'll consider an alert resolved if it hasn't been
            # triggered again in the last check cycle. In a real implementation,
            # you would re-check the specific conditions.

            # This is a simplified approach - a more robust implementation
            # would re-run the specific checker for each alert type
            if (timezone.now() - alert.timestamp).total_seconds() > self.check_interval_seconds * 2:
                alert.resolved = True
                alert.resolved_at = timezone.now()

                # Log resolution
                self.alert_logger.info(
                    'alert_resolved',
                    alert_type=alert.alert_type,
                    duration_seconds=(alert.resolved_at - alert.timestamp).total_seconds()
                )

                # Notify handlers of resolution
                self._notify_handlers(alert)

                # Remove from active alerts
                del self.active_alerts[alert_key]

    def _notify_handlers(self, alert: Alert):
        """
        Notify all registered alert handlers.

        Args:
            alert: The alert to notify about
        """
        for handler in self.alert_handlers:
            try:
                handler(alert)
            except Exception as e:
                self.alert_logger.error(
                    'alert_handler_error',
                    handler=handler.__name__,
                    error=str(e)
                )

    def get_active_alerts(self) -> List[Alert]:
        """
        Get all currently active alerts.

        Returns:
            List[Alert]: List of active alerts
        """
        return list(self.active_alerts.values())

    def clear_alert(self, alert_key: str):
        """
        Manually clear an alert.

        Args:
            alert_key: Key of the alert to clear
        """
        if alert_key in self.active_alerts:
            alert = self.active_alerts[alert_key]
            alert.resolved = True
            alert.resolved_at = timezone.now()

            self.alert_logger.info(
                'alert_manually_cleared',
                alert_type=alert.alert_type
            )

            self._notify_handlers(alert)
            del self.active_alerts[alert_key]

    def start_monitoring(self):
        """Start background monitoring thread."""
        if not hasattr(self, '_monitoring_thread') or not self._monitoring_thread.is_alive():
            self._monitoring_thread = threading.Thread(
                target=self._monitoring_loop,
                daemon=True,
                name='AlertManager'
            )
            self._monitoring_thread.start()
            self.alert_logger.info('alert_monitoring_started')

    def stop_monitoring(self):
        """Stop background monitoring thread."""
        if hasattr(self, '_monitoring_thread') and self._monitoring_thread.is_alive():
            # This is a simplified stop - in production you might want
            # a more graceful shutdown mechanism
            self.alert_logger.info('alert_monitoring_stopped')

    def _monitoring_loop(self):
        """Background monitoring loop."""
        while True:
            try:
                self.check_all_alerts()
                time.sleep(self.check_interval_seconds)
            except Exception as e:
                self.alert_logger.error(
                    'monitoring_loop_error',
                    error=str(e)
                )
                time.sleep(self.check_interval_seconds)


# Global alert manager instance
_alert_manager = None


def get_alert_manager() -> AlertManager:
    """
    Get the global alert manager instance.

    Returns:
        AlertManager: Global alert manager
    """
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager()
    return _alert_manager


def log_alert_handler(alert: Alert):
    """
    Default alert handler that logs alerts.

    Args:
        alert: The alert to log
    """
    alert_logger = structlog.get_logger('alert_handler')

    if alert.resolved:
        alert_logger.info(
            'alert_resolved',
            alert_type=alert.alert_type,
            title=alert.title,
            severity=alert.severity,
            duration_minutes=(alert.resolved_at - alert.timestamp).total_seconds() / 60,
        )
    else:
        getattr(alert_logger, alert.severity)(
            'alert_fired',
            alert_type=alert.alert_type,
            title=alert.title,
            description=alert.description,
            source=alert.source,
            metadata=alert.metadata,
        )