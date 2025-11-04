"""
Email Types and Priorities for Background Email Tasks
Following SOLID principles and comprehensive email management
"""

from enum import Enum
from typing import Optional


class EmailType(Enum):
    """
    Enumeration of email types with their corresponding templates.

    This follows the Single Responsibility Principle by centralizing
    email type management and template mapping.
    """

    WELCOME = 'WELCOME'
    PASSWORD_RESET = 'PASSWORD_RESET'
    DEAL_NOTIFICATION = 'DEAL_NOTIFICATION'
    ACTIVITY_REMINDER = 'ACTIVITY_REMINDER'
    BULK = 'BULK'
    CUSTOM = 'CUSTOM'

    def get_template_path(self, format_type: str = 'html') -> str:
        """
        Get template path for this email type.

        Args:
            format_type: 'html' or 'text' format

        Returns:
            str: Template file path
        """
        template_mapping = {
            EmailType.WELCOME: f'emails/welcome.{format_type}',
            EmailType.PASSWORD_RESET: f'emails/password_reset.{format_type}',
            EmailType.DEAL_NOTIFICATION: f'emails/deal_notification.{format_type}',
            EmailType.ACTIVITY_REMINDER: f'emails/activity_reminder.{format_type}',
            EmailType.BULK: f'emails/bulk.{format_type}',
            EmailType.CUSTOM: f'emails/custom.{format_type}',
        }
        return template_mapping[self]

    def get_default_subject(self) -> str:
        """Get default subject for this email type"""
        subject_mapping = {
            EmailType.WELCOME: 'Welcome to Our CRM',
            EmailType.PASSWORD_RESET: 'Password Reset Request',
            EmailType.DEAL_NOTIFICATION: 'New Deal Notification',
            EmailType.ACTIVITY_REMINDER: 'Activity Reminder',
            EmailType.BULK: 'Company Announcement',
            EmailType.CUSTOM: 'Notification',
        }
        return subject_mapping[self]

    def get_priority(self) -> 'EmailPriority':
        """Get default priority for this email type"""
        priority_mapping = {
            EmailType.WELCOME: EmailPriority.HIGH,
            EmailType.PASSWORD_RESET: EmailPriority.HIGH,
            EmailType.DEAL_NOTIFICATION: EmailPriority.NORMAL,
            EmailType.ACTIVITY_REMINDER: EmailPriority.NORMAL,
            EmailType.BULK: EmailPriority.LOW,
            EmailType.CUSTOM: EmailPriority.NORMAL,
        }
        return priority_mapping[self]


class EmailPriority(Enum):
    """
    Enumeration of email priorities with queue mapping.

    This follows the Open/Closed Principle by allowing easy extension
    of priority levels while maintaining consistent queue behavior.
    """

    LOW = 1
    NORMAL = 5
    HIGH = 8
    CRITICAL = 10

    def get_queue(self) -> str:
        """Get queue name for this priority level"""
        queue_mapping = {
            EmailPriority.LOW: 'email_low',
            EmailPriority.NORMAL: 'email_normal',
            EmailPriority.HIGH: 'email_high',
            EmailPriority.CRITICAL: 'email_critical',
        }
        return queue_mapping[self]

    def get_rate_limit(self) -> str:
        """Get rate limit for this priority level"""
        rate_limit_mapping = {
            EmailPriority.LOW: '10/m',      # 10 emails per minute
            EmailPriority.NORMAL: '30/m',   # 30 emails per minute
            EmailPriority.HIGH: '60/m',     # 60 emails per minute
            EmailPriority.CRITICAL: '100/m', # 100 emails per minute
        }
        return rate_limit_mapping[self]

    def get_retry_delay(self) -> int:
        """Get retry delay in seconds for this priority"""
        delay_mapping = {
            EmailPriority.LOW: 300,      # 5 minutes
            EmailPriority.NORMAL: 180,   # 3 minutes
            EmailPriority.HIGH: 60,      # 1 minute
            EmailPriority.CRITICAL: 30,  # 30 seconds
        }
        return delay_mapping[self]


