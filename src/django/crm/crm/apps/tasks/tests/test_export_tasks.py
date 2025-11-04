"""
Test suite for Data Export Tasks
Following TDD principles and comprehensive export testing
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock, mock_open
from datetime import datetime, timedelta
from decimal import Decimal
from io import StringIO, BytesIO
import csv
import json

from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.utils import timezone
from django.core.management import call_command

from ..base_tasks import TaskStatus
from ..export_tasks import (
    DataExportTask,
    ContactsExportTask,
    DealsExportTask,
    ActivitiesExportTask,
    UsersExportTask,
    ExportFormat,
    ExportStatus,
    ExportProgress,
)
from ..exceptions import (
    TaskValidationError,
    TaskExecutionError,
    TaskTimeoutError,
    TaskResourceError,
)

User = get_user_model()


class TestExportFormat:
    """Test the ExportFormat enum for export type management"""

    def test_export_format_values(self):
        """Test that ExportFormat has all required values"""
        assert ExportFormat.CSV.value == 'CSV'
        assert ExportFormat.EXCEL.value == 'EXCEL'
        assert ExportFormat.JSON.value == 'JSON'
        assert ExportFormat.PDF.value == 'PDF'

    def test_export_format_extensions(self):
        """Test that each export format has correct file extension"""
        assert ExportFormat.CSV.get_extension() == '.csv'
        assert ExportFormat.EXCEL.get_extension() == '.xlsx'
        assert ExportFormat.JSON.get_extension() == '.json'
        assert ExportFormat.PDF.get_extension() == '.pdf'

    def test_export_format_mime_types(self):
        """Test that each export format has correct MIME type"""
        assert ExportFormat.CSV.get_mime_type() == 'text/csv'
        assert ExportFormat.EXCEL.get_mime_type() == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        assert ExportFormat.JSON.get_mime_type() == 'application/json'
        assert ExportFormat.PDF.get_mime_type() == 'application/pdf'

    def test_export_format_content_type(self):
        """Test that each export format has correct Django content type"""
        assert ExportFormat.CSV.get_content_type() == 'text/csv'
        assert ExportFormat.EXCEL.get_content_type() == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        assert ExportFormat.JSON.get_content_type() == 'application/json'
        assert ExportFormat.PDF.get_content_type() == 'application/pdf'


class TestExportStatus:
    """Test the ExportStatus enum for export process tracking"""

    def test_export_status_values(self):
        """Test that ExportStatus has all required values"""
        assert ExportStatus.PENDING.value == 'PENDING'
        assert ExportStatus.PREPARING.value == 'PREPARING'
        assert ExportStatus.EXPORTING.value == 'EXPORTING'
        assert ExportStatus.COMPRESSING.value == 'COMPRESSING'
        assert ExportStatus.UPLOADING.value == 'UPLOADING'
        assert ExportStatus.COMPLETED.value == 'COMPLETED'
        assert ExportStatus.FAILED.value == 'FAILED'
        assert ExportStatus.CANCELLED.value == 'CANCELLED'

    def test_export_status_is_active(self):
        """Test active status checking"""
        assert ExportStatus.PREPARING.is_active() is True
        assert ExportStatus.EXPORTING.is_active() is True
        assert ExportStatus.COMPRESSING.is_active() is True
        assert ExportStatus.UPLOADING.is_active() is True

        assert ExportStatus.PENDING.is_active() is False
        assert ExportStatus.COMPLETED.is_active() is False
        assert ExportStatus.FAILED.is_active() is False
        assert ExportStatus.CANCELLED.is_active() is False

    def test_export_status_is_completed(self):
        """Test completed status checking"""
        assert ExportStatus.COMPLETED.is_completed() is True
        assert ExportStatus.FAILED.is_completed() is True
        assert ExportStatus.CANCELLED.is_completed() is True

        assert ExportStatus.PENDING.is_completed() is False
        assert ExportStatus.PREPARING.is_completed() is False
        assert ExportStatus.EXPORTING.is_completed() is False
        assert ExportStatus.COMPRESSING.is_completed() is False
        assert ExportStatus.UPLOADING.is_completed() is False


class TestExportProgress:
    """Test the ExportProgress class for progress tracking"""

    def test_export_progress_initialization(self):
        """Test ExportProgress initialization"""
        progress = ExportProgress(total_items=1000)

        assert progress.total_items == 1000
        assert progress.processed_items == 0
        assert progress.percentage == 0.0
        assert progress.current_stage == ExportStatus.PENDING

    def test_export_progress_update(self):
        """Test progress updates"""
        progress = ExportProgress(total_items=1000)

        progress.update(processed_items=250, stage=ExportStatus.EXPORTING)

        assert progress.processed_items == 250
        assert progress.percentage == 25.0
        assert progress.current_stage == ExportStatus.EXPORTING

    def test_export_progress_add_items(self):
        """Test adding processed items"""
        progress = ExportProgress(total_items=1000)

        progress.add_items(100)

        assert progress.processed_items == 100
        assert progress.percentage == 10.0

    def test_export_progress_complete(self):
        """Test marking progress as complete"""
        progress = ExportProgress(total_items=1000)

        progress.complete()

        assert progress.processed_items == 1000
        assert progress.percentage == 100.0
        assert progress.current_stage == ExportStatus.COMPLETED


class TestDataExportTask(TestCase):
    """Test the base DataExportTask class"""

    def setUp(self):
        """Set up test environment"""
        self.mock_task = Mock()
        self.mock_task.request.id = 'test-export-task-id'
        self.mock_task.request.retries = 0
        self.mock_task.request.hostname = 'test-export-worker'

        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )

        # Create test data
        self.sample_data = [
            {'id': 1, 'name': 'John Doe', 'email': 'john@example.com'},
            {'id': 2, 'name': 'Jane Smith', 'email': 'jane@example.com'},
            {'id': 3, 'name': 'Bob Johnson', 'email': 'bob@example.com'},
        ]

    def test_export_csv_format_success(self):
        """Test successful CSV export"""
        task = DataExportTask()
        task.request = self.mock_task.request

        with patch.object(task, 'set_task_status') as mock_set_status:
            with patch('builtins.open', mock_open()) as mock_file:
                result = task.export_data(
                    data=self.sample_data,
                    format=ExportFormat.CSV,
                    filename='test_contacts',
                    requested_by=self.user.id
                )

                self.assertTrue(result['success'])
                self.assertEqual(result['format'], ExportFormat.CSV.value)
                self.assertEqual(result['total_records'], len(self.sample_data))
                self.assertEqual(result['file_size'], mock_file().write.call_count)

                # Check that status was updated
                mock_set_status.assert_any_call(TaskStatus.RUNNING, progress=0)
                mock_set_status.assert_any_call(TaskStatus.SUCCESS, progress=100)

    def test_export_json_format_success(self):
        """Test successful JSON export"""
        task = DataExportTask()
        task.request = self.mock_task.request

        with patch.object(task, 'set_task_status') as mock_set_status:
            with patch('builtins.open', mock_open()) as mock_file:
                result = task.export_data(
                    data=self.sample_data,
                    format=ExportFormat.JSON,
                    filename='test_contacts',
                    requested_by=self.user.id
                )

                self.assertTrue(result['success'])
                self.assertEqual(result['format'], ExportFormat.JSON.value)
                self.assertEqual(result['total_records'], len(self.sample_data))

    def test_export_excel_format_success(self):
        """Test successful Excel export"""
        task = DataExportTask()
        task.request = self.mock_task.request

        with patch.object(task, 'set_task_status') as mock_set_status:
            with patch('pandas.DataFrame.to_excel') as mock_to_excel:
                mock_to_excel.return_value = None

                result = task.export_data(
                    data=self.sample_data,
                    format=ExportFormat.EXCEL,
                    filename='test_contacts',
                    requested_by=self.user.id
                )

                self.assertTrue(result['success'])
                self.assertEqual(result['format'], ExportFormat.EXCEL.value)
                mock_to_excel.assert_called_once()

    def test_export_with_progress_tracking(self):
        """Test export with progress tracking"""
        task = DataExportTask()
        task.request = self.mock_task.request

        # Create large dataset for progress testing
        large_data = [{'id': i, 'name': f'User {i}'} for i in range(1000)]

        with patch.object(task, 'set_task_status') as mock_set_status:
            with patch('builtins.open', mock_open()):
                task.export_data(
                    data=large_data,
                    format=ExportFormat.CSV,
                    filename='large_export',
                    requested_by=self.user.id
                )

                # Check that progress was updated multiple times
                progress_calls = [call for call in mock_set_status.call_args_list
                                if 'progress' in call[1]]
                self.assertTrue(len(progress_calls) > 1)

                # Check final progress
                final_progress = progress_calls[-1][1]['progress']
                self.assertEqual(final_progress, 100)

    def test_export_with_filtering(self):
        """Test export with data filtering"""
        task = DataExportTask()
        task.request = self.mock_task.request

        filters = {'name__icontains': 'John'}

        with patch.object(task, '_apply_filters') as mock_filters:
            mock_filters.return_value = [self.sample_data[0]]  # Only John Doe

            with patch('builtins.open', mock_open()):
                result = task.export_data(
                    data=self.sample_data,
                    format=ExportFormat.CSV,
                    filename='filtered_contacts',
                    requested_by=self.user.id,
                    filters=filters
                )

                mock_filters.assert_called_once_with(self.sample_data, filters)
                self.assertEqual(result['total_records'], 1)

    def test_export_with_field_selection(self):
        """Test export with specific field selection"""
        task = DataExportTask()
        task.request = self.mock_task.request

        fields = ['id', 'name']  # Exclude email field

        with patch.object(task, '_select_fields') as mock_select_fields:
            mock_select_fields.return_value = [
                {'id': 1, 'name': 'John Doe'},
                {'id': 2, 'name': 'Jane Smith'},
            ]

            with patch('builtins.open', mock_open()):
                result = task.export_data(
                    data=self.sample_data,
                    format=ExportFormat.CSV,
                    filename='selected_fields',
                    requested_by=self.user.id,
                    fields=fields
                )

                mock_select_fields.assert_called_once_with(self.sample_data, fields)

    def test_export_validation_missing_data(self):
        """Test export validation with missing data"""
        task = DataExportTask()
        task.request = self.mock_task.request

        with self.assertRaises(TaskValidationError):
            task.export_data(
                data=None,
                format=ExportFormat.CSV,
                filename='test',
                requested_by=self.user.id
            )

    def test_export_validation_invalid_format(self):
        """Test export validation with invalid format"""
        task = DataExportTask()
        task.request = self.mock_task.request

        with self.assertRaises(TaskValidationError):
            task.export_data(
                data=self.sample_data,
                format='INVALID',
                filename='test',
                requested_by=self.user.id
            )

    def test_export_validation_user_not_found(self):
        """Test export validation with non-existent user"""
        task = DataExportTask()
        task.request = self.mock_task.request

        with self.assertRaises(TaskValidationError):
            task.export_data(
                data=self.sample_data,
                format=ExportFormat.CSV,
                filename='test',
                requested_by=99999
            )

    def test_export_with_large_data_timeout(self):
        """Test export timeout with large datasets"""
        task = DataExportTask()
        task.request = self.mock_task.request
        task.soft_time_limit = 1  # 1 second limit

        # Create dataset that will take time to process
        huge_data = [{'id': i, 'data': 'x' * 1000} for i in range(10000)]

        with patch.object(task, '_export_to_csv') as mock_export:
            # Simulate slow export
            mock_export.side_effect = lambda *args, **kwargs: time.sleep(2)

            with self.assertRaises(TaskTimeoutError):
                task.export_data(
                    data=huge_data,
                    format=ExportFormat.CSV,
                    filename='huge_export',
                    requested_by=self.user.id
                )

    def test_export_disk_space_check(self):
        """Test export disk space validation"""
        task = DataExportTask()
        task.request = self.mock_task.request

        # Create large data that would exceed disk space
        large_data = [{'data': 'x' * 1000000} for _ in range(1000)]  # ~1GB

        with patch('os.statvfs') as mock_statvfs:
            # Mock insufficient disk space
            mock_statvfs.return_value.f_bavail = 100  # Only 100 blocks available
            mock_statvfs.return_value.f_frsize = 4096  # 4K block size

            with self.assertRaises(TaskResourceError):
                task.export_data(
                    data=large_data,
                    format=ExportFormat.CSV,
                    filename='large_export',
                    requested_by=self.user.id
                )

    def test_csv_writer_functionality(self):
        """Test CSV writer functionality"""
        task = DataExportTask()

        output = StringIO()
        task._write_csv(output, self.sample_data)

        csv_content = output.getvalue()
        lines = csv_content.strip().split('\n')

        # Check header
        self.assertIn('id,name,email', lines[0])

        # Check data rows
        self.assertEqual(len(lines), len(self.sample_data) + 1)  # +1 for header

    def test_json_writer_functionality(self):
        """Test JSON writer functionality"""
        task = DataExportTask()

        output = StringIO()
        task._write_json(output, self.sample_data)

        json_content = output.getvalue()
        parsed_data = json.loads(json_content)

        self.assertEqual(parsed_data, self.sample_data)

    def test_field_filtering_functionality(self):
        """Test field selection functionality"""
        task = DataExportTask()

        fields = ['id', 'name']
        filtered_data = task._select_fields(self.sample_data, fields)

        expected = [
            {'id': 1, 'name': 'John Doe'},
            {'id': 2, 'name': 'Jane Smith'},
            {'id': 3, 'name': 'Bob Johnson'},
        ]

        self.assertEqual(filtered_data, expected)

    def test_data_filtering_functionality(self):
        """Test data filtering functionality"""
        task = DataExportTask()

        filters = {'name__icontains': 'john'}
        filtered_data = task._apply_filters(self.sample_data, filters)

        # Should only return records with 'john' in name (case insensitive)
        self.assertEqual(len(filtered_data), 2)  # John Doe and Bob Johnson

    def test_export_file_naming(self):
        """Test export file naming conventions"""
        task = DataExportTask()

        filename = task._generate_filename(
            base_name='contacts',
            format=ExportFormat.CSV,
            user_id=self.user.id
        )

        expected_pattern = f'contacts_{self.user.id}_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv'
        self.assertEqual(filename, expected_pattern)

    def test_export_file_size_calculation(self):
        """Test export file size calculation"""
        task = DataExportTask()

        with patch('os.path.getsize') as mock_getsize:
            mock_getsize.return_value = 1024 * 1024  # 1MB

            size_mb = task._get_file_size('/tmp/test.csv')

            self.assertEqual(size_mb, 1.0)

    def test_export_compression(self):
        """Test export file compression"""
        task = DataExportTask()

        with patch('zipfile.ZipFile') as mock_zipfile:
            mock_zipfile.return_value.__enter__.return_value = Mock()
            mock_zipfile.return_value.__exit__.return_value = None

            compressed_file = task._compress_file('/tmp/test.csv', '/tmp/test.csv.zip')

            self.assertEqual(compressed_file, '/tmp/test.csv.zip')
            mock_zipfile.assert_called_once()


class TestContactsExportTask(TestCase):
    """Test the ContactsExportTask class"""

    def setUp(self):
        """Set up test environment"""
        self.mock_task = Mock()
        self.mock_task.request.id = 'test-contacts-export-task-id'
        self.mock_task.request.retries = 0
        self.mock_task.request.hostname = 'test-contacts-export-worker'

        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    @patch('crm.shared.repositories.contact_repository.ContactRepository.get_all')
    def test_export_contacts_success(self, mock_get_all):
        """Test successful contacts export"""
        task = ContactsExportTask()
        task.request = self.mock_task.request

        # Mock contact data
        mock_contacts = [
            {
                'id': 1,
                'first_name': 'John',
                'last_name': 'Doe',
                'email': 'john@example.com',
                'phone': '+1234567890',
                'company': 'ACME Corp',
                'created_at': timezone.now(),
            },
            {
                'id': 2,
                'first_name': 'Jane',
                'last_name': 'Smith',
                'email': 'jane@example.com',
                'phone': '+0987654321',
                'company': 'XYZ Inc',
                'created_at': timezone.now(),
            },
        ]
        mock_get_all.return_value = mock_contacts

        with patch.object(task, 'export_data') as mock_export:
            mock_export.return_value = {
                'success': True,
                'total_records': len(mock_contacts),
                'file_path': '/tmp/contacts_export.csv'
            }

            result = task.export_contacts(
                format=ExportFormat.CSV,
                requested_by=self.user.id,
                filters={'company': 'ACME Corp'},
                fields=['first_name', 'last_name', 'email']
            )

            self.assertTrue(result['success'])
            self.assertEqual(result['export_type'], 'contacts')
            self.assertEqual(result['total_records'], len(mock_contacts))

            # Verify export_data was called with correct parameters
            mock_export.assert_called_once()
            call_args = mock_export.call_args[1]
            self.assertEqual(call_args['data'], mock_contacts)
            self.assertEqual(call_args['format'], ExportFormat.CSV)
            self.assertEqual(call_args['requested_by'], self.user.id)

    def test_export_contacts_with_repository_error(self):
        """Test contacts export with repository error"""
        task = ContactsExportTask()
        task.request = self.mock_task.request

        with patch('crm.shared.repositories.contact_repository.ContactRepository.get_all') as mock_get_all:
            mock_get_all.side_effect = Exception("Database connection failed")

            with self.assertRaises(TaskExecutionError):
                task.export_contacts(
                    format=ExportFormat.CSV,
                    requested_by=self.user.id
                )


class TestDealsExportTask(TestCase):
    """Test the DealsExportTask class"""

    def setUp(self):
        """Set up test environment"""
        self.mock_task = Mock()
        self.mock_task.request.id = 'test-deals-export-task-id'
        self.mock_task.request.retries = 0
        self.mock_task.request.hostname = 'test-deals-export-worker'

        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    @patch('crm.shared.repositories.deal_repository.DealRepository.get_all')
    def test_export_deals_success(self, mock_get_all):
        """Test successful deals export"""
        task = DealsExportTask()
        task.request = self.mock_task.request

        # Mock deal data
        mock_deals = [
            {
                'id': 1,
                'title': 'Website Redesign',
                'value': Decimal('50000.00'),
                'stage': 'Proposal',
                'probability': 75,
                'expected_close_date': timezone.now() + timedelta(days=30),
                'assigned_to': self.user,
                'created_at': timezone.now(),
            },
            {
                'id': 2,
                'title': 'Mobile App Development',
                'value': Decimal('75000.00'),
                'stage': 'Negotiation',
                'probability': 90,
                'expected_close_date': timezone.now() + timedelta(days=15),
                'assigned_to': self.user,
                'created_at': timezone.now(),
            },
        ]
        mock_get_all.return_value = mock_deals

        with patch.object(task, 'export_data') as mock_export:
            mock_export.return_value = {
                'success': True,
                'total_records': len(mock_deals),
                'file_path': '/tmp/deals_export.csv'
            }

            result = task.export_deals(
                format=ExportFormat.EXCEL,
                requested_by=self.user.id,
                filters={'stage': 'Proposal'},
                fields=['title', 'value', 'stage']
            )

            self.assertTrue(result['success'])
            self.assertEqual(result['export_type'], 'deals')
            self.assertEqual(result['total_records'], len(mock_deals))


class TestActivitiesExportTask(TestCase):
    """Test the ActivitiesExportTask class"""

    def setUp(self):
        """Set up test environment"""
        self.mock_task = Mock()
        self.mock_task.request.id = 'test-activities-export-task-id'
        self.mock_task.request.retries = 0
        self.mock_task.request.hostname = 'test-activities-export-worker'

        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    @patch('crm.shared.repositories.activity_repository.ActivityRepository.get_all')
    def test_export_activities_success(self, mock_get_all):
        """Test successful activities export"""
        task = ActivitiesExportTask()
        task.request = self.mock_task.request

        # Mock activity data
        mock_activities = [
            {
                'id': 1,
                'title': 'Follow-up call',
                'description': 'Discuss proposal details',
                'type': 'Call',
                'priority': 'High',
                'due_date': timezone.now() + timedelta(hours=2),
                'assigned_to': self.user,
                'status': 'Pending',
                'created_at': timezone.now(),
            },
            {
                'id': 2,
                'title': 'Send proposal',
                'description': 'Email revised proposal',
                'type': 'Email',
                'priority': 'Normal',
                'due_date': timezone.now() + timedelta(days=1),
                'assigned_to': self.user,
                'status': 'Pending',
                'created_at': timezone.now(),
            },
        ]
        mock_get_all.return_value = mock_activities

        with patch.object(task, 'export_data') as mock_export:
            mock_export.return_value = {
                'success': True,
                'total_records': len(mock_activities),
                'file_path': '/tmp/activities_export.csv'
            }

            result = task.export_activities(
                format=ExportFormat.CSV,
                requested_by=self.user.id,
                filters={'status': 'Pending'},
                fields=['title', 'type', 'due_date']
            )

            self.assertTrue(result['success'])
            self.assertEqual(result['export_type'], 'activities')
            self.assertEqual(result['total_records'], len(mock_activities))


class TestUsersExportTask(TestCase):
    """Test the UsersExportTask class"""

    def setUp(self):
        """Set up test environment"""
        self.mock_task = Mock()
        self.mock_task.request.id = 'test-users-export-task-id'
        self.mock_task.request.retries = 0
        self.mock_task.request.hostname = 'test-users-export-worker'

        # Create admin user for export
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpass123',
            is_staff=True
        )

    @patch('crm.shared.repositories.user_repository.UserRepository.get_all')
    def test_export_users_success(self, mock_get_all):
        """Test successful users export"""
        task = UsersExportTask()
        task.request = self.mock_task.request

        # Mock user data
        mock_users = [
            {
                'id': 1,
                'username': 'john_doe',
                'email': 'john@example.com',
                'first_name': 'John',
                'last_name': 'Doe',
                'role': 'Sales',
                'is_active': True,
                'date_joined': timezone.now(),
            },
            {
                'id': 2,
                'username': 'jane_smith',
                'email': 'jane@example.com',
                'first_name': 'Jane',
                'last_name': 'Smith',
                'role': 'Manager',
                'is_active': True,
                'date_joined': timezone.now(),
            },
        ]
        mock_get_all.return_value = mock_users

        with patch.object(task, 'export_data') as mock_export:
            mock_export.return_value = {
                'success': True,
                'total_records': len(mock_users),
                'file_path': '/tmp/users_export.csv'
            }

            result = task.export_users(
                format=ExportFormat.JSON,
                requested_by=self.admin_user.id,
                filters={'is_active': True},
                fields=['username', 'email', 'role']
            )

            self.assertTrue(result['success'])
            self.assertEqual(result['export_type'], 'users')
            self.assertEqual(result['total_records'], len(mock_users))

    def test_export_users_permission_denied(self):
        """Test users export permission denied for non-admin"""
        task = UsersExportTask()
        task.request = self.mock_task.request

        # Create regular user
        regular_user = User.objects.create_user(
            username='regular',
            email='regular@example.com',
            password='regularpass123'
        )

        with self.assertRaises(TaskValidationError) as context:
            task.export_users(
                format=ExportFormat.CSV,
                requested_by=regular_user.id
            )

        self.assertIn('permission', str(context.exception).lower())