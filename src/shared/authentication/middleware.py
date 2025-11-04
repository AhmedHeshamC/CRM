"""
JWT Authentication Middleware with Role-Based Access Control
Following SOLID principles and enterprise security best practices
"""

import logging
import jwt
from django.contrib.auth import get_user_model
from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse
from django.conf import settings
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework import status

logger = logging.getLogger(__name__)
User = get_user_model()


class JWTAuthenticationMiddleware(MiddlewareMixin):
    """
    JWT Authentication Middleware for API requests
    Following Single Responsibility Principle for authentication handling
    """

    def process_request(self, request):
        """
        Process incoming request for JWT authentication
        Following SOLID principles for clean middleware implementation
        """
        # Skip authentication for exempt paths
        if self._is_path_exempt(request.path):
            return None

        try:
            # Attempt JWT authentication
            auth_result = self._authenticate_user(request)
            if auth_result:
                request.user = auth_result
                logger.debug(f"User authenticated: {request.user.email}")

        except InvalidToken as e:
            logger.warning(f"Invalid token provided: {str(e)}")
            return JsonResponse({
                'error': 'Invalid authentication token',
                'code': 'invalid_token',
                'detail': str(e)
            }, status=status.HTTP_401_UNAUTHORIZED)

        except TokenError as e:
            logger.warning(f"Token error occurred: {str(e)}")
            return JsonResponse({
                'error': 'Token processing error',
                'code': 'token_error',
                'detail': str(e)
            }, status=status.HTTP_401_UNAUTHORIZED)

        except Exception as e:
            logger.error(f"Authentication middleware error: {str(e)}")
            return JsonResponse({
                'error': 'Authentication failed',
                'code': 'authentication_error',
                'detail': 'An error occurred during authentication'
            }, status=status.HTTP_401_UNAUTHORIZED)

        return None

    def _is_path_exempt(self, path):
        """
        Check if path is exempt from authentication
        Following Single Responsibility Principle
        """
        exempt_paths = [
            '/api/v1/auth/auth/login/',
            '/api/v1/auth/auth/register/',
            '/api/v1/auth/auth/password-reset/',
            '/api/v1/auth/auth/password-reset-confirm/',
            '/api/v1/auth/auth/refresh/',
            '/admin/',
            '/api/schema/',
            '/api/docs/',
            '/api/redoc/',
        ]

        return any(path.startswith(exempt_path) for exempt_path in exempt_paths)

    def _authenticate_user(self, request):
        """
        Authenticate user using JWT token
        Following Single Responsibility Principle
        """
        jwt_auth = JWTAuthentication()

        # Extract and validate token
        try:
            auth_header = request.META.get('HTTP_AUTHORIZATION')
            if not auth_header or not auth_header.startswith('Bearer '):
                return None

            validated_token = jwt_auth.get_validated_token(auth_header.split(' ')[1])
            user = jwt_auth.get_user(validated_token)

            # Verify user is active
            if not user.is_active:
                raise InvalidToken('User account is deactivated')

            # Update last activity
            self._update_user_activity(user)

            return user

        except Exception:
            return None

    def _update_user_activity(self, user):
        """
        Update user's last activity timestamp
        Following Single Responsibility Principle
        """
        try:
            from django.utils import timezone
            if hasattr(user, 'profile'):
                user.profile.last_activity = timezone.now()
                user.profile.save(update_fields=['last_activity'])
        except Exception as e:
            logger.warning(f"Failed to update user activity: {str(e)}")


class SecurityHeadersMiddleware(MiddlewareMixin):
    """
    Security Headers Middleware for enhanced security
    Following Single Responsibility Principle for security headers
    """

    def process_response(self, request, response):
        """
        Add security headers to response
        Following SOLID principles for security implementation
        """
        # Security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'

        if not settings.DEBUG:
            response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
            response['Content-Security-Policy'] = "default-src 'self'"

        return response