"""
Custom Exceptions for CRM System
Following SOLID principles and enterprise best practices
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass


@dataclass
class ErrorDetail:
    """Error detail for structured error responses"""
    field: Optional[str] = None
    message: str = ""
    code: Optional[str] = None
    params: Optional[Dict[str, Any]] = None


class CRMException(Exception):
    """
    Base exception for all CRM-related errors
    Following SOLID Single Responsibility Principle
    """

    def __init__(self, message: str, error_code: Optional[str] = None,
                 details: Optional[List[ErrorDetail]] = None,
                 context: Optional[Dict[str, Any]] = None):
        """
        Initialize CRM exception

        Args:
            message: Error message
            error_code: Unique error code
            details: List of error details
            context: Additional context information
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or []
        self.context = context or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses"""
        return {
            'error': self.error_code,
            'message': self.message,
            'details': [
                {
                    'field': detail.field,
                    'message': detail.message,
                    'code': detail.code,
                    'params': detail.params
                }
                for detail in self.details
            ],
            'context': self.context
        }


class ValidationError(CRMException):
    """Exception raised when data validation fails"""

    def __init__(self, message: str, field: Optional[str] = None,
                 error_code: Optional[str] = None,
                 params: Optional[Dict[str, Any]] = None):
        """
        Initialize validation error

        Args:
            message: Error message
            field: Field that failed validation
            error_code: Specific error code
            params: Additional parameters
        """
        super().__init__(message, error_code or "VALIDATION_ERROR")
        self.field = field
        self.params = params or {}

        if field:
            self.details.append(ErrorDetail(
                field=field,
                message=message,
                code=error_code,
                params=self.params
            ))


class AuthenticationError(CRMException):
    """Exception raised when authentication fails"""

    def __init__(self, message: str = "Authentication failed", error_code: Optional[str] = None):
        super().__init__(message, error_code or "AUTHENTICATION_ERROR")


class AuthorizationError(CRMException):
    """Exception raised when user doesn't have permission"""

    def __init__(self, message: str = "Access denied", required_permission: Optional[str] = None):
        super().__init__(message, "AUTHORIZATION_ERROR")
        if required_permission:
            self.context['required_permission'] = required_permission


class NotFoundError(CRMException):
    """Exception raised when requested resource is not found"""

    def __init__(self, message: str, resource_type: str = "resource", resource_id: Optional[str] = None):
        super().__init__(message, "NOT_FOUND")
        self.context.update({
            'resource_type': resource_type,
            'resource_id': resource_id
        })


class ConflictError(CRMException):
    """Exception raised when business rule conflict occurs"""

    def __init__(self, message: str, conflict_type: Optional[str] = None,
                 conflicting_values: Optional[Dict[str, Any]] = None):
        super().__init__(message, "CONFLICT_ERROR")
        if conflict_type:
            self.context['conflict_type'] = conflict_type
        if conflicting_values:
            self.context['conflicting_values'] = conflicting_values


class BusinessLogicError(CRMException):
    """Exception raised when business logic rule is violated"""

    def __init__(self, message: str, rule_name: Optional[str] = None,
                 rule_params: Optional[Dict[str, Any]] = None):
        super().__init__(message, "BUSINESS_LOGIC_ERROR")
        if rule_name:
            self.context['rule_name'] = rule_name
        if rule_params:
            self.context['rule_params'] = rule_params


class ExternalServiceError(CRMException):
    """Exception raised when external service call fails"""

    def __init__(self, message: str, service_name: str,
                 status_code: Optional[int] = None,
                 response_data: Optional[Dict[str, Any]] = None):
        super().__init__(message, "EXTERNAL_SERVICE_ERROR")
        self.context.update({
            'service_name': service_name,
            'status_code': status_code,
            'response_data': response_data
        })


class DatabaseError(CRMException):
    """Exception raised when database operation fails"""

    def __init__(self, message: str, operation: Optional[str] = None,
                 query_params: Optional[Dict[str, Any]] = None):
        super().__init__(message, "DATABASE_ERROR")
        if operation:
            self.context['operation'] = operation
        if query_params:
            self.context['query_params'] = query_params


class ConfigurationError(CRMException):
    """Exception raised when configuration is invalid"""

    def __init__(self, message: str, config_key: Optional[str] = None,
                 expected_value: Optional[Any] = None):
        super().__init__(message, "CONFIGURATION_ERROR")
        if config_key:
            self.context['config_key'] = config_key
        if expected_value:
            self.context['expected_value'] = str(expected_value)


