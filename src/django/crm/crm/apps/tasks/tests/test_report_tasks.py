"""
Test suite for Report Generation Tasks
Following TDD principles and comprehensive report testing
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta, date
from decimal import Decimal
from io import StringIO, BytesIO
import json

from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Sum, Avg, Count, Q

from ..report_tasks import (
    ReportGenerationTask,
    SalesReportTask,
    ActivityReportTask,
    UserPerformanceReportTask,
    DealPipelineReportTask,
    MonthlySummaryReportTask,
    ReportType,
    ReportFormat,
    ReportStatus,
    ReportPeriod,
)
from ..base_tasks import TaskStatus
from ..exceptions import (
    TaskValidationError,
    TaskExecutionError,
    TaskTimeoutError,
    TaskResourceError,
)

User = get_user_model()


class TestReportType:
    """Test the ReportType enum for report categorization"""

    def test_report_type_values(self):
        """Test that ReportType has all required values"""
        assert ReportType.SALES.value == 'SALES'
        assert ReportType.ACTIVITY.value == 'ACTIVITY'
        assert ReportType.USER_PERFORMANCE.value == 'USER_PERFORMANCE'
        assert ReportType.DEAL_PIPELINE.value == 'DEAL_PIPELINE'
        assert ReportType.MONTHLY_SUMMARY.value == 'MONTHLY_SUMMARY'
        assert ReportType.CUSTOM.value == 'CUSTOM'

    def test_report_type_descriptions(self):
        """Test that each report type has description"""
        assert ReportType.SALES.get_description() == 'Sales performance and revenue reports'
        assert ReportType.ACTIVITY.get_description() == 'Activity and task completion reports'
        assert ReportType.USER_PERFORMANCE.get_description() == 'User performance and productivity reports'
        assert ReportType.DEAL_PIPELINE.get_description() == 'Deal pipeline and conversion reports'
        assert ReportType.MONTHLY_SUMMARY.get_description() == 'Monthly business summary reports'

    def test_report_type_permissions(self):
        """Test that each report type has correct permission requirements"""
        assert ReportType.SALES.requires_admin() is False
        assert ReportType.USER_PERFORMANCE.requires_admin() is True
        assert ReportType.MONTHLY_SUMMARY.requires_admin() is True
        assert ReportType.ACTIVITY.requires_admin() is False
        assert ReportType.DEAL_PIPELINE.requires_admin() is False


class TestReportFormat:
    """Test the ReportFormat enum for report output formats"""

    def test_report_format_values(self):
        """Test that ReportFormat has all required values"""
        assert ReportFormat.PDF.value == 'PDF'
        assert ReportFormat.EXCEL.value == 'EXCEL'
        assert ReportFormat.HTML.value == 'HTML'
        assert ReportFormat.JSON.value == 'JSON'

    def test_report_format_extensions(self):
        """Test that each report format has correct file extension"""
        assert ReportFormat.PDF.get_extension() == '.pdf'
        assert ReportFormat.EXCEL.get_extension() == '.xlsx'
        assert ReportFormat.HTML.get_extension() == '.html'
        assert ReportFormat.JSON.get_extension() == '.json'

    def test_report_format_mime_types(self):
        """Test that each report format has correct MIME type"""
        assert ReportFormat.PDF.get_mime_type() == 'application/pdf'
        assert ReportFormat.EXCEL.get_mime_type() == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        assert ReportFormat.HTML.get_mime_type() == 'text/html'
        assert ReportFormat.JSON.get_mime_type() == 'application/json'


class TestReportPeriod:
    """Test the ReportPeriod enum for time period management"""

    def test_report_period_values(self):
        """Test that ReportPeriod has all required values"""
        assert ReportType.DAILY.value == 'DAILY'
        assert ReportType.WEEKLY.value == 'WEEKLY'
        assert ReportType.MONTHLY.value == 'MONTHLY'
        assert ReportType.QUARTERLY.value == 'QUARTERLY'
        assert ReportType.YEARLY.value == 'YEARLY'
        assert ReportType.CUSTOM.value == 'CUSTOM'

    def test_report_period_date_ranges(self):
        """Test that each report period calculates correct date ranges"""
        today = timezone.now().date()

        # Test daily period
        start_date, end_date = ReportPeriod.DAILY.get_date_range(today)
        assert start_date == today
        assert end_date == today

        # Test weekly period
        start_date, end_date = ReportPeriod.WEEKLY.get_date_range(today)
        assert (end_date - start_date).days == 6  # 7 days total

        # Test monthly period
        start_date, end_date = ReportPeriod.MONTHLY.get_date_range(today)
        assert start_date.day == 1
        assert start_date.month == today.month
        assert end_date.month == today.month

    def test_report_period_next_period(self):
        """Test next period calculation"""
        today = timezone.now().date()

        next_daily = ReportPeriod.DAILY.get_next_period(today)
        assert next_daily == today + timedelta(days=1)

        next_weekly = ReportPeriod.WEEKLY.get_next_period(today)
        assert next_weekly == today + timedelta(days=7)


class TestReportGenerationTask(TestCase):
    """Test the base ReportGenerationTask class"""

    def setUp(self):
        """Set up test environment"""
        self.mock_task = Mock()
        self.mock_task.request.id = 'test-report-task-id'
        self.mock_task.request.retries = 0
        self.mock_task.request.hostname = 'test-report-worker'

        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )

        # Sample report data
        self.sample_report_data = {
            'title': 'Test Report',
            'generated_at': timezone.now(),
            'period': 'Monthly',
            'summary': {
                'total_records': 100,
                'total_value': Decimal('50000.00'),
                'growth_rate': 15.5
            },
            'details': [
                {'category': 'A', 'value': 1000, 'count': 10},
                {'category': 'B', 'value': 2000, 'count': 20},
                {'category': 'C', 'value': 3000, 'count': 30},
            ]
        }

    def test_generate_pdf_report_success(self):
        """Test successful PDF report generation"""
        task = ReportGenerationTask()
        task.request = self.mock_task.request

        with patch.object(task, 'set_task_status') as mock_set_status:
            with patch('builtins.open', mock_open()) as mock_file:
                result = task.generate_report(
                    report_type=ReportType.SALES,
                    format=ReportFormat.PDF,
                    data=self.sample_report_data,
                    requested_by=self.user.id,
                    period=ReportPeriod.MONTHLY
                )

                self.assertTrue(result['success'])
                self.assertEqual(result['format'], ReportFormat.PDF.value)
                self.assertEqual(result['report_type'], ReportType.SALES.value)
                self.assertIn('file_path', result)

                # Check that status was updated
                mock_set_status.assert_any_call(TaskStatus.RUNNING, progress=0)
                mock_set_status.assert_any_call(TaskStatus.SUCCESS, progress=100)

    def test_generate_excel_report_success(self):
        """Test successful Excel report generation"""
        task = ReportGenerationTask()
        task.request = self.mock_task.request

        with patch.object(task, 'set_task_status') as mock_set_status:
            with patch('pandas.DataFrame.to_excel') as mock_to_excel:
                mock_to_excel.return_value = None

                result = task.generate_report(
                    report_type=ReportType.SALES,
                    format=ReportFormat.EXCEL,
                    data=self.sample_report_data,
                    requested_by=self.user.id,
                    period=ReportPeriod.MONTHLY
                )

                self.assertTrue(result['success'])
                self.assertEqual(result['format'], ReportFormat.EXCEL.value)
                mock_to_excel.assert_called_once()

    def test_generate_html_report_success(self):
        """Test successful HTML report generation"""
        task = ReportGenerationTask()
        task.request = self.mock_task.request

        with patch.object(task, 'set_task_status') as mock_set_status:
            with patch('builtins.open', mock_open()) as mock_file:
                result = task.generate_report(
                    report_type=ReportType.SALES,
                    format=ReportFormat.HTML,
                    data=self.sample_report_data,
                    requested_by=self.user.id,
                    period=ReportPeriod.MONTHLY
                )

                self.assertTrue(result['success'])
                self.assertEqual(result['format'], ReportFormat.HTML.value)

    def test_generate_json_report_success(self):
        """Test successful JSON report generation"""
        task = ReportGenerationTask()
        task.request = self.mock_task.request

        with patch.object(task, 'set_task_status') as mock_set_status:
            with patch('builtins.open', mock_open()) as mock_file:
                result = task.generate_report(
                    report_type=ReportType.SALES,
                    format=ReportFormat.JSON,
                    data=self.sample_report_data,
                    requested_by=self.user.id,
                    period=ReportPeriod.MONTHLY
                )

                self.assertTrue(result['success'])
                self.assertEqual(result['format'], ReportFormat.JSON.value)

    def test_report_generation_with_progress_tracking(self):
        """Test report generation with progress tracking"""
        task = ReportGenerationTask()
        task.request = self.mock_task.request

        with patch.object(task, 'set_task_status') as mock_set_status:
            with patch('builtins.open', mock_open()):
                task.generate_report(
                    report_type=ReportType.SALES,
                    format=ReportFormat.PDF,
                    data=self.sample_report_data,
                    requested_by=self.user.id,
                    period=ReportPeriod.MONTHLY
                )

                # Check that progress was updated
                progress_calls = [call for call in mock_set_status.call_args_list
                                if 'progress' in call[1]]
                self.assertTrue(len(progress_calls) >= 3)  # Initial, intermediate, final

    def test_report_data_validation(self):
        """Test report data validation"""
        task = ReportGenerationTask()
        task.request = self.mock_task.request

        # Test missing title
        invalid_data = self.sample_report_data.copy()
        del invalid_data['title']

        with self.assertRaises(TaskValidationError):
            task.generate_report(
                report_type=ReportType.SALES,
                format=ReportFormat.PDF,
                data=invalid_data,
                requested_by=self.user.id,
                period=ReportPeriod.MONTHLY
            )

    def test_report_period_validation(self):
        """Test report period validation"""
        task = ReportGenerationTask()
        task.request = self.mock_task.request

        # Test custom period without date range
        with self.assertRaises(TaskValidationError):
            task.generate_report(
                report_type=ReportType.SALES,
                format=ReportFormat.PDF,
                data=self.sample_report_data,
                requested_by=self.user.id,
                period=ReportPeriod.CUSTOM,
                custom_start_date=None
            )

    def test_user_permission_validation(self):
        """Test user permission validation for admin-only reports"""
        task = ReportGenerationTask()
        task.request = self.mock_task.request

        # Create regular user (not admin)
        regular_user = User.objects.create_user(
            username='regular',
            email='regular@example.com',
            password='regularpass123'
        )

        # Try to generate admin-only report
        with self.assertRaises(TaskValidationError) as context:
            task.generate_report(
                report_type=ReportType.USER_PERFORMANCE,  # Requires admin
                format=ReportFormat.PDF,
                data=self.sample_report_data,
                requested_by=regular_user.id,
                period=ReportPeriod.MONTHLY
            )

        self.assertIn('permission', str(context.exception).lower())

    def test_report_template_rendering(self):
        """Test report template rendering"""
        task = ReportGenerationTask()

        template_data = {
            'title': 'Sales Report',
            'period': 'Monthly',
            'data': self.sample_report_data
        }

        with patch('django.template.loader.render_to_string') as mock_render:
            mock_render.return_value = '<html>Rendered template</html>'

            result = task._render_template('reports/sales_report.html', template_data)

            mock_render.assert_called_once_with('reports/sales_report.html', template_data)
            self.assertEqual(result, '<html>Rendered template</html>')

    def test_report_data_aggregation(self):
        """Test report data aggregation functionality"""
        task = ReportGenerationTask()

        raw_data = [
            {'category': 'A', 'value': 100, 'date': date(2023, 1, 1)},
            {'category': 'A', 'value': 200, 'date': date(2023, 1, 15)},
            {'category': 'B', 'value': 150, 'date': date(2023, 1, 10)},
            {'category': 'B', 'value': 250, 'date': date(2023, 1, 20)},
        ]

        aggregated = task._aggregate_data(raw_data, group_by='category', aggregations=['sum', 'count'])

        expected = {
            'A': {'sum': 300, 'count': 2},
            'B': {'sum': 400, 'count': 2}
        }

        self.assertEqual(aggregated, expected)

    def test_report_date_range_filtering(self):
        """Test report date range filtering"""
        task = ReportGenerationTask()

        data_with_dates = [
            {'value': 100, 'date': date(2023, 1, 1)},
            {'value': 200, 'date': date(2023, 1, 15)},
            {'value': 300, 'date': date(2023, 2, 1)},
            {'value': 400, 'date': date(2023, 2, 15)},
        ]

        filtered = task._filter_by_date_range(
            data_with_dates,
            date_field='date',
            start_date=date(2023, 1, 1),
            end_date=date(2023, 1, 31)
        )

        self.assertEqual(len(filtered), 2)
        self.assertEqual(filtered[0]['value'], 100)
        self.assertEqual(filtered[1]['value'], 200)

    def test_report_file_naming(self):
        """Test report file naming conventions"""
        task = ReportGenerationTask()

        filename = task._generate_filename(
            report_type=ReportType.SALES,
            period=ReportPeriod.MONTHLY,
            format=ReportFormat.PDF,
            user_id=self.user.id
        )

        expected_pattern = f'sales_report_monthly_{self.user.id}_{timezone.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        self.assertEqual(filename, expected_pattern)

    def test_report_timeout_handling(self):
        """Test report generation timeout handling"""
        task = ReportGenerationTask()
        task.request = self.mock_task.request
        task.soft_time_limit = 1  # 1 second limit

        with patch.object(task, '_generate_pdf_report') as mock_generate:
            # Simulate slow report generation
            mock_generate.side_effect = lambda *args, **kwargs: time.sleep(2)

            with self.assertRaises(TaskTimeoutError):
                task.generate_report(
                    report_type=ReportType.SALES,
                    format=ReportFormat.PDF,
                    data=self.sample_report_data,
                    requested_by=self.user.id,
                    period=ReportPeriod.MONTHLY
                )


class TestSalesReportTask(TestCase):
    """Test the SalesReportTask class"""

    def setUp(self):
        """Set up test environment"""
        self.mock_task = Mock()
        self.mock_task.request.id = 'test-sales-report-task-id'
        self.mock_task.request.retries = 0
        self.mock_task.request.hostname = 'test-sales-report-worker'

        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    @patch('crm.shared.repositories.deal_repository.DealRepository.get_sales_summary')
    @patch('crm.shared.repositories.deal_repository.DealRepository.get_deals_by_period')
    def test_generate_sales_report_success(self, mock_get_deals, mock_get_summary):
        """Test successful sales report generation"""
        task = SalesReportTask()
        task.request = self.mock_task.request

        # Mock deal data
        mock_deals = [
            {
                'id': 1,
                'title': 'Deal A',
                'value': Decimal('10000.00'),
                'stage': 'Won',
                'close_date': date(2023, 10, 15),
                'assigned_to': self.user,
            },
            {
                'id': 2,
                'title': 'Deal B',
                'value': Decimal('15000.00'),
                'stage': 'Won',
                'close_date': date(2023, 10, 20),
                'assigned_to': self.user,
            },
        ]
        mock_get_deals.return_value = mock_deals

        # Mock summary data
        mock_summary = {
            'total_deals': 2,
            'total_value': Decimal('25000.00'),
            'won_deals': 2,
            'won_value': Decimal('25000.00'),
            'conversion_rate': 100.0,
        }
        mock_get_summary.return_value = mock_summary

        with patch.object(task, 'generate_report') as mock_generate:
            mock_generate.return_value = {
                'success': True,
                'file_path': '/tmp/sales_report.pdf',
                'format': 'PDF'
            }

            result = task.generate_sales_report(
                format=ReportFormat.PDF,
                period=ReportPeriod.MONTHLY,
                requested_by=self.user.id
            )

            self.assertTrue(result['success'])
            self.assertEqual(result['report_type'], 'sales')

            # Verify generate_report was called with correct data
            mock_generate.assert_called_once()
            call_args = mock_generate.call_args[1]
            self.assertEqual(call_args['report_type'], ReportType.SALES)
            self.assertEqual(call_args['format'], ReportFormat.PDF)
            self.assertEqual(call_args['requested_by'], self.user.id)

            # Check report data structure
            report_data = call_args['data']
            self.assertIn('summary', report_data)
            self.assertIn('deals', report_data)
            self.assertIn('performance_metrics', report_data)

    def test_sales_report_with_date_range(self):
        """Test sales report generation with custom date range"""
        task = SalesReportTask()
        task.request = self.mock_task.request

        start_date = date(2023, 1, 1)
        end_date = date(2023, 1, 31)

        with patch.object(task, 'generate_report') as mock_generate:
            mock_generate.return_value = {'success': True}

            result = task.generate_sales_report(
                format=ReportFormat.EXCEL,
                period=ReportPeriod.CUSTOM,
                requested_by=self.user.id,
                custom_start_date=start_date,
                custom_end_date=end_date
            )

            self.assertTrue(result['success'])

            # Verify date range was passed correctly
            call_args = mock_generate.call_args[1]
            self.assertEqual(call_args['period'], ReportPeriod.CUSTOM)
            self.assertEqual(call_args['custom_start_date'], start_date)
            self.assertEqual(call_args['custom_end_date'], end_date)


class TestActivityReportTask(TestCase):
    """Test the ActivityReportTask class"""

    def setUp(self):
        """Set up test environment"""
        self.mock_task = Mock()
        self.mock_task.request.id = 'test-activity-report-task-id'
        self.mock_task.request.retries = 0
        self.mock_task.request.hostname = 'test-activity-report-worker'

        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    @patch('crm.shared.repositories.activity_repository.ActivityRepository.get_activity_summary')
    @patch('crm.shared.repositories.activity_repository.ActivityRepository.get_activities_by_period')
    def test_generate_activity_report_success(self, mock_get_activities, mock_get_summary):
        """Test successful activity report generation"""
        task = ActivityReportTask()
        task.request = self.mock_task.request

        # Mock activity data
        mock_activities = [
            {
                'id': 1,
                'title': 'Call Client',
                'type': 'Call',
                'status': 'Completed',
                'assigned_to': self.user,
                'completed_date': date(2023, 10, 15),
            },
            {
                'id': 2,
                'title': 'Send Proposal',
                'type': 'Email',
                'status': 'Pending',
                'assigned_to': self.user,
                'due_date': date(2023, 10, 20),
            },
        ]
        mock_get_activities.return_value = mock_activities

        # Mock summary data
        mock_summary = {
            'total_activities': 2,
            'completed_activities': 1,
            'pending_activities': 1,
            'completion_rate': 50.0,
        }
        mock_get_summary.return_value = mock_summary

        with patch.object(task, 'generate_report') as mock_generate:
            mock_generate.return_value = {'success': True}

            result = task.generate_activity_report(
                format=ReportFormat.HTML,
                period=ReportPeriod.WEEKLY,
                requested_by=self.user.id
            )

            self.assertTrue(result['success'])
            self.assertEqual(result['report_type'], 'activity')


class TestUserPerformanceReportTask(TestCase):
    """Test the UserPerformanceReportTask class"""

    def setUp(self):
        """Set up test environment"""
        self.mock_task = Mock()
        self.mock_task.request.id = 'test-user-perf-report-task-id'
        self.mock_task.request.retries = 0
        self.mock_task.request.hostname = 'test-user-perf-report-worker'

        # Create admin user
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpass123',
            is_staff=True
        )

        # Create regular users
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='user1pass123'
        )
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='user2pass123'
        )

    @patch('crm.shared.repositories.user_repository.UserRepository.get_performance_metrics')
    def test_generate_user_performance_report_success(self, mock_get_metrics):
        """Test successful user performance report generation"""
        task = UserPerformanceReportTask()
        task.request = self.mock_task.request

        # Mock performance data
        mock_metrics = {
            self.user1.id: {
                'deals_created': 5,
                'deals_won': 3,
                'total_deal_value': Decimal('50000.00'),
                'activities_completed': 25,
                'conversion_rate': 60.0,
            },
            self.user2.id: {
                'deals_created': 3,
                'deals_won': 2,
                'total_deal_value': Decimal('30000.00'),
                'activities_completed': 20,
                'conversion_rate': 66.7,
            }
        }
        mock_get_metrics.return_value = mock_metrics

        with patch.object(task, 'generate_report') as mock_generate:
            mock_generate.return_value = {'success': True}

            result = task.generate_user_performance_report(
                format=ReportFormat.EXCEL,
                period=ReportPeriod.MONTHLY,
                requested_by=self.admin_user.id
            )

            self.assertTrue(result['success'])
            self.assertEqual(result['report_type'], 'user_performance')

    def test_user_performance_report_permission_denied(self):
        """Test user performance report permission denied for non-admin"""
        task = UserPerformanceReportTask()
        task.request = self.mock_task.request

        with self.assertRaises(TaskValidationError) as context:
            task.generate_user_performance_report(
                format=ReportFormat.PDF,
                period=ReportPeriod.MONTHLY,
                requested_by=self.user1.id  # Non-admin user
            )

        self.assertIn('permission', str(context.exception).lower())


class TestDealPipelineReportTask(TestCase):
    """Test the DealPipelineReportTask class"""

    def setUp(self):
        """Set up test environment"""
        self.mock_task = Mock()
        self.mock_task.request.id = 'test-pipeline-report-task-id'
        self.mock_task.request.retries = 0
        self.mock_task.request.hostname = 'test-pipeline-report-worker'

        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    @patch('crm.shared.repositories.deal_repository.DealRepository.get_pipeline_summary')
    @patch('crm.shared.repositories.deal_repository.DealRepository.get_deals_by_stage')
    def test_generate_deal_pipeline_report_success(self, mock_get_deals, mock_get_summary):
        """Test successful deal pipeline report generation"""
        task = DealPipelineReportTask()
        task.request = self.mock_task.request

        # Mock pipeline data
        mock_deals_by_stage = {
            'Lead': [
                {'title': 'Lead A', 'value': Decimal('5000.00')},
                {'title': 'Lead B', 'value': Decimal('7500.00')},
            ],
            'Proposal': [
                {'title': 'Proposal A', 'value': Decimal('15000.00')},
            ],
            'Negotiation': [
                {'title': 'Deal A', 'value': Decimal('25000.00')},
            ],
        }
        mock_get_deals.return_value = mock_deals_by_stage

        # Mock summary data
        mock_summary = {
            'total_deals': 4,
            'total_pipeline_value': Decimal('52500.00'),
            'average_deal_size': Decimal('13125.00'),
            'stage_distribution': {
                'Lead': 2,
                'Proposal': 1,
                'Negotiation': 1,
            }
        }
        mock_get_summary.return_value = mock_summary

        with patch.object(task, 'generate_report') as mock_generate:
            mock_generate.return_value = {'success': True}

            result = task.generate_deal_pipeline_report(
                format=ReportFormat.PDF,
                period=ReportPeriod.MONTHLY,
                requested_by=self.user.id
            )

            self.assertTrue(result['success'])
            self.assertEqual(result['report_type'], 'deal_pipeline')


class TestMonthlySummaryReportTask(TestCase):
    """Test the MonthlySummaryReportTask class"""

    def setUp(self):
        """Set up test environment"""
        self.mock_task = Mock()
        self.mock_task.request.id = 'test-monthly-report-task-id'
        self.mock_task.request.retries = 0
        self.mock_task.request.hostname = 'test-monthly-report-worker'

        # Create admin user
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpass123',
            is_staff=True
        )

    @patch('crm.shared.repositories.deal_repository.DealRepository.get_monthly_summary')
    @patch('crm.shared.repositories.activity_repository.ActivityRepository.get_monthly_summary')
    @patch('crm.shared.repositories.contact_repository.ContactRepository.get_monthly_summary')
    def test_generate_monthly_summary_report_success(
        self,
        mock_contact_summary,
        mock_activity_summary,
        mock_deal_summary
    ):
        """Test successful monthly summary report generation"""
        task = MonthlySummaryReportTask()
        task.request = self.mock_task.request

        # Mock monthly data
        mock_deal_summary.return_value = {
            'new_deals': 10,
            'won_deals': 4,
            'total_revenue': Decimal('100000.00'),
            'conversion_rate': 40.0,
        }

        mock_activity_summary.return_value = {
            'total_activities': 50,
            'completed_activities': 40,
            'completion_rate': 80.0,
        }

        mock_contact_summary.return_value = {
            'new_contacts': 25,
            'active_contacts': 150,
        }

        with patch.object(task, 'generate_report') as mock_generate:
            mock_generate.return_value = {'success': True}

            result = task.generate_monthly_summary_report(
                format=ReportFormat.PDF,
                period=ReportPeriod.MONTHLY,
                requested_by=self.admin_user.id,
                report_month=date(2023, 10, 1)
            )

            self.assertTrue(result['success'])
            self.assertEqual(result['report_type'], 'monthly_summary')

            # Check that all data sources were included
            call_args = mock_generate.call_args[1]
            report_data = call_args['data']
            self.assertIn('deals_summary', report_data)
            self.assertIn('activities_summary', report_data)
            self.assertIn('contacts_summary', report_data)
            self.assertIn('overall_metrics', report_data)

    def test_monthly_summary_report_permission_denied(self):
        """Test monthly summary report permission denied for non-admin"""
        task = MonthlySummaryReportTask()
        task.request = self.mock_task.request

        # Create regular user
        regular_user = User.objects.create_user(
            username='regular',
            email='regular@example.com',
            password='regularpass123'
        )

        with self.assertRaises(TaskValidationError) as context:
            task.generate_monthly_summary_report(
                format=ReportFormat.PDF,
                period=ReportPeriod.MONTHLY,
                requested_by=regular_user.id,
                report_month=date(2023, 10, 1)
            )

        self.assertIn('permission', str(context.exception).lower())