"""
Test suite for Task Exception Classes
Following TDD principles and comprehensive error handling
"""

import pytest
from django.test import TestCase
from ..exceptions import (
    TaskExecutionError,
    TaskTimeoutError,
    TaskRetryError,
    TaskValidationError,
    TaskConfigurationError,
    TaskResourceError,
)


class TestTaskExecutionError(TestCase):
    """Test the TaskExecutionError for general task failures"""

    def test_task_execution_error_creation(self):
        """Test TaskExecutionError creation with message"""
        error = TaskExecutionError("Task execution failed")
        self.assertEqual(str(error), "Task execution failed")
        self.assertEqual(error.message, "Task execution failed")

    def test_task_execution_error_with_details(self):
        """Test TaskExecutionError with additional details"""
        details = {"error_code": "EXEC_FAILED", "context": "data processing"}
        error = TaskExecutionError("Task failed", details=details)

        self.assertEqual(error.details, details)
        self.assertEqual(error.error_code, "EXEC_FAILED")

    def test_task_execution_error_with_error_code(self):
        """Test TaskExecutionError with specific error code"""
        error = TaskExecutionError("Validation failed", error_code="VALIDATION_ERROR")
        self.assertEqual(error.error_code, "VALIDATION_ERROR")

    def test_task_execution_error_serialization(self):
        """Test TaskExecutionError can be serialized to dict"""
        details = {"step": "processing", "item_count": 100}
        error = TaskExecutionError("Processing failed", details=details, error_code="PROC_ERROR")

        error_dict = error.to_dict()
        expected = {
            "error_type": "TaskExecutionError",
            "message": "Processing failed",
            "error_code": "PROC_ERROR",
            "details": details
        }

        self.assertEqual(error_dict, expected)


class TestTaskTimeoutError(TestCase):
    """Test the TaskTimeoutError for timeout handling"""

    def test_task_timeout_error_creation(self):
        """Test TaskTimeoutError creation with timeout duration"""
        error = TaskTimeoutError(timeout_seconds=300)

        self.assertEqual(error.timeout_seconds, 300)
        self.assertIn("Task timed out after 300 seconds", str(error))

    def test_task_timeout_error_with_custom_message(self):
        """Test TaskTimeoutError with custom message"""
        error = TaskTimeoutError(timeout_seconds=600, message="Custom timeout message")

        self.assertEqual(str(error), "Custom timeout message")
        self.assertEqual(error.timeout_seconds, 600)

    def test_task_timeout_error_inheritance(self):
        """Test TaskTimeoutError inherits from TaskExecutionError"""
        error = TaskTimeoutError(timeout_seconds=120)

        self.assertIsInstance(error, TaskExecutionError)


class TestTaskRetryError(TestCase):
    """Test the TaskRetryError for retry logic"""

    def test_task_retry_error_creation(self):
        """Test TaskRetryError creation with retry count"""
        error = TaskRetryError(retry_count=3, max_retries=5)

        self.assertEqual(error.retry_count, 3)
        self.assertEqual(error.max_retries, 5)
        self.assertIn("Task retry 3 of 5", str(error))

    def test_task_retry_error_with_backoff_delay(self):
        """Test TaskRetryError with backoff delay"""
        error = TaskRetryError(retry_count=2, backoff_delay=60)

        self.assertEqual(error.backoff_delay, 60)
        self.assertIn("retry in 60 seconds", str(error))

    def test_task_retry_error_max_retries_exceeded(self):
        """Test TaskRetryError when max retries exceeded"""
        error = TaskRetryError(retry_count=5, max_retries=5)

        self.assertTrue(error.is_max_retries_exceeded())

    def test_task_retry_error_not_max_retries(self):
        """Test TaskRetryError when max retries not exceeded"""
        error = TaskRetryError(retry_count=2, max_retries=5)

        self.assertFalse(error.is_max_retries_exceeded())


class TestTaskValidationError(TestCase):
    """Test the TaskValidationError for input validation"""

    def test_task_validation_error_creation(self):
        """Test TaskValidationError creation with field errors"""
        field_errors = {
            "email": ["Invalid email format"],
            "phone": ["Phone number too short"]
        }
        error = TaskValidationError("Validation failed", field_errors=field_errors)

        self.assertEqual(error.field_errors, field_errors)
        self.assertEqual(error.message, "Validation failed")

    def test_task_validation_error_with_field_name(self):
        """Test TaskValidationError for single field"""
        error = TaskValidationError("Invalid value", field_name="age", field_value="-5")

        self.assertEqual(error.field_name, "age")
        self.assertEqual(error.field_value, "-5")
        self.assertIn("field 'age'", str(error))

    def test_task_validation_error_serialization(self):
        """Test TaskValidationError serialization"""
        field_errors = {"amount": ["Amount must be positive"]}
        error = TaskValidationError("Invalid amount", field_errors=field_errors)

        error_dict = error.to_dict()
        self.assertEqual(error_dict["field_errors"], field_errors)


