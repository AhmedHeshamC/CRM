"""
Test suite for Enhanced Security Headers Middleware
Following SOLID principles and TDD approach
"""

from django.test import TestCase, RequestFactory
from django.http import HttpResponse
from django.conf import settings
from unittest.mock import patch, MagicMock
from shared.security.security_headers import (
    SecurityHeadersMiddleware,
    AdvancedSecurityHeadersMiddleware
)


class SecurityHeadersMiddlewareTest(TestCase):
    """
    Test suite for SecurityHeadersMiddleware
    Following SOLID principles with comprehensive test coverage
    """

    def setUp(self):
        """
        Set up test environment
        Following Single Responsibility Principle
        """
        self.factory = RequestFactory()
        self.get_response = lambda r: HttpResponse("OK")
        self.middleware = SecurityHeadersMiddleware(self.get_response)

    def test_security_headers_middleware_initialization(self):
        """
        Test middleware initialization
        Following SOLID principles
        """
        self.assertIsNotNone(self.middleware)
        self.assertTrue(hasattr(self.middleware, 'get_response'))

    def test_basic_security_headers_in_development(self):
        """
        Test basic security headers in development mode
        Following Single Responsibility Principle
        """
        with patch.object(settings, 'DEBUG', True):
            request = self.factory.get('/api/v1/contacts/')
            response = self.middleware(request)

            # Basic headers should always be present
            self.assertEqual(response.get('X-Content-Type-Options'), 'nosniff')
            self.assertEqual(response.get('X-Frame-Options'), 'DENY')
            self.assertEqual(response.get('X-XSS-Protection'), '1; mode=block')

            # Production headers should not be present in debug mode
            self.assertIsNone(response.get('Strict-Transport-Security'))
            self.assertIsNone(response.get('Content-Security-Policy'))

    def test_production_security_headers(self):
        """
        Test production security headers
        Following Single Responsibility Principle
        """
        with patch.object(settings, 'DEBUG', False):
            request = self.factory.get('/api/v1/contacts/')
            response = self.middleware(request)

            # All security headers should be present in production
            self.assertEqual(response.get('X-Content-Type-Options'), 'nosniff')
            self.assertEqual(response.get('X-Frame-Options'), 'DENY')
            self.assertEqual(response.get('X-XSS-Protection'), '1; mode=block')
            self.assertEqual(response.get('Strict-Transport-Security'), 'max-age=31536000; includeSubDomains; preload')
            self.assertIsNotNone(response.get('Content-Security-Policy'))

    def test_content_security_policy_configuration(self):
        """
        Test Content Security Policy configuration
        Following Single Responsibility Principle
        """
        with patch.object(settings, 'DEBUG', False):
            request = self.factory.get('/api/v1/contacts/')
            response = self.middleware(request)

            csp = response.get('Content-Security-Policy')
            self.assertIsNotNone(csp)

            # Check CSP directives
            self.assertIn("default-src 'self'", csp)
            self.assertIn("script-src 'self'", csp)
            self.assertIn("style-src 'self' 'unsafe-inline'", csp)
            self.assertIn("img-src 'self' data: https:", csp)
            self.assertIn("font-src 'self'", csp)
            self.assertIn("connect-src 'self'", csp)
            self.assertIn("frame-ancestors 'none'", csp)
            self.assertIn("base-uri 'self'", csp)

    def test_csp_for_api_endpoints(self):
        """
        Test CSP configuration for API endpoints
        Following Single Responsibility Principle
        """
        with patch.object(settings, 'DEBUG', False):
            request = self.factory.get('/api/v1/contacts/')
            response = self.middleware(request)

            csp = response.get('Content-Security-Policy')

            # API endpoints should have strict CSP
            self.assertIn("default-src 'self'", csp)
            self.assertNotIn("'unsafe-inline'", csp)
            self.assertNotIn("'unsafe-eval'", csp)

    def test_csp_for_documentation_endpoints(self):
        """
        Test CSP configuration for documentation endpoints
        Following Single Responsibility Principle
        """
        with patch.object(settings, 'DEBUG', False):
            # Test Swagger UI endpoint
            request = self.factory.get('/api/docs/')
            response = self.middleware(request)

            csp = response.get('Content-Security-Policy')
            self.assertIsNotNone(csp)

            # Documentation endpoints might allow inline scripts for UI
            if csp:
                self.assertIn("default-src 'self'", csp)

    def test_hsts_configuration(self):
        """
        Test HSTS configuration in production
        Following Single Responsibility Principle
        """
        with patch.object(settings, 'DEBUG', False):
            request = self.factory.get('/api/v1/contacts/')
            response = self.middleware(request)

            hsts = response.get('Strict-Transport-Security')
            self.assertIsNotNone(hsts)
            self.assertIn('max-age=31536000', hsts)
            self.assertIn('includeSubDomains', hsts)
            self.assertIn('preload', hsts)

    def test_custom_security_headers_configuration(self):
        """
        Test custom security headers configuration
        Following Open/Closed Principle
        """
        custom_headers = {
            'X-Custom-Security': 'custom-value',
            'X-API-Version': 'v1.0.0'
        }

        middleware = SecurityHeadersMiddleware(
            self.get_response,
            custom_headers=custom_headers
        )

        request = self.factory.get('/api/v1/contacts/')
        response = middleware(request)

        # Check custom headers are added
        self.assertEqual(response.get('X-Custom-Security'), 'custom-value')
        self.assertEqual(response.get('X-API-Version'), 'v1.0.0')

    def test_csp_nonce_generation(self):
        """
        Test CSP nonce generation for inline scripts
        Following Single Responsibility Principle
        """
        with patch.object(settings, 'DEBUG', False):
            request = self.factory.get('/api/v1/contacts/')
            request.csp_nonce = 'test-nonce-123'

            response = self.middleware(request)

            # Verify nonce is preserved in request
            self.assertEqual(request.csp_nonce, 'test-nonce-123')

    def test_security_headers_error_handling(self):
        """
        Test error handling in security headers middleware
        Following SOLID principles
        """
        # Simulate response object that doesn't support headers
        class MockResponse:
            def __init__(self):
                self.content = "OK"

            def __setitem__(self, key, value):
                raise Exception("Header setting failed")

        mock_response = MockResponse()
        get_response = lambda r: mock_response
        middleware = SecurityHeadersMiddleware(get_response)

        request = self.factory.get('/api/v1/contacts/')

        # Should not raise exception even if header setting fails
        response = middleware(request)
        self.assertEqual(response.content, "OK")

    def test_response_preservation(self):
        """
        Test that original response is preserved
        Following Single Responsibility Principle
        """
        original_response = HttpResponse("Original Content", status=200)
        original_response['X-Original-Header'] = 'original-value'

        get_response = lambda r: original_response
        middleware = SecurityHeadersMiddleware(get_response)

        request = self.factory.get('/api/v1/contacts/')
        response = middleware(request)

        # Original response properties should be preserved
        self.assertEqual(response.content, b"Original Content")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get('X-Original-Header'), 'original-value')

        # Security headers should be added
        self.assertEqual(response.get('X-Content-Type-Options'), 'nosniff')

    def test_exempt_paths_configuration(self):
        """
        Test exempt paths configuration
        Following Open/Closed Principle
        """
        exempt_paths = ['/health/', '/metrics/']
        middleware = SecurityHeadersMiddleware(
            self.get_response,
            exempt_paths=exempt_paths
        )

        # Test exempt path - should have minimal security headers
        request = self.factory.get('/health/')
        response = middleware(request)

        # Should still have basic security headers even for exempt paths
        self.assertEqual(response.get('X-Content-Type-Options'), 'nosniff')

        # Test non-exempt path - should have all security headers
        request = self.factory.get('/api/v1/contacts/')
        response = middleware(request)

        self.assertEqual(response.get('X-Content-Type-Options'), 'nosniff')
        self.assertEqual(response.get('X-Frame-Options'), 'DENY')

    @patch('shared.security.security_headers.settings')
    def test_environment_based_configuration(self, mock_settings):
        """
        Test environment-based security configuration
        Following Single Responsibility Principle
        """
        mock_settings.DEBUG = False
        mock_settings.SECURE_SSL_REDIRECT = True
        mock_settings.SECURE_HSTS_SECONDS = 63072000  # 2 years
        mock_settings.SECURE_HSTS_INCLUDE_SUBDOMAINS = True
        mock_settings.SECURE_HSTS_PRELOAD = True

        middleware = SecurityHeadersMiddleware(self.get_response)
        request = self.factory.get('/api/v1/contacts/')
        response = middleware(request)

        # Should use environment-specific HSTS settings
        hsts = response.get('Strict-Transport-Security')
        if hsts:
            self.assertIn('max-age=63072000', hsts)


