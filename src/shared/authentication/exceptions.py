"""
Custom Exception Handlers for Authentication and Authorization
Following SOLID principles and enterprise error handling standards
"""

import logging
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import (
    AuthenticationFailed,
    NotAuthenticated,
    PermissionDenied,
    ValidationError,
)
from rest_framework_simplejwt.exceptions import (
    InvalidToken,
    TokenError,
    AuthenticationFailed as JWTAuthenticationFailed,
)
from django.http import Http404
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def custom_exception_handler(exc: Exception, context: Any) -> Optional[Response]:
    """
    Custom exception handler for authentication and authorization errors
    Following Single Responsibility Principle for error handling
    """
    # Call DRF's default exception handler first
    response = exception_handler(exc, context)

    # Handle specific authentication exceptions
    if isinstance(exc, (InvalidToken, TokenError, JWTAuthenticationFailed)):
        return handle_jwt_authentication_errors(exc, context)

    elif isinstance(exc, (AuthenticationFailed, NotAuthenticated)):
        return handle_authentication_errors(exc, context)

    elif isinstance(exc, PermissionDenied):
        return handle_authorization_errors(exc, context)

    elif isinstance(exc, ValidationError):
        return handle_validation_errors(exc, context)

    elif isinstance(exc, Http404):
        return handle_not_found_errors(exc, context)

    # Enhance existing response if present
    if response is not None:
        return enhance_error_response(response, exc, context)

    return None


def handle_jwt_authentication_errors(exc: Exception, context: Any) -> Response:
    """
    Handle JWT authentication specific errors
    Following Single Responsibility Principle
    """
    error_code = "token_invalid"
    error_message = "Authentication token is invalid or expired"
    http_status = status.HTTP_401_UNAUTHORIZED

    if isinstance(exc, InvalidToken):
        error_code = "token_invalid"
        error_message = "Invalid authentication token"
        logger.warning(f"Invalid token attempt: {str(exc)}")

    elif isinstance(exc, TokenError):
        error_code = "token_error"
        error_message = "Token processing error"
        logger.warning(f"Token error: {str(exc)}")

    elif isinstance(exc, JWTAuthenticationFailed):
        error_code = "jwt_authentication_failed"
        error_message = "JWT authentication failed"
        logger.warning(f"JWT authentication failed: {str(exc)}")

    return create_error_response(
        error_code=error_code,
        error_message=error_message,
        status_code=http_status,
        details=str(exc) if not isinstance(exc, (InvalidToken, TokenError)) else None
    )


def handle_authentication_errors(exc: Exception, context: Any) -> Response:
    """
    Handle general authentication errors
    Following Single Responsibility Principle
    """
    error_code = "authentication_required"
    error_message = "Authentication is required to access this resource"

    if isinstance(exc, NotAuthenticated):
        error_code = "authentication_missing"
        error_message = "Authentication credentials were not provided"
        logger.info(f"Authentication missing for {context['request'].path}")

    elif isinstance(exc, AuthenticationFailed):
        error_code = "authentication_failed"
        error_message = "Authentication failed"
        logger.warning(f"Authentication failed: {str(exc)}")

    return create_error_response(
        error_code=error_code,
        error_message=error_message,
        status_code=status.HTTP_401_UNAUTHORIZED,
        details=str(exc) if not isinstance(exc, NotAuthenticated) else None
    )


def handle_authorization_errors(exc: Exception, context: Any) -> Response:
    """
    Handle authorization/permission errors
    Following Single Responsibility Principle
    """
    error_code = "permission_denied"
    error_message = "You do not have permission to perform this action"

    logger.warning(
        f"Permission denied for user {context['request'].user.email if hasattr(context['request'], 'user') else 'anonymous'} "
        f"to {context['request'].method} {context['request'].path}: {str(exc)}"
    )

    return create_error_response(
        error_code=error_code,
        error_message=error_message,
        status_code=status.HTTP_403_FORBIDDEN,
        details=str(exc)
    )


