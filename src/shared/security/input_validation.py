"""
Input Validation and Sanitization System for Production Security Hardening
Following SOLID principles and enterprise-grade security standards
"""

import re
import html
import urllib.parse
import logging
from typing import Dict, List, Optional, Any, Union, Tuple
from django.core.exceptions import ValidationError
from rest_framework import serializers
from django.utils.html import strip_tags
from bleach import clean as bleach_clean
from bleach.sanitizer import ALLOWED_TAGS, ALLOWED_ATTRIBUTES
from shared.security.exceptions import (
    InputValidationError,
    SQLInjectionAttemptError,
    XSSAttemptError
)

logger = logging.getLogger(__name__)


class SQLInjectionDetector:
    """
    SQL Injection Detection and Prevention
    Following Single Responsibility Principle for SQL injection security

    Features:
    - Comprehensive SQL injection pattern detection
    - Advanced attack pattern recognition
    - Encoding-based attack detection
    - Context-aware validation
    """

    def __init__(self):
        """
        Initialize SQL injection detector
        Following SOLID principles
        """
        # SQL injection patterns
        self.sql_patterns = [
            # Basic SQL injection patterns
            r"(?i)(union|select|insert|update|delete|drop|create|alter|exec|execute)",
            r"(?i)(\b(or|and)\s+['\"]?\s*\d+['\"]?\s*=\s*['\"]?\s*\d+['\"]?)",
            r"(?i)('|(\\')|(;)|(\-\-)|(\#)|(\*|\/))",
            r"(?i)(waitfor\s+delay)",
            r"(?i)(benchmark\s*\()",
            r"(?i)(sleep\s*\()",
            r"(?i)(\b(xp_|sp_))",
            r"(?i)(load_file|into\s+outfile)",
            r"(?i)(information_schema|sysobjects|syscolumns)",
            r"(?i)(@@version|@@servername|user\(\))",
            r"(?i)(concat\s*\()",
            r"(?i)(substring\s*\()",
            r"(?i)(ascii\s*\()",
            r"(?i)(char\s*\()",
            r"(?i)(cast\s*\()",
            r"(?i)(convert\s*\()",
        ]

        self.patterns = [re.compile(pattern) for pattern in self.sql_patterns]

    def detect_sql_injection(self, input_text: str, decode_url: bool = True) -> bool:
        """
        Detect SQL injection in input text
        Following Single Responsibility Principle
        """
        if not input_text or len(input_text.strip()) == 0:
            return False

        # Decode URL-encoded input if requested
        if decode_url:
            try:
                decoded_text = urllib.parse.unquote(input_text)
            except Exception:
                decoded_text = input_text
        else:
            decoded_text = input_text

        # Check for SQL injection patterns
        for pattern in self.patterns:
            if pattern.search(decoded_text):
                return True

        # Check for common SQL injection strings
        sql_keywords = [
            "union select", "drop table", "insert into", "update set", "delete from",
            "create table", "alter table", "exec(", "execute(", "xp_cmdshell",
            "sp_executesql", "information_schema", "sysobjects", "syscolumns",
            "waitfor delay", "benchmark(", "sleep(", "load_file", "into outfile",
            "@@version", "@@servername", "user()", "database()",
            "concat(", "substring(", "ascii(", "char(", "cast(", "convert("
        ]

        decoded_text_lower = decoded_text.lower()
        for keyword in sql_keywords:
            if keyword in decoded_text_lower:
                return True

        return False

    def validate_input(self, input_text: str, field_name: str = None, **kwargs) -> str:
        """
        Validate input against SQL injection attacks
        Following Security First Principle
        """
        if self.detect_sql_injection(input_text, **kwargs):
            logger.warning(
                f"SQL injection attempt detected in field '{field_name}': {input_text[:100]}...",
                extra={
                    'field_name': field_name,
                    'input_length': len(input_text),
                    'detection_method': 'pattern_matching'
                }
            )
            raise SQLInjectionAttemptError(
                message=f"Potential SQL injection attempt detected in field '{field_name}'",
                field=field_name,
                input_preview=input_text[:100]
            )

        return input_text