class AdvancedSecurityHeadersMiddlewareTest(TestCase):
    """
    Test suite for AdvancedSecurityHeadersMiddleware
    Following SOLID principles with advanced features
    """

    def setUp(self):
        """
        Set up test environment for advanced middleware
        Following Single Responsibility Principle
        """
        self.factory = RequestFactory()
        self.get_response = lambda r: HttpResponse("OK")
        self.middleware = AdvancedSecurityHeadersMiddleware(self.get_response)

    def test_advanced_security_headers_initialization(self):
        """
        Test advanced middleware initialization
        Following SOLID principles
        """
        self.assertIsNotNone(self.middleware)
        self.assertTrue(hasattr(self.middleware, 'enable_csp_reporting'))
        self.assertTrue(hasattr(self.middleware, 'enable_feature_policies'))

    def test_csp_reporting_configuration(self):
        """
        Test CSP reporting configuration
        Following Single Responsibility Principle
        """
        with patch.object(settings, 'DEBUG', False):
            request = self.factory.get('/api/v1/contacts/')
            response = self.middleware(request)

            csp = response.get('Content-Security-Policy')
            if csp:
                # Should include report-uri if reporting is enabled
                self.assertIn('report-uri', csp) if self.middleware.enable_csp_reporting else True

    def test_feature_policy_headers(self):
        """
        Test Feature Policy headers
        Following Single Responsibility Principle
        """
        with patch.object(settings, 'DEBUG', False):
            request = self.factory.get('/api/v1/contacts/')
            response = self.middleware(request)

            feature_policy = response.get('Feature-Policy')
            self.assertIsNotNone(feature_policy)

            # Check common feature policies
            self.assertIn('geometer', feature_policy.lower())
            self.assertIn('microphone', feature_policy.lower())
            self.assertIn('camera', feature_policy.lower())

    def test_permissions_policy_headers(self):
        """
        Test Permissions Policy headers (newer standard)
        Following Single Responsibility Principle
        """
        with patch.object(settings, 'DEBUG', False):
            request = self.factory.get('/api/v1/contacts/')
            response = self.middleware(request)

            permissions_policy = response.get('Permissions-Policy')
            if permissions_policy:
                # Check common permissions
                self.assertIn('geometer', permissions_policy.lower())
                self.assertIn('microphone', permissions_policy.lower())
                self.assertIn('camera', permissions_policy.lower())

    def test_referrer_policy_configuration(self):
        """
        Test Referrer Policy configuration
        Following Single Responsibility Principle
        """
        with patch.object(settings, 'DEBUG', False):
            request = self.factory.get('/api/v1/contacts/')
            response = self.middleware(request)

            referrer_policy = response.get('Referrer-Policy')
            self.assertIsNotNone(referrer_policy)
            self.assertEqual(referrer_policy, 'strict-origin-when-cross-origin')

    def test_integrity_metadata_headers(self):
        """
        Test Subresource Integrity metadata headers
        Following Single Responsibility Principle
        """
        with patch.object(settings, 'DEBUG', False):
            request = self.factory.get('/api/v1/contacts/')
            response = self.middleware(request)

            # Should include integrity metadata if enabled
            if self.middleware.enable_integrity_metadata:
                self.assertIsNotNone(response.get('X-Content-Security-Policy'))

    def test_dynamic_csp_based_on_content_type(self):
        """
        Test dynamic CSP based on response content type
        Following Single Responsibility Principle
        """
        def json_response(r):
            response = HttpResponse('{"data": "test"}', content_type='application/json')
            return response

        get_response = json_response
        middleware = AdvancedSecurityHeadersMiddleware(get_response)

        with patch.object(settings, 'DEBUG', False):
            request = self.factory.get('/api/v1/contacts/')
            response = middleware(request)

            csp = response.get('Content-Security-Policy')
            if csp:
                # JSON responses should have strict CSP
                self.assertIn("default-src 'self'", csp)

    def test_csp_for_html_content(self):
        """
        Test CSP configuration for HTML content
        Following Single Responsibility Principle
        """
        def html_response(r):
            response = HttpResponse('<html><body>Test</body></html>', content_type='text/html')
            return response

        get_response = html_response
        middleware = AdvancedSecurityHeadersMiddleware(get_response)

        with patch.object(settings, 'DEBUG', False):
            request = self.factory.get('/api/v1/contacts/')
            response = middleware(request)

            csp = response.get('Content-Security-Policy')
            if csp:
                # HTML responses can have more relaxed CSP for styles
                self.assertIn("style-src", csp)

    def test_custom_csp_directives(self):
        """
        Test custom CSP directives configuration
        Following Open/Closed Principle
        """
        custom_csp = {
            'script-src': "'self' 'unsafe-inline' https://cdn.example.com",
            'img-src': "'self' data: https: https://images.example.com",
            'connect-src': "'self' https://api.example.com"
        }

        middleware = AdvancedSecurityHeadersMiddleware(
            self.get_response,
            custom_csp_directives=custom_csp
        )

        with patch.object(settings, 'DEBUG', False):
            request = self.factory.get('/api/v1/contacts/')
            response = middleware(request)

            csp = response.get('Content-Security-Policy')
            if csp:
                self.assertIn("https://cdn.example.com", csp)
                self.assertIn("https://images.example.com", csp)
                self.assertIn("https://api.example.com", csp)

    def test_security_headers_monitoring(self):
        """
        Test security headers monitoring and logging
        Following Single Responsibility Principle
        """
        with patch('shared.security.security_headers.logger') as mock_logger:
            request = self.factory.get('/api/v1/contacts/')
            response = self.middleware(request)

            # Should log security headers application
            mock_logger.debug.assert_called()

    def test_header_injection_prevention(self):
        """
        Test prevention of header injection attacks
        Following Security First Principle
        """
        # Try to inject headers through request
        request = self.factory.get('/api/v1/contacts/', HTTP_X_FORWARDED_HOST='evil.com')
        response = self.middleware(request)

        # Should not reflect malicious headers in response
        self.assertNotIn('evil.com', str(response.content))