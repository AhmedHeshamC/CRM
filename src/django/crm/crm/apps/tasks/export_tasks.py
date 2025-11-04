"""
Data Export Tasks for CRM Backend
Following SOLID principles and comprehensive export management
"""

import csv
import json
import os
import zipfile
import logging
import time
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from io import StringIO, BytesIO
from typing import Dict, Any, List, Optional, Union, BinaryIO
from pathlib import Path

import pandas as pd
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db.models import Q
from django.utils import timezone
from django.utils.text import slugify
from celery import shared_task

from .base_tasks import BaseTask, TaskStatus
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


class ExportFormat(Enum):
    """
    Enumeration of supported export formats.

    This follows the Single Responsibility Principle by centralizing
    export format management and providing consistent behavior.
    """

    CSV = 'CSV'
    EXCEL = 'EXCEL'
    JSON = 'JSON'
    PDF = 'PDF'

    def get_extension(self) -> str:
        """Get file extension for this format"""
        extensions = {
            ExportFormat.CSV: '.csv',
            ExportFormat.EXCEL: '.xlsx',
            ExportFormat.JSON: '.json',
            ExportFormat.PDF: '.pdf',
        }
        return extensions[self]

    def get_mime_type(self) -> str:
        """Get MIME type for this format"""
        mime_types = {
            ExportFormat.CSV: 'text/csv',
            ExportFormat.EXCEL: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            ExportFormat.JSON: 'application/json',
            ExportFormat.PDF: 'application/pdf',
        }
        return mime_types[self]

    def get_content_type(self) -> str:
        """Get Django content type for this format"""
        return self.get_mime_type()

    def requires_pandas(self) -> bool:
        """Check if format requires pandas for processing"""
        return self in {ExportFormat.EXCEL, ExportFormat.PDF}


class ExportStatus(Enum):
    """
    Enumeration of export process statuses.

    This follows the Single Responsibility Principle by providing
    a centralized status management system for export operations.
    """

    PENDING = 'PENDING'
    PREPARING = 'PREPARING'
    EXPORTING = 'EXPORTING'
    COMPRESSING = 'COMPRESSING'
    UPLOADING = 'UPLOADING'
    COMPLETED = 'COMPLETED'
    FAILED = 'FAILED'
    CANCELLED = 'CANCELLED'

    def is_active(self) -> bool:
        """Check if export is in an active state"""
        return self in {
            ExportStatus.PREPARING,
            ExportStatus.EXPORTING,
            ExportStatus.COMPRESSING,
            ExportStatus.UPLOADING
        }

    def is_completed(self) -> bool:
        """Check if export is in a completed state"""
        return self in {
            ExportStatus.COMPLETED,
            ExportStatus.FAILED,
            ExportStatus.CANCELLED
        }


class ExportProgress:
    """
    Class for tracking export progress.

    This follows the Single Responsibility Principle by focusing
    specifically on progress tracking functionality.
    """

    def __init__(self, total_items: int):
        self.total_items = total_items
        self.processed_items = 0
        self.current_stage = ExportStatus.PENDING
        self.start_time = timezone.now()
        self.updated_at = timezone.now()

    @property
    def percentage(self) -> float:
        """Calculate progress percentage"""
        if self.total_items == 0:
            return 100.0
        return min((self.processed_items / self.total_items) * 100, 100.0)

    def update(self, processed_items: Optional[int] = None, stage: Optional[ExportStatus] = None) -> None:
        """Update progress"""
        if processed_items is not None:
            self.processed_items = min(processed_items, self.total_items)
        if stage is not None:
            self.current_stage = stage
        self.updated_at = timezone.now()

    def add_items(self, count: int) -> None:
        """Add processed items"""
        self.update(self.processed_items + count)

    def complete(self) -> None:
        """Mark export as completed"""
        self.update(self.total_items, ExportStatus.COMPLETED)

    def get_eta(self) -> Optional[timedelta]:
        """Get estimated time remaining"""
        if self.processed_items == 0:
            return None

        elapsed = timezone.now() - self.start_time
        rate = self.processed_items / elapsed.total_seconds()
        remaining_items = self.total_items - self.processed_items

        if rate <= 0:
            return None

        eta_seconds = remaining_items / rate
        return timedelta(seconds=eta_seconds)