class XSSDetector:
    """
    XSS (Cross-Site Scripting) Detection and Prevention
    Following Single Responsibility Principle for XSS security

    Features:
    - Comprehensive XSS attack pattern detection
    - Advanced encoding-based attack detection
    - Context-aware validation
    - Event handler detection
    """

    def __init__(self):
        """
        Initialize XSS detector
        Following SOLID principles
        """
        # XSS attack patterns
        self.xss_patterns = [
            # Script and event handler patterns
            r"(?i)(<script[^>]*>.*?</script>)",
            r"(?i)(javascript\s*:)",
            r"(?i)(vbscript\s*:)",
            r"(?i)(data\s*:)",
            r"(?i)(on\w+\s*=)",
            r"(?i)(<iframe[^>]*>)",
            r"(?i)(<object[^>]*>)",
            r"(?i)(<embed[^>]*>)",
            r"(?i)(<link[^>]*>)",
            r"(?i)(<meta[^>]*>)",
            r"(?i)(<style[^>]*>.*?</style>)",
            r"(?i)(<form[^>]*action\s*=\s*['\"]?javascript)",
            r"(?i)(expression\s*\()",
            r"(?i)(@import)",
            r"(?i)(binding\s*:)",
        ]

        # HTML5 event handlers
        self.event_handlers = [
            'onabort', 'onafterprint', 'onbeforeprint', 'onbeforeunload', 'onblur',
            'oncanplay', 'oncanplaythrough', 'onchange', 'onclick', 'oncontextmenu',
            'oncopy', 'oncut', 'ondblclick', 'ondrag', 'ondragend', 'ondragenter',
            'ondragleave', 'ondragover', 'ondragstart', 'ondrop', 'ondurationchange',
            'onemptied', 'onended', 'onerror', 'onfocus', 'onhashchange', 'oninput',
            'oninvalid', 'onkeydown', 'onkeypress', 'onkeyup', 'onload', 'onloadeddata',
            'onloadedmetadata', 'onloadstart', 'onmessage', 'onmousedown', 'onmousemove',
            'onmouseout', 'onmouseover', 'onmouseup', 'onoffline', 'ononline', 'onpagehide',
            'onpageshow', 'onpaste', 'onpause', 'onplay', 'onplaying', 'onpopstate',
            'onprogress', 'onratechange', 'onreset', 'onresize', 'onscroll', 'onsearch',
            'onseeked', 'onseeking', 'onselect', 'onstalled', 'onstorage', 'onsubmit',
            'onsuspend', 'ontimeupdate', 'ontoggle', 'onunload', 'onvolumechange',
            'onwaiting', 'onwheel'
        ]

        self.patterns = [re.compile(pattern) for pattern in self.xss_patterns]

    def detect_xss(self, input_text: str, decode_html: bool = True) -> bool:
        """
        Detect XSS attacks in input text
        Following Single Responsibility Principle
        """
        if not input_text or len(input_text.strip()) == 0:
            return False

        # Decode HTML entities if requested
        if decode_html:
            try:
                decoded_text = html.unescape(input_text)
            except Exception:
                decoded_text = input_text
        else:
            decoded_text = input_text

        # Check for XSS patterns
        for pattern in self.patterns:
            if pattern.search(decoded_text):
                return True

        # Check for event handlers
        decoded_text_lower = decoded_text.lower()
        for handler in self.event_handlers:
            if handler in decoded_text_lower:
                return True

        # Check for suspicious HTML constructs
        suspicious_constructs = [
            '<script', 'javascript:', 'vbscript:', 'data:text/html',
            '<iframe', '<object', '<embed', 'expression(', 'behavior:',
            '@import', 'binding:', 'expression('
        ]

        for construct in suspicious_constructs:
            if construct in decoded_text_lower:
                return True

        return False

    def validate_input(self, input_text: str, field_name: str = None, **kwargs) -> str:
        """
        Validate input against XSS attacks
        Following Security First Principle
        """
        if self.detect_xss(input_text, **kwargs):
            logger.warning(
                f"XSS attempt detected in field '{field_name}': {input_text[:100]}...",
                extra={
                    'field_name': field_name,
                    'input_length': len(input_text),
                    'detection_method': 'pattern_matching'
                }
            )
            raise XSSAttemptError(
                message=f"Potential XSS attempt detected in field '{field_name}'",
                field=field_name,
                input_preview=input_text[:100]
            )

        return input_text