class TestTaskConfigurationError(TestCase):
    """Test the TaskConfigurationError for setup issues"""

    def test_task_configuration_error_creation(self):
        """Test TaskConfigurationError creation"""
        error = TaskConfigurationError("Missing required configuration", config_key="EMAIL_HOST")

        self.assertEqual(error.config_key, "EMAIL_HOST")
        self.assertIn("EMAIL_HOST", str(error))

    def test_task_configuration_error_with_multiple_keys(self):
        """Test TaskConfigurationError with multiple missing keys"""
        error = TaskConfigurationError(
            "Missing email configuration",
            config_keys=["EMAIL_HOST", "EMAIL_PORT", "EMAIL_USER"]
        )

        self.assertEqual(error.config_keys, ["EMAIL_HOST", "EMAIL_PORT", "EMAIL_USER"])

    def test_task_configuration_error_inheritance(self):
        """Test TaskConfigurationError inheritance"""
        error = TaskConfigurationError("Config error")

        self.assertIsInstance(error, TaskExecutionError)


class TestTaskResourceError(TestCase):
    """Test the TaskResourceError for resource issues"""

    def test_task_resource_error_creation(self):
        """Test TaskResourceError creation"""
        error = TaskResourceError(
            "Insufficient memory",
            resource_type="memory",
            current_usage="8GB",
            limit="4GB"
        )

        self.assertEqual(error.resource_type, "memory")
        self.assertEqual(error.current_usage, "8GB")
        self.assertEqual(error.limit, "4GB")
        self.assertIn("memory resource", str(error))

    def test_task_resource_error_for_disk_space(self):
        """Test TaskResourceError for disk space"""
        error = TaskResourceError(
            "Insufficient disk space",
            resource_type="disk",
            current_usage="95%",
            limit="80%"
        )

        self.assertEqual(error.resource_type, "disk")

    def test_task_resource_error_for_database(self):
        """Test TaskResourceError for database connections"""
        error = TaskResourceError(
            "Database connection pool exhausted",
            resource_type="database_connections",
            current_usage="100",
            limit="50"
        )

        self.assertEqual(error.resource_type, "database_connections")

    def test_task_resource_error_inheritance(self):
        """Test TaskResourceError inheritance"""
        error = TaskResourceError("Resource error")

        self.assertIsInstance(error, TaskExecutionError)


class TestTaskExceptionIntegration(TestCase):
    """Test integration between different task exceptions"""

    def test_exception_hierarchy(self):
        """Test that all task exceptions inherit from TaskExecutionError"""
        exceptions = [
            TaskTimeoutError(timeout_seconds=300),
            TaskRetryError(retry_count=1),
            TaskValidationError("Validation error"),
            TaskConfigurationError("Config error"),
            TaskResourceError("Resource error")
        ]

        for exception in exceptions:
            self.assertIsInstance(exception, TaskExecutionError)

    def test_exception_error_codes(self):
        """Test that all exceptions have proper error codes"""
        test_cases = [
            (TaskExecutionError("Test"), "EXECUTION_ERROR"),
            (TaskTimeoutError(timeout_seconds=300), "TIMEOUT_ERROR"),
            (TaskRetryError(retry_count=1), "RETRY_ERROR"),
            (TaskValidationError("Validation error"), "VALIDATION_ERROR"),
            (TaskConfigurationError("Config error"), "CONFIGURATION_ERROR"),
            (TaskResourceError("Resource error"), "RESOURCE_ERROR")
        ]

        for exception, expected_code in test_cases:
            self.assertEqual(exception.error_code, expected_code)

    def test_exception_to_dict_consistency(self):
        """Test that all exceptions have consistent to_dict format"""
        exceptions = [
            TaskExecutionError("Test error", details={"test": "value"}),
            TaskTimeoutError(timeout_seconds=300),
            TaskRetryError(retry_count=2, max_retries=5),
            TaskValidationError("Validation error", field_errors={"field": ["error"]}),
            TaskConfigurationError("Config error", config_key="TEST_KEY"),
            TaskResourceError("Resource error", resource_type="memory")
        ]

        for exception in exceptions:
            error_dict = exception.to_dict()

            # Check required fields
            self.assertIn("error_type", error_dict)
            self.assertIn("message", error_dict)
            self.assertIn("error_code", error_dict)

            # Check that error_type matches class name
            self.assertEqual(error_dict["error_type"], exception.__class__.__name__)

            # Check that message matches
            self.assertEqual(error_dict["message"], str(exception))