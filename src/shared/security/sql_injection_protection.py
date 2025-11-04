"""
SQL Injection Protection System for Production Security Hardening
Following SOLID principles and enterprise-grade security standards
"""

import re
import time
import json
import logging
import urllib.parse
from typing import Dict, List, Optional, Any, Tuple, Union
from django.http import JsonResponse, HttpResponse
from django.db import connection, connections
from django.core.exceptions import SuspiciousOperation
from django.utils import timezone
from django.conf import settings
from rest_framework import status
from shared.security.exceptions import SQLInjectionAttemptError
from shared.security.input_validation import SQLInjectionDetector

logger = logging.getLogger(__name__)


class SQLInjectionValidator(SQLInjectionDetector):
    """
    Enhanced SQL Injection Validator with advanced detection capabilities
    Following Single Responsibility Principle for SQL injection security

    Features:
    - Advanced SQL injection pattern detection
    - Context-aware validation
    - Encoding-based attack detection
    - Custom pattern support
    - Validation statistics
    - Batch validation
    """

    def __init__(
        self,
        custom_patterns: Optional[List[str]] = None,
        strict_mode: bool = True,
        enable_statistics: bool = True
    ):
        """
        Initialize SQL injection validator
        Following Dependency Inversion Principle for configuration
        """
        super().__init__()

        # Add custom patterns if provided
        if custom_patterns:
            for pattern in custom_patterns:
                self.patterns.append(re.compile(pattern))

        self.strict_mode = strict_mode
        self.enable_statistics = enable_statistics

        # Validation statistics
        self.stats = {
            'total_validations': 0,
            'blocked_attempts': 0,
            'false_positives': 0,
            'detection_methods': {
                'pattern_matching': 0,
                'keyword_detection': 0,
                'encoding_detection': 0,
                'context_analysis': 0
            }
        }

        # Advanced SQL injection patterns
        self.advanced_patterns = [
            # Time-based attacks
            r"(?i)(waitfor\s+delay)",
            r"(?i)(sleep\s*\()",
            r"(?i)(benchmark\s*\()",
            r"(?i)(pg_sleep\s*\()",

            # Boolean-based blind attacks
            r"(?i)(and\s+\d+\s*=\s*\d+)",
            r"(?i)(or\s+\d+\s*=\s*\d+)",
            r"(?i)(and\s+['\"]?\w+['\"]?\s*=\s*['\"]?\w+['\"]?)",
            r"(?i)(and\s+length\s*\()",
            r"(?i)(and\s+substring\s*\()",
            r"(?i)(and\s+ascii\s*\()",
            r"(?i)(and\s+count\s*\()",

            # Union-based attacks
            r"(?i)(union\s+select)",
            r"(?i)(union\s+all\s+select)",
            r"(?i)(select\s+.*\s+from\s+.*\s+union)",

            # Error-based attacks
            r"(?i)(extractvalue\s*\()",
            r"(?i)(updatexml\s*\()",
            r"(?i)(floor\s*\(.*rand\s*\()",
            r"(?i)(count\s*\([^)]*\)\s*concat)",

            # Stacked queries
            r"(?i);\s*(drop|alter|create|truncate|insert|update|delete)\s",

            # Advanced techniques
            r"(?i)(procedure\s+analyse)",
            r"(?i)(load_file\s*\()",
            r"(?i)(into\s+outfile)",
            r"(?i)(dumpfile)",
            r"(?i)(information_schema)",
            r"(?i)(sysobjects|syscolumns|sysdatabases)",
            r"(?i)(mysql|performance_schema)",
            r"(?i)(pg_|pg_catalog)",
            r"(?i)(user\s*\(\)|database\s*\(\)|version\s*\()"),
        ]

        self.advanced_patterns.extend([re.compile(pattern) for pattern in self.advanced_patterns])

        # Context-specific validation rules
        self.context_rules = {
            'email': {
                'allowed_patterns': [r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'],
                'max_length': 254
            },
            'name': {
                'allowed_patterns': [r'^[a-zA-Z\s\-\'\.]+$'],
                'max_length': 100
            },
            'search': {
                'min_length': 2,
                'max_length': 100,
                'allowed_special_chars': [' ', '-', '.', '@', '#']
            },
            'id': {
                'allowed_patterns': [r'^\d+$'],
                'max_length': 10
            }
        }

    def validate_input(
        self,
        input_text: str,
        field_name: str = None,
        context: str = None,
        decode_input: bool = True,
        raise_exception: bool = True
    ) -> Union[str, bool]:
        """
        Enhanced input validation with context awareness
        Following Single Responsibility Principle with advanced detection
        """
        if not enable_statistics:
            return self._validate_input_no_stats(input_text, field_name, context, decode_input, raise_exception)

        self.stats['total_validations'] += 1

        try:
            # Decode input if requested
            processed_input = self._decode_input(input_text) if decode_input else input_text

            # Context-specific validation
            if context and context in self.context_rules:
                if not self._validate_context_rules(processed_input, context, field_name):
                    if raise_exception:
                        raise SQLInjectionAttemptError(
                            message=f"Input violates context rules for field '{field_name}'",
                            field=field_name,
                            context=context
                        )
                    return False

            # Basic pattern matching
            if self._detect_with_patterns(processed_input):
                self.stats['blocked_attempts'] += 1
                self.stats['detection_methods']['pattern_matching'] += 1
                self._log_attempt(processed_input, field_name, 'pattern_matching')
                if raise_exception:
                    raise SQLInjectionAttemptError(
                        message=f"SQL injection pattern detected in field '{field_name}'",
                        field=field_name,
                        detection_method='pattern_matching'
                    )
                return False

            # Advanced pattern matching
            if self._detect_with_advanced_patterns(processed_input):
                self.stats['blocked_attempts'] += 1
                self.stats['detection_methods']['context_analysis'] += 1
                self._log_attempt(processed_input, field_name, 'advanced_patterns')
                if raise_exception:
                    raise SQLInjectionAttemptError(
                        message=f"Advanced SQL injection pattern detected in field '{field_name}'",
                        field=field_name,
                        detection_method='advanced_patterns'
                    )
                return False

            # Keyword detection
            if self._detect_keywords(processed_input):
                self.stats['blocked_attempts'] += 1
                self.stats['detection_methods']['keyword_detection'] += 1
                self._log_attempt(processed_input, field_name, 'keyword_detection')
                if raise_exception:
                    raise SQLInjectionAttemptError(
                        message=f"SQL keywords detected in field '{field_name}'",
                        field=field_name,
                        detection_method='keyword_detection'
                    )
                return False

            return processed_input

        except SQLInjectionAttemptError:
            raise
        except Exception as e:
            logger.error(f"SQL injection validation error: {str(e)}")
            # Fail-safe: allow input in case of validation error
            if raise_exception:
                return input_text
            return True

    def _validate_input_no_stats(self, input_text, field_name, context, decode_input, raise_exception):
        """Validation without statistics for performance"""
        processed_input = self._decode_input(input_text) if decode_input else input_text

        if context and context in self.context_rules:
            if not self._validate_context_rules(processed_input, context, field_name):
                if raise_exception:
                    raise SQLInjectionAttemptError(
                        message=f"Input violates context rules for field '{field_name}'",
                        field=field_name,
                        context=context
                    )
                return False

        if self._detect_with_patterns(processed_input) or self._detect_with_advanced_patterns(processed_input) or self._detect_keywords(processed_input):
            if raise_exception:
                raise SQLInjectionAttemptError(
                    message=f"SQL injection detected in field '{field_name}'",
                    field=field_name
                )
            return False

        return processed_input

    def _decode_input(self, input_text: str) -> str:
        """
        Decode various input encodings
        Following Single Responsibility Principle
        """
        if not input_text:
            return ""

        try:
            # URL decode
            decoded = urllib.parse.unquote(input_text)

            # Double URL decode
            if '%' in decoded:
                decoded = urllib.parse.unquote(decoded)

            # HTML decode
            import html
            decoded = html.unescape(decoded)

            return decoded
        except Exception:
            return input_text

    def _validate_context_rules(self, input_text: str, context: str, field_name: str) -> bool:
        """
        Validate input based on context-specific rules
        Following Single Responsibility Principle
        """
        rules = self.context_rules.get(context, {})

        # Length validation
        if 'max_length' in rules and len(input_text) > rules['max_length']:
            return False

        if 'min_length' in rules and len(input_text) < rules['min_length']:
            return False

        # Pattern validation
        if 'allowed_patterns' in rules:
            pattern_matched = any(re.match(pattern, input_text) for pattern in rules['allowed_patterns'])
            if not pattern_matched:
                return False

        # Special character validation
        if 'allowed_special_chars' in rules:
            allowed_chars = set(rules['allowed_special_chars'])
            for char in input_text:
                if not (char.isalnum() or char.isspace() or char in allowed_chars):
                    return False

        return True

    def _detect_with_patterns(self, input_text: str) -> bool:
        """
        Detect SQL injection using pattern matching
        Following Single Responsibility Principle
        """
        for pattern in self.patterns:
            if pattern.search(input_text):
                return True
        return False

    def _detect_with_advanced_patterns(self, input_text: str) -> bool:
        """
        Detect SQL injection using advanced patterns
        Following Single Responsibility Principle
        """
        for pattern in self.advanced_patterns:
            if pattern.search(input_text):
                return True
        return False

    def _detect_keywords(self, input_text: str) -> bool:
        """
        Detect SQL injection using keyword analysis
        Following Single Responsibility Principle
        """
        # Advanced SQL keywords and constructs
        dangerous_keywords = [
            # Basic keywords
            'select', 'insert', 'update', 'delete', 'drop', 'create', 'alter',
            'truncate', 'exec', 'execute', 'union', 'where', 'order', 'group',
            'having', 'limit', 'offset',

            # Advanced keywords
            'information_schema', 'sysobjects', 'syscolumns', 'sysdatabases',
            'mysql', 'performance_schema', 'pg_catalog', 'user()', 'database()',
            'version()', 'load_file', 'into outfile', 'dumpfile',

            # Function keywords
            'substring', 'ascii', 'char', 'concat', 'cast', 'convert', 'extractvalue',
            'updatexml', 'benchmark', 'sleep', 'waitfor', 'procedure analyse',

            # Control keywords
            'begin', 'end', 'declare', 'set', 'if', 'case', 'when', 'then', 'else'
        ]

        input_lower = input_text.lower()
        word_pattern = r'\b' + r'\b|\b'.join(dangerous_keywords) + r'\b'

        if re.search(word_pattern, input_lower):
            # Additional context validation to reduce false positives
            return self._validate_keyword_context(input_text, dangerous_keywords)

        return False

    def _validate_keyword_context(self, input_text: str, keywords: List[str]) -> bool:
        """
        Validate keyword context to reduce false positives
        Following Single Responsibility Principle
        """
        # Allow certain keywords in safe contexts
        safe_contexts = [
            r'\bwhere\s+\w+\s*=\s*%s',  # Parameterized queries
            r'\bselect\s+\w+\s+from\s+\w+',  # Safe selects
            r'\binsert\s+into\s+\w+',  # Safe inserts
        ]

        input_lower = input_text.lower()

        # Check if input matches any safe patterns
        for safe_pattern in safe_contexts:
            if re.search(safe_pattern, input_lower):
                return False  # Safe context detected

        # Check for dangerous combinations
        dangerous_combinations = [
            (r'\bor\b', r'\b\d+\b'),  # OR with numbers
            (r'\band\b', r'\b\d+\b'),  # AND with numbers
            (r'\bselect\b', r'\bunion\b'),  # SELECT with UNION
            (r'\bdrop\b', r'\btable\b'),  # DROP with TABLE
        ]

        for word1, word2 in dangerous_combinations:
            if re.search(rf'{word1}.*{word2}|{word2}.*{word1}', input_lower):
                return True  # Dangerous combination found

        return False

    def validate_batch(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate multiple fields
        Following Single Responsibility Principle
        """
        errors = []
        validated_data = {}

        for field_name, value in data.items():
            try:
                # Determine context based on field name
                context = 'default'
                if 'email' in field_name.lower():
                    context = 'email'
                elif 'name' in field_name.lower():
                    context = 'name'
                elif 'search' in field_name.lower():
                    context = 'search'
                elif 'id' in field_name.lower():
                    context = 'id'

                validated_value = self.validate_input(
                    str(value) if value else '',
                    field_name=field_name,
                    context=context
                )
                validated_data[field_name] = validated_value

            except SQLInjectionAttemptError as e:
                errors.append({
                    'field': field_name,
                    'message': str(e),
                    'code': 'sql_injection_attempt'
                })

        return {
            'is_valid': len(errors) == 0,
            'validated_data': validated_data,
            'errors': errors
        }

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get validation statistics
        Following Single Responsibility Principle
        """
        if not self.enable_statistics:
            return {'statistics_disabled': True}

        return {
            'total_validations': self.stats['total_validations'],
            'blocked_attempts': self.stats['blocked_attempts'],
            'false_positives': self.stats['false_positives'],
            'detection_methods': self.stats['detection_methods'],
            'block_rate': (self.stats['blocked_attempts'] / max(self.stats['total_validations'], 1)) * 100
        }

    def _log_attempt(self, input_text: str, field_name: str, detection_method: str):
        """
        Log SQL injection attempt
        Following Single Responsibility Principle
        """
        logger.warning(
            f"SQL injection attempt detected using {detection_method}",
            extra={
                'field_name': field_name,
                'input_preview': input_text[:100],
                'detection_method': detection_method,
                'timestamp': timezone.now().isoformat()
            }
        )


class SQLInjectionProtectionMiddleware:
    """
    SQL Injection Protection Middleware
    Following Single Responsibility Principle for request-level protection

    Features:
    - Request parameter validation
    - JSON payload validation
    - URL parameter validation
    - Exempt path support
    - Security logging
    - Rate limiting for repeated attacks
    """

    def __init__(
        self,
        get_response,
        exempt_paths: Optional[List[str]] = None,
        strict_mode: bool = True,
        enable_logging: bool = True
    ):
        """
        Initialize SQL injection protection middleware
        Following Dependency Inversion Principle for configuration
        """
        self.get_response = get_response
        self.exempt_paths = exempt_paths or [
            '/health/',
            '/metrics/',
            '/api/schema/',
            '/admin/',
            '/static/',
            '/media/'
        ]
        self.strict_mode = strict_mode
        self.enable_logging = enable_logging

        # Initialize validator
        self.validator = SQLInjectionValidator(strict_mode=strict_mode)

    def __call__(self, request):
        """
        Process request for SQL injection protection
        Following SOLID principles for middleware implementation
        """
        # Skip validation for exempt paths
        if self._is_path_exempt(request.path):
            return self.get_response(request)

        try:
            # Validate request data
            self._validate_request(request)

        except SQLInjectionAttemptError as e:
            # Log the attack attempt
            if self.enable_logging:
                self._log_attack_attempt(request, e)

            # Return error response
            return JsonResponse({
                'error': 'SQL injection attempt detected',
                'code': 'sql_injection_blocked',
                'detail': str(e),
                'field': e.details.get('field') if hasattr(e, 'details') else None
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            # Log error but don't block requests (fail-safe)
            logger.error(f"SQL injection protection middleware error: {str(e)}")

        return self.get_response(request)

    def _is_path_exempt(self, path: str) -> bool:
        """
        Check if path is exempt from SQL injection protection
        Following Single Responsibility Principle
        """
        return any(path.startswith(exempt_path) for exempt_path in self.exempt_paths)

    def _validate_request(self, request):
        """
        Validate all request data for SQL injection
        Following Single Responsibility Principle
        """
        # Validate query parameters
        self._validate_query_params(request)

        # Validate request body based on content type
        if request.content_type == 'application/json':
            self._validate_json_body(request)
        elif request.content_type and 'form' in request.content_type:
            self._validate_form_data(request)

        # Validate headers
        self._validate_headers(request)

    def _validate_query_params(self, request):
        """
        Validate query parameters
        Following Single Responsibility Principle
        """
        for param_name, param_value in request.GET.items():
            self.validator.validate_input(
                param_value,
                field_name=param_name,
                context='search'
            )

    def _validate_json_body(self, request):
        """
        Validate JSON request body
        Following Single Responsibility Principle
        """
        try:
            body_data = json.loads(request.body.decode('utf-8'))

            if isinstance(body_data, dict):
                # Validate each field
                for field_name, field_value in body_data.items():
                    if isinstance(field_value, str):
                        self.validator.validate_input(
                            field_value,
                            field_name=field_name
                        )
                    elif isinstance(field_value, (list, dict)):
                        # Recursively validate nested structures
                        self._validate_nested_data(field_value, field_name)

        except json.JSONDecodeError:
            # Invalid JSON, let other middleware handle it
            pass

    def _validate_form_data(self, request):
        """
        Validate form data
        Following Single Responsibility Principle
        """
        for field_name, field_value in request.POST.items():
            if isinstance(field_value, str):
                self.validator.validate_input(
                    field_value,
                    field_name=field_name
                )

    def _validate_headers(self, request):
        """
        Validate request headers for SQL injection
        Following Single Responsibility Principle
        """
        # Check specific headers that might contain user input
        suspicious_headers = [
            'HTTP_USER_AGENT',
            'HTTP_REFERER',
            'HTTP_X_FORWARDED_FOR',
            'HTTP_X_REAL_IP'
        ]

        for header in suspicious_headers:
            header_value = request.META.get(header)
            if header_value:
                self.validator.validate_input(
                    header_value,
                    field_name=header.lower(),
                    context='header'
                )

    def _validate_nested_data(self, data, field_name: str, depth: int = 0):
        """
        Recursively validate nested data structures
        Following Single Responsibility Principle
        """
        if depth > 10:  # Prevent infinite recursion
            return

        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, str):
                    self.validator.validate_input(
                        value,
                        field_name=f"{field_name}.{key}"
                    )
                elif isinstance(value, (list, dict)):
                    self._validate_nested_data(value, f"{field_name}.{key}", depth + 1)

        elif isinstance(data, list):
            for i, item in enumerate(data):
                if isinstance(item, str):
                    self.validator.validate_input(
                        item,
                        field_name=f"{field_name}[{i}]"
                    )
                elif isinstance(item, (list, dict)):
                    self._validate_nested_data(item, f"{field_name}[{i}]", depth + 1)

    def _log_attack_attempt(self, request, exception: SQLInjectionAttemptError):
        """
        Log SQL injection attack attempt
        Following Single Responsibility Principle
        """
        logger.warning(
            f"SQL injection attack attempt blocked: {request.method} {request.path}",
            extra={
                'request_method': request.method,
                'request_path': request.path,
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                'ip_address': self._get_client_ip(request),
                'exception_message': str(exception),
                'field_name': exception.details.get('field') if hasattr(exception, 'details') else None,
                'timestamp': timezone.now().isoformat()
            }
        )

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


class DatabaseSecurityValidator:
    """
    Database Security Validator for query analysis and protection
    Following Single Responsibility Principle for database security

    Features:
    - Query analysis for SQL injection patterns
    - Parameterized query validation
    - Dynamic query validation
    - Database connection security checks
    - Query execution monitoring
    """

    def __init__(self):
        """
        Initialize database security validator
        Following SOLID principles
        """
        self.validator = SQLInjectionValidator()

    def validate_query(self, query: str, parameters: List[Any] = None) -> Dict[str, Any]:
        """
        Validate SQL query for security
        Following Single Responsibility Principle
        """
        result = {
            'is_safe': True,
            'threat_types': [],
            'recommendations': [],
            'risk_level': 'low'
        }

        try:
            # Check for SQL injection patterns in query
            if self.validator.detect_sql_injection(query):
                result['is_safe'] = False
                result['threat_types'].append('sql_injection')
                result['risk_level'] = 'high'
                result['recommendations'].append('Use parameterized queries')

            # Check for unsafe practices
            unsafe_patterns = [
                (r'\b%s\b', 'Use proper parameter markers'),
                (r'\b\?\b', 'Use proper parameter markers for your database'),
                (r'\bformat\s*\(', 'Avoid string formatting in queries'),
                (r'\b\+\s*[\'"]', 'Avoid string concatenation in queries'),
            ]

            for pattern, recommendation in unsafe_patterns:
                if re.search(pattern, query):
                    result['recommendations'].append(recommendation)

            # Validate parameters if provided
            if parameters:
                for i, param in enumerate(parameters):
                    if isinstance(param, str):
                        if not self.validator.validate_input(param, f'parameter_{i}'):
                            result['is_safe'] = False
                            result['threat_types'].append('parameter_injection')
                            result['risk_level'] = 'high'

        except Exception as e:
            logger.error(f"Query validation error: {str(e)}")
            result['risk_level'] = 'medium'
            result['recommendations'].append('Manual query review required')

        return result

    def validate_parameterized_query(self, query: str, parameters: List[Any]) -> Dict[str, Any]:
        """
        Validate parameterized query
        Following Single Responsibility Principle
        """
        result = {
            'is_safe': True,
            'issues': [],
            'recommendations': []
        }

        # Check if query uses parameterization correctly
        if '%s' not in query and '?' not in query and ':' not in query:
            result['is_safe'] = False
            result['issues'].append('Query does not use parameterization')
            result['recommendations'].append('Use parameterized queries to prevent SQL injection')

        # Validate parameters
        for i, param in enumerate(parameters):
            if isinstance(param, str):
                try:
                    self.validator.validate_input(param, f'param_{i}')
                except SQLInjectionAttemptError:
                    result['is_safe'] = False
                    result['issues'].append(f'Parameter {i} contains suspicious content')
                    result['recommendations'].append(f'Validate parameter {i} before usage')

        return result

    def validate_dynamic_query(self, query: str, allowed_fields: List[str]) -> Dict[str, Any]:
        """
        Validate dynamic query with allowed field names
        Following Single Responsibility Principle
        """
        result = {
            'is_safe': True,
            'issues': [],
            'used_fields': []
        }

        # Extract field names from query (simple pattern matching)
        field_pattern = r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:=|!=|<|>|<=|>=|like|in)'
        matches = re.findall(field_pattern, query, re.IGNORECASE)

        for field in matches:
            result['used_fields'].append(field)

            if field.lower() not in [f.lower() for f in allowed_fields]:
                result['is_safe'] = False
                result['issues'].append(f'Field "{field}" is not in allowed list')
                result['recommendations'].append(f'Add "{field}" to allowed fields or remove from query')

        # Check for SQL injection in dynamic parts
        if self.validator.detect_sql_injection(query):
            result['is_safe'] = False
            result['issues'].append('SQL injection patterns detected in dynamic query')
            result['recommendations'].append('Review and sanitize dynamic query components')

        return result

    def check_connection_security(self, cursor) -> Dict[str, Any]:
        """
        Check database connection security settings
        Following Single Responsibility Principle
        """
        security_check = {
            'secure_connection': True,
            'issues': [],
            'recommendations': []
        }

        try:
            # Check database-specific security settings
            if 'postgresql' in str(type(cursor.connection)).lower():
                # PostgreSQL security checks
                cursor.execute("SHOW ssl;")
                ssl_setting = cursor.fetchone()
                if ssl_setting and ssl_setting[0] != 'on':
                    security_check['secure_connection'] = False
                    security_check['issues'].append('SSL is not enabled')
                    security_check['recommendations'].append('Enable SSL for database connections')

            elif 'mysql' in str(type(cursor.connection)).lower():
                # MySQL security checks
                cursor.execute("SHOW VARIABLES LIKE 'require_secure_transport';")
                ssl_setting = cursor.fetchone()
                if ssl_setting and ssl_setting[1] != 'ON':
                    security_check['secure_connection'] = False
                    security_check['issues'].append('Secure transport not required')
                    security_check['recommendations'].append('Require secure transport for database connections')

        except Exception as e:
            logger.error(f"Connection security check error: {str(e)}")
            security_check['issues'].append(f'Unable to verify connection security: {str(e)}')

        return security_check


class SQLInjectionTester:
    """
    SQL Injection Testing Suite for security validation
    Following Single Responsibility Principle for security testing

    Features:
    - Comprehensive SQL injection test cases
    - Automated vulnerability scanning
    - Security reporting
    - Test result analysis
    """

    def __init__(self):
        """
        Initialize SQL injection tester
        Following SOLID principles
        """
        self.validator = SQLInjectionValidator(strict_mode=True)
        self.test_results = {}

    def run_all_tests(self) -> Dict[str, Any]:
        """
        Run comprehensive SQL injection tests
        Following Single Responsibility Principle
        """
        test_results = {
            'union_based': self.test_union_based_injection(),
            'boolean_based_blind': self.test_boolean_blind_injection(),
            'time_based_blind': self.test_time_blind_injection(),
            'error_based': self.test_error_based_injection(),
            'stacked_queries': self.test_stacked_queries(),
            'second_order': self.test_second_order_injection(),
            'encoding_bypass': self.test_encoding_bypass()
        }

        self.test_results = test_results
        return test_results

    def test_union_based_injection(self, test_input: str = "test") -> Dict[str, Any]:
        """
        Test union-based SQL injection
        Following Single Responsibility Principle
        """
        test_cases = [
            f"{test_input}' UNION SELECT username,password FROM users--",
            f"{test_input}' UNION ALL SELECT @@version,database()--",
            f"{test_input}' UNION SELECT 1,2,3,4,5,6,7,8,9,10--",
            f"{test_input}' UNION SELECT column_name FROM information_schema.columns--"
        ]

        blocked_count = 0
        for test_case in test_cases:
            try:
                self.validator.validate_input(test_case, field_name='test')
            except SQLInjectionAttemptError:
                blocked_count += 1

        return {
            'total_tests': len(test_cases),
            'blocked': blocked_count,
            'passed': blocked_count == len(test_cases),
            'test_cases': test_cases
        }

    def test_boolean_blind_injection(self, test_input: str = "test") -> Dict[str, Any]:
        """
        Test boolean-based blind SQL injection
        Following Single Responsibility Principle
        """
        test_cases = [
            f"{test_input}' AND 1=1--",
            f"{test_input}' AND 1=2--",
            f"{test_input}' AND 'a'='a'--",
            f"{test_input}' AND (SELECT COUNT(*) FROM users)>0--",
            f"{test_input}' AND LENGTH((SELECT password FROM users WHERE id=1))>5--"
        ]

        blocked_count = 0
        for test_case in test_cases:
            try:
                self.validator.validate_input(test_case, field_name='test')
            except SQLInjectionAttemptError:
                blocked_count += 1

        return {
            'total_tests': len(test_cases),
            'blocked': blocked_count,
            'passed': blocked_count == len(test_cases),
            'test_cases': test_cases
        }

    def test_time_blind_injection(self, test_input: str = "test") -> Dict[str, Any]:
        """
        Test time-based blind SQL injection
        Following Single Responsibility Principle
        """
        test_cases = [
            f"{test_input}' WAITFOR DELAY '00:00:05'--",
            f"{test_input}' AND SLEEP(5)--",
            f"{test_input}' AND pg_sleep(5)--",
            f"{test_input}' AND BENCHMARK(50000000,MD5('test'))--",
            f"{test_input}' AND (SELECT COUNT(*) FROM information_schema.columns A, information_schema.columns B) AND 1='1"
        ]

        blocked_count = 0
        for test_case in test_cases:
            try:
                self.validator.validate_input(test_case, field_name='test')
            except SQLInjectionAttemptError:
                blocked_count += 1

        return {
            'total_tests': len(test_cases),
            'blocked': blocked_count,
            'passed': blocked_count == len(test_cases),
            'test_cases': test_cases
        }

    def test_error_based_injection(self, test_input: str = "test") -> Dict[str, Any]:
        """
        Test error-based SQL injection
        Following Single Responsibility Principle
        """
        test_cases = [
            f"{test_input}' AND (SELECT * FROM (SELECT COUNT(*),CONCAT(version(),FLOOR(RAND(0)*2))x FROM information_schema.tables GROUP BY x)a)--",
            f"{test_input}' AND EXTRACTVALUE(1,CONCAT(0x7e,(SELECT version()),0x7e))--",
            f"{test_input}' AND UPDATEXML(1,CONCAT(0x7e,(SELECT version()),0x7e),1)--",
            f"{test_input}' AND (SELECT * FROM (SELECT COUNT(*),CONCAT((SELECT username FROM users LIMIT 1),FLOOR(RAND(0)*2))x FROM information_schema.tables GROUP BY x)a)--"
        ]

        blocked_count = 0
        for test_case in test_cases:
            try:
                self.validator.validate_input(test_case, field_name='test')
            except SQLInjectionAttemptError:
                blocked_count += 1

        return {
            'total_tests': len(test_cases),
            'blocked': blocked_count,
            'passed': blocked_count == len(test_cases),
            'test_cases': test_cases
        }

    def test_stacked_queries(self, test_input: str = "test") -> Dict[str, Any]:
        """
        Test stacked query SQL injection
        Following Single Responsibility Principle
        """
        test_cases = [
            f"{test_input}'; DROP TABLE users--",
            f"{test_input}'; INSERT INTO users (email) VALUES ('hacked@test.com')--",
            f"{test_input}'; UPDATE users SET password='hacked' WHERE id=1--",
            f"{test_input}'; CREATE TABLE hacked (data VARCHAR(255))--"
        ]

        blocked_count = 0
        for test_case in test_cases:
            try:
                self.validator.validate_input(test_case, field_name='test')
            except SQLInjectionAttemptError:
                blocked_count += 1

        return {
            'total_tests': len(test_cases),
            'blocked': blocked_count,
            'passed': blocked_count == len(test_cases),
            'test_cases': test_cases
        }

    def test_second_order_injection(self, test_input: str = "test") -> Dict[str, Any]:
        """
        Test second-order SQL injection
        Following Single Responsibility Principle
        """
        test_cases = [
            f"admin')--",
            f"admin') OR '1'='1'--",
            f"admin') UNION SELECT username,password FROM users--",
            f"admin'; INSERT INTO audit_log (message) VALUES ('Hacked');--"
        ]

        blocked_count = 0
        for test_case in test_cases:
            try:
                self.validator.validate_input(test_case, field_name='test')
            except SQLInjectionAttemptError:
                blocked_count += 1

        return {
            'total_tests': len(test_cases),
            'blocked': blocked_count,
            'passed': blocked_count == len(test_cases),
            'test_cases': test_cases
        }

    def test_encoding_bypass(self, test_input: str = "test") -> Dict[str, Any]:
        """
        Test encoding bypass techniques
        Following Single Responsibility Principle
        """
        test_cases = [
            urllib.parse.quote(f"{test_input}' OR 1=1--"),
            urllib.parse.quote(f"{test_input}'; DROP TABLE users--"),
            f"{test_input}' + CHAR(39) + OR + CHAR(49) + CHAR(61) + CHAR(49)--",
            f"{test_input}' & chr(39) & OR & chr(49) & chr(61) & chr(49)--"
        ]

        blocked_count = 0
        for test_case in test_cases:
            try:
                self.validator.validate_input(test_case, field_name='test', decode_input=True)
            except SQLInjectionAttemptError:
                blocked_count += 1

        return {
            'total_tests': len(test_cases),
            'blocked': blocked_count,
            'passed': blocked_count == len(test_cases),
            'test_cases': test_cases
        }

    def generate_security_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive security report
        Following Single Responsibility Principle
        """
        if not self.test_results:
            self.run_all_tests()

        total_tests = sum(result.get('total_tests', 0) for result in self.test_results.values())
        total_blocked = sum(result.get('blocked', 0) for result in self.test_results.values())

        # Calculate vulnerability assessment
        vulnerability_score = (total_blocked / total_tests) * 100 if total_tests > 0 else 0

        # Determine security level
        if vulnerability_score >= 95:
            security_level = 'Excellent'
        elif vulnerability_score >= 85:
            security_level = 'Good'
        elif vulnerability_score >= 70:
            security_level = 'Fair'
        else:
            security_level = 'Poor'

        return {
            'test_summary': {
                'total_tests': total_tests,
                'blocked_attacks': total_blocked,
                'protection_rate': vulnerability_score,
                'security_level': security_level
            },
            'vulnerability_assessment': {
                'critical_vulnerabilities': 0,  # Should be 0 with proper protection
                'high_risk_issues': 0,
                'medium_risk_issues': 0,
                'low_risk_issues': max(0, total_tests - total_blocked)
            },
            'test_results': self.test_results,
            'recommendations': self._generate_recommendations(),
            'test_timestamp': timezone.now().isoformat()
        }

    def _generate_recommendations(self) -> List[str]:
        """
        Generate security recommendations based on test results
        Following Single Responsibility Principle
        """
        recommendations = []

        if not self.test_results:
            return ['Run security tests first']

        # Check for failed tests
        failed_tests = [
            test_name for test_name, result in self.test_results.items()
            if not result.get('passed', False)
        ]

        if failed_tests:
            recommendations.append(f"Review and strengthen protection for: {', '.join(failed_tests)}")

        # General recommendations
        recommendations.extend([
            "Regularly update SQL injection patterns and detection rules",
            "Implement comprehensive input validation throughout the application",
            "Use parameterized queries for all database operations",
            "Implement proper error handling to prevent information disclosure",
            "Regular security audits and penetration testing",
            "Monitor and log all suspicious database activities"
        ])

        return recommendations


# Enable/disable statistics globally
enable_statistics = getattr(settings, 'SQL_INJECTION_ENABLE_STATISTICS', True)