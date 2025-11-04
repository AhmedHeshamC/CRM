"""
Report Generation Tasks for CRM Backend
Following SOLID principles and comprehensive report management
"""

import json
import logging
import os
import time
from datetime import datetime, date, timedelta
from decimal import Decimal
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db.models import Sum, Avg, Count, Q
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.text import slugify
from django.urls import reverse
from celery import shared_task

from .base_tasks import BaseTask, TaskStatus
from .report_types import (
    ReportType,
    ReportFormat,
    ReportPeriod,
    ReportStatus,
    ReportConfiguration,
)
from .exceptions import (
    TaskValidationError,
    TaskExecutionError,
    TaskTimeoutError,
    TaskResourceError,
    TaskExceptionFactory,
)

# Configure logger
logger = logging.getLogger(__name__)

User = get_user_model()


class ReportGenerationTask(BaseTask):
    """
    Base class for report generation tasks.

    This follows SOLID principles:
    - Single Responsibility: Handles report-specific functionality
    - Open/Closed: Extensible for different report types
    - Liskov Substitution: Compatible with BaseTask interface
    - Interface Segregation: Minimal, focused interface
    - Dependency Inversion: Depends on abstractions (ReportType, etc.)
    """

    # Task configuration
    name = 'report_generation'
    queue = 'reports'
    soft_time_limit = 900  # 15 minutes
    time_limit = 1800      # 30 minutes
    max_retries = 2
    default_retry_delay = 300  # 5 minutes

    def __init__(self):
        super().__init__()
        self.report_config = ReportConfiguration()

    def execute(self, *args, **kwargs) -> Dict[str, Any]:
        """
        Main report generation method.

        This follows the Template Method pattern by defining the
        overall report generation process while allowing customization.
        """
        report_type = ReportType(kwargs.get('report_type', 'SALES'))
        format_type = ReportFormat(kwargs.get('format', 'PDF'))
        data = kwargs.get('data')
        requested_by = kwargs.get('requested_by')
        period = ReportPeriod(kwargs.get('period', 'MONTHLY'))
        custom_start_date = kwargs.get('custom_start_date')
        custom_end_date = kwargs.get('custom_end_date')

        # Validate inputs
        self._validate_report_input(report_type, format_type, data, requested_by, period, custom_start_date)

        # Get user
        try:
            user = User.objects.get(id=requested_by)
        except User.DoesNotExist:
            raise TaskValidationError(
                f"User with ID {requested_by} does not exist",
                field_name="requested_by",
                field_value=requested_by
            )

        # Check permissions
        if report_type.requires_admin() and not user.is_staff:
            raise TaskValidationError(
                f"Report type {report_type.value} requires admin privileges",
                field_name="permissions",
                field_value=user.is_staff
            )

        # Get date range
        start_date, end_date = self._get_date_range(period, custom_start_date, custom_end_date)

        # Update status
        self.set_task_status(TaskStatus.RUNNING, progress=5)

        try:
            # Collect data
            self.set_task_status(TaskStatus.RUNNING, progress=10)
            collected_data = self._collect_report_data(report_type, user, start_date, end_date, kwargs)

            # Process data
            self.set_task_status(TaskStatus.RUNNING, progress=30)
            processed_data = self._process_report_data(collected_data, report_type, period)

            # Generate report
            self.set_task_status(TaskStatus.RUNNING, progress=60)
            report_result = self._generate_report_file(
                report_type,
                format_type,
                processed_data,
                user,
                start_date,
                end_date
            )

            # Complete report
            self.set_task_status(TaskStatus.SUCCESS, progress=100)

            result = {
                'success': True,
                'report_type': report_type.value,
                'format': format_type.value,
                'period': period.value,
                'start_date': start_date.isoformat() if start_date else None,
                'end_date': end_date.isoformat() if end_date else None,
                'file_path': report_result['file_path'],
                'file_size': report_result['file_size'],
                'download_url': self._generate_download_url(report_result['file_path']),
                'requested_by': user.username,
                'generated_at': timezone.now().isoformat(),
                'duration': (timezone.now() - self.created_at).total_seconds(),
            }

            # Log successful report generation
            logger.info(
                f"Report generated successfully: {report_type.value} in {format_type.value}",
                extra={
                    'task_id': self.task_id,
                    'user_id': requested_by,
                    'report_type': report_type.value,
                    'format': format_type.value,
                    'file_size_mb': report_result['file_size'] / (1024 * 1024)
                }
            )

            return result

        except Exception as e:
            self.set_task_status(TaskStatus.FAILURE)
            logger.error(
                f"Report generation failed: {str(e)}",
                extra={
                    'task_id': self.task_id,
                    'user_id': requested_by,
                    'report_type': report_type.value,
                    'error_type': e.__class__.__name__,
                    'error_message': str(e)
                }
            )
            raise TaskExecutionError(
                f"Report generation failed: {str(e)}",
                details={
                    'user_id': requested_by,
                    'report_type': report_type.value,
                    'format': format_type.value,
                    'error_type': e.__class__.__name__
                }
            )

    def _validate_report_input(
        self,
        report_type: ReportType,
        format_type: ReportFormat,
        data: Any,
        requested_by: int,
        period: ReportPeriod,
        custom_start_date: Optional[date]
    ) -> None:
        """
        Validate report generation inputs.

        This follows the Single Responsibility Principle by focusing
        specifically on input validation for report tasks.
        """
        if not isinstance(report_type, ReportType):
            raise TaskValidationError(
                f"Invalid report type: {report_type}",
                field_name="report_type",
                field_value=report_type
            )

        if not isinstance(format_type, ReportFormat):
            raise TaskValidationError(
                f"Invalid report format: {format_type}",
                field_name="format",
                field_value=format_type
            )

        if not requested_by or not isinstance(requested_by, int):
            raise TaskValidationError(
                "Valid user ID is required for report generation",
                field_name="requested_by",
                field_value=requested_by
            )

        if not isinstance(period, ReportPeriod):
            raise TaskValidationError(
                f"Invalid report period: {period}",
                field_name="period",
                field_value=period
            )

        # Validate custom period
        if period == ReportPeriod.CUSTOM and custom_start_date is None:
            raise TaskValidationError(
                "Custom start date is required for CUSTOM period",
                field_name="custom_start_date",
                field_value=custom_start_date
            )

        # Check if pandas is available for Excel reports
        if format_type.requires_pandas():
            try:
                import pandas as pd
            except ImportError:
                raise TaskConfigurationError(
                    f"Report format {format_type.value} requires pandas but it's not installed",
                    config_key="PANDAS_AVAILABLE"
                )

    def _get_date_range(
        self,
        period: ReportPeriod,
        custom_start_date: Optional[date],
        custom_end_date: Optional[date] = None
    ) -> Tuple[Optional[date], Optional[date]]:
        """
        Get date range for report period.

        This handles date range calculation for different period types.
        """
        if period == ReportPeriod.CUSTOM:
            return custom_start_date, custom_end_date
        else:
            return period.get_date_range()

    def _collect_report_data(
        self,
        report_type: ReportType,
        user: User,
        start_date: Optional[date],
        end_date: Optional[date],
        kwargs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Collect data for report based on type.

        This follows the Strategy pattern by delegating to specific
        data collection methods based on report type.
        """
        data = {}

        # Base data collection
        data['generated_at'] = timezone.now()
        data['generated_by'] = user.get_full_name() or user.username
        data['period_start'] = start_date
        data['period_end'] = end_date
        data['report_type'] = report_type.value

        # Collect type-specific data
        if report_type == ReportType.SALES:
            data.update(self._collect_sales_data(start_date, end_date))
        elif report_type == ReportType.ACTIVITY:
            data.update(self._collect_activity_data(start_date, end_date))
        elif report_type == ReportType.USER_PERFORMANCE:
            data.update(self._collect_user_performance_data(start_date, end_date))
        elif report_type == ReportType.DEAL_PIPELINE:
            data.update(self._collect_pipeline_data(start_date, end_date))
        elif report_type == ReportType.MONTHLY_SUMMARY:
            data.update(self._collect_monthly_summary_data(start_date, end_date))

        return data

    def _collect_sales_data(self, start_date: Optional[date], end_date: Optional[date]) -> Dict[str, Any]:
        """Collect sales-related data"""
        try:
            from ..repositories.deal_repository import DealRepository

            repo = DealRepository()
            deals = repo.get_deals_by_date_range(start_date, end_date)
            summary = repo.get_sales_summary(start_date, end_date)

            return {
                'deals': deals,
                'summary': summary,
                'metrics': self._calculate_sales_metrics(deals, summary)
            }
        except Exception as e:
            raise TaskExecutionError(
                f"Failed to collect sales data: {str(e)}",
                error_code="SALES_DATA_COLLECTION_ERROR"
            )

    def _collect_activity_data(self, start_date: Optional[date], end_date: Optional[date]) -> Dict[str, Any]:
        """Collect activity-related data"""
        try:
            from ..repositories.activity_repository import ActivityRepository

            repo = ActivityRepository()
            activities = repo.get_activities_by_date_range(start_date, end_date)
            summary = repo.get_activity_summary(start_date, end_date)

            return {
                'activities': activities,
                'summary': summary,
                'metrics': self._calculate_activity_metrics(activities, summary)
            }
        except Exception as e:
            raise TaskExecutionError(
                f"Failed to collect activity data: {str(e)}",
                error_code="ACTIVITY_DATA_COLLECTION_ERROR"
            )

    def _collect_user_performance_data(self, start_date: Optional[date], end_date: Optional[date]) -> Dict[str, Any]:
        """Collect user performance data"""
        try:
            from ..repositories.user_repository import UserRepository

            repo = UserRepository()
            performance_metrics = repo.get_performance_metrics(start_date, end_date)

            return {
                'performance_metrics': performance_metrics,
                'summary': self._calculate_user_performance_summary(performance_metrics)
            }
        except Exception as e:
            raise TaskExecutionError(
                f"Failed to collect user performance data: {str(e)}",
                error_code="USER_PERFORMANCE_DATA_COLLECTION_ERROR"
            )

    def _collect_pipeline_data(self, start_date: Optional[date], end_date: Optional[date]) -> Dict[str, Any]:
        """Collect deal pipeline data"""
        try:
            from ..repositories.deal_repository import DealRepository

            repo = DealRepository()
            deals_by_stage = repo.get_deals_by_stage()
            pipeline_summary = repo.get_pipeline_summary()

            return {
                'deals_by_stage': deals_by_stage,
                'pipeline_summary': pipeline_summary,
                'conversion_metrics': self._calculate_conversion_metrics(deals_by_stage)
            }
        except Exception as e:
            raise TaskExecutionError(
                f"Failed to collect pipeline data: {str(e)}",
                error_code="PIPELINE_DATA_COLLECTION_ERROR"
            )

    def _collect_monthly_summary_data(self, start_date: Optional[date], end_date: Optional[date]) -> Dict[str, Any]:
        """Collect monthly summary data"""
        try:
            # Collect data from multiple sources
            sales_data = self._collect_sales_data(start_date, end_date)
            activity_data = self._collect_activity_data(start_date, end_date)
            try:
                from ..repositories.contact_repository import ContactRepository
                contact_repo = ContactRepository()
                contacts_summary = contact_repo.get_monthly_summary(start_date, end_date)
            except:
                contacts_summary = {'new_contacts': 0, 'active_contacts': 0}

            return {
                'sales_summary': sales_data.get('summary', {}),
                'activities_summary': activity_data.get('summary', {}),
                'contacts_summary': contacts_summary,
                'overall_metrics': self._calculate_overall_metrics(
                    sales_data, activity_data, contacts_summary
                )
            }
        except Exception as e:
            raise TaskExecutionError(
                f"Failed to collect monthly summary data: {str(e)}",
                error_code="MONTHLY_SUMMARY_DATA_COLLECTION_ERROR"
            )

    def _process_report_data(
        self,
        collected_data: Dict[str, Any],
        report_type: ReportType,
        period: ReportPeriod
    ) -> Dict[str, Any]:
        """
        Process collected data for report generation.

        This includes data transformation, aggregation, and formatting.
        """
        processed_data = collected_data.copy()

        # Add computed metrics
        processed_data['computed_metrics'] = self._compute_additional_metrics(collected_data, report_type)

        # Add charts data if format supports it
        processed_data['charts_data'] = self._prepare_charts_data(collected_data, report_type)

        # Add summary sections
        processed_data['summary_sections'] = self._prepare_summary_sections(collected_data, report_type)

        # Add metadata
        processed_data['metadata'] = {
            'report_version': '1.0',
            'generated_at': timezone.now().isoformat(),
            'period_name': period.get_display_name(),
            'data_freshness': 'real-time'
        }

        return processed_data

    def _calculate_sales_metrics(self, deals: List[Dict], summary: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate sales-specific metrics"""
        metrics = {
            'total_deals': len(deals),
            'total_value': summary.get('total_value', 0),
            'average_deal_size': 0,
            'conversion_rate': summary.get('conversion_rate', 0),
            'sales_velocity': 0,  # Deals per day
        }

        if len(deals) > 0:
            metrics['average_deal_size'] = summary.get('total_value', 0) / len(deals)

        # Calculate sales velocity
        if summary.get('won_deals', 0) > 0:
            # Simple calculation - could be more sophisticated
            metrics['sales_velocity'] = summary.get('won_deals', 0) / 30  # Assuming 30-day period

        return metrics

    def _calculate_activity_metrics(self, activities: List[Dict], summary: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate activity-specific metrics"""
        metrics = {
            'total_activities': len(activities),
            'completion_rate': summary.get('completion_rate', 0),
            'activities_per_day': 0,
            'top_activity_types': [],
        }

        # Calculate activities per day
        if len(activities) > 0:
            metrics['activities_per_day'] = len(activities) / 30  # Assuming 30-day period

        # Find top activity types
        activity_type_counts = defaultdict(int)
        for activity in activities:
            activity_type_counts[activity.get('type', 'Unknown')] += 1

        metrics['top_activity_types'] = sorted(
            activity_type_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]

        return metrics

    def _calculate_user_performance_summary(self, performance_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate user performance summary"""
        summary = {
            'total_users': len(performance_metrics),
            'average_deals_per_user': 0,
            'average_completion_rate': 0,
            'top_performers': [],
            'performance_distribution': {},
        }

        if performance_metrics:
            total_deals = sum(metrics.get('deals_created', 0) for metrics in performance_metrics.values())
            total_completion_rate = sum(metrics.get('completion_rate', 0) for metrics in performance_metrics.values())

            summary['average_deals_per_user'] = total_deals / len(performance_metrics)
            summary['average_completion_rate'] = total_completion_rate / len(performance_metrics)

            # Find top performers
            performers = []
            for user_id, metrics in performance_metrics.items():
                performers.append({
                    'user_id': user_id,
                    'score': self._calculate_performance_score(metrics)
                })

            summary['top_performers'] = sorted(performers, key=lambda x: x['score'], reverse=True)[:5]

        return summary

    def _calculate_conversion_metrics(self, deals_by_stage: Dict[str, List[Dict]]) -> Dict[str, Any]:
        """Calculate conversion metrics for pipeline"""
        metrics = {
            'total_pipeline_value': 0,
            'stage_conversion_rates': {},
            'average_time_in_stage': {},
            'pipeline_health_score': 0,
        }

        stage_counts = {}
        for stage, deals in deals_by_stage.items():
            stage_counts[stage] = len(deals)
            metrics['total_pipeline_value'] += sum(
                deal.get('value', 0) for deal in deals
            )

        # Calculate conversion rates (simplified)
        stages = ['Lead', 'Qualified', 'Proposal', 'Negotiation', 'Won']
        for i in range(len(stages) - 1):
            current_stage = stages[i]
            next_stage = stages[i + 1]

            current_count = stage_counts.get(current_stage, 0)
            next_count = stage_counts.get(next_stage, 0)

            if current_count > 0:
                conversion_rate = (next_count / current_count) * 100
                metrics['stage_conversion_rates'][f"{current_stage}_to_{next_stage}"] = conversion_rate

        return metrics

    def _calculate_performance_score(self, metrics: Dict[str, Any]) -> float:
        """Calculate overall performance score for a user"""
        score = 0

        # Deals created (weight: 30%)
        score += min(metrics.get('deals_created', 0) * 2, 30)

        # Completion rate (weight: 40%)
        score += metrics.get('completion_rate', 0) * 0.4

        # Total value (weight: 30%)
        score += min(float(metrics.get('total_deal_value', 0)) / 1000, 30)

        return min(score, 100)

    def _compute_additional_metrics(
        self,
        data: Dict[str, Any],
        report_type: ReportType
    ) -> Dict[str, Any]:
        """Compute additional metrics for the report"""
        metrics = {}

        if report_type == ReportType.SALES:
            metrics['growth_rate'] = self._calculate_growth_rate(data)
            metrics['forecast_accuracy'] = self._calculate_forecast_accuracy(data)
        elif report_type == ReportType.ACTIVITY:
            metrics['productivity_trend'] = self._calculate_productivity_trend(data)
        elif report_type == ReportType.USER_PERFORMANCE:
            metrics['team_efficiency'] = self._calculate_team_efficiency(data)

        return metrics

    def _prepare_charts_data(
        self,
        data: Dict[str, Any],
        report_type: ReportType
    ) -> Dict[str, Any]:
        """Prepare data for charts visualization"""
        charts = {}

        if report_type == ReportType.SALES:
            charts['sales_trend'] = self._prepare_sales_trend_data(data)
            charts['deal_distribution'] = self._prepare_deal_distribution_data(data)
        elif report_type == ReportType.ACTIVITY:
            charts['activity_completion'] = self._prepare_activity_completion_data(data)
            charts['activity_types'] = self._prepare_activity_types_data(data)

        return charts

    def _prepare_summary_sections(
        self,
        data: Dict[str, Any],
        report_type: ReportType
    ) -> List[Dict[str, Any]]:
        """Prepare summary sections for the report"""
        sections = []

        # Executive summary
        sections.append({
            'title': 'Executive Summary',
            'type': 'summary',
            'data': self._create_executive_summary(data, report_type)
        })

        # Key metrics
        sections.append({
            'title': 'Key Metrics',
            'type': 'metrics',
            'data': self._extract_key_metrics(data, report_type)
        })

        return sections

    def _generate_report_file(
        self,
        report_type: ReportType,
        format_type: ReportFormat,
        data: Dict[str, Any],
        user: User,
        start_date: Optional[date],
        end_date: Optional[date]
    ) -> Dict[str, Any]:
        """
        Generate report file in specified format.

        This follows the Strategy pattern by delegating to specific
        format generation methods.
        """
        # Generate filename
        filename = self._generate_filename(report_type, format_type, user.id)

        # Generate file path
        file_path = self._get_report_file_path(filename)

        try:
            if format_type == ReportFormat.PDF:
                result = self._generate_pdf_report(data, file_path, report_type)
            elif format_type == ReportFormat.EXCEL:
                result = self._generate_excel_report(data, file_path, report_type)
            elif format_type == ReportFormat.HTML:
                result = self._generate_html_report(data, file_path, report_type)
            elif format_type == ReportFormat.JSON:
                result = self._generate_json_report(data, file_path, report_type)
            else:
                raise TaskValidationError(
                    f"Unsupported report format: {format_type.value}",
                    field_name="format",
                    field_value=format_type.value
                )

            return {
                'file_path': file_path,
                'file_size': os.path.getsize(file_path),
                'format': format_type.value
            }

        except Exception as e:
            # Clean up file on error
            if os.path.exists(file_path):
                os.remove(file_path)
            raise

    def _generate_pdf_report(
        self,
        data: Dict[str, Any],
        file_path: str,
        report_type: ReportType
    ) -> Dict[str, Any]:
        """
        Generate PDF report.

        This follows the Single Responsibility Principle by focusing
        specifically on PDF generation functionality.
        """
        # Render HTML template
        template_path = self.report_config.get_template_path(report_type, ReportFormat.PDF)
        html_content = render_to_string(template_path, {
            'data': data,
            'report_type': report_type,
            'format': ReportFormat.PDF,
            'config': self.report_config.get_format_settings(ReportFormat.PDF)
        })

        # Convert HTML to PDF (simplified implementation)
        # In a real implementation, you'd use WeasyPrint, ReportLab, or similar
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(f"""<!DOCTYPE html>
<html>
<head>
    <title>{data.get('title', 'Report')}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        .header {{ border-bottom: 2px solid #333; padding-bottom: 20px; margin-bottom: 30px; }}
        .summary {{ background: #f5f5f5; padding: 20px; margin: 20px 0; }}
        .metrics {{ display: flex; justify-content: space-between; margin: 20px 0; }}
        .metric {{ text-align: center; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{data.get('title', 'Report')}</h1>
        <p>Generated on {data.get('generated_at', '')}</p>
        <p>Period: {data.get('period_name', '')}</p>
    </div>
    <div class="summary">
        <h2>Summary</h2>
        <p>Report summary content would go here</p>
    </div>
    <div class="metrics">
        <div class="metric">
            <h3>Total Records</h3>
            <p>{data.get('total_records', 0)}</p>
        </div>
    </div>
    <div>
        <h2>Detailed Data</h2>
        <pre>{json.dumps(data, indent=2)}</pre>
    </div>
</body>
</html>""")

        return {'file_path': file_path, 'format': 'PDF'}

    def _generate_excel_report(
        self,
        data: Dict[str, Any],
        file_path: str,
        report_type: ReportType
    ) -> Dict[str, Any]:
        """
        Generate Excel report.

        This follows the Single Responsibility Principle by focusing
        specifically on Excel generation functionality.
        """
        try:
            import pandas as pd
        except ImportError:
            raise TaskConfigurationError(
                "Excel report generation requires pandas but it's not installed",
                config_key="PANDAS_AVAILABLE"
            )

        # Create Excel writer
        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            # Summary sheet
            summary_data = self._prepare_excel_summary_data(data)
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='Summary', index=False)

            # Details sheet
            if 'details' in data and data['details']:
                details_df = pd.DataFrame(data['details'])
                details_df.to_excel(writer, sheet_name='Details', index=False)

            # Charts data sheet
            if 'charts_data' in data and data['charts_data']:
                charts_df = pd.DataFrame(data['charts_data'])
                charts_df.to_excel(writer, sheet_name='Charts Data', index=False)

        return {'file_path': file_path, 'format': 'EXCEL'}

    def _generate_html_report(
        self,
        data: Dict[str, Any],
        file_path: str,
        report_type: ReportType
    ) -> Dict[str, Any]:
        """
        Generate HTML report.

        This follows the Single Responsibility Principle by focusing
        specifically on HTML generation functionality.
        """
        template_path = self.report_config.get_template_path(report_type, ReportFormat.HTML)
        html_content = render_to_string(template_path, {
            'data': data,
            'report_type': report_type,
            'format': ReportFormat.HTML,
            'config': self.report_config.get_format_settings(ReportFormat.HTML)
        })

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        return {'file_path': file_path, 'format': 'HTML'}

    def _generate_json_report(
        self,
        data: Dict[str, Any],
        file_path: str,
        report_type: ReportType
    ) -> Dict[str, Any]:
        """
        Generate JSON report.

        This follows the Single Responsibility Principle by focusing
        specifically on JSON generation functionality.
        """
        report_data = {
            'metadata': data.get('metadata', {}),
            'report_type': report_type.value,
            'generated_at': data.get('generated_at'),
            'data': data
        }

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, default=str, ensure_ascii=False)

        return {'file_path': file_path, 'format': 'JSON'}

    def _generate_filename(
        self,
        report_type: ReportType,
        format_type: ReportFormat,
        user_id: int
    ) -> str:
        """
        Generate unique filename for report.

        This follows the Single Responsibility Principle by handling
        filename generation with proper sanitization.
        """
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        safe_name = slugify(report_type.value.lower())
        return f"{safe_name}_report_{user_id}_{timestamp}{format_type.get_extension()}"

    def _get_report_file_path(self, filename: str) -> str:
        """
        Get file path for report.

        This ensures files are stored in the proper reports directory.
        """
        reports_dir = getattr(settings, 'REPORTS_DIR', '/tmp/reports')
        import os
        os.makedirs(reports_dir, exist_ok=True)
        return os.path.join(reports_dir, filename)

    def _generate_download_url(self, file_path: str) -> str:
        """
        Generate download URL for report.

        This provides a secure way for users to download their reports.
        """
        filename = os.path.basename(file_path)
        return f"/api/v1/reports/download/{filename}/"

    def generate_report(self, *args, **kwargs) -> Dict[str, Any]:
        """Public method for report generation"""
        return self.execute(*args, **kwargs)


