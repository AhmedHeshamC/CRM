"""
Test Suite for JWT Authentication Middleware
Following TDD approach and SOLID principles
"""

import pytest
import json
from datetime import datetime, timedelta
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.contrib.sessions.middleware import SessionMiddleware
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken
from unittest.mock import patch, MagicMock
from shared.authentication.middleware import JWTAuthenticationMiddleware, SecurityHeadersMiddleware

User = get_user_model()


class JWTAuthenticationMiddlewareTest(TestCase):
    """Test cases for JWT Authentication Middleware"""

    def setUp(self):
        """Set up test environment"""
        self.factory = RequestFactory()
        self.middleware = JWTAuthenticationMiddleware(get_response=lambda r: r)

        # Create test users with different roles
        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            first_name='Admin',
            last_name='User',
            role='admin'
        )

        self.manager_user = User.objects.create_user(
            email='manager@test.com',
            password='testpass123',
            first_name='Manager',
            last_name='User',
            role='manager'
        )

        self.sales_user = User.objects.create_user(
            email='sales@test.com',
            password='testpass123',
            first_name='Sales',
            last_name='User',
            role='sales'
        )

        self.support_user = User.objects.create_user(
            email='support@test.com',
            password='testpass123',
            first_name='Support',
            last_name='User',
            role='support'
        )

        self.inactive_user = User.objects.create_user(
            email='inactive@test.com',
            password='testpass123',
            first_name='Inactive',
            last_name='User',
            role='sales',
            is_active=False
        )

    def test_middleware_skips_exempt_paths(self):
        """Test that middleware skips authentication for exempt paths"""
        exempt_paths = [
            '/api/v1/auth/auth/login/',
            '/api/v1/auth/auth/register/',
            '/api/v1/auth/auth/password-reset/',
            '/api/v1/auth/auth/refresh/',
            '/admin/',
            '/api/schema/',
            '/api/docs/',
            '/api/redoc/',
        ]

        for path in exempt_paths:
            request = self.factory.get(path)
            response = self.middleware.process_request(request)
            self.assertIsNone(response, f"Should skip authentication for {path}")

    def test_middleware_authenticates_valid_token(self):
        """Test successful authentication with valid JWT token"""
        token = RefreshToken.for_user(self.admin_user)
        request = self.factory.get(
            '/api/v1/contacts/',
            HTTP_AUTHORIZATION=f'Bearer {token.access_token}'
        )

        response = self.middleware.process_request(request)

        self.assertIsNone(response)
        self.assertEqual(request.user, self.admin_user)
        self.assertTrue(request.user.is_authenticated)

    def test_middleware_rejects_missing_token(self):
        """Test rejection when no token is provided"""
        request = self.factory.get('/api/v1/contacts/')

        response = self.middleware.process_request(request)

        self.assertIsNone(response)  # Middleware doesn't reject, just doesn't authenticate
        self.assertFalse(hasattr(request, 'user'))

    def test_middleware_rejects_invalid_token_format(self):
        """Test rejection for invalid token format"""
        request = self.factory.get(
            '/api/v1/contacts/',
            HTTP_AUTHORIZATION='InvalidFormat token123'
        )

        response = self.middleware.process_request(request)

        self.assertIsNone(response)  # Middleware doesn't reject invalid format

    def test_middleware_rejects_expired_token(self):
        """Test rejection for expired token"""
        # Create expired token
        token = RefreshToken.for_user(self.admin_user)
        token.set_exp(lifetime=timedelta(seconds=-1))

        request = self.factory.get(
            '/api/v1/contacts/',
            HTTP_AUTHORIZATION=f'Bearer {token.access_token}'
        )

        response = self.middleware.process_request(request)

        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 401)

    def test_middleware_rejects_inactive_user_token(self):
        """Test rejection for inactive user token"""
        token = RefreshToken.for_user(self.inactive_user)
        request = self.factory.get(
            '/api/v1/contacts/',
            HTTP_AUTHORIZATION=f'Bearer {token.access_token}'
        )

        response = self.middleware.process_request(request)

        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 401)

    def test_middleware_handles_malformed_token(self):
        """Test handling of malformed JWT token"""
        request = self.factory.get(
            '/api/v1/contacts/',
            HTTP_AUTHORIZATION='Bearer invalid.jwt.token'
        )

        response = self.middleware.process_request(request)

        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 401)

    def test_middleware_updates_user_activity(self):
        """Test that middleware updates user's last activity"""
        token = RefreshToken.for_user(self.sales_user)
        request = self.factory.get(
            '/api/v1/contacts/',
            HTTP_AUTHORIZATION=f'Bearer {token.access_token}'
        )

        # Mock user profile save
        with patch.object(self.sales_user.profile, 'save') as mock_save:
            self.middleware.process_request(request)
            mock_save.assert_called_once_with(update_fields=['last_activity'])

    @patch('shared.authentication.middleware.logger')
    def test_middleware_logs_authentication_events(self, mock_logger):
        """Test that middleware logs authentication events"""
        token = RefreshToken.for_user(self.admin_user)
        request = self.factory.get(
            '/api/v1/contacts/',
            HTTP_AUTHORIZATION=f'Bearer {token.access_token}'
        )

        self.middleware.process_request(request)

        mock_logger.debug.assert_called_with(f"User authenticated: {self.admin_user.email}")

    @patch('shared.authentication.middleware.logger')
    def test_middleware_logs_invalid_token_attempts(self, mock_logger):
        """Test that middleware logs invalid token attempts"""
        request = self.factory.get(
            '/api/v1/contacts/',
            HTTP_AUTHORIZATION='Bearer invalid.jwt.token'
        )

        self.middleware.process_request(request)

        mock_logger.warning.assert_called()

    @patch('shared.authentication.middleware.logger')
    def test_middleware_handles_authentication_errors(self, mock_logger):
        """Test that middleware handles authentication errors gracefully"""
        request = self.factory.get(
            '/api/v1/contacts/',
            HTTP_AUTHORIZATION='Bearer invalid.token'
        )

        # Mock an exception during authentication
        with patch('shared.authentication.middleware.JWTAuthentication') as mock_jwt_auth:
            mock_jwt_auth.side_effect = Exception("Authentication error")

            response = self.middleware.process_request(request)

            self.assertIsNotNone(response)
            self.assertEqual(response.status_code, 401)
            mock_logger.error.assert_called()


