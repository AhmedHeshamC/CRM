"""
Email Notification Tasks for CRM Backend
Following SOLID principles and comprehensive email management
"""

import logging
import re
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union
from urllib.parse import urljoin, urlencode

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.mail import EmailMessage, EmailMultiAlternatives, send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from celery import shared_task

from .base_tasks import BaseTask, TaskStatus
from .email_types import (
    EmailType,
    EmailPriority,
    EmailStatus,
    EmailTemplate,
    EmailConfiguration,
)
from .exceptions import (
    TaskValidationError,
    TaskExecutionError,
    TaskConfigurationError,
    TaskRetryError,
    TaskExceptionFactory,
)

# Configure logger
logger = logging.getLogger(__name__)

User = get_user_model()


class EmailNotificationTask(BaseTask):
    """
    Base class for email notification tasks.

    This follows SOLID principles:
    - Single Responsibility: Handles email-specific functionality
    - Open/Closed: Extensible for different email types
    - Liskov Substitution: Compatible with BaseTask interface
    - Interface Segregation: Minimal, focused interface
    - Dependency Inversion: Depends on abstractions (EmailType, etc.)
    """

    # Task configuration
    name = 'email_notification'
    queue = 'email'
    soft_time_limit = 120  # 2 minutes
    time_limit = 300       # 5 minutes
    max_retries = 3
    default_retry_delay = 60  # 1 minute

    def __init__(self):
        super().__init__()
        self.email_config = EmailConfiguration()

    def execute(self, *args, **kwargs) -> Dict[str, Any]:
        """
        Main email execution method.

        This follows the Template Method pattern by defining the
        overall email sending process while allowing customization.
        """
        email_type = kwargs.get('email_type', EmailType.CUSTOM)
        recipient = kwargs.get('recipient')
        subject = kwargs.get('subject')
        message = kwargs.get('message')
        context = kwargs.get('context', {})
        priority = kwargs.get('priority', EmailType(email_type).get_priority())
        template = kwargs.get('template')
        attachments = kwargs.get('attachments', [])

        # Validate inputs
        self._validate_email_input(recipient, subject, message)

        # Validate configuration
        self._validate_email_configuration()

        # Check rate limiting
        self._check_rate_limit(recipient, priority)

        # Setup tracking
        tracking_data = self._setup_email_tracking(recipient, subject)

        # Prepare email content
        email_content = self._prepare_email_content(
            email_type, template, message, context, tracking_data
        )

        # Send email
        result = self._send_email_with_tracking(
            recipient=recipient,
            subject=subject,
            content=email_content,
            priority=priority,
            attachments=attachments,
            tracking_data=tracking_data
        )

        return result

    def _validate_email_input(self, recipient: str, subject: str, message: str) -> None:
        """
        Validate email input parameters.

        This follows the Single Responsibility Principle by focusing
        specifically on input validation for email tasks.
        """
        if not recipient:
            raise TaskValidationError(
                "Email recipient is required",
                field_name="recipient",
                field_value=recipient
            )

        # Email format validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, recipient):
            raise TaskValidationError(
                f"Invalid email format: {recipient}",
                field_name="recipient",
                field_value=recipient
            )

        if not subject or not subject.strip():
            raise TaskValidationError(
                "Email subject is required",
                field_name="subject",
                field_value=subject
            )

        if not message or not message.strip():
            raise TaskValidationError(
                "Email message is required",
                field_name="message",
                field_value=message
            )

        # Check email size
        if not self.email_config.validate_email_size(message):
            raise TaskValidationError(
                "Email content exceeds maximum size limit",
                field_name="message"
            )

    def _validate_email_configuration(self) -> None:
        """
        Validate email configuration.

        This follows the Single Responsibility Principle by handling
        configuration validation separately from execution logic.
        """
        required_settings = [
            'EMAIL_BACKEND',
            'DEFAULT_FROM_EMAIL'
        ]

        missing_configs = []
        for setting in required_settings:
            if not hasattr(settings, setting) or not getattr(settings, setting):
                missing_configs.append(setting)

        if missing_configs:
            raise TaskExceptionFactory.create_config_error(
                missing_configs,
                "email sending"
            )

    def _check_rate_limit(self, recipient: str, priority: EmailPriority) -> None:
        """
        Check email rate limiting.

        This prevents overwhelming email servers and respects
        service provider limitations.
        """
        rate_limit = self.email_config.get_rate_limit(priority)
        cache_key = f'email_rate_limit_{recipient}_{priority.value}'

        # Simple rate limiting implementation
        current_count = cache.get(cache_key, 0)
        if current_count >= int(rate_limit.split('/')[0]):
            raise TaskExecutionError(
                f"Rate limit exceeded for {recipient}",
                error_code="RATE_LIMIT_EXCEEDED",
                details={
                    "recipient": recipient,
                    "priority": priority.value,
                    "rate_limit": rate_limit,
                    "current_count": current_count
                }
            )

        # Increment counter
        cache.set(cache_key, current_count + 1, timeout=60)

    def _setup_email_tracking(self, recipient: str, subject: str) -> Dict[str, Any]:
        """
        Setup email tracking for open and click tracking.

        This provides analytics for email engagement and delivery.
        """
        if not settings.EMAIL_TRACKING_ENABLED:
            return {}

        tracking_id = str(uuid.uuid4())
        tracking_data = {
            'tracking_id': tracking_id,
            'task_id': self.task_id,
            'recipient': recipient,
            'subject': subject,
            'sent_at': timezone.now().isoformat(),
            'tracking_pixel_url': urljoin(
                settings.SITE_URL,
                f"{EmailConfiguration.TRACKING_PIXEL_URL}?{urlencode({'id': tracking_id})}"
            )
        }

        # Store tracking data in cache
        cache.set(f'email_tracking_{tracking_id}', tracking_data, timeout=86400 * 30)  # 30 days

        return tracking_data

    def _prepare_email_content(
        self,
        email_type: EmailType,
        template: Optional[str],
        message: str,
        context: Dict[str, Any],
        tracking_data: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        Prepare email content with templates and tracking.

        This follows the Template Method pattern by providing a consistent
        way to prepare email content across different email types.
        """
        # Add tracking data to context
        if tracking_data:
            context.update({
                'tracking_pixel': tracking_data.get('tracking_pixel_url', ''),
                'tracking_id': tracking_data.get('tracking_id', ''),
            })

        # Add default context variables
        context.update({
            'company_name': getattr(settings, 'COMPANY_NAME', 'CRM'),
            'support_email': getattr(settings, 'SUPPORT_EMAIL', settings.DEFAULT_FROM_EMAIL),
            'site_url': settings.SITE_URL,
            'current_year': datetime.now().year,
        })

        # Render content if template is provided
        if template:
            html_content = self._render_template_with_fallback(
                template.replace('.txt', '.html'),
                template,
                context
            )
            text_content = render_to_string(template, context)
        else:
            html_content = self._render_html_message(message, context)
            text_content = message

        return {
            'html': html_content,
            'text': text_content,
        }

    def _render_template_with_fallback(
        self,
        html_template: str,
        text_template: str,
        context: Dict[str, Any]
    ) -> str:
        """
        Render template with HTML fallback to text.

        This provides graceful degradation when HTML templates
        are not available.
        """
        try:
            # Try to render HTML template first
            return render_to_string(html_template, context)
        except:
            # Fallback to text template
            try:
                return render_to_string(text_template, context)
            except:
                # Final fallback to plain text
                return str(context.get('message', ''))

    def _render_html_message(self, message: str, context: Dict[str, Any]) -> str:
        """
        Convert plain text message to HTML.

        This provides basic HTML formatting for text emails.
        """
        # Personalize message
        personalized_message = self._personalize_message(message, context)

        # Basic HTML formatting
        html_message = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{context.get('subject', 'Notification')}</title>
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="background-color: #f8f9fa; padding: 20px; border-radius: 5px;">
                    {personalized_message.replace('\n', '<br>')}
                </div>
                <hr style="margin: 20px 0;">
                <footer style="font-size: 12px; color: #666;">
                    <p>This email was sent by {context.get('company_name', 'CRM')}.</p>
                    <p>If you have any questions, contact us at {context.get('support_email', '')}.</p>
                </footer>
            </div>
            {context.get('tracking_pixel', '')}
        </body>
        </html>
        """
        return html_message

    def _personalize_message(self, message: str, context: Dict[str, Any]) -> str:
        """
        Personalize message using context variables.

        This allows for dynamic content insertion based on context.
        """
        try:
            return message.format(**context)
        except KeyError as e:
            # Handle missing template variables gracefully
            logger.warning(f"Missing template variable in email: {e}")
            return message

    def _send_email_with_tracking(
        self,
        recipient: str,
        subject: str,
        content: Dict[str, str],
        priority: EmailPriority,
        attachments: Optional[List] = None,
        tracking_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Send email with tracking and comprehensive error handling.

        This is the core email sending method with all the necessary
        error handling, logging, and tracking functionality.
        """
        start_time = timezone.now()
        sent_at = None
        error_details = {}

        try:
            # Update progress
            self.set_task_status(TaskStatus.RUNNING, progress=25)

            # Prepare email message
            email = EmailMultiAlternatives(
                subject=subject,
                body=content['text'],
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[recipient],
                reply_to=[getattr(settings, 'REPLY_TO_EMAIL', settings.DEFAULT_FROM_EMAIL)]
            )

            # Attach HTML content
            if content['html']:
                email.attach_alternative(content['html'], 'text/html')

            # Add tracking headers
            if tracking_data and getattr(settings, 'EMAIL_TRACKING_ENABLED', False):
                email.extra_headers['X-Email-Tracking-ID'] = tracking_data.get('tracking_id')
                email.extra_headers['X-Email-Task-ID'] = self.task_id

            # Add unsubscribe header if enabled
            if getattr(settings, 'EMAIL_UNSUBSCRIBE_ENABLED', False):
                unsubscribe_url = urljoin(
                    settings.SITE_URL,
                    f"{EmailConfiguration.UNSUBSCRIBE_URL}?{urlencode({'email': recipient})}"
                )
                email.extra_headers['List-Unsubscribe'] = f'<{unsubscribe_url}>'

            # Add attachments
            if attachments:
                for attachment in attachments:
                    if isinstance(attachment, tuple) and len(attachment) >= 2:
                        filename, file_content, content_type = (
                            attachment[0],
                            attachment[1],
                            attachment[2] if len(attachment) > 2 else 'application/octet-stream'
                        )
                        email.attach(filename, file_content, content_type)

            # Update progress
            self.set_task_status(TaskStatus.RUNNING, progress=75)

            # Send email
            email.send(fail_silently=False)
            sent_at = timezone.now()

            # Log successful send
            logger.info(
                f"Email sent successfully to {recipient}",
                extra={
                    'task_id': self.task_id,
                    'recipient': recipient,
                    'subject': subject,
                    'sent_at': sent_at.isoformat(),
                    'duration': (sent_at - start_time).total_seconds()
                }
            )

            return {
                'success': True,
                'recipient': recipient,
                'subject': subject,
                'sent_at': sent_at.isoformat(),
                'duration_seconds': (sent_at - start_time).total_seconds(),
                'tracking_id': tracking_data.get('tracking_id') if tracking_data else None,
                'message_id': getattr(email, 'message_id', None)
            }

        except Exception as e:
            error_details = {
                'error_type': e.__class__.__name__,
                'error_message': str(e),
                'recipient': recipient,
                'subject': subject,
                'attempted_at': start_time.isoformat()
            }

            logger.error(
                f"Failed to send email to {recipient}: {str(e)}",
                extra={
                    'task_id': self.task_id,
                    'error_details': error_details
                }
            )

            # Determine if we should retry
            if self._should_retry_email(e):
                raise TaskRetryError(
                    retry_count=getattr(self.request, 'retries', 0),
                    max_retries=self.max_retries,
                    backoff_delay=self.email_config.get_retry_delay(getattr(self.request, 'retries', 0)),
                    details=error_details
                )
            else:
                raise TaskExecutionError(
                    f"Failed to send email: {str(e)}",
                    details=error_details
                )

    def _should_retry_email(self, error: Exception) -> bool:
        """
        Determine if email sending should be retried based on error type.

        This implements intelligent retry logic based on the type of error.
        """
        retryable_errors = [
            'ConnectionRefusedError',
            'TimeoutError',
            'SMTPException',
            'SMTPRecipientsRefused',
            'SMTPSenderRefused',
            'SMTPDataError',
            'SMTPConnectError',
            'SMTPAuthenticationError',
        ]

        return any(error_type in str(type(error)) for error_type in retryable_errors)

    def _send_email(self, recipient: str, subject: str, message: str, **kwargs) -> Dict[str, Any]:
        """
        Simple email sending method for basic notifications.

        This provides a simplified interface for basic email sending
        without templates or advanced features.
        """
        return self.execute(
            email_type=EmailType.CUSTOM,
            recipient=recipient,
            subject=subject,
            message=message,
            **kwargs
        )


@shared_task(bind=True, base=EmailNotificationTask, name='send_welcome_email')
class WelcomeEmailTask(EmailNotificationTask):
    """
    Task for sending welcome emails to new users.

    This follows the Single Responsibility Principle by focusing
    specifically on welcome email functionality.
    """

    def execute(self, user_id: int, **kwargs) -> Dict[str, Any]:
        """
        Send welcome email to newly registered user.

        Args:
            user_id: ID of the user to send welcome email to

        Returns:
            Dict[str, Any]: Email sending result
        """
        try:
            # Get user
            user = User.objects.get(id=user_id)

            # Prepare context
            context = {
                'user': user,
                'first_name': user.first_name or user.username,
                'login_url': urljoin(settings.SITE_URL, reverse('login')),
                'subject': EmailType.WELCOME.get_default_subject()
            }

            # Send welcome email
            result = self._send_email_with_tracking(
                recipient=user.email,
                subject=EmailType.WELCOME.get_default_subject(),
                content=self._prepare_email_content(
                    EmailType.WELCOME,
                    EmailTemplate.WELCOME_USER.value,
                    '',
                    context,
                    {}
                ),
                priority=EmailType.WELCOME.get_priority()
            )

            result.update({
                'email_type': EmailType.WELCOME.value,
                'user_id': user_id
            })

            return result

        except User.DoesNotExist:
            raise TaskValidationError(
                f"User with ID {user_id} does not exist",
                field_name="user_id",
                field_value=user_id
            )

    def send_welcome_email(self, user_id: int) -> Dict[str, Any]:
        """Public method for sending welcome email"""
        return self.execute(user_id=user_id)


@shared_task(bind=True, base=EmailNotificationTask, name='send_password_reset_email')
class PasswordResetEmailTask(EmailNotificationTask):
    """
    Task for sending password reset emails.

    This follows the Single Responsibility Principle by focusing
    specifically on password reset email functionality.
    """

    def execute(self, user_id: int, reset_token: str, **kwargs) -> Dict[str, Any]:
        """
        Send password reset email to user.

        Args:
            user_id: ID of the user requesting password reset
            reset_token: Password reset token

        Returns:
            Dict[str, Any]: Email sending result
        """
        try:
            # Get user
            user = User.objects.get(id=user_id)

            # Generate reset URL
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            reset_url = urljoin(
                settings.SITE_URL,
                reverse('password_reset_confirm', kwargs={'uidb64': uid, 'token': reset_token})
            )

            # Prepare context
            context = {
                'user': user,
                'first_name': user.first_name or user.username,
                'reset_url': reset_url,
                'reset_token': reset_token,
                'expiry_hours': getattr(settings, 'PASSWORD_RESET_TIMEOUT_HOURS', 24),
                'subject': EmailType.PASSWORD_RESET.get_default_subject()
            }

            # Send password reset email
            result = self._send_email_with_tracking(
                recipient=user.email,
                subject=EmailType.PASSWORD_RESET.get_default_subject(),
                content=self._prepare_email_content(
                    EmailType.PASSWORD_RESET,
                    EmailTemplate.PASSWORD_RESET.value,
                    '',
                    context,
                    {}
                ),
                priority=EmailType.PASSWORD_RESET.get_priority()
            )

            result.update({
                'email_type': EmailType.PASSWORD_RESET.value,
                'user_id': user_id
            })

            return result

        except User.DoesNotExist:
            raise TaskValidationError(
                f"User with ID {user_id} does not exist",
                field_name="user_id",
                field_value=user_id
            )

    def send_password_reset_email(self, user_id: int, reset_token: str) -> Dict[str, Any]:
        """Public method for sending password reset email"""
        return self.execute(user_id=user_id, reset_token=reset_token)


@shared_task(bind=True, base=EmailNotificationTask, name='send_deal_notification_email')
class DealNotificationEmailTask(EmailNotificationTask):
    """
    Task for sending deal notification emails.

    This follows the Single Responsibility Principle by focusing
    specifically on deal notification email functionality.
    """

    def execute(self, deal_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        Send deal notification email to assigned user.

        Args:
            deal_data: Dictionary containing deal information

        Returns:
            Dict[str, Any]: Email sending result
        """
        try:
            # Validate deal data
            required_fields = ['deal_id', 'deal_title', 'assigned_to_email']
            for field in required_fields:
                if field not in deal_data:
                    raise TaskValidationError(
                        f"Missing required field: {field}",
                        field_name=field,
                        field_value=deal_data.get(field)
                    )

            # Prepare context
            context = {
                'deal': deal_data,
                'deal_title': deal_data['deal_title'],
                'deal_id': deal_data['deal_id'],
                'deal_stage': deal_data.get('deal_stage', 'New'),
                'deal_value': deal_data.get('deal_value', 0),
                'assigned_to': deal_data.get('assigned_to_name', 'Team Member'),
                'created_by': deal_data.get('created_by_name', 'System'),
                'deal_url': urljoin(
                    settings.SITE_URL,
                    reverse('deal-detail', kwargs={'pk': deal_data['deal_id']})
                ),
                'subject': f"Deal Notification: {deal_data['deal_title']}"
            }

            # Send deal notification email
            result = self._send_email_with_tracking(
                recipient=deal_data['assigned_to_email'],
                subject=context['subject'],
                content=self._prepare_email_content(
                    EmailType.DEAL_NOTIFICATION,
                    EmailTemplate.DEAL_CREATED.value,
                    '',
                    context,
                    {}
                ),
                priority=EmailType.DEAL_NOTIFICATION.get_priority()
            )

            result.update({
                'email_type': EmailType.DEAL_NOTIFICATION.value,
                'deal_id': deal_data['deal_id']
            })

            return result

        except Exception as e:
            raise TaskValidationError(
                f"Invalid deal data: {str(e)}",
                field_name="deal_data",
                field_value=deal_data
            )

    def send_deal_notification_email(self, deal_data: Dict[str, Any]) -> Dict[str, Any]:
        """Public method for sending deal notification email"""
        return self.execute(deal_data=deal_data)


@shared_task(bind=True, base=EmailNotificationTask, name='send_activity_reminder_email')
class ActivityReminderEmailTask(EmailNotificationTask):
    """
    Task for sending activity reminder emails.

    This follows the Single Responsibility Principle by focusing
    specifically on activity reminder email functionality.
    """

    def execute(self, activity_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        Send activity reminder email to assigned user.

        Args:
            activity_data: Dictionary containing activity information

        Returns:
            Dict[str, Any]: Email sending result
        """
        try:
            # Validate activity data
            required_fields = ['activity_id', 'activity_title', 'assigned_to_email']
            for field in required_fields:
                if field not in activity_data:
                    raise TaskValidationError(
                        f"Missing required field: {field}",
                        field_name=field,
                        field_value=activity_data.get(field)
                    )

            # Prepare context
            context = {
                'activity': activity_data,
                'activity_title': activity_data['activity_title'],
                'activity_id': activity_data['activity_id'],
                'activity_due_date': activity_data.get('activity_due_date'),
                'activity_type': activity_data.get('activity_type', 'Task'),
                'assigned_to': activity_data.get('assigned_to_name', 'Team Member'),
                'contact_name': activity_data.get('contact_name', 'Contact'),
                'activity_url': urljoin(
                    settings.SITE_URL,
                    reverse('activity-detail', kwargs={'pk': activity_data['activity_id']})
                ),
                'subject': f"Activity Reminder: {activity_data['activity_title']}"
            }

            # Send activity reminder email
            result = self._send_email_with_tracking(
                recipient=activity_data['assigned_to_email'],
                subject=context['subject'],
                content=self._prepare_email_content(
                    EmailType.ACTIVITY_REMINDER,
                    EmailTemplate.ACTIVITY_REMINDER.value,
                    '',
                    context,
                    {}
                ),
                priority=EmailType.ACTIVITY_REMINDER.get_priority()
            )

            result.update({
                'email_type': EmailType.ACTIVITY_REMINDER.value,
                'activity_id': activity_data['activity_id']
            })

            return result

        except Exception as e:
            raise TaskValidationError(
                f"Invalid activity data: {str(e)}",
                field_name="activity_data",
                field_value=activity_data
            )

    def send_activity_reminder_email(self, activity_data: Dict[str, Any]) -> Dict[str, Any]:
        """Public method for sending activity reminder email"""
        return self.execute(activity_data=activity_data)


@shared_task(bind=True, base=EmailNotificationTask, name='send_bulk_email')
class BulkEmailTask(EmailNotificationTask):
    """
    Task for sending bulk emails to multiple recipients.

    This follows the Single Responsibility Principle by focusing
    specifically on bulk email functionality with progress tracking.
    """

    def execute(self, recipients: List[str], subject: str, message: str, context: Dict[str, Any] = None, **kwargs) -> Dict[str, Any]:
        """
        Send bulk email to multiple recipients.

        Args:
            recipients: List of email addresses to send to
            subject: Email subject
            message: Email message content
            context: Template context variables

        Returns:
            Dict[str, Any]: Bulk email sending result with statistics
        """
        context = context or {}
        total_recipients = len(recipients)
        sent_count = 0
        failed_count = 0
        results = []

        # Validate recipients limit
        if total_recipients > EmailConfiguration.MAX_RECIPIENTS_PER_EMAIL:
            raise TaskValidationError(
                f"Too many recipients: {total_recipients} (max: {EmailConfiguration.MAX_RECIPIENTS_PER_EMAIL})",
                field_name="recipients",
                field_value=total_recipients
            )

        for i, recipient in enumerate(recipients):
            try:
                # Update progress
                progress = int((i / total_recipients) * 100)
                self.set_task_status(TaskStatus.RUNNING, progress=progress)

                # Send individual email
                result = self._send_email_with_tracking(
                    recipient=recipient,
                    subject=subject,
                    content=self._prepare_email_content(
                        EmailType.BULK,
                        None,  # No template for bulk
                        message,
                        {**context, 'recipient_email': recipient},
                        {}
                    ),
                    priority=EmailPriority.LOW
                )

                sent_count += 1
                results.append({
                    'recipient': recipient,
                    'success': True,
                    'result': result
                })

                # Small delay to prevent overwhelming email server
                import time
                time.sleep(0.1)

            except Exception as e:
                failed_count += 1
                results.append({
                    'recipient': recipient,
                    'success': False,
                    'error': str(e)
                })

                logger.error(f"Failed to send bulk email to {recipient}: {str(e)}")

        # Final result
        return {
            'success': sent_count > 0,
            'total_recipients': total_recipients,
            'sent_count': sent_count,
            'failed_count': failed_count,
            'success_rate': (sent_count / total_recipients) * 100 if total_recipients > 0 else 0,
            'results': results,
            'email_type': EmailType.BULK.value
        }

    def send_bulk_email(
        self,
        recipients: List[str],
        subject: str,
        message: str,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Public method for sending bulk email"""
        return self.execute(
            recipients=recipients,
            subject=subject,
            message=message,
            context=context or {}
        )