class EmailStatus(Enum):
    """
    Enumeration of email sending statuses.

    This follows the Single Responsibility Principle by providing
    a centralized status tracking system for email operations.
    """

    PENDING = 'PENDING'
    SENDING = 'SENDING'
    SENT = 'SENT'
    FAILED = 'FAILED'
    BOUNCED = 'BOUNCED'
    DELIVERED = 'DELIVERED'
    OPENED = 'OPENED'
    CLICKED = 'CLICKED'
    UNSUBSCRIBED = 'UNSUBSCRIBED'

    def is_completed(self) -> bool:
        """Check if email is in a completed state"""
        return self in {
            EmailStatus.SENT,
            EmailStatus.DELIVERED,
            EmailStatus.OPENED,
            EmailStatus.CLICKED,
            EmailStatus.BOUNCED,
            EmailStatus.FAILED,
            EmailStatus.UNSUBSCRIBED
        }

    def is_successful(self) -> bool:
        """Check if email processing was successful"""
        return self in {
            EmailStatus.SENT,
            EmailStatus.DELIVERED,
            EmailStatus.OPENED,
            EmailStatus.CLICKED
        }

    def is_failure(self) -> bool:
        """Check if email processing failed"""
        return self in {EmailStatus.FAILED, EmailStatus.BOUNCED}


class EmailTemplate(Enum):
    """
    Enumeration of email templates with their metadata.

    This follows the Open/Closed Principle by allowing template
    management without modifying existing code.
    """

    WELCOME_USER = 'emails/welcome_user.html'
    WELCOME_ADMIN = 'emails/welcome_admin.html'
    PASSWORD_RESET = 'emails/password_reset.html'
    DEAL_CREATED = 'emails/deal_created.html'
    DEAL_UPDATED = 'emails/deal_updated.html'
    DEAL_WON = 'emails/deal_won.html'
    DEAL_LOST = 'emails/deal_lost.html'
    ACTIVITY_REMINDER = 'emails/activity_reminder.html'
    ACTIVITY_OVERDUE = 'emails/activity_overdue.html'
    BULK_ANNOUNCEMENT = 'emails/bulk_announcement.html'
    SYSTEM_MAINTENANCE = 'emails/system_maintenance.html'
    MONTHLY_REPORT = 'emails/monthly_report.html'
    WEEKLY_SUMMARY = 'emails/weekly_summary.html'

    def get_context_variables(self) -> list:
        """Get required context variables for this template"""
        context_mapping = {
            EmailTemplate.WELCOME_USER: ['user', 'company_name', 'login_url'],
            EmailTemplate.WELCOME_ADMIN: ['user', 'admin_dashboard_url'],
            EmailTemplate.PASSWORD_RESET: ['user', 'reset_token', 'reset_url'],
            EmailTemplate.DEAL_CREATED: ['deal', 'assigned_to', 'created_by'],
            EmailTemplate.DEAL_UPDATED: ['deal', 'updated_fields', 'updated_by'],
            EmailTemplate.DEAL_WON: ['deal', 'sales_rep', 'deal_value'],
            EmailTemplate.DEAL_LOST: ['deal', 'loss_reason', 'sales_rep'],
            EmailTemplate.ACTIVITY_REMINDER: ['activity', 'assigned_to', 'due_date'],
            EmailTemplate.ACTIVITY_OVERDUE: ['activity', 'assigned_to', 'overdue_days'],
            EmailTemplate.BULK_ANNOUNCEMENT: ['announcement', 'sender', 'company_name'],
            EmailTemplate.SYSTEM_MAINTENANCE: ['maintenance_window', 'affected_features'],
            EmailTemplate.MONTHLY_REPORT: ['user', 'report_data', 'report_month'],
            EmailTemplate.WEEKLY_SUMMARY: ['user', 'summary_data', 'week_range'],
        }
        return context_mapping.get(self, [])

    def get_email_type(self) -> EmailType:
        """Get email type for this template"""
        type_mapping = {
            EmailTemplate.WELCOME_USER: EmailType.WELCOME,
            EmailTemplate.WELCOME_ADMIN: EmailType.WELCOME,
            EmailTemplate.PASSWORD_RESET: EmailType.PASSWORD_RESET,
            EmailTemplate.DEAL_CREATED: EmailType.DEAL_NOTIFICATION,
            EmailTemplate.DEAL_UPDATED: EmailType.DEAL_NOTIFICATION,
            EmailTemplate.DEAL_WON: EmailType.DEAL_NOTIFICATION,
            EmailTemplate.DEAL_LOST: EmailType.DEAL_NOTIFICATION,
            EmailTemplate.ACTIVITY_REMINDER: EmailType.ACTIVITY_REMINDER,
            EmailTemplate.ACTIVITY_OVERDUE: EmailType.ACTIVITY_REMINDER,
            EmailTemplate.BULK_ANNOUNCEMENT: EmailType.BULK,
            EmailTemplate.SYSTEM_MAINTENANCE: EmailType.CUSTOM,
            EmailTemplate.MONTHLY_REPORT: EmailType.CUSTOM,
            EmailTemplate.WEEKLY_SUMMARY: EmailType.CUSTOM,
        }
        return type_mapping[self]