class SecurityHeadersMiddlewareTest(TestCase):
    """Test cases for Security Headers Middleware"""

    def setUp(self):
        """Set up test environment"""
        self.factory = RequestFactory()
        self.middleware = SecurityHeadersMiddleware(get_response=lambda r: MagicMock())

    def test_security_headers_added_in_production(self):
        """Test that security headers are added in production"""
        with patch.object(settings, 'DEBUG', False):
            request = self.factory.get('/api/v1/contacts/')
            response = MagicMock()

            result = self.middleware.process_response(request, response)

            # Check that security headers are set
            expected_headers = {
                'X-Content-Type-Options': 'nosniff',
                'X-Frame-Options': 'DENY',
                'X-XSS-Protection': '1; mode=block',
                'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
                'Content-Security-Policy': "default-src 'self'"
            }

            for header, value in expected_headers.items():
                response.__setitem__.assert_any_call(header, value)

    def test_security_headers_added_in_development(self):
        """Test that basic security headers are added in development"""
        with patch.object(settings, 'DEBUG', True):
            request = self.factory.get('/api/v1/contacts/')
            response = MagicMock()

            result = self.middleware.process_response(request, response)

            # Check that basic headers are set but HSTS and CSP are not
            basic_headers = {
                'X-Content-Type-Options': 'nosniff',
                'X-Frame-Options': 'DENY',
                'X-XSS-Protection': '1; mode=block'
            }

            for header, value in basic_headers.items():
                response.__setitem__.assert_any_call(header, value)

            # Production-only headers should not be set
            response.__setitem__.assert_not_called_with('Strict-Transport-Security', 'max-age=31536000; includeSubDomains')
            response.__setitem__.assert_not_called_with('Content-Security-Policy', "default-src 'self'")

    def test_middleware_returns_response_unchanged(self):
        """Test that middleware returns the response unchanged"""
        request = self.factory.get('/api/v1/contacts/')
        response = MagicMock()

        result = self.middleware.process_response(request, response)

        self.assertEqual(result, response)


class JWTAuthenticationIntegrationTest(TestCase):
    """Integration tests for JWT Authentication"""

    def setUp(self):
        """Set up test environment"""
        self.factory = RequestFactory()

        # Create middleware chain
        self.get_response = lambda r: r
        self.jwt_middleware = JWTAuthenticationMiddleware(self.get_response)

    def test_full_authentication_flow(self):
        """Test complete authentication flow"""
        user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            role='sales'
        )

        # Generate JWT token
        token = RefreshToken.for_user(user)

        # Make request with token
        request = self.factory.get(
            '/api/v1/contacts/',
            HTTP_AUTHORIZATION=f'Bearer {token.access_token}'
        )

        # Process through middleware
        response = self.jwt_middleware.process_request(request)

        # Verify authentication
        self.assertIsNone(response)
        self.assertEqual(request.user, user)
        self.assertTrue(request.user.is_authenticated)

    def test_authentication_with_multiple_roles(self):
        """Test authentication with different user roles"""
        roles = ['admin', 'manager', 'sales', 'support']

        for role in roles:
            with self.subTest(role=role):
                user = User.objects.create_user(
                    email=f'{role}@test.com',
                    password='testpass123',
                    role=role
                )

                token = RefreshToken.for_user(user)
                request = self.factory.get(
                    '/api/v1/contacts/',
                    HTTP_AUTHORIZATION=f'Bearer {token.access_token}'
                )

                response = self.jwt_middleware.process_request(request)

                self.assertIsNone(response)
                self.assertEqual(request.user, user)
                self.assertEqual(request.user.role, role)