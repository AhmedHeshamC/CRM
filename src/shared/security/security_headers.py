"""
Enhanced Security Headers Middleware for Production Security Hardening
Following SOLID principles and enterprise-grade security standards
"""

import logging
import secrets
from typing import Dict, List, Optional, Any
from django.http import HttpResponse
from django.conf import settings
from django.utils import timezone
from shared.security.exceptions import SecurityHeadersError

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware:
    """
    Enhanced Security Headers Middleware
    Following Single Responsibility Principle for security header management

    Security Headers Implemented:
    - X-Content-Type-Options: Prevents MIME-type sniffing
    - X-Frame-Options: Prevents clickjacking attacks
    - X-XSS-Protection: Enables XSS protection in older browsers
    - Strict-Transport-Security (HSTS): Enforces HTTPS connections
    - Content-Security-Policy (CSP): Prevents various injection attacks
    - Referrer-Policy: Controls referrer information leakage
    - Feature-Policy/Permissions-Policy: Controls browser feature access
    """

    def __init__(
        self,
        get_response,
        custom_headers: Optional[Dict[str, str]] = None,
        exempt_paths: Optional[List[str]] = None
    ):
        """
        Initialize security headers middleware
        Following Dependency Inversion Principle for configuration
        """
        self.get_response = get_response
        self.custom_headers = custom_headers or {}
        self.exempt_paths = exempt_paths or []

        # Security settings from Django settings
        self.enable_hsts = getattr(settings, 'SECURE_HSTS_ENABLED', not settings.DEBUG)
        self.hsts_max_age = getattr(settings, 'SECURE_HSTS_SECONDS', 31536000)
        self.hsts_include_subdomains = getattr(settings, 'SECURE_HSTS_INCLUDE_SUBDOMAINS', True)
        self.hsts_preload = getattr(settings, 'SECURE_HSTS_PRELOAD', True)

        # CSP configuration
        self.enable_csp = getattr(settings, 'ENABLE_CSP', not settings.DEBUG)
        self.csp_report_only = getattr(settings, 'CSP_REPORT_ONLY', False)
        self.csp_report_uri = getattr(settings, 'CSP_REPORT_URI', '/api/security/csp-report/')

        # Feature policy configuration
        self.enable_feature_policy = getattr(settings, 'ENABLE_FEATURE_POLICY', True)

        # Security monitoring
        self.enable_security_logging = getattr(settings, 'SECURITY_HEADERS_LOGGING', True)

    def __call__(self, request):
        """
        Process response to add security headers
        Following SOLID principles for middleware implementation
        """
        response = self.get_response(request)

        try:
            # Add security headers
            self._add_security_headers(request, response)

            # Add custom headers
            self._add_custom_headers(response)

            # Log security header application if enabled
            if self.enable_security_logging:
                self._log_security_headers(request, response)

        except Exception as e:
            # Log error but don't break the response
            logger.error(f"Security headers middleware error: {str(e)}")

        return response

    def _add_security_headers(self, request, response: HttpResponse):
        """
        Add all security headers to response
        Following Single Responsibility Principle
        """
        # Basic security headers (always applied)
        self._add_basic_security_headers(response)

        # HSTS header (HTTPS enforcement)
        if self.enable_hsts and not settings.DEBUG:
            self._add_hsts_header(response)

        # CSP header (Content Security Policy)
        if self.enable_csp:
            self._add_csp_header(request, response)

        # Referrer Policy header
        self._add_referrer_policy_header(response)

        # Feature Policy / Permissions Policy header
        if self.enable_feature_policy:
            self._add_feature_policy_header(response)

    def _add_basic_security_headers(self, response: HttpResponse):
        """
        Add basic security headers
        Following Single Responsibility Principle
        """
        # Prevent MIME-type sniffing
        response['X-Content-Type-Options'] = 'nosniff'

        # Prevent clickjacking
        response['X-Frame-Options'] = 'DENY'

        # XSS protection (legacy browser support)
        response['X-XSS-Protection'] = '1; mode=block'

        # Additional security headers
        response['X-Permitted-Cross-Domain-Policies'] = 'none'
        response['X-Download-Options'] = 'noopen'

    def _add_hsts_header(self, response: HttpResponse):
        """
        Add HTTP Strict Transport Security header
        Following Single Responsibility Principle
        """
        hsts_value = f"max-age={self.hsts_max_age}"

        if self.hsts_include_subdomains:
            hsts_value += "; includeSubDomains"

        if self.hsts_preload:
            hsts_value += "; preload"

        response['Strict-Transport-Security'] = hsts_value

    def _add_csp_header(self, request, response: HttpResponse):
        """
        Add Content Security Policy header
        Following Single Responsibility Principle with dynamic policy generation
        """
        csp_directives = self._generate_csp_policy(request, response)

        if self.csp_report_only:
            response['Content-Security-Policy-Report-Only'] = csp_directives
        else:
            response['Content-Security-Policy'] = csp_directives

    def _generate_csp_policy(self, request, response: HttpResponse) -> str:
        """
        Generate CSP policy based on request and response
        Following Single Responsibility Principle with context awareness
        """
        directives = []

        # Default source directive
        directives.append("default-src 'self'")

        # Script sources
        script_sources = ["'self'"]
        if getattr(settings, 'CSP_ALLOW_SCRIPT_INLINE', False):
            script_sources.append("'unsafe-inline'")
        if getattr(settings, 'CSP_ALLOW_SCRIPT_EVAL', False):
            script_sources.append("'unsafe-eval'")
        directives.append(f"script-src {' '.join(script_sources)}")

        # Style sources
        style_sources = ["'self'"]
        if getattr(settings, 'CSP_ALLOW_STYLE_INLINE', True):
            style_sources.append("'unsafe-inline'")
        directives.append(f"style-src {' '.join(style_sources)}")

        # Image sources
        img_sources = ["'self'", "data:", "https:"]
        if hasattr(settings, 'CSP_IMG_DOMAINS'):
            img_sources.extend(settings.CSP_IMG_DOMAINS)
        directives.append(f"img-src {' '.join(img_sources)}")

        # Font sources
        font_sources = ["'self'", "data:"]
        if hasattr(settings, 'CSP_FONT_DOMAINS'):
            font_sources.extend(settings.CSP_FONT_DOMAINS)
        directives.append(f"font-src {' '.join(font_sources)}")

        # Connect sources (API calls)
        connect_sources = ["'self'"]
        if hasattr(settings, 'CSP_CONNECT_DOMAINS'):
            connect_sources.extend(settings.CSP_CONNECT_DOMAINS)
        directives.append(f"connect-src {' '.join(connect_sources)}")

        # Media sources
        directives.append("media-src 'self' https:")

        # Object sources
        directives.append("object-src 'none'")

        # Frame sources
        directives.append("frame-src 'none'")

        # Frame ancestors (prevent clickjacking)
        directives.append("frame-ancestors 'none'")

        # Base URI
        directives.append("base-uri 'self'")

        # Form action
        directives.append("form-action 'self'")

        # Manifest sources
        directives.append("manifest-src 'self'")

        # Worker sources
        directives.append("worker-src 'self'")

        # Report URI (for CSP violations)
        if self.csp_report_uri:
            directives.append(f"report-uri {self.csp_report_uri}")

        # Add nonce for inline scripts if supported
        if hasattr(request, 'csp_nonce') and request.csp_nonce:
            # Update script-src with nonce
            script_directive = next((d for d in directives if d.startswith('script-src ')), None)
            if script_directive:
                script_directive += f" 'nonce-{request.csp_nonce}'"
                directives[directives.index(script_directive)] = script_directive

        return '; '.join(directives)

    def _add_referrer_policy_header(self, response: HttpResponse):
        """
        Add Referrer Policy header
        Following Single Responsibility Principle
        """
        referrer_policy = getattr(settings, 'REFERRER_POLICY', 'strict-origin-when-cross-origin')
        response['Referrer-Policy'] = referrer_policy

    def _add_feature_policy_header(self, response: HttpResponse):
        """
        Add Feature Policy / Permissions Policy header
        Following Single Responsibility Principle
        """
        # Feature policies (deprecated but still supported)
        feature_policies = [
            'geometer=()',
            'microphone=()',
            'camera=()',
            'payment=()',
            'usb=()',
            'magnetometer=()',
            'gyroscope=()',
            'accelerometer=()',
            'ambient-light-sensor=()',
        ]

        if getattr(settings, 'ENABLE_FEATURE_POLICY', True):
            response['Feature-Policy'] = ', '.join(feature_policies)

        # Permissions Policy (newer standard)
        permissions_policies = [
            'geometer=()',
            'microphone=()',
            'camera=()',
            'payment=()',
            'usb=()',
            'magnetometer=()',
            'gyroscope=()',
            'accelerometer=()',
            'ambient-light-sensor=()',
            'interest-cohort=()',  # Disable FLoC
        ]

        if getattr(settings, 'ENABLE_PERMISSIONS_POLICY', True):
            response['Permissions-Policy'] = ', '.join(permissions_policies)

    def _add_custom_headers(self, response: HttpResponse):
        """
        Add custom security headers
        Following Open/Closed Principle for extensibility
        """
        for header_name, header_value in self.custom_headers.items():
            response[header_name] = header_value

    def _log_security_headers(self, request, response: HttpResponse):
        """
        Log security header application for monitoring
        Following Single Responsibility Principle
        """
        try:
            security_headers = [
                'X-Content-Type-Options',
                'X-Frame-Options',
                'X-XSS-Protection',
                'Strict-Transport-Security',
                'Content-Security-Policy',
                'Content-Security-Policy-Report-Only',
                'Referrer-Policy',
                'Feature-Policy',
                'Permissions-Policy'
            ]

            applied_headers = {
                header: response.get(header)
                for header in security_headers
                if response.get(header)
            }

            if applied_headers:
                logger.debug(
                    f"Security headers applied to {request.method} {request.path}",
                    extra={
                        'request_method': request.method,
                        'request_path': request.path,
                        'security_headers': applied_headers,
                        'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                        'ip_address': self._get_client_ip(request)
                    }
                )

        except Exception as e:
            logger.error(f"Failed to log security headers: {str(e)}")

    def _get_client_ip(self, request) -> str:
        """
        Get client IP address from request
        Following Single Responsibility Principle with proxy support
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')

        return ip or 'unknown'


class AdvancedSecurityHeadersMiddleware(SecurityHeadersMiddleware):
    """
    Advanced Security Headers Middleware with additional features
    Following Open/Closed Principle for extensibility

    Additional Features:
    - CSP nonce generation and management
    - CSP violation reporting
    - Dynamic CSP based on content type
    - Subresource Integrity (SRI) metadata
    - Cache control headers
    - API security headers
    """

    def __init__(self, get_response, **kwargs):
        """
        Initialize advanced security headers middleware
        Following Dependency Inversion Principle
        """
        super().__init__(get_response, **kwargs)

        # Advanced features configuration
        self.enable_csp_nonce = getattr(settings, 'ENABLE_CSP_NONCE', False)
        self.enable_csp_reporting = getattr(settings, 'ENABLE_CSP_REPORTING', False)
        self.enable_sri = getattr(settings, 'ENABLE_SRI', False)
        self.enable_cache_control = getattr(settings, 'ENABLE_CACHE_CONTROL', True)
        self.enable_api_security = getattr(settings, 'ENABLE_API_SECURITY', True)

    def __call__(self, request):
        """
        Process request with advanced security features
        Following SOLID principles
        """
        # Generate CSP nonce if enabled
        if self.enable_csp_nonce:
            request.csp_nonce = secrets.token_urlsafe(16)

        response = self.get_response(request)

        try:
            # Add standard security headers
            self._add_security_headers(request, response)

            # Add advanced security features
            if self.enable_api_security and request.path.startswith('/api/'):
                self._add_api_security_headers(response)

            if self.enable_cache_control:
                self._add_cache_control_headers(request, response)

            if self.enable_sri:
                self._add_sri_metadata(response)

            # Add custom headers
            self._add_custom_headers(response)

            # Log security header application
            if self.enable_security_logging:
                self._log_security_headers(request, response)

        except Exception as e:
            logger.error(f"Advanced security headers middleware error: {str(e)}")

        return response

    def _add_api_security_headers(self, response: HttpResponse):
        """
        Add API-specific security headers
        Following Single Responsibility Principle
        """
        # API rate limit information (if available)
        response['X-API-Version'] = getattr(settings, 'API_VERSION', '1.0.0')

        # API security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Download-Options'] = 'noopen'
        response['X-Permitted-Cross-Domain-Policies'] = 'none'

        # Prevent caching of API responses
        if 'Cache-Control' not in response:
            response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'

    def _add_cache_control_headers(self, request, response: HttpResponse):
        """
        Add cache control headers based on response type
        Following Single Responsibility Principle
        """
        if 'Cache-Control' in response:
            return  # Skip if already set

        # Don't cache API responses
        if request.path.startswith('/api/'):
            response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'

        # Set caching policy for static assets
        elif request.path.startswith('/static/'):
            response['Cache-Control'] = 'public, max-age=31536000, immutable'

        # Set caching policy for media files
        elif request.path.startswith('/media/'):
            response['Cache-Control'] = 'public, max-age=86400'

        # Default caching policy
        else:
            response['Cache-Control'] = 'private, max-age=3600'

    def _add_sri_metadata(self, response: HttpResponse):
        """
        Add Subresource Integrity metadata headers
        Following Single Responsibility Principle
        """
        if hasattr(response, 'content_type') and response.content_type == 'text/html':
            # Add SRI metadata header for HTML responses
            response['X-Content-Security-Policy'] = 'sri-enabled'

    def _generate_csp_policy(self, request, response: HttpResponse) -> str:
        """
        Generate enhanced CSP policy with advanced features
        Following Single Responsibility Principle
        """
        base_csp = super()._generate_csp_policy(request, response)

        # Add report-to directive if CSP reporting is enabled
        if self.enable_csp_reporting and hasattr(settings, 'CSP_REPORT_TO_GROUP'):
            base_csp += f"; report-to {settings.CSP_REPORT_TO_GROUP}"

        # Add worker-src with nonce if CSP nonce is enabled
        if self.enable_csp_nonce and hasattr(request, 'csp_nonce'):
            base_csp += f"; worker-src 'self' 'nonce-{request.csp_nonce}'"

        return base_csp

    def _log_security_headers(self, request, response: HttpResponse):
        """
        Enhanced logging with additional security monitoring
        Following Single Responsibility Principle
        """
        super()._log_security_headers(request, response)

        # Log additional security metrics
        try:
            security_metrics = {
                'has_csp': bool(response.get('Content-Security-Policy')),
                'has_hsts': bool(response.get('Strict-Transport-Security')),
                'csp_nonce_used': hasattr(request, 'csp_nonce') and request.csp_nonce is not None,
                'is_api_request': request.path.startswith('/api/'),
                'response_size': len(response.content) if hasattr(response, 'content') else 0,
            }

            logger.debug(
                f"Advanced security metrics for {request.method} {request.path}",
                extra={
                    'security_metrics': security_metrics,
                    'timestamp': timezone.now().isoformat(),
                }
            )

        except Exception as e:
            logger.error(f"Failed to log advanced security metrics: {str(e)}")