class InputSanitizer:
    """
    Input Sanitization System
    Following Single Responsibility Principle for input sanitization

    Features:
    - HTML sanitization with allowed tags/attributes
    - URL sanitization
    - SQL injection sanitization
    - XSS sanitization
    - Custom sanitization rules
    """

    def __init__(
        self,
        allowed_tags: Optional[List[str]] = None,
        allowed_attributes: Optional[Dict[str, List[str]]] = None,
        strip_disallowed_tags: bool = True
    ):
        """
        Initialize input sanitizer
        Following Dependency Inversion Principle for configuration
        """
        self.allowed_tags = allowed_tags or [
            'p', 'br', 'strong', 'em', 'u', 'i', 'b',
            'ul', 'ol', 'li', 'blockquote', 'code', 'pre'
        ]

        self.allowed_attributes = allowed_attributes or {
            '*': ['class'],
            'a': ['href', 'title'],
            'img': ['src', 'alt', 'width', 'height']
        }

        self.strip_disallowed_tags = strip_disallowed_tags

        # Initialize detectors
        self.sql_detector = SQLInjectionDetector()
        self.xss_detector = XSSDetector()

    def sanitize_html(self, html_text: str) -> str:
        """
        Sanitize HTML content
        Following Single Responsibility Principle
        """
        if not html_text:
            return ""

        try:
            # Use bleach for HTML sanitization
            sanitized = bleach_clean(
                html_text,
                tags=self.allowed_tags,
                attributes=self.allowed_attributes,
                strip=self.strip_disallowed_tags,
                strip_comments=True
            )

            return sanitized.strip()

        except Exception as e:
            logger.error(f"HTML sanitization error: {str(e)}")
            # Fallback to basic HTML stripping
            return strip_tags(html_text)

    def sanitize_url(self, url: str) -> str:
        """
        Sanitize URL to prevent XSS
        Following Single Responsibility Principle
        """
        if not url:
            return ""

        try:
            # Decode URL first
            decoded_url = urllib.parse.unquote(url)

            # Check for dangerous protocols
            dangerous_protocols = ['javascript:', 'vbscript:', 'data:', 'file:', 'ftp:']
            for protocol in dangerous_protocols:
                if decoded_url.lower().startswith(protocol):
                    logger.warning(f"Dangerous URL protocol detected: {url}")
                    return "#"  # Return safe anchor

            # Validate and parse URL
            parsed = urllib.parse.urlparse(decoded_url)
            if not parsed.scheme or not parsed.netloc:
                if decoded_url.startswith('/'):
                    # Relative URL, keep as is
                    return url
                else:
                    # Invalid URL
                    return "#"

            # Reconstruct safe URL
            safe_url = urllib.parse.urlunparse((
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                urllib.parse.parse_qs(parsed.query),
                parsed.fragment
            ))

            return safe_url

        except Exception as e:
            logger.error(f"URL sanitization error: {str(e)}")
            return "#"

    def sanitize_sql(self, sql_text: str) -> str:
        """
        Sanitize text to prevent SQL injection
        Following Single Responsibility Principle
        """
        if not sql_text:
            return ""

        try:
            # Remove dangerous SQL characters and patterns
            sanitized = sql_text

            # Remove SQL comments
            sanitized = re.sub(r'(--|#|/\*|\*/)', '', sanitized)

            # Remove multiple semicolons
            sanitized = re.sub(r';+', ';', sanitized)

            # Remove dangerous SQL keywords
            dangerous_keywords = [
                'DROP', 'DELETE', 'UPDATE', 'INSERT', 'CREATE', 'ALTER',
                'EXEC', 'EXECUTE', 'UNION', 'SELECT', 'FROM', 'WHERE',
                'TRUNCATE', 'ALTER', 'EXEC', 'DECLARE', 'CAST', 'CONVERT'
            ]

            for keyword in dangerous_keywords:
                # Remove case-insensitive occurrences
                pattern = re.compile(r'\b' + re.escape(keyword) + r'\b', re.IGNORECASE)
                sanitized = pattern.sub('', sanitized)

            # Remove extra whitespace
            sanitized = re.sub(r'\s+', ' ', sanitized).strip()

            return sanitized

        except Exception as e:
            logger.error(f"SQL sanitization error: {str(e)}")
            return ""

    def sanitize_text(self, text: str) -> str:
        """
        Sanitize plain text
        Following Single Responsibility Principle
        """
        if not text:
            return ""

        try:
            # Remove potential XSS content
            sanitized = self.xss_detector.validate_input(text, raise_exception=False)
            if isinstance(sanitized, str):
                text = sanitized

            # Remove SQL injection patterns
            sanitized = self.sql_detector.validate_input(text, raise_exception=False)
            if isinstance(sanitized, str):
                text = sanitized

            # Strip HTML tags
            text = strip_tags(text)

            # Normalize whitespace
            text = re.sub(r'\s+', ' ', text).strip()

            return text

        except Exception as e:
            logger.error(f"Text sanitization error: {str(e)}")
            return strip_tags(text)


