"""
Security Exceptions for the CRM Application
Following SOLID principles and enterprise-grade exception handling
"""

from typing import Dict, Any, Optional


class SecurityError(Exception):
    """
    Base Security Exception Class
    Following Single Responsibility Principle for security error handling
    """

    def __init__(self, message: str, code: str = "security_error", details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)


class RateLimitExceededError(SecurityError):
    """
    Exception raised when rate limit is exceeded
    Following Single Responsibility Principle
    """

    def __init__(self, message: str = "Rate limit exceeded", retry_after: int = 60, **kwargs):
        self.retry_after = retry_after
        super().__init__(
            message=message,
            code="rate_limit_exceeded",
            details={"retry_after": retry_after, **kwargs}
        )


class InputValidationError(SecurityError):
    """
    Exception raised for input validation failures
    Following Single Responsibility Principle
    """

    def __init__(self, message: str = "Input validation failed", field: str = None, **kwargs):
        self.field = field
        super().__init__(
            message=message,
            code="input_validation_error",
            details={"field": field, **kwargs}
        )


class SQLInjectionAttemptError(SecurityError):
    """
    Exception raised for SQL injection attempts
    Following Single Responsibility Principle
    """

    def __init__(self, message: str = "SQL injection attempt detected", **kwargs):
        super().__init__(
            message=message,
            code="sql_injection_attempt",
            details={"severity": "high", **kwargs}
        )


class XSSAttemptError(SecurityError):
    """
    Exception raised for XSS (Cross-Site Scripting) attempts
    Following Single Responsibility Principle
    """

    def __init__(self, message: str = "XSS attempt detected", **kwargs):
        super().__init__(
            message=message,
            code="xss_attempt",
            details={"severity": "high", **kwargs}
        )


class CSFRViolationError(SecurityError):
    """
    Exception raised for CSRF violations
    Following Single Responsibility Principle
    """

    def __init__(self, message: str = "CSRF violation detected", **kwargs):
        super().__init__(
            message=message,
            code="csrf_violation",
            details={"severity": "medium", **kwargs}
        )


class SuspiciousActivityError(SecurityError):
    """
    Exception raised for suspicious activity
    Following Single Responsibility Principle
    """

    def __init__(self, message: str = "Suspicious activity detected", severity: str = "medium", **kwargs):
        self.severity = severity
        super().__init__(
            message=message,
            code="suspicious_activity",
            details={"severity": severity, **kwargs}
        )


class UnauthorizedAccessError(SecurityError):
    """
    Exception raised for unauthorized access attempts
    Following Single Responsibility Principle
    """

    def __init__(self, message: str = "Unauthorized access attempt", resource: str = None, **kwargs):
        self.resource = resource
        super().__init__(
            message=message,
            code="unauthorized_access",
            details={"resource": resource, **kwargs}
        )


class SecurityConfigError(SecurityError):
    """
    Exception raised for security configuration errors
    Following Single Responsibility Principle
    """

    def __init__(self, message: str = "Security configuration error", config_key: str = None, **kwargs):
        self.config_key = config_key
        super().__init__(
            message=message,
            code="security_config_error",
            details={"config_key": config_key, **kwargs}
        )


class SecurityHeadersError(SecurityError):
    """
    Exception raised for security header errors
    Following Single Responsibility Principle
    """

    def __init__(self, message: str = "Security header error", header: str = None, **kwargs):
        self.header = header
        super().__init__(
            message=message,
            code="security_header_error",
            details={"header": header, **kwargs}
        )


class CORSPolicyError(SecurityError):
    """
    Exception raised for CORS policy violations
    Following Single Responsibility Principle
    """

    def __init__(self, message: str = "CORS policy violation", origin: str = None, **kwargs):
        self.origin = origin
        super().__init__(
            message=message,
            code="cors_policy_violation",
            details={"origin": origin, **kwargs}
        )


class ContentSecurityPolicyError(SecurityError):
    """
    Exception raised for Content Security Policy violations
    Following Single Responsibility Principle
    """

    def __init__(self, message: str = "Content Security Policy violation", directive: str = None, **kwargs):
        self.directive = directive
        super().__init__(
            message=message,
            code="csp_violation",
            details={"directive": directive, **kwargs}
        )


class FileUploadSecurityError(SecurityError):
    """
    Exception raised for file upload security violations
    Following Single Responsibility Principle
    """

    def __init__(self, message: str = "File upload security violation", filename: str = None, **kwargs):
        self.filename = filename
        super().__init__(
            message=message,
            code="file_upload_security_violation",
            details={"filename": filename, **kwargs}
        )


class AuthenticationSecurityError(SecurityError):
    """
    Exception raised for authentication security issues
    Following Single Responsibility Principle
    """

    def __init__(self, message: str = "Authentication security issue", **kwargs):
        super().__init__(
            message=message,
            code="authentication_security_issue",
            details={"severity": "high", **kwargs}
        )


class TokenSecurityError(SecurityError):
    """
    Exception raised for token security issues
    Following Single Responsibility Principle
    """

    def __init__(self, message: str = "Token security issue", token_type: str = None, **kwargs):
        self.token_type = token_type
        super().__init__(
            message=message,
            code="token_security_issue",
            details={"token_type": token_type, **kwargs}
        )


class SecurityMonitoringError(SecurityError):
    """
    Exception raised for security monitoring issues
    Following Single Responsibility Principle
    """

    def __init__(self, message: str = "Security monitoring issue", monitor_type: str = None, **kwargs):
        self.monitor_type = monitor_type
        super().__init__(
            message=message,
            code="security_monitoring_issue",
            details={"monitor_type": monitor_type, **kwargs}
        )