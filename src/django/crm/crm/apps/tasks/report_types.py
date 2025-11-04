"""
Report Types and Formats for Background Report Tasks
Following SOLID principles and comprehensive report management
"""

from enum import Enum
from datetime import date, timedelta
from typing import Tuple, Optional


class ReportType(Enum):
    """
    Enumeration of report types with their metadata.

    This follows the Single Responsibility Principle by centralizing
    report type management and providing consistent behavior.
    """

    SALES = 'SALES'
    ACTIVITY = 'ACTIVITY'
    USER_PERFORMANCE = 'USER_PERFORMANCE'
    DEAL_PIPELINE = 'DEAL_PIPELINE'
    MONTHLY_SUMMARY = 'MONTHLY_SUMMARY'
    CUSTOM = 'CUSTOM'

    def get_description(self) -> str:
        """Get description for this report type"""
        descriptions = {
            ReportType.SALES: 'Sales performance and revenue reports',
            ReportType.ACTIVITY: 'Activity and task completion reports',
            ReportType.USER_PERFORMANCE: 'User performance and productivity reports',
            ReportType.DEAL_PIPELINE: 'Deal pipeline and conversion reports',
            ReportType.MONTHLY_SUMMARY: 'Monthly business summary reports',
            ReportType.CUSTOM: 'Custom reports with specific parameters',
        }
        return descriptions[self]

    def requires_admin(self) -> bool:
        """Check if this report type requires admin privileges"""
        admin_reports = {
            ReportType.USER_PERFORMANCE,
            ReportType.MONTHLY_SUMMARY,
        }
        return self in admin_reports

    def get_template_name(self, format_type: 'ReportFormat') -> str:
        """Get template name for this report type and format"""
        template_mapping = {
            ReportType.SALES: 'reports/sales_report',
            ReportType.ACTIVITY: 'reports/activity_report',
            ReportType.USER_PERFORMANCE: 'reports/user_performance_report',
            ReportType.DEAL_PIPELINE: 'reports/deal_pipeline_report',
            ReportType.MONTHLY_SUMMARY: 'reports/monthly_summary_report',
            ReportType.CUSTOM: 'reports/custom_report',
        }
        return template_mapping[self]

    def get_default_format(self) -> 'ReportFormat':
        """Get default format for this report type"""
        default_formats = {
            ReportType.SALES: ReportFormat.PDF,
            ReportType.ACTIVITY: ReportFormat.EXCEL,
            ReportType.USER_PERFORMANCE: ReportFormat.EXCEL,
            ReportType.DEAL_PIPELINE: ReportFormat.PDF,
            ReportType.MONTHLY_SUMMARY: ReportFormat.PDF,
            ReportType.CUSTOM: ReportFormat.HTML,
        }
        return default_formats[self]


class ReportFormat(Enum):
    """
    Enumeration of report output formats.

    This follows the Single Responsibility Principle by centralizing
    format management and providing consistent behavior.
    """

    PDF = 'PDF'
    EXCEL = 'EXCEL'
    HTML = 'HTML'
    JSON = 'JSON'

    def get_extension(self) -> str:
        """Get file extension for this format"""
        extensions = {
            ReportFormat.PDF: '.pdf',
            ReportFormat.EXCEL: '.xlsx',
            ReportFormat.HTML: '.html',
            ReportFormat.JSON: '.json',
        }
        return extensions[self]

    def get_mime_type(self) -> str:
        """Get MIME type for this format"""
        mime_types = {
            ReportFormat.PDF: 'application/pdf',
            ReportFormat.EXCEL: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            ReportFormat.HTML: 'text/html',
            ReportFormat.JSON: 'application/json',
        }
        return mime_types[self]

    def requires_pandas(self) -> bool:
        """Check if format requires pandas for processing"""
        return self == ReportFormat.EXCEL

    def supports_charts(self) -> bool:
        """Check if format supports embedded charts"""
        chart_formats = {ReportFormat.PDF, ReportFormat.HTML}
        return self in chart_formats

    def supports_interactivity(self) -> bool:
        """Check if format supports interactive elements"""
        return self == ReportFormat.HTML


