"""
Enhanced CORS Policy Enforcement for Production Security Hardening
Following SOLID principles and enterprise-grade security standards
"""

import re
import json
import logging
from typing import Dict, List, Optional, Any, Set
from django.http import HttpResponse
from django.conf import settings
from django.utils import timezone
from rest_framework import status
from shared.security.exceptions import CORSPolicyError

logger = logging.getLogger(__name__)


class CORSPolicyEnforcer:
    """
    Enhanced CORS Policy Enforcer
    Following Single Responsibility Principle for CORS security

    Features:
    - Dynamic origin validation
    - Environment-specific CORS policies
    - Request method validation
    - Header validation
    - Credential policy enforcement
    - Security logging
    - CORS violation tracking
    """

    def __init__(self):
        """
        Initialize CORS policy enforcer
        Following Dependency Inversion Principle for configuration
        """
        # Load configuration from Django settings
        self.allowed_origins = self._load_allowed_origins()
        self.allowed_methods = getattr(settings, 'CORS_ALLOWED_METHODS', [
            'GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS', 'HEAD'
        ])
        self.allowed_headers = getattr(settings, 'CORS_ALLOWED_HEADERS', [
            'accept', 'accept-encoding', 'authorization', 'content-type',
            'dnt', 'origin', 'user-agent', 'x-csrftoken', 'x-requested-with'
        ])
        self.exposed_headers = getattr(settings, 'CORS_EXPOSED_HEADERS', [
            'content-length', 'content-type', 'x-total-count', 'x-page-count'
        ])

        # CORS policy settings
        self.allow_credentials = getattr(settings, 'CORS_ALLOW_CREDENTIALS', False)
        self.max_age = getattr(settings, 'CORS_MAX_AGE', 86400)  # 24 hours
        self.strict_mode = getattr(settings, 'CORS_STRICT_MODE', True)
        self.enable_logging = getattr(settings, 'CORS_LOGGING', True)

        # Advanced security settings
        self.origin_regex_patterns = getattr(settings, 'CORS_ORIGIN_REGEX_WHITELIST', [])
        self.subdomain_policy = getattr(settings, 'CORS_SUBDOMAIN_POLICY', 'strict')  # strict, permissive, disabled
        self.dev_origins = getattr(settings, 'CORS_DEV_ORIGINS', [
            'http://localhost:3000',
            'http://127.0.0.1:3000',
            'http://localhost:8080',
            'http://127.0.0.1:8080'
        ])

        # Pre-flight cache
        self._preflight_cache = {}
        self._cache_timeout = 300  # 5 minutes

        # Statistics
        self.stats = {
            'total_requests': 0,
            'allowed_requests': 0,
            'blocked_requests': 0,
            'preflight_requests': 0,
            'violations_by_origin': {},
            'violations_by_reason': {}
        }

    def _load_allowed_origins(self) -> Set[str]:
        """
        Load allowed origins from settings
        Following Single Responsibility Principle
        """
        origins = set()

        # Production origins
        production_origins = getattr(settings, 'CORS_ALLOWED_ORIGINS', [])
        origins.update(production_origins)

        # Add environment-specific origins
        if settings.DEBUG:
            dev_origins = getattr(settings, 'CORS_DEV_ORIGINS', [
                'http://localhost:3000',
                'http://127.0.0.1:3000',
                'http://localhost:8080'
            ])
            origins.update(dev_origins)
        else:
            # Production origins from settings
            prod_origins = getattr(settings, 'CORS_PROD_ORIGINS', [])
            origins.update(prod_origins)

        # Staging origins
        if getattr(settings, 'STAGING', False):
            staging_origins = getattr(settings, 'CORS_STAGING_ORIGINS', [])
            origins.update(staging_origins)

        return origins

    def validate_origin(self, origin: str) -> Dict[str, Any]:
        """
        Validate request origin against CORS policy
        Following Single Responsibility Principle with comprehensive validation
        """
        if not origin:
            return {
                'is_valid': False,
                'reason': 'missing_origin',
                'message': 'Origin header is required'
            }

        self.stats['total_requests'] += 1

        # Check exact origin match
        if origin in self.allowed_origins:
            self.stats['allowed_requests'] += 1
            return {
                'is_valid': True,
                'reason': 'exact_match',
                'policy_level': 'allowed'
            }

        # Check regex patterns
        for pattern in self.origin_regex_patterns:
            if re.match(pattern, origin):
                self.stats['allowed_requests'] += 1
                return {
                    'is_valid': True,
                    'reason': 'regex_match',
                    'pattern': pattern,
                    'policy_level': 'allowed'
                }

        # Check subdomain policy
        subdomain_result = self._validate_subdomain_origin(origin)
        if subdomain_result['is_valid']:
            self.stats['allowed_requests'] += 1
            return subdomain_result

        # Check wildcard patterns
        wildcard_result = self._validate_wildcard_origin(origin)
        if wildcard_result['is_valid']:
            self.stats['allowed_requests'] += 1
            return wildcard_result

        # Origin is not allowed
        self.stats['blocked_requests'] += 1
        self._record_violation(origin, 'origin_not_allowed')

        return {
            'is_valid': False,
            'reason': 'origin_not_allowed',
            'message': f'Origin {origin} is not allowed by CORS policy',
            'policy_level': 'blocked'
        }

    def _validate_subdomain_origin(self, origin: str) -> Dict[str, Any]:
        """
        Validate origin against subdomain policy
        Following Single Responsibility Principle
        """
        if self.subdomain_policy == 'disabled':
            return {'is_valid': False, 'reason': 'subdomain_policy_disabled'}

        try:
            from urllib.parse import urlparse
            parsed = urlparse(origin)
            domain = parsed.netloc.lower()

            # Check if it's a subdomain of any allowed domain
            for allowed_origin in self.allowed_origins:
                allowed_parsed = urlparse(allowed_origin)
                allowed_domain = allowed_parsed.netloc.lower()

                # Check if origin is a subdomain of allowed origin
                if domain.endswith('.' + allowed_domain) or domain == allowed_domain:
                    if self.subdomain_policy == 'permissive':
                        return {
                            'is_valid': True,
                            'reason': 'subdomain_match_permissive',
                            'parent_domain': allowed_domain,
                            'policy_level': 'allowed'
                        }
                    elif self.subdomain_policy == 'strict':
                        # Additional validation for strict mode
                        if self._validate_strict_subdomain(domain, allowed_domain):
                            return {
                                'is_valid': True,
                                'reason': 'subdomain_match_strict',
                                'parent_domain': allowed_domain,
                                'policy_level': 'allowed'
                            }

        except Exception as e:
            logger.error(f"Subdomain validation error: {str(e)}")

        return {'is_valid': False, 'reason': 'no_subdomain_match'}

    def _validate_strict_subdomain(self, subdomain: str, parent_domain: str) -> bool:
        """
        Validate subdomain under strict policy
        Following Single Responsibility Principle
        """
        # Extract subdomain part
        if subdomain.endswith('.' + parent_domain):
            subdomain_part = subdomain[:-len('.' + parent_domain)]
        else:
            return False

        # Validate subdomain part (no dots, no suspicious patterns)
        if '.' in subdomain_part:
            return False

        # Check for suspicious subdomain patterns
        suspicious_patterns = [
            r'^www\d+\.',  # www with numbers
            r'^test\d+\.',  # test with numbers
            r'^dev\d+\.',   # dev with numbers
            r'^staging\d+\.',  # staging with numbers
        ]

        subdomain_lower = subdomain_part.lower()
        for pattern in suspicious_patterns:
            if re.match(pattern, subdomain_lower):
                return False

        return True

    def _validate_wildcard_origin(self, origin: str) -> Dict[str, Any]:
        """
        Validate origin against wildcard patterns
        Following Single Responsibility Principle
        """
        for allowed_origin in self.allowed_origins:
            if '*' in allowed_origin:
                # Convert wildcard to regex
                pattern = allowed_origin.replace('*', '.*')
                if re.match(pattern, origin):
                    return {
                        'is_valid': True,
                        'reason': 'wildcard_match',
                        'pattern': allowed_origin,
                        'policy_level': 'allowed'
                    }

        return {'is_valid': False, 'reason': 'no_wildcard_match'}

    def validate_method(self, method: str) -> Dict[str, Any]:
        """
        Validate HTTP method against CORS policy
        Following Single Responsibility Principle
        """
        if method.upper() in self.allowed_methods:
            return {
                'is_valid': True,
                'reason': 'method_allowed'
            }

        return {
            'is_valid': False,
            'reason': 'method_not_allowed',
            'message': f'Method {method} is not allowed by CORS policy',
            'allowed_methods': self.allowed_methods
        }

    def validate_headers(self, headers: List[str]) -> Dict[str, Any]:
        """
        Validate request headers against CORS policy
        Following Single Responsibility Principle
        """
        invalid_headers = []
        valid_headers = []

        for header in headers:
            header_lower = header.lower().strip()
            if header_lower in [h.lower() for h in self.allowed_headers]:
                valid_headers.append(header)
            else:
                invalid_headers.append(header)

        if invalid_headers:
            return {
                'is_valid': False,
                'reason': 'headers_not_allowed',
                'invalid_headers': invalid_headers,
                'allowed_headers': self.allowed_headers
            }

        return {
            'is_valid': True,
            'reason': 'headers_allowed',
            'valid_headers': valid_headers
        }

    def create_cors_headers(self, origin: str, method: str = None, headers: List[str] = None) -> Dict[str, str]:
        """
        Create appropriate CORS headers for response
        Following Single Responsibility Principle
        """
        cors_headers = {}

        # Always include origin if it's valid
        if origin:
            origin_validation = self.validate_origin(origin)
            if origin_validation['is_valid']:
                cors_headers['Access-Control-Allow-Origin'] = origin

                # Vary header for proper caching
                cors_headers['Vary'] = 'Origin'

        # Method-specific headers
        if method:
            method_validation = self.validate_method(method)
            if method_validation['is_valid']:
                cors_headers['Access-Control-Allow-Methods'] = ', '.join(self.allowed_methods)

        # Header-specific headers
        if headers:
            header_validation = self.validate_headers(headers)
            if header_validation['is_valid']:
                cors_headers['Access-Control-Allow-Headers'] = ', '.join(self.allowed_headers)

        # Credentials header
        if self.allow_credentials:
            cors_headers['Access-Control-Allow-Credentials'] = 'true'

        # Exposed headers
        if self.exposed_headers:
            cors_headers['Access-Control-Expose-Headers'] = ', '.join(self.exposed_headers)

        # Max age for pre-flight requests
        if method and method.upper() == 'OPTIONS':
            cors_headers['Access-Control-Max-Age'] = str(self.max_age)

        return cors_headers

    def handle_preflight_request(self, request) -> HttpResponse:
        """
        Handle CORS pre-flight request
        Following Single Responsibility Principle
        """
        self.stats['preflight_requests'] += 1

        origin = request.META.get('HTTP_ORIGIN')
        method = request.META.get('HTTP_ACCESS_CONTROL_REQUEST_METHOD')
        headers = request.META.get('HTTP_ACCESS_CONTROL_REQUEST_HEADERS', '').split(',')

        # Validate origin
        origin_validation = self.validate_origin(origin)
        if not origin_validation['is_valid']:
            self._log_preflight_violation(request, origin_validation)
            return self._create_error_response(origin_validation, status.HTTP_403_FORBIDDEN)

        # Validate method
        method_validation = self.validate_method(method)
        if not method_validation['is_valid']:
            self._log_preflight_violation(request, method_validation)
            return self._create_error_response(method_validation, status.HTTP_405_METHOD_NOT_ALLOWED)

        # Validate headers
        if headers:
            header_validation = self.validate_headers(headers)
            if not header_validation['is_valid']:
                self._log_preflight_violation(request, header_validation)
                return self._create_error_response(header_validation, status.HTTP_400_BAD_REQUEST)

        # Create successful pre-flight response
        response = HttpResponse()
        cors_headers = self.create_cors_headers(origin, method, headers)

        for header, value in cors_headers.items():
            response[header] = value

        return response

    def _create_error_response(self, validation_result: Dict[str, Any], status_code: int) -> HttpResponse:
        """
        Create CORS error response
        Following Single Responsibility Principle
        """
        response = HttpResponse(
            content=json.dumps({
                'error': 'CORS policy violation',
                'code': validation_result['reason'],
                'message': validation_result.get('message', 'CORS policy validation failed')
            }),
            status=status_code,
            content_type='application/json'
        )

        # Add CORS headers to help with debugging
        if 'message' in validation_result:
            response['Access-Control-Allow-Origin'] = '*'
            response['Access-Control-Allow-Methods'] = ', '.join(self.allowed_methods)
            response['Access-Control-Allow-Headers'] = ', '.join(self.allowed_headers)

        return response

    def _record_violation(self, origin: str, reason: str):
        """
        Record CORS violation for monitoring
        Following Single Responsibility Principle
        """
        # Track violations by origin
        if origin not in self.stats['violations_by_origin']:
            self.stats['violations_by_origin'][origin] = 0
        self.stats['violations_by_origin'][origin] += 1

        # Track violations by reason
        if reason not in self.stats['violations_by_reason']:
            self.stats['violations_by_reason'][reason] = 0
        self.stats['violations_by_reason'][reason] += 1

        # Log violation
        if self.enable_logging:
            logger.warning(
                f"CORS policy violation: {reason} from origin {origin}",
                extra={
                    'origin': origin,
                    'violation_reason': reason,
                    'timestamp': timezone.now().isoformat()
                }
            )

    def _log_preflight_violation(self, request, validation_result: Dict[str, Any]):
        """
        Log pre-flight request violations
        Following Single Responsibility Principle
        """
        if self.enable_logging:
            logger.warning(
                f"CORS pre-flight request blocked: {validation_result['reason']}",
                extra={
                    'origin': request.META.get('HTTP_ORIGIN'),
                    'method': request.META.get('HTTP_ACCESS_CONTROL_REQUEST_METHOD'),
                    'headers': request.META.get('HTTP_ACCESS_CONTROL_REQUEST_HEADERS'),
                    'validation_reason': validation_result['reason'],
                    'timestamp': timezone.now().isoformat()
                }
            )

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get CORS enforcement statistics
        Following Single Responsibility Principle
        """
        total_requests = self.stats['total_requests']
        allowed_requests = self.stats['allowed_requests']
        blocked_requests = self.stats['blocked_requests']

        return {
            'total_requests': total_requests,
            'allowed_requests': allowed_requests,
            'blocked_requests': blocked_requests,
            'preflight_requests': self.stats['preflight_requests'],
            'allow_rate': (allowed_requests / max(total_requests, 1)) * 100,
            'block_rate': (blocked_requests / max(total_requests, 1)) * 100,
            'violations_by_origin': self.stats['violations_by_origin'],
            'violations_by_reason': self.stats['violations_by_reason'],
            'policy_config': {
                'allowed_origins_count': len(self.allowed_origins),
                'allowed_methods': self.allowed_methods,
                'allow_credentials': self.allow_credentials,
                'strict_mode': self.strict_mode,
                'subdomain_policy': self.subdomain_policy
            }
        }

    def reset_statistics(self):
        """
        Reset CORS enforcement statistics
        Following Single Responsibility Principle
        """
        self.stats = {
            'total_requests': 0,
            'allowed_requests': 0,
            'blocked_requests': 0,
            'preflight_requests': 0,
            'violations_by_origin': {},
            'violations_by_reason': {}
        }


class CORSMiddleware:
    """
    Django CORS Middleware with Enhanced Security Features
    Following Single Responsibility Principle for request processing

    Features:
    - Pre-flight request handling
    - Simple request processing
    - Dynamic CORS headers
    - Security enforcement
    - Performance optimization
    """

    def __init__(self, get_response):
        """
        Initialize CORS middleware
        Following Dependency Inversion Principle
        """
        self.get_response = get_response
        self.policy_enforcer = CORSPolicyEnforcer()

        # Performance optimization settings
        self.cache_enabled = getattr(settings, 'CORS_CACHE_ENABLED', True)
        self.cache_timeout = getattr(settings, 'CORS_CACHE_TIMEOUT', 300)  # 5 minutes

        # Header cache for performance
        self._header_cache = {}
        self._cache_timestamp = 0
        self._cache_ttl = 60  # 1 minute for header cache

    def __call__(self, request):
        """
        Process request through CORS middleware
        Following SOLID principles for middleware implementation
        """
        # Check if this is a pre-flight request
        if request.method == 'OPTIONS':
            return self.policy_enforcer.handle_preflight_request(request)

        # Process normal request
        response = self.get_response(request)

        # Add CORS headers to response
        self._add_cors_headers(request, response)

        return response

    def _add_cors_headers(self, request, response: HttpResponse):
        """
        Add CORS headers to response
        Following Single Responsibility Principle
        """
        origin = request.META.get('HTTP_ORIGIN')
        if not origin:
            return  # No origin header, no CORS headers needed

        try:
            # Validate origin
            origin_validation = self.policy_enforcer.validate_origin(origin)
            if origin_validation['is_valid']:
                # Add allowed origin header
                response['Access-Control-Allow-Origin'] = origin
                response['Vary'] = 'Origin'

                # Add credentials header if allowed
                if self.policy_enforcer.allow_credentials:
                    response['Access-Control-Allow-Credentials'] = 'true'

                # Add exposed headers
                if self.policy_enforcer.exposed_headers:
                    response['Access-Control-Expose-Headers'] = ', '.join(self.policy_enforcer.exposed_headers)

            elif settings.DEBUG:
                # In debug mode, add helpful error information
                response['Access-Control-Allow-Origin'] = '*'
                response['Access-Control-Allow-Methods'] = ', '.join(self.policy_enforcer.allowed_methods)
                response['Access-Control-Allow-Headers'] = ', '.join(self.policy_enforcer.allowed_headers)

        except Exception as e:
            logger.error(f"Error adding CORS headers: {str(e)}")
            # Don't fail the request due to CORS header issues

    def get_cors_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive CORS statistics
        Following Single Responsibility Principle
        """
        return self.policy_enforcer.get_statistics()

    def reset_cors_statistics(self):
        """
        Reset CORS statistics
        Following Single Responsibility Principle
        """
        self.policy_enforcer.reset_statistics()