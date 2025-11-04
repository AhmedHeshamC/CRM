"""
Custom Exception Classes for Background Tasks
Following SOLID principles and comprehensive error handling
"""

from typing import Dict, Any, Optional
from enum import Enum


class TaskExecutionError(Exception):
    """
    Base exception class for all task-related errors.

    This follows the Exception Composition pattern from SOLID principles,
    providing structured error information for better error handling and debugging.
    """

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None
    ):
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.error_code = error_code or self._get_default_error_code()

    def _get_default_error_code(self) -> str:
        """Get default error code based on exception class name"""
        return f"{self.__class__.__name__.upper().replace('ERROR', '_ERROR')}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for serialization"""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "error_code": self.error_code,
            "details": self.details
        }


class TaskTimeoutError(TaskExecutionError):
    """
    Exception raised when a task exceeds its time limit.

    This follows the Single Responsibility Principle by specifically handling
    timeout-related errors with detailed timing information.
    """

    def __init__(
        self,
        timeout_seconds: int,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.timeout_seconds = timeout_seconds
        if message is None:
            message = f"Task timed out after {timeout_seconds} seconds"
        super().__init__(message, details, "TIMEOUT_ERROR")


class TaskRetryError(TaskExecutionError):
    """
    Exception raised when a task fails but can be retried.

    This encapsulates retry logic and provides information about retry attempts,
    following the Single Responsibility Principle for retry-specific errors.
    """

    def __init__(
        self,
        retry_count: int,
        max_retries: int = 3,
        backoff_delay: Optional[int] = None,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.retry_count = retry_count
        self.max_retries = max_retries
        self.backoff_delay = backoff_delay

        if message is None:
            if backoff_delay:
                message = f"Task retry {retry_count} of {max_retries}, retry in {backoff_delay} seconds"
            else:
                message = f"Task retry {retry_count} of {max_retries}"

        retry_details = {
            "retry_count": retry_count,
            "max_retries": max_retries,
            "is_max_retries_exceeded": retry_count >= max_retries
        }

        if backoff_delay:
            retry_details["backoff_delay"] = backoff_delay

        if details:
            retry_details.update(details)

        super().__init__(message, retry_details, "RETRY_ERROR")

    def is_max_retries_exceeded(self) -> bool:
        """Check if maximum retry attempts have been exceeded"""
        return self.retry_count >= self.max_retries


class TaskValidationError(TaskExecutionError):
    """
    Exception raised when task input validation fails.

    This follows the Single Responsibility Principle by handling validation-specific
    errors with detailed field-level information.
    """

    def __init__(
        self,
        message: str,
        field_name: Optional[str] = None,
        field_value: Optional[Any] = None,
        field_errors: Optional[Dict[str, list]] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.field_name = field_name
        self.field_value = field_value
        self.field_errors = field_errors or {}

        validation_details = {"field_errors": self.field_errors}

        if field_name:
            validation_details["field_name"] = field_name
            if field_value is not None:
                validation_details["field_value"] = field_value

            if not message:
                message = f"Validation failed for field '{field_name}'"

        if details:
            validation_details.update(details)

        super().__init__(message, validation_details, "VALIDATION_ERROR")


class TaskConfigurationError(TaskExecutionError):
    """
    Exception raised when task configuration is invalid or missing.

    This follows the Single Responsibility Principle by handling configuration-
    specific errors with detailed configuration context.
    """

    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        config_keys: Optional[list] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.config_key = config_key
        self.config_keys = config_keys or []

        config_details = {"missing_configs": self.config_keys}

        if config_key:
            config_details["config_key"] = config_key

        if details:
            config_details.update(details)

        super().__init__(message, config_details, "CONFIGURATION_ERROR")


class TaskResourceError(TaskExecutionError):
    """
    Exception raised when task encounters resource constraints.

    This follows the Single Responsibility Principle by handling resource-specific
    errors with detailed resource usage information.
    """

    def __init__(
        self,
        message: str,
        resource_type: str,
        current_usage: Optional[str] = None,
        limit: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.resource_type = resource_type
        self.current_usage = current_usage
        self.limit = limit

        resource_details = {
            "resource_type": resource_type
        }

        if current_usage:
            resource_details["current_usage"] = current_usage
        if limit:
            resource_details["limit"] = limit

        if details:
            resource_details.update(details)

        super().__init__(message, resource_details, "RESOURCE_ERROR")


class TaskErrorCodes(Enum):
    """
    Enumeration of all possible task error codes.

    This follows the Open/Closed Principle by allowing extension of error codes
    without modifying existing code, and provides a centralized error code registry.
    """

    EXECUTION_ERROR = "EXECUTION_ERROR"
    TIMEOUT_ERROR = "TIMEOUT_ERROR"
    RETRY_ERROR = "RETRY_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    RESOURCE_ERROR = "RESOURCE_ERROR"
    NETWORK_ERROR = "NETWORK_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    EMAIL_ERROR = "EMAIL_ERROR"
    EXPORT_ERROR = "EXPORT_ERROR"
    REPORT_ERROR = "REPORT_ERROR"
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    AUTHORIZATION_ERROR = "AUTHORIZATION_ERROR"
    QUEUE_ERROR = "QUEUE_ERROR"
    WORKER_ERROR = "WORKER_ERROR"

    @classmethod
    def has_value(cls, value: str) -> bool:
        """Check if error code exists in enumeration"""
        return any(error_code.value == value for error_code in cls)

    @classmethod
    def get_all_codes(cls) -> list:
        """Get all available error codes"""
        return [error_code.value for error_code in cls]


class TaskExceptionFactory:
    """
    Factory class for creating task exceptions.

    This follows the Factory Method pattern from SOLID principles,
    providing a centralized way to create exceptions with consistent formatting.
    """

    @staticmethod
    def create_timeout_error(timeout_seconds: int, context: Optional[str] = None) -> TaskTimeoutError:
        """Create a timeout error with optional context"""
        message = f"Task timed out after {timeout_seconds} seconds"
        if context:
            message += f" during {context}"

        return TaskTimeoutError(
            timeout_seconds=timeout_seconds,
            message=message,
            details={"context": context} if context else None
        )

    @staticmethod
    def create_validation_error(
        field_name: str,
        field_value: Any,
        validation_message: str
    ) -> TaskValidationError:
        """Create a validation error for a specific field"""
        return TaskValidationError(
            message=validation_message,
            field_name=field_name,
            field_value=field_value
        )

    @staticmethod
    def create_resource_error(
        resource_type: str,
        current_usage: str,
        limit: str,
        operation: Optional[str] = None
    ) -> TaskResourceError:
        """Create a resource error with usage details"""
        message = f"Insufficient {resource_type} resource: {current_usage} used, limit is {limit}"
        if operation:
            message += f" during {operation}"

        return TaskResourceError(
            message=message,
            resource_type=resource_type,
            current_usage=current_usage,
            limit=limit,
            details={"operation": operation} if operation else None
        )

    @staticmethod
    def create_config_error(
        missing_configs: list,
        operation: Optional[str] = None
    ) -> TaskConfigurationError:
        """Create a configuration error for missing settings"""
        if len(missing_configs) == 1:
            message = f"Missing required configuration: {missing_configs[0]}"
        else:
            message = f"Missing required configurations: {', '.join(missing_configs)}"

        if operation:
            message += f" for {operation}"

        return TaskConfigurationError(
            message=message,
            config_keys=missing_configs,
            details={"operation": operation} if operation else None
        )