class ReportPeriod(Enum):
    """
    Enumeration of report periods with date range calculations.

    This follows the Single Responsibility Principle by centralizing
    period management and providing date calculation utilities.
    """

    DAILY = 'DAILY'
    WEEKLY = 'WEEKLY'
    MONTHLY = 'MONTHLY'
    QUARTERLY = 'QUARTERLY'
    YEARLY = 'YEARLY'
    CUSTOM = 'CUSTOM'

    def get_date_range(self, reference_date: date = None) -> Tuple[date, date]:
        """
        Get start and end dates for this period.

        Args:
            reference_date: Reference date for calculation (default: today)

        Returns:
            Tuple[date, date]: (start_date, end_date)
        """
        if reference_date is None:
            from django.utils import timezone
            reference_date = timezone.now().date()

        if self == ReportPeriod.DAILY:
            start_date = end_date = reference_date

        elif self == ReportPeriod.WEEKLY:
            # Start from Monday of the week
            start_date = reference_date - timedelta(days=reference_date.weekday())
            end_date = start_date + timedelta(days=6)

        elif self == ReportPeriod.MONTHLY:
            start_date = reference_date.replace(day=1)
            # Get last day of month
            if reference_date.month == 12:
                next_month = reference_date.replace(year=reference_date.year + 1, month=1, day=1)
            else:
                next_month = reference_date.replace(month=reference_date.month + 1, day=1)
            end_date = next_month - timedelta(days=1)

        elif self == ReportPeriod.QUARTERLY:
            quarter = (reference_date.month - 1) // 3 + 1
            start_month = (quarter - 1) * 3 + 1
            start_date = reference_date.replace(month=start_month, day=1)
            if start_month + 3 > 12:
                end_date = reference_date.replace(year=reference_date.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                end_date = reference_date.replace(month=start_month + 3, day=1) - timedelta(days=1)

        elif self == ReportPeriod.YEARLY:
            start_date = reference_date.replace(month=1, day=1)
            end_date = reference_date.replace(month=12, day=31)

        elif self == ReportPeriod.CUSTOM:
            # For custom period, return None to indicate explicit dates needed
            return None, None

        else:
            raise ValueError(f"Unsupported report period: {self}")

        return start_date, end_date

    def get_next_period(self, reference_date: date = None) -> date:
        """
        Get the start date of the next period.

        Args:
            reference_date: Reference date for calculation

        Returns:
            date: Start date of next period
        """
        if reference_date is None:
            from django.utils import timezone
            reference_date = timezone.now().date()

        if self == ReportPeriod.DAILY:
            return reference_date + timedelta(days=1)

        elif self == ReportPeriod.WEEKLY:
            return reference_date + timedelta(weeks=1)

        elif self == ReportPeriod.MONTHLY:
            if reference_date.month == 12:
                return reference_date.replace(year=reference_date.year + 1, month=1, day=1)
            else:
                return reference_date.replace(month=reference_date.month + 1, day=1)

        elif self == ReportPeriod.QUARTERLY:
            current_quarter = (reference_date.month - 1) // 3 + 1
            if current_quarter == 4:
                return reference_date.replace(year=reference_date.year + 1, month=1, day=1)
            else:
                next_quarter_month = current_quarter * 3 + 1
                return reference_date.replace(month=next_quarter_month, day=1)

        elif self == ReportPeriod.YEARLY:
            return reference_date.replace(year=reference_date.year + 1, month=1, day=1)

        elif self == ReportPeriod.CUSTOM:
            raise ValueError("Cannot calculate next period for CUSTOM period type")

        else:
            raise ValueError(f"Unsupported report period: {self}")

    def get_display_name(self) -> str:
        """Get human-readable display name for this period"""
        display_names = {
            ReportPeriod.DAILY: 'Daily',
            ReportPeriod.WEEKLY: 'Weekly',
            ReportPeriod.MONTHLY: 'Monthly',
            ReportPeriod.QUARTERLY: 'Quarterly',
            ReportPeriod.YEARLY: 'Yearly',
            ReportPeriod.CUSTOM: 'Custom',
        }
        return display_names[self]


class ReportStatus(Enum):
    """
    Enumeration of report generation statuses.

    This follows the Single Responsibility Principle by providing
    a centralized status management system for report operations.
    """

    PENDING = 'PENDING'
    DATA_COLLECTION = 'DATA_COLLECTION'
    PROCESSING = 'PROCESSING'
    GENERATING = 'GENERATING'
    FORMATTING = 'FORMATTING'
    COMPLETED = 'COMPLETED'
    FAILED = 'FAILED'
    CANCELLED = 'CANCELLED'

    def is_active(self) -> bool:
        """Check if report generation is in an active state"""
        active_statuses = {
            ReportStatus.DATA_COLLECTION,
            ReportStatus.PROCESSING,
            ReportStatus.GENERATING,
            ReportStatus.FORMATTING
        }
        return self in active_statuses

    def is_completed(self) -> bool:
        """Check if report generation is in a completed state"""
        completed_statuses = {
            ReportStatus.COMPLETED,
            ReportStatus.FAILED,
            ReportStatus.CANCELLED
        }
        return self in completed_statuses

    def is_successful(self) -> bool:
        """Check if report generation was successful"""
        return self == ReportStatus.COMPLETED

    def get_progress_weight(self) -> float:
        """Get progress weight for this status"""
        progress_weights = {
            ReportStatus.PENDING: 0.0,
            ReportStatus.DATA_COLLECTION: 0.2,
            ReportStatus.PROCESSING: 0.4,
            ReportStatus.GENERATING: 0.7,
            ReportStatus.FORMATTING: 0.9,
            ReportStatus.COMPLETED: 1.0,
            ReportStatus.FAILED: 0.0,
            ReportStatus.CANCELLED: 0.0,
        }
        return progress_weights[self]


class ReportConfiguration:
    """
    Configuration class for report settings.

    This follows the Single Responsibility Principle by centralizing
    report configuration management.
    """

    # Report limits
    MAX_REPORT_SIZE_MB = 50
    MAX_RECORDS_PER_REPORT = 100000
    MAX_CONCURRENT_REPORTS = 5

    # Timeouts (in seconds)
    DATA_COLLECTION_TIMEOUT = 300      # 5 minutes
    REPORT_GENERATION_TIMEOUT = 600    # 10 minutes
    TOTAL_TIMEOUT = 900                # 15 minutes

    # Caching
    CACHE_DURATION_MINUTES = 60        # 1 hour
    ENABLE_RESULT_CACHING = True

    # Formatting
    DEFAULT_PAGE_SIZE = 'A4'
    DEFAULT_ORIENTATION = 'portrait'
    INCLUDE_CHARTS = True
    INCLUDE_SUMMARIES = True

    # Templates
    TEMPLATE_DIR = 'reports/'
    FALLBACK_TEMPLATE = 'reports/generic_report.html'

    # Export settings
    ENABLE_COMPRESSION = True
    COMPRESSION_THRESHOLD_MB = 10
    RETENTION_DAYS = 30

    @classmethod
    def get_timeout_for_status(cls, status: ReportStatus) -> int:
        """Get timeout for specific status"""
        timeout_mapping = {
            ReportStatus.DATA_COLLECTION: cls.DATA_COLLECTION_TIMEOUT,
            ReportStatus.PROCESSING: cls.REPORT_GENERATION_TIMEOUT,
            ReportStatus.GENERATING: cls.REPORT_GENERATION_TIMEOUT,
            ReportStatus.FORMATTING: 300,  # 5 minutes
        }
        return timeout_mapping.get(status, cls.TOTAL_TIMEOUT)

    @classmethod
    def validate_report_size(cls, estimated_size_mb: float) -> bool:
        """Validate if report size is within limits"""
        return estimated_size_mb <= cls.MAX_REPORT_SIZE_MB

    @classmethod
    def validate_record_count(cls, record_count: int) -> bool:
        """Validate if record count is within limits"""
        return record_count <= cls.MAX_RECORDS_PER_REPORT

    @classmethod
    def get_cache_key(cls, report_type: ReportType, period: ReportPeriod, **kwargs) -> str:
        """Generate cache key for report"""
        key_parts = [
            'report',
            report_type.value.lower(),
            period.value.lower(),
        ]

        # Add additional parameters to cache key
        for key, value in sorted(kwargs.items()):
            if value is not None:
                key_parts.append(f"{key}_{value}")

        return '_'.join(key_parts)

    @classmethod
    def get_template_path(cls, report_type: ReportType, format_type: ReportFormat) -> str:
        """Get template path for report type and format"""
        base_template = report_type.get_template_name(format_type)

        if format_type == ReportFormat.HTML:
            return f"{base_template}.html"
        elif format_type == ReportFormat.PDF:
            return f"{base_template}_pdf.html"
        else:
            return f"{base_template}.html"  # Fallback

    @classmethod
    def get_format_settings(cls, format_type: ReportFormat) -> dict:
        """Get format-specific settings"""
        format_settings = {
            ReportFormat.PDF: {
                'page_size': cls.DEFAULT_PAGE_SIZE,
                'orientation': cls.DEFAULT_ORIENTATION,
                'include_charts': cls.INCLUDE_CHARTS,
                'include_summaries': cls.INCLUDE_SUMMARIES,
            },
            ReportFormat.EXCEL: {
                'include_charts': False,
                'auto_filter': True,
                'freeze_header': True,
            },
            ReportFormat.HTML: {
                'include_charts': True,
                'responsive': True,
                'include_navigation': True,
            },
            ReportFormat.JSON: {
                'pretty_print': True,
                'include_metadata': True,
            }
        }
        return format_settings.get(format_type, {})