class RateLimitError(CRMException):
    """Exception raised when rate limit is exceeded"""

    def __init__(self, message: str, limit: Optional[int] = None,
                 window_seconds: Optional[int] = None,
                 retry_after: Optional[int] = None):
        super().__init__(message, "RATE_LIMIT_ERROR")
        if limit:
            self.context['limit'] = limit
        if window_seconds:
            self.context['window_seconds'] = window_seconds
        if retry_after:
            self.context['retry_after'] = retry_after


class FileUploadError(CRMException):
    """Exception raised when file upload fails"""

    def __init__(self, message: str, file_name: Optional[str] = None,
                 file_size: Optional[int] = None,
                 allowed_types: Optional[List[str]] = None):
        super().__init__(message, "FILE_UPLOAD_ERROR")
        if file_name:
            self.context['file_name'] = file_name
        if file_size:
            self.context['file_size'] = file_size
        if allowed_types:
            self.context['allowed_types'] = allowed_types


class IntegrationError(CRMException):
    """Exception raised when third-party integration fails"""

    def __init__(self, message: str, integration_name: str,
                 error_code: Optional[str] = None,
                 error_details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "INTEGRATION_ERROR")
        self.context.update({
            'integration_name': integration_name,
            'integration_error_code': error_code,
            'integration_error_details': error_details
        })


class EmailError(CRMException):
    """Exception raised when email sending fails"""

    def __init__(self, message: str, recipient: Optional[str] = None,
                 email_type: Optional[str] = None,
                 smtp_error: Optional[str] = None):
        super().__init__(message, "EMAIL_ERROR")
        if recipient:
            self.context['recipient'] = recipient
        if email_type:
            self.context['email_type'] = email_type
        if smtp_error:
            self.context['smtp_error'] = smtp_error


class CacheError(CRMException):
    """Exception raised when cache operation fails"""

    def __init__(self, message: str, operation: Optional[str] = None,
                 cache_key: Optional[str] = None):
        super().__init__(message, "CACHE_ERROR")
        if operation:
            self.context['operation'] = operation
        if cache_key:
            self.context['cache_key'] = cache_key


class TaskExecutionError(CRMException):
    """Exception raised when background task execution fails"""

    def __init__(self, message: str, task_name: Optional[str] = None,
                 task_id: Optional[str] = None,
                 retry_count: Optional[int] = None):
        super().__init__(message, "TASK_EXECUTION_ERROR")
        if task_name:
            self.context['task_name'] = task_name
        if task_id:
            self.context['task_id'] = task_id
        if retry_count:
            self.context['retry_count'] = retry_count


# Exception handler utilities
def handle_django_validation_error(django_error, field_mapping: Optional[Dict[str, str]] = None) -> ValidationError:
    """
    Convert Django ValidationError to CRM ValidationError

    Args:
        django_error: Django ValidationError instance
        field_mapping: Optional mapping of field names

    Returns:
        CRM ValidationError with details
    """
    details = []
    field_mapping = field_mapping or {}

    if hasattr(django_error, 'error_dict'):
        # Handle form validation errors
        for field, field_errors in django_error.error_dict.items():
            mapped_field = field_mapping.get(field, field)
            for error in field_errors:
                details.append(ErrorDetail(
                    field=mapped_field,
                    message=str(error.message),
                    code=error.code,
                    params=error.params
                ))
    else:
        # Handle model validation errors
        if hasattr(django_error, 'error_dict'):
            for field, field_errors in django_error.error_dict.items():
                mapped_field = field_mapping.get(field, field)
                for error in field_errors:
                    details.append(ErrorDetail(
                        field=mapped_field,
                        message=str(error.message),
                        code=error.code,
                        params=error.params
                    ))
        else:
            # Single error message
            details.append(ErrorDetail(
                message=str(django_error.message),
                code=getattr(django_error, 'code', None),
                params=getattr(django_error, 'params', None)
            ))

    return ValidationError(
        message="Validation failed",
        error_code="VALIDATION_ERROR",
        details=details
    )


def create_not_found_error(resource_type: str, identifier: Any, field_name: str = "id") -> NotFoundError:
    """
    Create a standardized NotFoundError

    Args:
        resource_type: Type of resource
        identifier: Resource identifier
        field_name: Name of the identifier field

    Returns:
        NotFoundError instance
    """
    return NotFoundError(
        message=f"{resource_type.title()} with {field_name} '{identifier}' not found",
        resource_type=resource_type,
        resource_id=str(identifier)
    )


def create_permission_error(action: str, resource_type: str) -> AuthorizationError:
    """
    Create a standardized permission error

    Args:
        action: Action being attempted
        resource_type: Type of resource

    Returns:
        AuthorizationError instance
    """
    return AuthorizationError(
        message=f"You don't have permission to {action} {resource_type}",
        required_permission=f"{action}_{resource_type}"
    )