class EmailConfiguration:
    """
    Configuration class for email settings.

    This follows the Single Responsibility Principle by centralizing
    email configuration management.
    """

    # SMTP Configuration
    SMTP_HOST = 'smtp.gmail.com'
    SMTP_PORT = 587
    SMTP_USE_TLS = True
    SMTP_USE_SSL = False
    SMTP_TIMEOUT = 30

    # Email Limits
    MAX_EMAIL_SIZE_MB = 25
    MAX_ATTACHMENT_SIZE_MB = 20
    MAX_RECIPIENTS_PER_EMAIL = 100
    MAX_ATTACHMENTS_PER_EMAIL = 10

    # Rate Limiting
    DEFAULT_RATE_LIMIT = '30/m'  # 30 emails per minute
    BULK_RATE_LIMIT = '5/m'      # 5 emails per minute for bulk
    PRIORITY_RATE_LIMITS = {
        EmailPriority.LOW: '10/m',
        EmailPriority.NORMAL: '30/m',
        EmailPriority.HIGH: '60/m',
        EmailPriority.CRITICAL: '100/m',
    }

    # Retry Configuration
    MAX_RETRIES = 3
    RETRY_DELAYS = [60, 300, 900]  # 1min, 5min, 15min

    # Tracking
    ENABLE_OPEN_TRACKING = True
    ENABLE_CLICK_TRACKING = True
    TRACKING_PIXEL_URL = '/email/track/open/'
    TRACKING_LINK_PREFIX = '/email/track/click/'

    # Unsubscribe
    ENABLE_UNSUBSCRIBE = True
    UNSUBSCRIBE_URL = '/email/unsubscribe/'
    UNSUBSCRIBE_HEADER = True

    # Security
    ENABLE_DKIM = True
    ENABLE_SPF = True
    ENABLE_DMARC = True

    @classmethod
    def get_rate_limit(cls, priority: EmailPriority) -> str:
        """Get rate limit for specific priority"""
        return cls.PRIORITY_RATE_LIMITS.get(priority, cls.DEFAULT_RATE_LIMIT)

    @classmethod
    def validate_email_size(cls, content: str, attachments: list = None) -> bool:
        """Validate email size against limits"""
        import sys

        # Calculate email size in bytes
        email_size = sys.getsizeof(content.encode('utf-8'))

        if attachments:
            for attachment in attachments:
                if isinstance(attachment, tuple) and len(attachment) >= 2:
                    email_size += sys.getsizeof(attachment[1])

        size_mb = email_size / (1024 * 1024)
        return size_mb <= cls.MAX_EMAIL_SIZE_MB

    @classmethod
    def get_retry_delay(cls, retry_count: int) -> int:
        """Get retry delay for specific retry attempt"""
        if retry_count < len(cls.RETRY_DELAYS):
            return cls.RETRY_DELAYS[retry_count]
        return cls.RETRY_DELAYS[-1]  # Return last delay if retry_count exceeds list