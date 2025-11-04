"""
Authentication monitoring and metrics.

This module provides authentication event tracking following SOLID principles:
- Single Responsibility: Focuses solely on authentication monitoring
- Open/Closed: Can be extended without modification
- Dependency Inversion: Depends on logging and metrics abstractions
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from django.utils import timezone
from django.core.cache import cache
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver
from django.db.models import Count

import structlog

from .metrics import get_alert_manager

logger = structlog.get_logger(__name__)


@dataclass
class AuthEvent:
    """
    Data class representing an authentication event.

    This class follows the Single Responsibility Principle by focusing
    solely on representing authentication event data.
    """
    event_type: str  # 'login_success', 'login_failure', 'logout'
    username: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    timestamp: datetime
    user_id: Optional[int] = None
    failure_reason: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        """Initialize metadata if not provided."""
        if self.metadata is None:
            self.metadata = {}


class AuthenticationMonitor:
    """
    Monitor for authentication events and security.

    This class follows the Single Responsibility Principle by focusing
    solely on authentication monitoring and security analysis.
    """

    def __init__(self):
        """Initialize authentication monitor."""
        self.auth_logger = structlog.get_logger('auth_events')

        # Configuration
        self.failure_threshold = 5  # Number of failures before alert
        self.failure_window_minutes = 15  # Time window for failure counting
        self.lockout_duration_minutes = 30  # Duration of IP-based lockout

    def record_login_success(self, user, request, metadata: Optional[Dict[str, Any]] = None):
        """
        Record a successful login event.

        Args:
            user: The user object
            request: Django request object
            metadata: Additional metadata to record
        """
        event = AuthEvent(
            event_type='login_success',
            username=user.username,
            ip_address=self._get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            timestamp=timezone.now(),
            user_id=user.id,
            metadata=metadata or {}
        )

        self._record_event(event)
        self._update_login_metrics(event)

    def record_login_failure(self, username: str, request, failure_reason: str = None, metadata: Optional[Dict[str, Any]] = None):
        """
        Record a failed login attempt.

        Args:
            username: Username that was attempted
            request: Django request object
            failure_reason: Reason for the failure
            metadata: Additional metadata to record
        """
        event = AuthEvent(
            event_type='login_failure',
            username=username,
            ip_address=self._get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            timestamp=timezone.now(),
            failure_reason=failure_reason,
            metadata=metadata or {}
        )

        self._record_event(event)
        self._update_failure_metrics(event)
        self._check_security_alerts(event)

    def record_logout(self, user, request, metadata: Optional[Dict[str, Any]] = None):
        """
        Record a logout event.

        Args:
            user: The user object
            request: Django request object
            metadata: Additional metadata to record
        """
        event = AuthEvent(
            event_type='logout',
            username=user.username,
            ip_address=self._get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            timestamp=timezone.now(),
            user_id=user.id,
            metadata=metadata or {}
        )

        self._record_event(event)
        self._update_logout_metrics(event)

    def get_authentication_stats(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get authentication statistics for the specified time period.

        Args:
            hours: Number of hours to look back

        Returns:
            Dict[str, Any]: Authentication statistics
        """
        try:
            cutoff_time = timezone.now() - timedelta(hours=hours)

            # Get recent auth events from cache or database
            cache_key = f'auth_stats_{hours}h'
            stats = cache.get(cache_key)

            if stats is None:
                stats = self._calculate_auth_stats(cutoff_time)
                cache.set(cache_key, stats, timeout=300)  # Cache for 5 minutes

            return stats

        except Exception as e:
            logger.error(f"Failed to get authentication stats: {e}")
            return {
                'error': str(e),
                'login_success': 0,
                'login_failure': 0,
                'logout': 0,
                'unique_users': 0,
                'failure_rate': 0.0,
            }

    def _record_event(self, event: AuthEvent):
        """
        Record an authentication event.

        Args:
            event: The authentication event to record
        """
        # Log the event
        log_data = {
            'event_type': event.event_type,
            'username': event.username,
            'ip_address': event.ip_address,
            'user_agent': event.user_agent,
            'timestamp': event.timestamp.isoformat(),
        }

        if event.user_id:
            log_data['user_id'] = event.user_id

        if event.failure_reason:
            log_data['failure_reason'] = event.failure_reason

        if event.metadata:
            log_data['metadata'] = event.metadata

        # Log with appropriate level
        if event.event_type == 'login_failure':
            self.auth_logger.warning('auth_event', **log_data)
        else:
            self.auth_logger.info('auth_event', **log_data)

        # Store in cache for real-time analysis
        self._store_event_in_cache(event)

    def _store_event_in_cache(self, event: AuthEvent):
        """
        Store event in cache for real-time analysis.

        Args:
            event: The authentication event to store
        """
        try:
            # Store recent events in cache for security analysis
            cache_key = f'auth_events_{event.event_type}'
            recent_events = cache.get(cache_key, [])

            # Add new event
            recent_events.append({
                'username': event.username,
                'ip_address': event.ip_address,
                'timestamp': event.timestamp.isoformat(),
                'failure_reason': event.failure_reason,
            })

            # Keep only last 100 events
            recent_events = recent_events[-100:]

            # Store with 15-minute timeout
            cache.set(cache_key, recent_events, timeout=900)

        except Exception as e:
            logger.error(f"Failed to store auth event in cache: {e}")

    def _update_login_metrics(self, event: AuthEvent):
        """
        Update login success metrics.

        Args:
            event: The login success event
        """
        try:
            # Update Prometheus metrics if available
            try:
                from .metrics import MetricsCollector
                metrics = MetricsCollector()
                metrics.record_auth_attempt('success')
            except ImportError:
                pass

            # Update cache-based counters
            cache_key = 'auth_metrics_24h'
            metrics_data = cache.get(cache_key, {
                'login_success': 0,
                'login_failure': 0,
                'logout': 0,
                'unique_users': set(),
            })

            metrics_data['login_success'] += 1
            metrics_data['unique_users'].add(event.username)

            cache.set(cache_key, metrics_data, timeout=3600)

        except Exception as e:
            logger.error(f"Failed to update login metrics: {e}")

    def _update_failure_metrics(self, event: AuthEvent):
        """
        Update login failure metrics.

        Args:
            event: The login failure event
        """
        try:
            # Update Prometheus metrics if available
            try:
                from .metrics import MetricsCollector
                metrics = MetricsCollector()
                metrics.record_auth_attempt('failure')
            except ImportError:
                pass

            # Update cache-based counters
            cache_key = 'auth_metrics_24h'
            metrics_data = cache.get(cache_key, {
                'login_success': 0,
                'login_failure': 0,
                'logout': 0,
                'unique_users': set(),
            })

            metrics_data['login_failure'] += 1

            cache.set(cache_key, metrics_data, timeout=3600)

            # Update IP-based failure tracking
            self._update_ip_failure_count(event.ip_address, event.timestamp)

        except Exception as e:
            logger.error(f"Failed to update failure metrics: {e}")

    def _update_logout_metrics(self, event: AuthEvent):
        """
        Update logout metrics.

        Args:
            event: The logout event
        """
        try:
            # Update cache-based counters
            cache_key = 'auth_metrics_24h'
            metrics_data = cache.get(cache_key, {
                'login_success': 0,
                'login_failure': 0,
                'logout': 0,
                'unique_users': set(),
            })

            metrics_data['logout'] += 1

            cache.set(cache_key, metrics_data, timeout=3600)

        except Exception as e:
            logger.error(f"Failed to update logout metrics: {e}")

    def _update_ip_failure_count(self, ip_address: str, timestamp: datetime):
        """
        Update failure count for an IP address.

        Args:
            ip_address: The IP address
            timestamp: The timestamp of the failure
        """
        if not ip_address:
            return

        try:
            cache_key = f'auth_failures_ip_{ip_address}'
            failures = cache.get(cache_key, [])

            # Add current failure
            failures.append(timestamp.isoformat())

            # Clean old failures (outside window)
            cutoff_time = timestamp - timedelta(minutes=self.failure_window_minutes)
            failures = [
                f for f in failures
                if datetime.fromisoformat(f) > cutoff_time
            ]

            # Store updated failures
            cache.set(cache_key, failures, timeout=self.failure_window_minutes * 60)

        except Exception as e:
            logger.error(f"Failed to update IP failure count: {e}")

    def _check_security_alerts(self, event: AuthEvent):
        """
        Check for security alerts based on authentication events.

        Args:
            event: The authentication event to check
        """
        try:
            if event.event_type != 'login_failure':
                return

            # Check for multiple failures from same IP
            if event.ip_address:
                self._check_ip_based_alerts(event)

            # Check for multiple failures for same username
            if event.username:
                self._check_username_based_alerts(event)

        except Exception as e:
            logger.error(f"Failed to check security alerts: {e}")

    def _check_ip_based_alerts(self, event: AuthEvent):
        """
        Check for IP-based security alerts.

        Args:
            event: The authentication event to check
        """
        try:
            cache_key = f'auth_failures_ip_{event.ip_address}'
            failures = cache.get(cache_key, [])

            if len(failures) >= self.failure_threshold:
                # Trigger security alert
                self._trigger_security_alert(
                    alert_type='multiple_login_failures_ip',
                    severity='warning',
                    title=f'Multiple Login Failures from IP: {event.ip_address}',
                    description=f'{len(failures)} failed login attempts from IP {event.ip_address} in the last {self.failure_window_minutes} minutes',
                    metadata={
                        'ip_address': event.ip_address,
                        'failure_count': len(failures),
                        'time_window_minutes': self.failure_window_minutes,
                        'failures': failures,
                    }
                )

        except Exception as e:
            logger.error(f"Failed to check IP-based alerts: {e}")

    def _check_username_based_alerts(self, event: AuthEvent):
        """
        Check for username-based security alerts.

        Args:
            event: The authentication event to check
        """
        try:
            # This would require tracking failures per username
            # For simplicity, we'll focus on IP-based alerts for now
            pass

        except Exception as e:
            logger.error(f"Failed to check username-based alerts: {e}")

    def _trigger_security_alert(self, alert_type: str, severity: str, title: str, description: str, metadata: Dict[str, Any]):
        """
        Trigger a security alert.

        Args:
            alert_type: Type of security alert
            severity: Alert severity level
            title: Alert title
            description: Alert description
            metadata: Additional metadata
        """
        try:
            from .alerts import Alert, get_alert_manager

            alert = Alert(
                alert_type=alert_type,
                severity=severity,
                title=title,
                description=description,
                source='auth_monitor',
                timestamp=timezone.now(),
                metadata=metadata
            )

            alert_manager = get_alert_manager()
            alert_manager.active_alerts[f"auth_{alert_type}"] = alert

            # Log the alert
            self.auth_logger.error(
                'security_alert',
                alert_type=alert_type,
                severity=severity,
                title=title,
                description=description,
                metadata=metadata,
            )

        except Exception as e:
            logger.error(f"Failed to trigger security alert: {e}")

    def _calculate_auth_stats(self, cutoff_time: datetime) -> Dict[str, Any]:
        """
        Calculate authentication statistics from database.

        Args:
            cutoff_time: Time cutoff for statistics calculation

        Returns:
            Dict[str, Any]: Calculated statistics
        """
        # This is a placeholder implementation
        # In a real system, you might want to store auth events in a database table
        # for historical analysis

        # For now, return data from cache
        cache_key = 'auth_metrics_24h'
        metrics_data = cache.get(cache_key, {
            'login_success': 0,
            'login_failure': 0,
            'logout': 0,
            'unique_users': set(),
        })

        total_attempts = metrics_data['login_success'] + metrics_data['login_failure']
        failure_rate = (metrics_data['login_failure'] / total_attempts * 100) if total_attempts > 0 else 0

        return {
            'login_success': metrics_data['login_success'],
            'login_failure': metrics_data['login_failure'],
            'logout': metrics_data['logout'],
            'unique_users': len(metrics_data['unique_users']),
            'failure_rate': round(failure_rate, 2),
            'total_attempts': total_attempts,
        }

    def _get_client_ip(self, request) -> Optional[str]:
        """
        Get client IP address from request.

        Args:
            request: Django request object

        Returns:
            Optional[str]: Client IP address
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')


# Global authentication monitor instance
_auth_monitor = None


def get_auth_monitor() -> AuthenticationMonitor:
    """
    Get the global authentication monitor instance.

    Returns:
        AuthenticationMonitor: Global authentication monitor
    """
    global _auth_monitor
    if _auth_monitor is None:
        _auth_monitor = AuthenticationMonitor()
    return _auth_monitor


# Django signal receivers for automatic authentication tracking

@receiver(user_logged_in)
def user_logged_in_handler(sender, request, user, **kwargs):
    """Handle user login success signal."""
    monitor = get_auth_monitor()
    monitor.record_login_success(user, request)


@receiver(user_logged_out)
def user_logged_out_handler(sender, request, user, **kwargs):
    """Handle user logout signal."""
    monitor = get_auth_monitor()
    monitor.record_logout(user, request)


@receiver(user_login_failed)
def user_login_failed_handler(sender, credentials, request, **kwargs):
    """Handle user login failure signal."""
    monitor = get_auth_monitor()
    monitor.record_login_failure(
        username=credentials.get('username', ''),
        request=request,
        failure_reason='invalid_credentials'
    )