class DataExportTask(BaseTask):
    """
    Base class for data export tasks.

    This follows SOLID principles:
    - Single Responsibility: Handles export-specific functionality
    - Open/Closed: Extensible for different data types
    - Liskov Substitution: Compatible with BaseTask interface
    - Interface Segregation: Minimal, focused interface
    - Dependency Inversion: Depends on abstractions (ExportFormat, etc.)
    """

    # Task configuration
    name = 'data_export'
    queue = 'exports'
    soft_time_limit = 1800  # 30 minutes
    time_limit = 3600       # 1 hour
    max_retries = 2
    default_retry_delay = 300  # 5 minutes

    def __init__(self):
        super().__init__()
        self.max_file_size_mb = getattr(settings, 'MAX_EXPORT_SIZE_MB', 100)
        self.chunk_size = getattr(settings, 'EXPORT_CHUNK_SIZE', 1000)
        self.compression_enabled = getattr(settings, 'EXPORT_COMPRESSION_ENABLED', True)

    def execute(self, *args, **kwargs) -> Dict[str, Any]:
        """
        Main export execution method.

        This follows the Template Method pattern by defining the
        overall export process while allowing customization.
        """
        data = kwargs.get('data')
        format_type = ExportFormat(kwargs.get('format', 'CSV'))
        filename = kwargs.get('filename', 'export')
        requested_by = kwargs.get('requested_by')
        filters = kwargs.get('filters', {})
        fields = kwargs.get('fields', None)
        compress = kwargs.get('compress', self.compression_enabled)

        # Validate inputs
        self._validate_export_input(data, format_type, requested_by)

        # Get user
        try:
            user = User.objects.get(id=requested_by)
        except User.DoesNotExist:
            raise TaskValidationError(
                f"User with ID {requested_by} does not exist",
                field_name="requested_by",
                field_value=requested_by
            )

        # Initialize progress tracking
        progress = ExportProgress(len(data) if data else 0)
        self.set_task_status(TaskStatus.RUNNING, progress=0)

        try:
            # Prepare data
            self.set_task_status(TaskStatus.RUNNING, progress=10)
            prepared_data = self._prepare_data(data, filters, fields)

            # Export data
            self.set_task_status(TaskStatus.RUNNING, progress=30)
            export_result = self._export_data(prepared_data, format_type, filename, progress)

            # Compress if requested
            if compress and self._should_compress(export_result['file_size']):
                self.set_task_status(TaskStatus.RUNNING, progress=80)
                export_result = self._compress_export(export_result)

            # Generate download URL
            self.set_task_status(TaskStatus.RUNNING, progress=90)
            download_url = self._generate_download_url(export_result['file_path'])

            # Complete export
            self.set_task_status(TaskStatus.SUCCESS, progress=100)

            result = {
                'success': True,
                'format': format_type.value,
                'total_records': len(prepared_data),
                'file_size': export_result['file_size'],
                'file_path': export_result['file_path'],
                'download_url': download_url,
                'requested_by': user.username,
                'exported_at': timezone.now().isoformat(),
                'duration': (timezone.now() - progress.start_time).total_seconds(),
            }

            # Log successful export
            logger.info(
                f"Export completed successfully: {len(prepared_data)} records in {result['format']}",
                extra={
                    'task_id': self.task_id,
                    'user_id': requested_by,
                    'format': result['format'],
                    'record_count': result['total_records'],
                    'file_size_mb': result['file_size'] / (1024 * 1024)
                }
            )

            return result

        except Exception as e:
            self.set_task_status(TaskStatus.FAILURE)
            logger.error(
                f"Export failed: {str(e)}",
                extra={
                    'task_id': self.task_id,
                    'user_id': requested_by,
                    'error_type': e.__class__.__name__,
                    'error_message': str(e)
                }
            )
            raise TaskExecutionError(
                f"Export failed: {str(e)}",
                details={
                    'user_id': requested_by,
                    'format': format_type.value,
                    'error_type': e.__class__.__name__
                }
            )

    def _validate_export_input(
        self,
        data: Any,
        format_type: ExportFormat,
        requested_by: int
    ) -> None:
        """
        Validate export input parameters.

        This follows the Single Responsibility Principle by focusing
        specifically on input validation for export tasks.
        """
        if data is None:
            raise TaskValidationError(
                "Data for export is required",
                field_name="data",
                field_value=data
            )

        if not isinstance(format_type, ExportFormat):
            raise TaskValidationError(
                f"Invalid export format: {format_type}",
                field_name="format",
                field_value=format_type
            )

        if not requested_by or not isinstance(requested_by, int):
            raise TaskValidationError(
                "Valid user ID is required for export",
                field_name="requested_by",
                field_value=requested_by
            )

        # Check if pandas is available for Excel/PDF exports
        if format_type.requires_pandas():
            try:
                import pandas as pd
            except ImportError:
                raise TaskConfigurationError(
                    f"Export format {format_type.value} requires pandas but it's not installed",
                    config_key="PANDAS_AVAILABLE"
                )

    def _prepare_data(
        self,
        data: List[Dict[str, Any]],
        filters: Dict[str, Any],
        fields: Optional[List[str]]
    ) -> List[Dict[str, Any]]:
        """
        Prepare data for export by applying filters and field selection.

        This follows the Single Responsibility Principle by handling
        data preparation separately from export logic.
        """
        # Apply filters
        if filters:
            data = self._apply_filters(data, filters)

        # Select fields
        if fields:
            data = self._select_fields(data, fields)

        # Clean data (handle Decimal, datetime objects, etc.)
        data = self._clean_data_for_export(data)

        return data

    def _apply_filters(self, data: List[Dict[str, Any]], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Apply filters to data.

        This provides a simple filtering mechanism for export data.
        """
        if not filters or not data:
            return data

        filtered_data = []

        for item in data:
            match = True
            for field, filter_value in filters.items():
                if '__icontains' in field:
                    field_name = field.replace('__icontains', '')
                    item_value = str(item.get(field_name, '')).lower()
                    filter_str = str(filter_value).lower()
                    if filter_str not in item_value:
                        match = False
                        break
                elif '__in' in field:
                    field_name = field.replace('__in', '')
                    if item.get(field_name) not in filter_value:
                        match = False
                        break
                elif '__gt' in field:
                    field_name = field.replace('__gt', '')
                    if item.get(field_name) <= filter_value:
                        match = False
                        break
                elif '__lt' in field:
                    field_name = field.replace('__lt', '')
                    if item.get(field_name) >= filter_value:
                        match = False
                        break
                else:
                    if item.get(field) != filter_value:
                        match = False
                        break

            if match:
                filtered_data.append(item)

        return filtered_data

    def _select_fields(self, data: List[Dict[str, Any]], fields: List[str]) -> List[Dict[str, Any]]:
        """
        Select specific fields from data.

        This provides field selection functionality for exports.
        """
        if not fields or not data:
            return data

        selected_data = []
        for item in data:
            selected_item = {}
            for field in fields:
                if field in item:
                    selected_item[field] = item[field]
            selected_data.append(selected_item)

        return selected_data

    def _clean_data_for_export(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Clean data for export by handling special data types.

        This ensures that data is properly formatted for export formats.
        """
        cleaned_data = []

        for item in data:
            cleaned_item = {}
            for key, value in item.items():
                if isinstance(value, Decimal):
                    cleaned_item[key] = float(value)
                elif isinstance(value, datetime):
                    cleaned_item[key] = value.isoformat()
                elif value is None:
                    cleaned_item[key] = ''
                else:
                    cleaned_item[key] = str(value)
            cleaned_data.append(cleaned_item)

        return cleaned_data

    def _export_data(
        self,
        data: List[Dict[str, Any]],
        format_type: ExportFormat,
        filename: str,
        progress: ExportProgress
    ) -> Dict[str, Any]:
        """
        Export data in specified format.

        This follows the Strategy pattern by delegating to specific
        export methods based on format type.
        """
        # Generate filename
        export_filename = self._generate_filename(filename, format_type)
        file_path = self._get_temp_file_path(export_filename)

        try:
            if format_type == ExportFormat.CSV:
                result = self._export_to_csv(data, file_path, progress)
            elif format_type == ExportFormat.JSON:
                result = self._export_to_json(data, file_path)
            elif format_type == ExportFormat.EXCEL:
                result = self._export_to_excel(data, file_path, progress)
            elif format_type == ExportFormat.PDF:
                result = self._export_to_pdf(data, file_path, progress)
            else:
                raise TaskValidationError(
                    f"Unsupported export format: {format_type.value}",
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

    def _export_to_csv(
        self,
        data: List[Dict[str, Any]],
        file_path: str,
        progress: ExportProgress
    ) -> Dict[str, Any]:
        """
        Export data to CSV format.

        This follows the Single Responsibility Principle by focusing
        specifically on CSV export functionality.
        """
        if not data:
            raise TaskValidationError("No data to export")

        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = data[0].keys()
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            # Write header
            writer.writeheader()
            progress.current_stage = ExportStatus.EXPORTING

            # Write data rows
            for i, row in enumerate(data):
                writer.writerow(row)
                progress.add_items(1)

                # Update task progress periodically
                if i % self.chunk_size == 0:
                    progress_percentage = min((i / len(data)) * 50 + 30, 80)  # 30-80%
                    self.set_task_status(TaskStatus.RUNNING, progress=int(progress_percentage))

        return {'file_path': file_path, 'total_records': len(data)}

    def _export_to_json(self, data: List[Dict[str, Any]], file_path: str) -> Dict[str, Any]:
        """
        Export data to JSON format.

        This follows the Single Responsibility Principle by focusing
        specifically on JSON export functionality.
        """
        with open(file_path, 'w', encoding='utf-8') as jsonfile:
            json.dump(data, jsonfile, indent=2, ensure_ascii=False)

        return {'file_path': file_path, 'total_records': len(data)}

    def _export_to_excel(
        self,
        data: List[Dict[str, Any]],
        file_path: str,
        progress: ExportProgress
    ) -> Dict[str, Any]:
        """
        Export data to Excel format.

        This follows the Single Responsibility Principle by focusing
        specifically on Excel export functionality.
        """
        try:
            import pandas as pd
        except ImportError:
            raise TaskConfigurationError(
                "Excel export requires pandas but it's not installed",
                config_key="PANDAS_AVAILABLE"
            )

        if not data:
            raise TaskValidationError("No data to export")

        # Convert to DataFrame
        df = pd.DataFrame(data)

        # Create Excel writer
        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Export Data', index=False)

        progress.complete()

        return {'file_path': file_path, 'total_records': len(data)}

    def _export_to_pdf(
        self,
        data: List[Dict[str, Any]],
        file_path: str,
        progress: ExportProgress
    ) -> Dict[str, Any]:
        """
        Export data to PDF format.

        This follows the Single Responsibility Principle by focusing
        specifically on PDF export functionality.
        """
        # For now, we'll create a simple text-based PDF
        # In a production environment, you'd use ReportLab or similar
        raise TaskExecutionError(
            "PDF export not yet implemented",
            error_code="NOT_IMPLEMENTED",
            details={"format": "PDF"}
        )

    def _generate_filename(self, base_name: str, format_type: ExportFormat, user_id: Optional[int] = None) -> str:
        """
        Generate unique filename for export.

        This follows the Single Responsibility Principle by handling
        filename generation with proper sanitization.
        """
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        safe_name = slugify(base_name)

        if user_id:
            filename = f"{safe_name}_{user_id}_{timestamp}{format_type.get_extension()}"
        else:
            filename = f"{safe_name}_{timestamp}{format_type.get_extension()}"

        return filename

    def _get_temp_file_path(self, filename: str) -> str:
        """
        Get temporary file path for export.

        This ensures files are stored in the proper temp directory.
        """
        temp_dir = getattr(settings, 'EXPORT_TEMP_DIR', '/tmp')
        os.makedirs(temp_dir, exist_ok=True)
        return os.path.join(temp_dir, filename)

    def _should_compress(self, file_size: int) -> bool:
        """
        Determine if file should be compressed.

        This checks if file size exceeds compression threshold.
        """
        compression_threshold = getattr(settings, 'EXPORT_COMPRESSION_THRESHOLD_MB', 10) * 1024 * 1024
        return self.compression_enabled and file_size > compression_threshold

    def _compress_export(self, export_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compress exported file.

        This follows the Single Responsibility Principle by handling
        file compression separately from export logic.
        """
        original_path = export_result['file_path']
        compressed_path = original_path + '.zip'

        try:
            with zipfile.ZipFile(compressed_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(original_path, os.path.basename(original_path))

            # Remove original file
            os.remove(original_path)

            # Update result
            compressed_size = os.path.getsize(compressed_path)
            export_result.update({
                'file_path': compressed_path,
                'file_size': compressed_size,
                'compressed': True,
                'compression_ratio': (1 - compressed_size / export_result['file_size']) * 100
            })

            return export_result

        except Exception as e:
            # Remove compressed file if it exists
            if os.path.exists(compressed_path):
                os.remove(compressed_path)
            raise TaskExecutionError(
                f"Failed to compress export file: {str(e)}",
                error_code="COMPRESSION_ERROR"
            )

    def _generate_download_url(self, file_path: str) -> str:
        """
        Generate download URL for exported file.

        This provides a secure way for users to download their exports.
        """
        # In a real implementation, this would generate a secure, time-limited URL
        # For now, we'll return a basic URL
        filename = os.path.basename(file_path)
        return f"/api/v1/exports/download/{filename}/"

    def export_data(self, *args, **kwargs) -> Dict[str, Any]:
        """Public method for data export"""
        return self.execute(*args, **kwargs)


@shared_task(bind=True, base=DataExportTask, name='export_contacts')
class ContactsExportTask(DataExportTask):
    """
    Task for exporting contacts data.

    This follows the Single Responsibility Principle by focusing
    specifically on contact export functionality.
    """

    def execute(self, *args, **kwargs) -> Dict[str, Any]:
        """
        Export contacts data.

        Args:
            format: Export format (CSV, EXCEL, JSON, PDF)
            requested_by: User ID requesting the export
            filters: Optional filters to apply
            fields: Optional fields to include

        Returns:
            Dict[str, Any]: Export result with download information
        """
        try:
            from ..repositories.contact_repository import ContactRepository

            # Get contacts data
            repo = ContactRepository()
            contacts = repo.get_all()

            # Convert to list of dicts
            contacts_data = []
            for contact in contacts:
                contacts_data.append({
                    'id': contact.id,
                    'first_name': contact.first_name,
                    'last_name': contact.last_name,
                    'email': contact.email,
                    'phone': contact.phone,
                    'company': contact.company,
                    'job_title': contact.job_title,
                    'address': contact.address,
                    'city': contact.city,
                    'country': contact.country,
                    'created_at': contact.created_at,
                    'updated_at': contact.updated_at,
                })

            # Add contact-specific data to kwargs
            kwargs['data'] = contacts_data

            # Call parent export method
            result = super().execute(*args, **kwargs)
            result['export_type'] = 'contacts'

            return result

        except Exception as e:
            raise TaskExecutionError(
                f"Failed to export contacts: {str(e)}",
                error_code="CONTACTS_EXPORT_ERROR",
                details={'original_error': str(e)}
            )

    def export_contacts(self, **kwargs) -> Dict[str, Any]:
        """Public method for contacts export"""
        return self.execute(**kwargs)


@shared_task(bind=True, base=DataExportTask, name='export_deals')
class DealsExportTask(DataExportTask):
    """
    Task for exporting deals data.

    This follows the Single Responsibility Principle by focusing
    specifically on deal export functionality.
    """

    def execute(self, *args, **kwargs) -> Dict[str, Any]:
        """
        Export deals data.

        Returns:
            Dict[str, Any]: Export result with download information
        """
        try:
            from ..repositories.deal_repository import DealRepository

            # Get deals data
            repo = DealRepository()
            deals = repo.get_all()

            # Convert to list of dicts
            deals_data = []
            for deal in deals:
                deals_data.append({
                    'id': deal.id,
                    'title': deal.title,
                    'description': deal.description,
                    'value': float(deal.value) if deal.value else 0,
                    'stage': deal.stage,
                    'probability': deal.probability,
                    'expected_close_date': deal.expected_close_date.isoformat() if deal.expected_close_date else None,
                    'actual_close_date': deal.actual_close_date.isoformat() if deal.actual_close_date else None,
                    'assigned_to_id': deal.assigned_to.id if deal.assigned_to else None,
                    'assigned_to_name': deal.assigned_to.get_full_name() if deal.assigned_to else None,
                    'contact_id': deal.contact.id if deal.contact else None,
                    'contact_name': f"{deal.contact.first_name} {deal.contact.last_name}" if deal.contact else None,
                    'created_at': deal.created_at,
                    'updated_at': deal.updated_at,
                })

            # Add deal-specific data to kwargs
            kwargs['data'] = deals_data

            # Call parent export method
            result = super().execute(*args, **kwargs)
            result['export_type'] = 'deals'

            return result

        except Exception as e:
            raise TaskExecutionError(
                f"Failed to export deals: {str(e)}",
                error_code="DEALS_EXPORT_ERROR",
                details={'original_error': str(e)}
            )

    def export_deals(self, **kwargs) -> Dict[str, Any]:
        """Public method for deals export"""
        return self.execute(**kwargs)


@shared_task(bind=True, base=DataExportTask, name='export_activities')
class ActivitiesExportTask(DataExportTask):
    """
    Task for exporting activities data.

    This follows the Single Responsibility Principle by focusing
    specifically on activity export functionality.
    """

    def execute(self, *args, **kwargs) -> Dict[str, Any]:
        """
        Export activities data.

        Returns:
            Dict[str, Any]: Export result with download information
        """
        try:
            from ..repositories.activity_repository import ActivityRepository

            # Get activities data
            repo = ActivityRepository()
            activities = repo.get_all()

            # Convert to list of dicts
            activities_data = []
            for activity in activities:
                activities_data.append({
                    'id': activity.id,
                    'title': activity.title,
                    'description': activity.description,
                    'type': activity.type,
                    'priority': activity.priority,
                    'status': activity.status,
                    'due_date': activity.due_date.isoformat() if activity.due_date else None,
                    'completed_date': activity.completed_date.isoformat() if activity.completed_date else None,
                    'assigned_to_id': activity.assigned_to.id if activity.assigned_to else None,
                    'assigned_to_name': activity.assigned_to.get_full_name() if activity.assigned_to else None,
                    'contact_id': activity.contact.id if activity.contact else None,
                    'contact_name': f"{activity.contact.first_name} {activity.contact.last_name}" if activity.contact else None,
                    'deal_id': activity.deal.id if activity.deal else None,
                    'deal_title': activity.deal.title if activity.deal else None,
                    'created_at': activity.created_at,
                    'updated_at': activity.updated_at,
                })

            # Add activity-specific data to kwargs
            kwargs['data'] = activities_data

            # Call parent export method
            result = super().execute(*args, **kwargs)
            result['export_type'] = 'activities'

            return result

        except Exception as e:
            raise TaskExecutionError(
                f"Failed to export activities: {str(e)}",
                error_code="ACTIVITIES_EXPORT_ERROR",
                details={'original_error': str(e)}
            )

    def export_activities(self, **kwargs) -> Dict[str, Any]:
        """Public method for activities export"""
        return self.execute(**kwargs)


@shared_task(bind=True, base=DataExportTask, name='export_users')
class UsersExportTask(DataExportTask):
    """
    Task for exporting users data (admin only).

    This follows the Single Responsibility Principle by focusing
    specifically on user export functionality with permission checks.
    """

    def execute(self, *args, **kwargs) -> Dict[str, Any]:
        """
        Export users data (admin only).

        Returns:
            Dict[str, Any]: Export result with download information
        """
        try:
            # Check if user has admin permissions
            requested_by = kwargs.get('requested_by')
            if not requested_by:
                raise TaskValidationError(
                    "User ID is required for users export",
                    field_name="requested_by",
                    field_value=requested_by
                )

            try:
                user = User.objects.get(id=requested_by)
                if not user.is_staff and not user.is_superuser:
                    raise TaskValidationError(
                        "Only administrators can export user data",
                        field_name="permissions",
                        field_value=user.is_staff
                    )
            except User.DoesNotExist:
                raise TaskValidationError(
                    f"User with ID {requested_by} does not exist",
                    field_name="requested_by",
                    field_value=requested_by
                )

            from ..repositories.user_repository import UserRepository

            # Get users data
            repo = UserRepository()
            users = repo.get_all()

            # Convert to list of dicts (exclude sensitive data)
            users_data = []
            for user_obj in users:
                users_data.append({
                    'id': user_obj.id,
                    'username': user_obj.username,
                    'email': user_obj.email,
                    'first_name': user_obj.first_name,
                    'last_name': user_obj.last_name,
                    'role': getattr(user_obj, 'role', 'User'),
                    'is_active': user_obj.is_active,
                    'is_staff': user_obj.is_staff,
                    'date_joined': user_obj.date_joined,
                    'last_login': user_obj.last_login,
                })

            # Add user-specific data to kwargs
            kwargs['data'] = users_data

            # Call parent export method
            result = super().execute(*args, **kwargs)
            result['export_type'] = 'users'

            return result

        except TaskValidationError:
            raise
        except Exception as e:
            raise TaskExecutionError(
                f"Failed to export users: {str(e)}",
                error_code="USERS_EXPORT_ERROR",
                details={'original_error': str(e)}
            )

    def export_users(self, **kwargs) -> Dict[str, Any]:
        """Public method for users export"""
        return self.execute(**kwargs)