@shared_task(bind=True, base=ReportGenerationTask, name='generate_sales_report')
class SalesReportTask(ReportGenerationTask):
    """
    Task for generating sales reports.

    This follows the Single Responsibility Principle by focusing
    specifically on sales report functionality.
    """

    def generate_sales_report(self, **kwargs) -> Dict[str, Any]:
        """Public method for sales report generation"""
        kwargs['report_type'] = ReportType.SALES.value
        return self.generate_report(**kwargs)


@shared_task(bind=True, base=ReportGenerationTask, name='generate_activity_report')
class ActivityReportTask(ReportGenerationTask):
    """
    Task for generating activity reports.

    This follows the Single Responsibility Principle by focusing
    specifically on activity report functionality.
    """

    def generate_activity_report(self, **kwargs) -> Dict[str, Any]:
        """Public method for activity report generation"""
        kwargs['report_type'] = ReportType.ACTIVITY.value
        return self.generate_report(**kwargs)


@shared_task(bind=True, base=ReportGenerationTask, name='generate_user_performance_report')
class UserPerformanceReportTask(ReportGenerationTask):
    """
    Task for generating user performance reports (admin only).

    This follows the Single Responsibility Principle by focusing
    specifically on user performance report functionality.
    """

    def generate_user_performance_report(self, **kwargs) -> Dict[str, Any]:
        """Public method for user performance report generation"""
        kwargs['report_type'] = ReportType.USER_PERFORMANCE.value
        return self.generate_report(**kwargs)


@shared_task(bind=True, base=ReportGenerationTask, name='generate_deal_pipeline_report')
class DealPipelineReportTask(ReportGenerationTask):
    """
    Task for generating deal pipeline reports.

    This follows the Single Responsibility Principle by focusing
    specifically on deal pipeline report functionality.
    """

    def generate_deal_pipeline_report(self, **kwargs) -> Dict[str, Any]:
        """Public method for deal pipeline report generation"""
        kwargs['report_type'] = ReportType.DEAL_PIPELINE.value
        return self.generate_report(**kwargs)


@shared_task(bind=True, base=ReportGenerationTask, name='generate_monthly_summary_report')
class MonthlySummaryReportTask(ReportGenerationTask):
    """
    Task for generating monthly summary reports (admin only).

    This follows the Single Responsibility Principle by focusing
    specifically on monthly summary report functionality.
    """

    def generate_monthly_summary_report(self, **kwargs) -> Dict[str, Any]:
        """Public method for monthly summary report generation"""
        kwargs['report_type'] = ReportType.MONTHLY_SUMMARY.value
        return self.generate_report(**kwargs)