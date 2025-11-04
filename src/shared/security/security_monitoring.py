"""
Comprehensive Security Logging and Monitoring System
Following SOLID principles and enterprise-grade security standards
"""

import json
import logging
import time
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
from django.core.cache import cache
from django.conf import settings
from django.utils import timezone
from django.db import models
from django.contrib.auth import get_user_model
from shared.security.exceptions import SecurityError

logger = logging.getLogger(__name__)

User = get_user_model()


class SecurityEventType(Enum):
    """
    Security event types
    Following Single Responsibility Principle for event categorization
    """
    AUTHENTICATION_FAILURE = "authentication_failure"
    AUTHENTICATION_SUCCESS = "authentication_success"
    AUTHORIZATION_FAILURE = "authorization_failure"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SQL_INJECTION_ATTEMPT = "sql_injection_attempt"
    XSS_ATTEMPT = "xss_attempt"
    CORS_VIOLATION = "cors_violation"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    MALICIOUS_REQUEST = "malicious_request"
    BRUTE_FORCE_ATTEMPT = "brute_force_attempt"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    DATA_EXFILTRATION_ATTEMPT = "data_exfiltration_attempt"
    ABNORMAL_API_USAGE = "abnormal_api_usage"
    SECURITY_POLICY_VIOLATION = "security_policy_violation"
    VULNERABILITY_SCAN = "vulnerability_scan"
    INTRUSION_ATTEMPT = "intrusion_attempt"


