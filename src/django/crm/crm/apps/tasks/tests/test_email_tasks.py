"""
Test suite for Email Notification Tasks
Following TDD principles and comprehensive email testing
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from django.test import TestCase, override_settings
from django.core import mail
from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.utils import timezone
from celery.exceptions import Retry

from ..email_tasks import (
    EmailNotificationTask,
    WelcomeEmailTask,
    PasswordResetEmailTask,
    DealNotificationEmailTask,
    ActivityReminderEmailTask,
    BulkEmailTask,
    EmailType,
    EmailPriority,
)
from ..exceptions import (
    TaskValidationError,
    TaskExecutionError,
    TaskConfigurationError,
    TaskRetryError,
)

User = get_user_model()


class TestEmailType:
    """Test the EmailType enum for email categorization"""

    def test_email_type_values(self):
        """Test that EmailType has all required values"""
        assert EmailType.WELCOME.value == 'WELCOME'
        assert EmailType.PASSWORD_RESET.value == 'PASSWORD_RESET'
        assert EmailType.DEAL_NOTIFICATION.value == 'DEAL_NOTIFICATION'
        assert EmailType.ACTIVITY_REMINDER.value == 'ACTIVITY_REMINDER'
        assert EmailType.BULK.value == 'BULK'
        assert EmailType.CUSTOM.value == 'CUSTOM'

    def test_email_type_templates(self):
        """Test that each email type has correct template path"""
        assert EmailType.WELCOME.get_template_path('html') == 'emails/welcome.html'
        assert EmailType.WELCOME.get_template_path('text') == 'emails/welcome.txt'
        assert EmailType.PASSWORD_RESET.get_template_path('html') == 'emails/password_reset.html'
        assert EmailType.DEAL_NOTIFICATION.get_template_path('html') == 'emails/deal_notification.html'


class TestEmailPriority:
    """Test the EmailPriority enum for queue management"""

    def test_email_priority_values(self):
        """Test that EmailPriority has correct numeric values"""
        assert EmailPriority.LOW.value == 1
        assert EmailPriority.NORMAL.value == 5
        assert EmailPriority.HIGH.value == 8
        assert EmailPriority.CRITICAL.value == 10

    def test_email_priority_queue_mapping(self):
        """Test that priorities map to correct queues"""
        assert EmailPriority.LOW.get_queue() == 'email_low'
        assert EmailPriority.NORMAL.get_queue() == 'email_normal'
        assert EmailPriority.HIGH.get_queue() == 'email_high'
        assert EmailPriority.CRITICAL.get_queue() == 'email_critical'


class TestEmailNotificationTask(TestCase):
    """Test the base EmailNotificationTask class"""

    def setUp(self):
        """Set up test environment"""
        self.mock_task = Mock()
        self.mock_task.request.id = 'test-email-task-id'
        self.mock_task.request.retries = 0
        self.mock_task.request.hostname = 'test-email-worker'

        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        DEFAULT_FROM_EMAIL='test@crm.com'
    )
    def test_send_welcome_email_success(self):
        """Test successful welcome email sending"""
        task = WelcomeEmailTask()
        task.request = self.mock_task.request

        with patch.object(task, 'set_task_status') as mock_set_status:
            result = task.send_welcome_email(self.user.id)

            self.assertTrue(result['success'])
            self.assertEqual(result['email_type'], EmailType.WELCOME.value)
            self.assertEqual(result['recipient'], self.user.email)

            # Check email was sent
            self.assertEqual(len(mail.outbox), 1)
            sent_email = mail.outbox[0]
            self.assertEqual(sent_email.to, [self.user.email])
            self.assertIn('Welcome', sent_email.subject)

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        DEFAULT_FROM_EMAIL='test@crm.com'
    )
    def test_send_password_reset_email_success(self):
        """Test successful password reset email sending"""
        task = PasswordResetEmailTask()
        task.request = self.mock_task.request

        reset_token = 'test-reset-token-123'
        with patch.object(task, 'set_task_status') as mock_set_status:
            result = task.send_password_reset_email(self.user.id, reset_token)

            self.assertTrue(result['success'])
            self.assertEqual(result['email_type'], EmailType.PASSWORD_RESET.value)
            self.assertEqual(result['recipient'], self.user.email)

            # Check email was sent
            self.assertEqual(len(mail.outbox), 1)
            sent_email = mail.outbox[0]
            self.assertEqual(sent_email.to, [self.user.email])
            self.assertIn('Password Reset', sent_email.subject)

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        DEFAULT_FROM_EMAIL='test@crm.com'
    )
    def test_send_deal_notification_email_success(self):
        """Test successful deal notification email sending"""
        task = DealNotificationEmailTask()
        task.request = self.mock_task.request

        deal_data = {
            'deal_id': 123,
            'deal_title': 'Test Deal',
            'deal_stage': 'Proposal',
            'deal_value': 50000,
            'assigned_to_email': 'manager@example.com'
        }

        with patch.object(task, 'set_task_status') as mock_set_status:
            result = task.send_deal_notification_email(deal_data)

            self.assertTrue(result['success'])
            self.assertEqual(result['email_type'], EmailType.DEAL_NOTIFICATION.value)
            self.assertEqual(result['recipient'], deal_data['assigned_to_email'])

            # Check email was sent
            self.assertEqual(len(mail.outbox), 1)
            sent_email = mail.outbox[0]
            self.assertEqual(sent_email.to, [deal_data['assigned_to_email']])
            self.assertIn('Deal Notification', sent_email.subject)

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        DEFAULT_FROM_EMAIL='test@crm.com'
    )
    def test_send_activity_reminder_email_success(self):
        """Test successful activity reminder email sending"""
        task = ActivityReminderEmailTask()
        task.request = self.mock_task.request

        activity_data = {
            'activity_id': 456,
            'activity_title': 'Follow-up call',
            'activity_due_date': timezone.now() + timedelta(hours=2),
            'assigned_to_email': 'sales@example.com',
            'contact_name': 'John Doe'
        }

        with patch.object(task, 'set_task_status') as mock_set_status:
            result = task.send_activity_reminder_email(activity_data)

            self.assertTrue(result['success'])
            self.assertEqual(result['email_type'], EmailType.ACTIVITY_REMINDER.value)
            self.assertEqual(result['recipient'], activity_data['assigned_to_email'])

            # Check email was sent
            self.assertEqual(len(mail.outbox), 1)
            sent_email = mail.outbox[0]
            self.assertEqual(sent_email.to, [activity_data['assigned_to_email']])
            self.assertIn('Activity Reminder', sent_email.subject)

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        DEFAULT_FROM_EMAIL='test@crm.com'
    )
    def test_send_bulk_email_success(self):
        """Test successful bulk email sending"""
        task = BulkEmailTask()
        task.request = self.mock_task.request

        recipients = ['user1@example.com', 'user2@example.com', 'user3@example.com']
        subject = 'Bulk Test Email'
        message = 'This is a test bulk email message'
        template_context = {'company_name': 'Test Company'}

        with patch.object(task, 'set_task_status') as mock_set_status:
            result = task.send_bulk_email(recipients, subject, message, template_context)

            self.assertTrue(result['success'])
            self.assertEqual(result['email_type'], EmailType.BULK.value)
            self.assertEqual(result['sent_count'], len(recipients))
            self.assertEqual(result['failed_count'], 0)

            # Check all emails were sent
            self.assertEqual(len(mail.outbox), len(recipients))
            for i, email in enumerate(mail.outbox):
                self.assertEqual(email.to, [recipients[i]])

    def test_send_welcome_email_user_not_found(self):
        """Test welcome email with non-existent user"""
        task = WelcomeEmailTask()
        task.request = self.mock_task.request

        with self.assertRaises(TaskValidationError):
            task.send_welcome_email(99999)

    def test_send_email_with_invalid_recipient(self):
        """Test email sending with invalid recipient"""
        task = EmailNotificationTask()
        task.request = self.mock_task.request

        with self.assertRaises(TaskValidationError):
            task._send_email(
                recipient='invalid-email',
                subject='Test',
                message='Test message'
            )

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend')
    def test_send_email_smtp_error_retry(self):
        """Test email sending with SMTP error triggers retry"""
        task = EmailNotificationTask()
        task.request = self.mock_task.request

        with patch('django.core.mail.send_mail') as mock_send_mail:
            mock_send_mail.side_effect = Exception('SMTP connection failed')

            with self.assertRaises(Retry):
                task._send_email(
                    recipient='test@example.com',
                    subject='Test',
                    message='Test message'
                )

    def test_email_template_rendering(self):
        """Test email template rendering with context"""
        task = EmailNotificationTask()

        context = {
            'user': self.user,
            'company_name': 'Test Company',
            'support_email': 'support@test.com'
        }

        with patch('django.template.loader.render_to_string') as mock_render:
            mock_render.return_value = 'Rendered template content'

            result = task._render_template('emails/test.html', context)

            mock_render.assert_called_once_with('emails/test.html', context)
            self.assertEqual(result, 'Rendered template content')

    def test_email_tracking_setup(self):
        """Test email tracking pixel and link generation"""
        task = EmailNotificationTask()
        task.task_id = 'test-task-123'

        tracking_data = task._setup_email_tracking(
            recipient='test@example.com',
            subject='Test Subject'
        )

        self.assertIn('tracking_pixel_url', tracking_data)
        self.assertIn('tracked_links', tracking_data)
        self.assertEqual(tracking_data['task_id'], task.task_id)

    def test_validate_email_inputs(self):
        """Test email input validation"""
        task = EmailNotificationTask()

        # Test valid email
        task._validate_email_input('test@example.com', 'Subject', 'Message')

        # Test invalid email
        with self.assertRaises(TaskValidationError):
            task._validate_email_input('invalid-email', 'Subject', 'Message')

        # Test empty subject
        with self.assertRaises(TaskValidationError):
            task._validate_email_input('test@example.com', '', 'Message')

        # Test empty message
        with self.assertRaises(TaskValidationError):
            task._validate_email_input('test@example.com', 'Subject', '')

    def test_email_configuration_validation(self):
        """Test email configuration validation"""
        task = EmailNotificationTask()

        # Test with valid configuration
        with override_settings(
            EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
            DEFAULT_FROM_EMAIL='test@crm.com'
        ):
            task._validate_email_configuration()

        # Test with missing configuration
        with override_settings(DEFAULT_FROM_EMAIL=''):
            with self.assertRaises(TaskConfigurationError):
                task._validate_email_configuration()

    def test_progress_tracking_during_bulk_send(self):
        """Test progress tracking during bulk email operations"""
        task = BulkEmailTask()
        task.task_id = 'bulk-task-123'

        recipients = [f'user{i}@example.com' for i in range(10)]

        with patch.object(task, 'set_task_status') as mock_set_status:
            with patch.object(task, '_send_email') as mock_send:
                mock_send.return_value = {'success': True}

                # Mock sending to a subset of recipients
                def mock_send_side_effect(recipient, *args, **kwargs):
                    # Simulate progress updates
                    progress = (recipients.index(recipient) + 1) / len(recipients) * 100
                    task.set_task_status(TaskStatus.RUNNING, progress=int(progress))
                    return {'success': True}

                mock_send.side_effect = mock_send_side_effect

                task.send_bulk_email(recipients, 'Test', 'Message', {})

                # Check that progress was updated
                progress_calls = [call for call in mock_set_status.call_args_list
                                if 'progress' in call[1]]
                self.assertTrue(len(progress_calls) > 0)

    def test_email_rate_limiting(self):
        """Test email rate limiting functionality"""
        task = EmailNotificationTask()

        with patch('django.core.cache.cache') as mock_cache:
            # Mock rate limit exceeded
            mock_cache.get.return_value = 100  # Exceeds rate limit

            with self.assertRaises(TaskExecutionError):
                task._check_rate_limit('test@example.com')

    def test_email_personalization(self):
        """Test email content personalization"""
        task = EmailNotificationTask()

        base_message = "Hello {name}, your account is ready!"
        context = {'name': 'John Doe', 'company': 'ACME Corp'}

        personalized = task._personalize_message(base_message, context)

        self.assertEqual(personalized, "Hello John Doe, your account is ready!")

    def test_html_and_text_email_versions(self):
        """Test sending both HTML and text versions"""
        task = EmailNotificationTask()

        with patch('django.core.mail.EmailMultiAlternatives') as mock_email_class:
            mock_email = Mock()
            mock_email_class.return_value = mock_email

            task._send_html_text_email(
                recipient='test@example.com',
                subject='Test',
                html_content='<p>HTML content</p>',
                text_content='Text content'
            )

            mock_email.attach_alternative.assert_called_once_with('<p>HTML content</p>', 'text/html')
            mock_email.send.assert_called_once()

    def test_email_attachment_handling(self):
        """Test email attachment functionality"""
        task = EmailNotificationTask()

        attachments = [
            ('document.pdf', b'PDF content', 'application/pdf'),
            ('image.png', b'PNG content', 'image/png')
        ]

        with patch('django.core.mail.EmailMessage') as mock_email_class:
            mock_email = Mock()
            mock_email_class.return_value = mock_email

            task._send_email_with_attachments(
                recipient='test@example.com',
                subject='Test with attachments',
                message='Test message',
                attachments=attachments
            )

            # Check that attachments were added
            self.assertEqual(mock_email.attach.call_count, len(attachments))

    def test_email_performance_metrics(self):
        """Test email performance metrics collection"""
        task = EmailNotificationTask()
        task.task_id = 'metrics-task-123'

        with patch.object(task, '_send_email') as mock_send:
            mock_send.return_value = {'success': True}

            start_time = timezone.now()
            result = task._send_email('test@example.com', 'Test', 'Message')
            end_time = timezone.now()

            self.assertTrue(result['success'])
            self.assertIn('sent_at', result)
            self.assertTrue(start_time <= result['sent_at'] <= end_time)

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        DEFAULT_FROM_EMAIL='test@crm.com'
    )
    def test_email_send_failure_handling(self):
        """Test handling of email send failures"""
        task = EmailNotificationTask()
        task.request = self.mock_task.request

        with patch('django.core.mail.send_mail') as mock_send:
            mock_send.side_effect = Exception('SMTP server unavailable')

            with self.assertRaises(TaskExecutionError):
                task._send_email('test@example.com', 'Test', 'Message')

    def test_email_template_fallback(self):
        """Test email template fallback to text when HTML fails"""
        task = EmailNotificationTask()

        with patch('django.template.loader.render_to_string') as mock_render:
            # First call (HTML) fails, second call (text) succeeds
            mock_render.side_effect = ['HTML content', 'Text content']

            result = task._render_template_with_fallback(
                'emails/test.html',
                'emails/test.txt',
                {}
            )

            self.assertEqual(result, 'Text content')
            self.assertEqual(mock_render.call_count, 2)