def handle_validation_errors(exc: Exception, context: Any) -> Response:
    """
    Handle validation errors
    Following Single Responsibility Principle
    """
    error_code = "validation_error"
    error_message = "Invalid data provided"

    # Extract validation details
    details = None
    if hasattr(exc, 'detail'):
        details = exc.detail
        logger.warning(f"Validation error for {context['request'].path}: {details}")

    return create_error_response(
        error_code=error_code,
        error_message=error_message,
        status_code=status.HTTP_400_BAD_REQUEST,
        details=details
    )


def handle_not_found_errors(exc: Exception, context: Any) -> Response:
    """
    Handle 404 not found errors
    Following Single Responsibility Principle
    """
    error_code = "resource_not_found"
    error_message = "The requested resource was not found"

    logger.info(f"Resource not found: {context['request'].path}")

    return create_error_response(
        error_code=error_code,
        error_message=error_message,
        status_code=status.HTTP_404_NOT_FOUND
    )


def enhance_error_response(response: Response, exc: Exception, context: Any) -> Response:
    """
    Enhance existing error response with additional context
    Following Single Responsibility Principle
    """
    if response.status_code == status.HTTP_401_UNAUTHORIZED:
        response.data = {
            'error': 'Authentication required',
            'code': 'authentication_required',
            'detail': response.data.get('detail', 'Authentication failed'),
            'timestamp': context.get('timestamp'),
        }

    elif response.status_code == status.HTTP_403_FORBIDDEN:
        response.data = {
            'error': 'Permission denied',
            'code': 'permission_denied',
            'detail': response.data.get('detail', 'You do not have permission to perform this action'),
            'required_permissions': get_required_permissions(context),
            'timestamp': context.get('timestamp'),
        }

    elif response.status_code == status.HTTP_400_BAD_REQUEST:
        response.data = {
            'error': 'Bad request',
            'code': 'validation_error',
            'detail': response.data,
            'timestamp': context.get('timestamp'),
        }

    return response


def create_error_response(
    error_code: str,
    error_message: str,
    status_code: int,
    details: Optional[Any] = None
) -> Response:
    """
    Create standardized error response
    Following Single Responsibility Principle
    """
    response_data = {
        'error': error_message,
        'code': error_code,
        'timestamp': get_current_timestamp(),
    }

    if details:
        response_data['details'] = details

    # Add help information for specific errors
    if status_code == status.HTTP_401_UNAUTHORIZED:
        response_data['help'] = {
            'message': 'Please provide valid authentication credentials',
            'solutions': [
                'Include a valid JWT token in the Authorization header',
                'Ensure the token has not expired',
                'Check if your account is active'
            ]
        }

    elif status_code == status.HTTP_403_FORBIDDEN:
        response_data['help'] = {
            'message': 'You do not have sufficient permissions for this action',
            'solutions': [
                'Contact your administrator for required permissions',
                'Check if your account has the appropriate role',
                'Verify you are accessing the correct resource'
            ]
        }

    return Response(response_data, status=status_code)


def get_required_permissions(context: Any) -> Optional[list]:
    """
    Extract required permissions from context if available
    Following Single Responsibility Principle
    """
    view = context.get('view')
    if view and hasattr(view, 'permission_classes'):
        try:
            permissions = []
            for perm_class in view.permission_classes:
                permissions.append(perm_class.__name__)
            return permissions
        except Exception:
            pass

    return None


def get_current_timestamp() -> str:
    """
    Get current timestamp in ISO format
    Following Single Responsibility Principle
    """
    from django.utils import timezone
    return timezone.now().isoformat()


class AuthenticationError(Exception):
    """
    Custom authentication error class
    Following Single Responsibility Principle
    """

    def __init__(self, message: str, code: str = "authentication_error", details: Optional[Dict] = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(message)


class AuthorizationError(Exception):
    """
    Custom authorization error class
    Following Single Responsibility Principle
    """

    def __init__(self, message: str, code: str = "authorization_error", details: Optional[Dict] = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(message)


class TokenError(Exception):
    """
    Custom token error class
    Following Single Responsibility Principle
    """

    def __init__(self, message: str, code: str = "token_error", details: Optional[Dict] = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(message)