class InputValidator:
    """
    Comprehensive Input Validation System
    Following Single Responsibility Principle for input validation

    Features:
    - SQL injection detection
    - XSS attack detection
    - Length validation
    - Format validation (email, phone, URL)
    - Custom validation rules
    - Batch validation
    """

    def __init__(
        self,
        max_field_length: int = 10000,
        allowed_patterns: Optional[List[str]] = None,
        strict_mode: bool = True
    ):
        """
        Initialize input validator
        Following Dependency Inversion Principle for configuration
        """
        self.max_field_length = max_field_length
        self.allowed_patterns = allowed_patterns or []
        self.strict_mode = strict_mode

        # Initialize detectors and sanitizer
        self.sql_detector = SQLInjectionDetector()
        self.xss_detector = XSSDetector()
        self.sanitizer = InputSanitizer()

    def validate_string(self, input_text: str, field_name: str = None, **kwargs) -> str:
        """
        Validate string input
        Following Single Responsibility Principle
        """
        if input_text is None:
            return ""

        # Check length
        if len(input_text) > self.max_field_length:
            raise InputValidationError(
                message=f"Input too long. Maximum length is {self.max_field_length}",
                field=field_name,
                max_length=self.max_field_length,
                actual_length=len(input_text)
            )

        # Validate against allowed patterns if specified
        if self.allowed_patterns:
            pattern_matched = any(
                re.match(pattern, input_text) for pattern in self.allowed_patterns
            )
            if not pattern_matched:
                raise InputValidationError(
                    message=f"Input does not match allowed patterns",
                    field=field_name,
                    allowed_patterns=self.allowed_patterns
                )

        # Security validation
        self.sql_detector.validate_input(input_text, field_name=field_name, **kwargs)
        self.xss_detector.validate_input(input_text, field_name=field_name, **kwargs)

        return input_text

    def validate_email(self, email: str, field_name: str = None) -> str:
        """
        Validate email format
        Following Single Responsibility Principle
        """
        if not email:
            return ""

        # Basic security validation first
        self.validate_string(email, field_name)

        # Email format validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email.strip()):
            raise InputValidationError(
                message="Invalid email format",
                field=field_name,
                value=email
            )

        return email.strip().lower()

    def validate_phone(self, phone: str, field_name: str = None) -> str:
        """
        Validate phone number format
        Following Single Responsibility Principle
        """
        if not phone:
            return ""

        # Basic security validation first
        self.validate_string(phone, field_name)

        # Remove common formatting characters
        cleaned_phone = re.sub(r'[\s\-\(\)\.]', '', phone)

        # Phone number validation (supports international formats)
        phone_pattern = r'^\+?[1-9]\d{6,14}$'
        if not re.match(phone_pattern, cleaned_phone):
            raise InputValidationError(
                message="Invalid phone number format",
                field=field_name,
                value=phone
            )

        return phone.strip()

    def validate_url(self, url: str, field_name: str = None) -> str:
        """
        Validate URL format
        Following Single Responsibility Principle
        """
        if not url:
            return ""

        # Basic security validation first
        self.validate_string(url, field_name)

        # URL format validation
        url_pattern = r'^https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)$'
        if not re.match(url_pattern, url.strip()):
            raise InputValidationError(
                message="Invalid URL format",
                field=field_name,
                value=url
            )

        # Sanitize URL
        return self.sanitizer.sanitize_url(url.strip())

    def validate_field(self, field_name: str, value: Any, field_type: str = 'string') -> Any:
        """
        Validate field based on field type
        Following Single Responsibility Principle
        """
        if value is None:
            return None

        if field_type == 'string':
            return self.validate_string(str(value), field_name)
        elif field_type == 'email':
            return self.validate_email(str(value), field_name)
        elif field_type == 'phone':
            return self.validate_phone(str(value), field_name)
        elif field_type == 'url':
            return self.validate_url(str(value), field_name)
        else:
            return self.validate_string(str(value), field_name)

    def validate_batch(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate multiple fields
        Following Single Responsibility Principle
        """
        errors = []
        validated_data = {}

        for field_name, value in data.items():
            try:
                # Determine field type based on field name
                field_type = 'string'
                if 'email' in field_name.lower():
                    field_type = 'email'
                elif 'phone' in field_name.lower() or 'mobile' in field_name.lower():
                    field_type = 'phone'
                elif 'url' in field_name.lower() or 'website' in field_name.lower():
                    field_type = 'url'

                validated_value = self.validate_field(field_name, value, field_type)
                validated_data[field_name] = validated_value

            except (InputValidationError, SQLInjectionAttemptError, XSSAttemptError) as e:
                errors.append({
                    'field': field_name,
                    'message': str(e),
                    'code': e.code if hasattr(e, 'code') else 'validation_error'
                })

        return {
            'is_valid': len(errors) == 0,
            'validated_data': validated_data,
            'errors': errors
        }


class SecurityValidationMixin:
    """
    Mixin for integrating security validation with Django serializers
    Following Open/Closed Principle for extensibility
    """

    def validate(self, attrs):
        """
        Validate all fields for security
        Following Security First Principle
        """
        # Get standard validation
        attrs = super().validate(attrs) if hasattr(super(), 'validate') else attrs

        # Perform security validation
        validator = InputValidator(strict_mode=True)
        validation_result = validator.validate_batch(attrs)

        if not validation_result['is_valid']:
            # Add security validation errors
            if 'security_validation' not in self.errors:
                self.errors['security_validation'] = []

            for error in validation_result['errors']:
                self.errors['security_validation'].append(error)

            raise serializers.ValidationError(self.errors)

        return validation_result['validated_data']

    def validate_field_security(self, value, field_name):
        """
        Validate individual field for security
        Following Single Responsibility Principle
        """
        validator = InputValidator()
        return validator.validate_string(str(value), field_name) if value else value