class SecuritySeverity(Enum):
    """
    Security event severity levels
    Following Single Responsibility Principle for severity classification
    """
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SecurityEvent:
    """
    Security event data structure
    Following Single Responsibility Principle for event data management
    """
    event_type: SecurityEventType
    severity: SecuritySeverity
    timestamp: datetime
    user_id: Optional[int] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    request_path: Optional[str] = None
    request_method: Optional[str] = None
    source: Optional[str] = None
    description: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    correlation_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary"""
        data = asdict(self)
        # Convert enums to strings
        data['event_type'] = self.event_type.value
        data['severity'] = self.severity.value
        data['timestamp'] = self.timestamp.isoformat()
        return data

    def to_json(self) -> str:
        """Convert event to JSON string"""
        return json.dumps(self.to_dict(), default=str)


class SecurityAlertManager:
    """
    Security Alert Management System
    Following Single Responsibility Principle for alert processing

    Features:
    - Alert threshold monitoring
    - Escalation management
    - Alert aggregation
    - Notification dispatch
    - Alert history tracking
    """

    def __init__(self):
        """
        Initialize security alert manager
        Following Dependency Inversion Principle for configuration
        """
        self.alert_thresholds = getattr(settings, 'SECURITY_ALERT_THRESHOLDS', {
            SecurityEventType.RATE_LIMIT_EXCEEDED: 10,  # 10 per minute
            SecurityEventType.SQL_INJECTION_ATTEMPT: 1,  # Any attempt
            SecurityEventType.XSS_ATTEMPT: 1,  # Any attempt
            SecurityEventType.AUTHENTICATION_FAILURE: 5,  # 5 per minute
            SecurityEventType.SUSPICIOUS_ACTIVITY: 3,  # 3 per minute
            SecurityEventType.BRUTE_FORCE_ATTEMPT: 3,  # 3 per minute
        })

        self.escalation_thresholds = getattr(settings, 'SECURITY_ESCALATION_THRESHOLDS', {
            SecuritySeverity.HIGH: 3,  # 3 high-severity events
            SecuritySeverity.CRITICAL: 1,  # Any critical event
        })

        self.alert_cooldown = getattr(settings, 'SECURITY_ALERT_COOLDOWN', 300)  # 5 minutes
        self.enable_notifications = getattr(settings, 'SECURITY_NOTIFICATIONS_ENABLED', True)

        # Alert state tracking
        self._alert_cache = {}
        self._escalation_cache = {}

    def process_security_event(self, event: SecurityEvent) -> Dict[str, Any]:
        """
        Process security event and generate alerts if needed
        Following Single Responsibility Principle
        """
        alert_result = {
            'event_processed': True,
            'alert_generated': False,
            'escalation_triggered': False,
            'notifications_sent': []
        }

        try:
            # Check alert thresholds
            alert_check = self._check_alert_threshold(event)
            if alert_check['should_alert']:
                alert_result['alert_generated'] = True
                self._generate_alert(event, alert_check)

                # Check escalation
                escalation_check = self._check_escalation_threshold(event)
                if escalation_check['should_escalate']:
                    alert_result['escalation_triggered'] = True
                    self._escalate_alert(event, escalation_check)

                # Send notifications
                if self.enable_notifications:
                    notifications = self._send_notifications(event)
                    alert_result['notifications_sent'] = notifications

        except Exception as e:
            logger.error(f"Error processing security event: {str(e)}")

        return alert_result

    def _check_alert_threshold(self, event: SecurityEvent) -> Dict[str, Any]:
        """
        Check if event exceeds alert threshold
        Following Single Responsibility Principle
        """
        threshold = self.alert_thresholds.get(event.event_type, 5)  # Default threshold
        time_window = 60  # 1 minute

        # Create cache key
        cache_key = f"security_alert:{event.event_type.value}:{event.ip_address or 'no_ip'}"

        # Get current count
        current_count = cache.get(cache_key, 0)

        # Increment count
        new_count = current_count + 1
        cache.set(cache_key, new_count, timeout=time_window)

        return {
            'should_alert': new_count >= threshold,
            'current_count': new_count,
            'threshold': threshold,
            'time_window': time_window
        }

    def _check_escalation_threshold(self, event: SecurityEvent) -> Dict[str, Any]:
        """
        Check if event requires escalation
        Following Single Responsibility Principle
        """
        threshold = self.escalation_thresholds.get(event.severity, 5)
        time_window = 300  # 5 minutes

        # Create cache key
        cache_key = f"security_escalation:{event.severity.value}:{event.ip_address or 'no_ip'}"

        # Get current count
        current_count = cache.get(cache_key, 0)

        # Increment count
        new_count = current_count + 1
        cache.set(cache_key, new_count, timeout=time_window)

        return {
            'should_escalate': new_count >= threshold,
            'current_count': new_count,
            'threshold': threshold,
            'time_window': time_window
        }

    def _generate_alert(self, event: SecurityEvent, alert_check: Dict[str, Any]):
        """
        Generate security alert
        Following Single Responsibility Principle
        """
        alert_data = {
            'alert_id': self._generate_alert_id(event),
            'event_type': event.event_type.value,
            'severity': event.severity.value,
            'timestamp': event.timestamp.isoformat(),
            'ip_address': event.ip_address,
            'user_id': event.user_id,
            'description': f"Security alert: {event.event_type.value}",
            'details': event.details or {},
            'threshold_info': alert_check,
            'requires_action': event.severity in [SecuritySeverity.HIGH, SecuritySeverity.CRITICAL]
        }

        # Log alert
        logger.warning(
            f"Security alert generated: {event.event_type.value} from {event.ip_address}",
            extra={'alert_data': alert_data}
        )

        # Store alert in cache for dashboard
        alert_cache_key = f"security_alert_dashboard:{alert_data['alert_id']}"
        cache.set(alert_cache_key, alert_data, timeout=3600)  # 1 hour

    def _escalate_alert(self, event: SecurityEvent, escalation_check: Dict[str, Any]):
        """
        Escalate security alert
        Following Single Responsibility Principle
        """
        escalation_data = {
            'escalation_id': self._generate_escalation_id(event),
            'alert_id': self._generate_alert_id(event),
            'event_type': event.event_type.value,
            'severity': event.severity.value,
            'timestamp': event.timestamp.isoformat(),
            'ip_address': event.ip_address,
            'user_id': event.user_id,
            'escalation_reason': f"Threshold exceeded: {escalation_check['current_count']}/{escalation_check['threshold']}",
            'requires_immediate_action': event.severity == SecuritySeverity.CRITICAL
        }

        # Log escalation
        logger.critical(
            f"Security alert escalated: {event.event_type.value} from {event.ip_address}",
            extra={'escalation_data': escalation_data}
        )

    def _send_notifications(self, event: SecurityEvent) -> List[str]:
        """
        Send security notifications
        Following Single Responsibility Principle
        """
        notifications_sent = []

        try:
            # High and critical severity events require immediate notification
            if event.severity in [SecuritySeverity.HIGH, SecuritySeverity.CRITICAL]:
                # Email notification
                if getattr(settings, 'SECURITY_EMAIL_NOTIFICATIONS', False):
                    self._send_email_notification(event)
                    notifications_sent.append('email')

                # SMS notification for critical events
                if event.severity == SecuritySeverity.CRITICAL:
                    if getattr(settings, 'SECURITY_SMS_NOTIFICATIONS', False):
                        self._send_sms_notification(event)
                        notifications_sent.append('sms')

                # Slack notification
                if getattr(settings, 'SECURITY_SLACK_NOTIFICATIONS', False):
                    self._send_slack_notification(event)
                    notifications_sent.append('slack')

        except Exception as e:
            logger.error(f"Error sending security notifications: {str(e)}")

        return notifications_sent

    def _send_email_notification(self, event: SecurityEvent):
        """Send email notification (implementation depends on email backend)"""
        from django.core.mail import send_mail

        subject = f"Security Alert: {event.event_type.value}"
        message = f"""
        Security Event Details:
        - Type: {event.event_type.value}
        - Severity: {event.severity.value}
        - Timestamp: {event.timestamp}
        - IP Address: {event.ip_address}
        - User ID: {event.user_id}
        - Request Path: {event.request_path}
        - Description: {event.description}
        """

        send_mail(
            subject=subject,
            message=message,
            from_email=getattr(settings, 'SECURITY_ALERT_FROM_EMAIL', 'noreply@crm.com'),
            recipient_list=getattr(settings, 'SECURITY_ALERT_EMAIL_RECIPIENTS', []),
            fail_silently=False
        )

    def _send_sms_notification(self, event: SecurityEvent):
        """Send SMS notification (implementation depends on SMS service)"""
        # Placeholder for SMS implementation
        logger.info(f"SMS notification would be sent for critical security event: {event.event_type.value}")

    def _send_slack_notification(self, event: SecurityEvent):
        """Send Slack notification (implementation depends on Slack integration)"""
        # Placeholder for Slack implementation
        logger.info(f"Slack notification would be sent for security event: {event.event_type.value}")

    def _generate_alert_id(self, event: SecurityEvent) -> str:
        """Generate unique alert ID"""
        timestamp_str = event.timestamp.strftime('%Y%m%d%H%M%S')
        event_str = f"{event.event_type.value}{event.ip_address or 'no_ip'}{event.user_id or 'no_user'}"
        hash_str = hashlib.md5(event_str.encode()).hexdigest()[:8]
        return f"ALERT-{timestamp_str}-{hash_str}"

    def _generate_escalation_id(self, event: SecurityEvent) -> str:
        """Generate unique escalation ID"""
        timestamp_str = event.timestamp.strftime('%Y%m%d%H%M%S')
        event_str = f"{event.severity.value}{event.event_type.value}{event.ip_address or 'no_ip'}"
        hash_str = hashlib.md5(event_str.encode()).hexdigest()[:8]
        return f"ESC-{timestamp_str}-{hash_str}"


class SecurityEventLogger:
    """
    Security Event Logging System
    Following Single Responsibility Principle for event logging

    Features:
    - Structured event logging
    - Event persistence
    - Event aggregation
    - Log rotation
    - Performance monitoring
    """

    def __init__(self):
        """
        Initialize security event logger
        Following Dependency Inversion Principle for configuration
        """
        self.enable_file_logging = getattr(settings, 'SECURITY_FILE_LOGGING', True)
        self.enable_database_logging = getattr(settings, 'SECURITY_DATABASE_LOGGING', False)
        self.log_retention_days = getattr(settings, 'SECURITY_LOG_RETENTION_DAYS', 90)
        self.log_level = getattr(settings, 'SECURITY_LOG_LEVEL', 'INFO')

        # Configure security logger
        self._configure_security_logger()

    def _configure_security_logger(self):
        """Configure dedicated security logger"""
        self.security_logger = logging.getLogger('security.events')

        if not self.security_logger.handlers:
            # File handler for security events
            if self.enable_file_logging:
                from logging.handlers import RotatingFileHandler

                handler = RotatingFileHandler(
                    filename=getattr(settings, 'SECURITY_LOG_FILE', 'logs/security.log'),
                    maxBytes=getattr(settings, 'SECURITY_LOG_MAX_SIZE', 50 * 1024 * 1024),  # 50MB
                    backupCount=getattr(settings, 'SECURITY_LOG_BACKUP_COUNT', 5)
                )

                formatter = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )
                handler.setFormatter(formatter)
                self.security_logger.addHandler(handler)

            self.security_logger.setLevel(getattr(logging, self.log_level))

    def log_security_event(self, event: SecurityEvent):
        """
        Log security event
        Following Single Responsibility Principle
        """
        try:
            # File logging
            if self.enable_file_logging:
                self._log_to_file(event)

            # Database logging
            if self.enable_database_logging:
                self._log_to_database(event)

            # Structured logging
            self._log_structured(event)

        except Exception as e:
            logger.error(f"Error logging security event: {str(e)}")

    def _log_to_file(self, event: SecurityEvent):
        """Log event to file"""
        log_message = f"{event.event_type.value} | {event.severity.value} | {event.ip_address} | {event.description}"
        self.security_logger.info(log_message, extra={'security_event': event.to_dict()})

    def _log_to_database(self, event: SecurityEvent):
        """Log event to database (if SecurityEventLog model exists)"""
        # This would require a SecurityEventLog model to be defined
        # Placeholder for database logging implementation
        pass

    def _log_structured(self, event: SecurityEvent):
        """Log event in structured format"""
        log_data = {
            'event_type': event.event_type.value,
            'severity': event.severity.value,
            'timestamp': event.timestamp.isoformat(),
            'user_id': event.user_id,
            'ip_address': event.ip_address,
            'request_path': event.request_path,
            'request_method': event.request_method,
            'description': event.description,
            'details': event.details
        }

        # Use appropriate log level based on severity
        if event.severity == SecuritySeverity.CRITICAL:
            logger.critical("Security event detected", extra={'security_event': log_data})
        elif event.severity == SecuritySeverity.HIGH:
            logger.error("Security event detected", extra={'security_event': log_data})
        elif event.severity == SecuritySeverity.MEDIUM:
            logger.warning("Security event detected", extra={'security_event': log_data})
        else:
            logger.info("Security event detected", extra={'security_event': log_data})


class SecurityMonitor:
    """
    Main Security Monitoring System
    Following Single Responsibility Principle for security monitoring

    Features:
    - Real-time security monitoring
    - Event correlation
    - Anomaly detection
    - Performance monitoring
    - Dashboard integration
    """

    def __init__(self):
        """
        Initialize security monitor
        Following Dependency Inversion Principle
        """
        self.alert_manager = SecurityAlertManager()
        self.event_logger = SecurityEventLogger()

        # Monitoring settings
        self.enable_real_time_monitoring = getattr(settings, 'SECURITY_REAL_TIME_MONITORING', True)
        self.anomaly_detection_enabled = getattr(settings, 'SECURITY_ANOMALY_DETECTION', True)
        self.performance_monitoring_enabled = getattr(settings, 'SECURITY_PERFORMANCE_MONITORING', True)

        # Statistics tracking
        self.stats = {
            'events_processed': 0,
            'alerts_generated': 0,
            'escalations_triggered': 0,
            'events_by_type': {},
            'events_by_severity': {},
            'top_offenders': {},
            'processing_times': []
        }

    def process_security_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process security event data
        Following Single Responsibility Principle
        """
        start_time = time.time()

        try:
            # Create SecurityEvent object
            event = self._create_security_event(event_data)

            # Update statistics
            self._update_statistics(event)

            # Log event
            self.event_logger.log_security_event(event)

            # Process alerts
            alert_result = self.alert_manager.process_security_event(event)

            # Anomaly detection
            if self.anomaly_detection_enabled:
                self._detect_anomalies(event)

            processing_time = time.time() - start_time
            self.stats['processing_times'].append(processing_time)

            return {
                'event_id': self._generate_event_id(event),
                'processed': True,
                'alert_result': alert_result,
                'processing_time': processing_time
            }

        except Exception as e:
            logger.error(f"Error processing security event: {str(e)}")
            return {
                'processed': False,
                'error': str(e),
                'processing_time': time.time() - start_time
            }

    def _create_security_event(self, event_data: Dict[str, Any]) -> SecurityEvent:
        """
        Create SecurityEvent object from data
        Following Single Responsibility Principle
        """
        # Convert string values to enums
        event_type = SecurityEventType(event_data.get('event_type', SecurityEventType.SUSPICIOUS_ACTIVITY.value))
        severity = SecuritySeverity(event_data.get('severity', SecuritySeverity.MEDIUM.value))

        return SecurityEvent(
            event_type=event_type,
            severity=severity,
            timestamp=event_data.get('timestamp', timezone.now()),
            user_id=event_data.get('user_id'),
            ip_address=event_data.get('ip_address'),
            user_agent=event_data.get('user_agent'),
            request_path=event_data.get('request_path'),
            request_method=event_data.get('request_method'),
            source=event_data.get('source'),
            description=event_data.get('description'),
            details=event_data.get('details'),
            session_id=event_data.get('session_id'),
            request_id=event_data.get('request_id'),
            correlation_id=event_data.get('correlation_id')
        )

    def _update_statistics(self, event: SecurityEvent):
        """
        Update monitoring statistics
        Following Single Responsibility Principle
        """
        self.stats['events_processed'] += 1

        # Events by type
        event_type = event.event_type.value
        self.stats['events_by_type'][event_type] = self.stats['events_by_type'].get(event_type, 0) + 1

        # Events by severity
        severity = event.severity.value
        self.stats['events_by_severity'][severity] = self.stats['events_by_severity'].get(severity, 0) + 1

        # Top offenders (by IP)
        if event.ip_address:
            self.stats['top_offenders'][event.ip_address] = self.stats['top_offenders'].get(event.ip_address, 0) + 1

        # Alert and escalation counts
        alert_result = self.alert_manager.process_security_event(event)
        if alert_result['alert_generated']:
            self.stats['alerts_generated'] += 1
        if alert_result['escalation_triggered']:
            self.stats['escalations_triggered'] += 1

    def _detect_anomalies(self, event: SecurityEvent):
        """
        Detect security anomalies
        Following Single Responsibility Principle
        """
        # Implementation for anomaly detection
        # This could include pattern analysis, machine learning, etc.
        pass

    def _generate_event_id(self, event: SecurityEvent) -> str:
        """Generate unique event ID"""
        timestamp_str = event.timestamp.strftime('%Y%m%d%H%M%S%f')
        event_str = f"{event.event_type.value}{event.ip_address or 'no_ip'}{event.user_id or 'no_user'}"
        hash_str = hashlib.md5(event_str.encode()).hexdigest()[:8]
        return f"EVT-{timestamp_str}-{hash_str}"

    def get_monitoring_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive monitoring statistics
        Following Single Responsibility Principle
        """
        processing_times = self.stats['processing_times']
        avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0

        return {
            'events_processed': self.stats['events_processed'],
            'alerts_generated': self.stats['alerts_generated'],
            'escalations_triggered': self.stats['escalations_triggered'],
            'average_processing_time_ms': avg_processing_time * 1000,
            'events_by_type': self.stats['events_by_type'],
            'events_by_severity': self.stats['events_by_severity'],
            'top_offenders': dict(sorted(self.stats['top_offenders'].items(), key=lambda x: x[1], reverse=True)[:10]),
            'alert_statistics': self.alert_manager.policy_enforcer.get_statistics() if hasattr(self.alert_manager, 'policy_enforcer') else {}
        }

    def reset_statistics(self):
        """Reset monitoring statistics"""
        self.stats = {
            'events_processed': 0,
            'alerts_generated': 0,
            'escalations_triggered': 0,
            'events_by_type': {},
            'events_by_severity': {},
            'top_offenders': {},
            'processing_times': []
        }


# Global security monitor instance
security_monitor = SecurityMonitor()


def log_security_event(
    event_type: Union[str, SecurityEventType],
    severity: Union[str, SecuritySeverity] = SecuritySeverity.MEDIUM,
    **kwargs
) -> Dict[str, Any]:
    """
    Convenience function to log security events
    Following Single Responsibility Principle
    """
    event_data = {
        'event_type': event_type,
        'severity': severity,
        **kwargs
    }

    return security_monitor.process_security_event(event_data)