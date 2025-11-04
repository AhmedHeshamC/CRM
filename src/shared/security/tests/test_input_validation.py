"""
Test suite for Input Validation and Sanitization
Following SOLID principles and TDD approach
"""

import re
from unittest.mock import Mock, patch
from django.test import TestCase
from django.core.exceptions import ValidationError
from rest_framework import serializers
from shared.security.input_validation import (
    InputValidator,
    SQLInjectionDetector,
    XSSDetector,
    InputSanitizer,
    SecurityValidationMixin
)
from shared.security.exceptions import (
    InputValidationError,
    SQLInjectionAttemptError,
    XSSAttemptError
)


class InputValidatorTest(TestCase):
    """
    Test suite for InputValidator
    Following SOLID principles with comprehensive test coverage
    """

    def setUp(self):
        """
        Set up test environment
        Following Single Responsibility Principle
        """
        self.validator = InputValidator()

    def test_validator_initialization(self):
        """
        Test validator initialization
        Following SOLID principles
        """
        self.assertIsNotNone(self.validator)
        self.assertTrue(hasattr(self.validator, 'max_field_length'))
        self.assertTrue(hasattr(self.validator, 'allowed_html_tags'))

    def test_safe_string_validation(self):
        """
        Test validation of safe strings
        Following Single Responsibility Principle
        """
        safe_strings = [
            "John Doe",
            "john.doe@example.com",
            "Hello, World!",
            "1234567890",
            "Regular text with punctuation.",
            "Multi-line\ntext\ncontent",
            "Text with numbers 123 and symbols !@#$%"
        ]

        for text in safe_strings:
            result = self.validator.validate_string(text)
            self.assertTrue(result, f"String should be valid: '{text}'")

    def test_sql_injection_detection(self):
        """
        Test SQL injection pattern detection
        Following Security First Principle
        """
        malicious_inputs = [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "UNION SELECT * FROM passwords",
            "'; INSERT INTO users VALUES ('hacker', 'password'); --",
            "1'; UPDATE users SET password='hacked' WHERE id=1; --",
            "'; DELETE FROM contacts; --",
            "1' OR SLEEP(5)--",
            "'; EXEC xp_cmdshell('dir'); --",
            "1' UNION SELECT @@version--",
            "'; SHUTDOWN; --"
        ]

        for malicious_input in malicious_inputs:
            with self.assertRaises(SQLInjectionAttemptError):
                self.validator.validate_string(malicious_input)

    def test_xss_attack_detection(self):
        """
        Test XSS attack pattern detection
        Following Security First Principle
        """
        xss_attacks = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "javascript:alert('XSS')",
            "<svg onload=alert('XSS')>",
            "<iframe src=javascript:alert('XSS')>",
            "<body onload=alert('XSS')>",
            "<input onfocus=alert('XSS') autofocus>",
            "<select onfocus=alert('XSS') autofocus>",
            "<textarea onfocus=alert('XSS') autofocus>",
            "<keygen onfocus=alert('XSS') autofocus>",
            "<video><source onerror=alert('XSS')>",
            "<audio src=x onerror=alert('XSS')>"
        ]

        for xss_attack in xss_attacks:
            with self.assertRaises(XSSAttemptError):
                self.validator.validate_string(xss_attack)

    def test_input_length_validation(self):
        """
        Test input length validation
        Following Single Responsibility Principle
        """
        # Valid length
        valid_text = "a" * 100  # 100 characters
        result = self.validator.validate_string(valid_text)
        self.assertTrue(result)

        # Invalid length (too long)
        long_text = "a" * 10001  # 10001 characters
        with self.assertRaises(InputValidationError):
            self.validator.validate_string(long_text)

    def test_email_validation(self):
        """
        Test email validation
        Following Single Responsibility Principle
        """
        valid_emails = [
            "user@example.com",
            "test.email+tag@example.com",
            "user123@sub.example.co.uk",
            "firstname.lastname@example.com"
        ]

        invalid_emails = [
            "invalid-email",
            "@example.com",
            "user@",
            "user..name@example.com",
            ".username@yahoo.com",
            "username@yahoo.com.",
            "username@yahoo..com"
        ]

        for email in valid_emails:
            result = self.validator.validate_email(email)
            self.assertTrue(result, f"Email should be valid: {email}")

        for email in invalid_emails:
            with self.assertRaises(InputValidationError):
                self.validator.validate_email(email)

    def test_phone_number_validation(self):
        """
        Test phone number validation
        Following Single Responsibility Principle
        """
        valid_phones = [
            "+1234567890",
            "+1 (555) 123-4567",
            "555-123-4567",
            "(555) 123-4567",
            "555.123.4567",
            "5551234567"
        ]

        invalid_phones = [
            "123",
            "abc-def-ghij",
            "1-800-555-55555",
            "555-5555-555"
        ]

        for phone in valid_phones:
            result = self.validator.validate_phone(phone)
            self.assertTrue(result, f"Phone should be valid: {phone}")

        for phone in invalid_phones:
            with self.assertRaises(InputValidationError):
                self.validator.validate_phone(phone)

    def test_url_validation(self):
        """
        Test URL validation
        Following Single Responsibility Principle
        """
        valid_urls = [
            "https://example.com",
            "http://sub.example.com/path",
            "https://example.com:8080/path?query=value",
            "https://example.com/path#fragment"
        ]

        invalid_urls = [
            "ftp://example.com",
            "javascript:alert('XSS')",
            "data:text/html,<script>alert('XSS')</script>",
            "not-a-url",
            "http://",
            "https://"
        ]

        for url in valid_urls:
            result = self.validator.validate_url(url)
            self.assertTrue(result, f"URL should be valid: {url}")

        for url in invalid_urls:
            with self.assertRaises(InputValidationError):
                self.validator.validate_url(url)

    def test_custom_validation_rules(self):
        """
        Test custom validation rules
        Following Open/Closed Principle
        """
        # Create validator with custom rules
        custom_validator = InputValidator(
            max_field_length=50,
            allowed_patterns=[r'^[A-Za-z\s]+$']  # Only letters and spaces
        )

        # Valid input
        result = custom_validator.validate_string("John Doe")
        self.assertTrue(result)

        # Invalid input (contains numbers)
        with self.assertRaises(InputValidationError):
            custom_validator.validate_string("John Doe 123")

    def test_field_validation_context(self):
        """
        Test field validation with context
        Following Single Responsibility Principle
        """
        # Test name field
        result = self.validator.validate_field("name", "John Doe")
        self.assertTrue(result)

        # Test email field
        result = self.validator.validate_field("email", "user@example.com")
        self.assertTrue(result)

        # Test invalid email
        with self.assertRaises(InputValidationError):
            self.validator.validate_field("email", "invalid-email")

    def test_batch_validation(self):
        """
        Test batch validation of multiple fields
        Following Single Responsibility Principle
        """
        data = {
            "name": "John Doe",
            "email": "john@example.com",
            "phone": "+1-555-123-4567",
            "message": "This is a safe message."
        }

        result = self.validator.validate_batch(data)
        self.assertTrue(result['is_valid'])
        self.assertEqual(len(result['errors']), 0)

    def test_batch_validation_with_errors(self):
        """
        Test batch validation with validation errors
        Following Single Responsibility Principle
        """
        data = {
            "name": "John'; DROP TABLE users; --",
            "email": "invalid-email",
            "phone": "invalid-phone",
            "message": "<script>alert('XSS')</script>"
        }

        result = self.validator.validate_batch(data)
        self.assertFalse(result['is_valid'])
        self.assertGreater(len(result['errors']), 0)

        # Check specific errors
        error_fields = [error['field'] for error in result['errors']]
        self.assertIn('name', error_fields)
        self.assertIn('email', error_fields)
        self.assertIn('phone', error_fields)
        self.assertIn('message', error_fields)


class SQLInjectionDetectorTest(TestCase):
    """
    Test suite for SQLInjectionDetector
    Following SOLID principles with comprehensive test coverage
    """

    def setUp(self):
        """
        Set up test environment
        Following Single Responsibility Principle
        """
        self.detector = SQLInjectionDetector()

    def test_sql_pattern_detection(self):
        """
        Test SQL injection pattern detection
        Following Security First Principle
        """
        sql_patterns = [
            ("SELECT * FROM users", True),
            ("DROP TABLE users", True),
            ("INSERT INTO users", True),
            ("UPDATE users SET", True),
            ("DELETE FROM users", True),
            ("UNION SELECT", True),
            ("' OR '1'='1", True),
            ("'; --", True),
            ("Normal user input", False),
            "Regular text without SQL",
            "Hello world"
        ]

        for text, expected_threat in sql_patterns:
            is_threat = self.detector.detect_sql_injection(text)
            self.assertEqual(is_threat, expected_threat, f"SQL detection failed for: {text}")

    def test_advanced_sql_injection_patterns(self):
        """
        Test advanced SQL injection patterns
        Following Security First Principle
        """
        advanced_attacks = [
            "1' AND (SELECT COUNT(*) FROM users) > 0 --",
            "'; EXEC xp_cmdshell('dir'); --",
            "1' WAITFOR DELAY '00:00:05' --",
            "'; SHUTDOWN; --",
            "1' UNION SELECT @@version --",
            "'; ALTER TABLE users ADD COLUMN password VARCHAR(255); --"
        ]

        for attack in advanced_attacks:
            with self.assertRaises(SQLInjectionAttemptError):
                self.detector.validate_input(attack)

    def test_sql_injection_with_encoding(self):
        """
        Test SQL injection detection with encoding
        Following Security First Principle
        """
        encoded_attacks = [
            "%27%20OR%201=1--",  # ' OR 1=1--
            "%3B%20DROP%20TABLE%20users--",  # ; DROP TABLE users--
            "SELECT%20*%20FROM%20users"  # SELECT * FROM users
        ]

        for attack in encoded_attacks:
            # Test with URL decoding
            with self.assertRaises(SQLInjectionAttemptError):
                self.detector.validate_input(attack, decode_url=True)


class XSSDetectorTest(TestCase):
    """
    Test suite for XSSDetector
    Following SOLID principles with comprehensive test coverage
    """

    def setUp(self):
        """
        Set up test environment
        Following Single Responsibility Principle
        """
        self.detector = XSSDetector()

    def test_xss_pattern_detection(self):
        """
        Test XSS pattern detection
        Following Security First Principle
        """
        xss_patterns = [
            ("<script>", True),
            ("javascript:", True),
            ("onerror=", True),
            ("onload=", True),
            ("onclick=", True),
            ("Normal text", False),
            "Regular HTML without events",
            "Just plain text content"
        ]

        for text, expected_threat in xss_patterns:
            is_threat = self.detector.detect_xss(text)
            self.assertEqual(is_threat, expected_threat, f"XSS detection failed for: {text}")

    def test_advanced_xss_attacks(self):
        """
        Test advanced XSS attack patterns
        Following Security First Principle
        """
        advanced_attacks = [
            "<svg onload=alert(1)>",
            "<iframe src=javascript:alert(1)>",
            "<body onload=alert(1)>",
            "<input autofocus onfocus=alert(1)>",
            "<details open ontoggle=alert(1)>",
            "<marquee onstart=alert(1)>"
        ]

        for attack in advanced_attacks:
            with self.assertRaises(XSSAttemptError):
                self.detector.validate_input(attack)

    def test_xss_with_html_encoding(self):
        """
        Test XSS detection with HTML encoding
        Following Security First Principle
        """
        encoded_attacks = [
            "&lt;script&gt;alert('XSS')&lt;/script&gt;",
            "&#60;script&#62;alert('XSS')&#60;/script&#62;",
            "&#x3C;script&#x3E;alert('XSS')&#x3C;/script&#x3E;"
        ]

        for attack in encoded_attacks:
            # Should detect XSS after decoding
            with self.assertRaises(XSSAttemptError):
                self.detector.validate_input(attack, decode_html=True)


class InputSanitizerTest(TestCase):
    """
    Test suite for InputSanitizer
    Following SOLID principles with comprehensive test coverage
    """

    def setUp(self):
        """
        Set up test environment
        Following Single Responsibility Principle
        """
        self.sanitizer = InputSanitizer()

    def test_html_sanitization(self):
        """
        Test HTML sanitization
        Following Single Responsibility Principle
        """
        dangerous_html = "<script>alert('XSS')</script><p>Safe content</p>"
        sanitized = self.sanitizer.sanitize_html(dangerous_html)

        self.assertNotIn("<script>", sanitized)
        self.assertIn("<p>Safe content</p>", sanitized)

    def test_attribute_sanitization(self):
        """
        Test HTML attribute sanitization
        Following Single Responsibility Principle
        """
        dangerous_html = '<div onclick="alert(\'XSS\')" class="safe">Content</div>'
        sanitized = self.sanitizer.sanitize_html(dangerous_html)

        self.assertNotIn("onclick", sanitized)
        self.assertIn('class="safe"', sanitized)

    def test_url_sanitization(self):
        """
        Test URL sanitization
        Following Single Responsibility Principle
        """
        dangerous_urls = [
            "javascript:alert('XSS')",
            "data:text/html,<script>alert('XSS')</script>",
            "vbscript:msgbox('XSS')"
        ]

        for url in dangerous_urls:
            sanitized = self.sanitizer.sanitize_url(url)
            self.assertEqual(sanitized, "#")  # Should be replaced with safe anchor

    def test_sql_sanitization(self):
        """
        Test SQL sanitization
        Following Single Responsibility Principle
        """
        dangerous_input = "'; DROP TABLE users; --"
        sanitized = self.sanitizer.sanitize_sql(dangerous_input)

        self.assertNotIn(";", sanitized)
        self.assertNotIn("--", sanitized)
        self.assertNotIn("DROP", sanitized)

    def test_custom_sanitization_rules(self):
        """
        Test custom sanitization rules
        Following Open/Closed Principle
        """
        custom_sanitizer = InputSanitizer(
            allowed_tags=['b', 'i'],
            allowed_attributes=['class']
        )

        html = '<p onclick="alert(\'XSS\')" class="text"><b>Bold</b> <script>Dangerous</script></p>'
        sanitized = custom_sanitizer.sanitize_html(html)

        self.assertIn('<b>Bold</b>', sanitized)
        self.assertNotIn('<script>', sanitized)
        self.assertNotIn('onclick', sanitized)
        self.assertIn('class="text"', sanitized)


class SecurityValidationMixinTest(TestCase):
    """
    Test suite for SecurityValidationMixin
    Following SOLID principles with comprehensive test coverage
    """

    def test_mixin_integration(self):
        """
        Test mixin integration with serializers
        Following SOLID principles
        """
        class TestSerializer(SecurityValidationMixin, serializers.Serializer):
            name = serializers.CharField(max_length=100)
            email = serializers.EmailField()
            message = serializers.CharField()

        serializer = TestSerializer(data={
            'name': 'John Doe',
            'email': 'john@example.com',
            'message': 'Safe message'
        })

        self.assertTrue(serializer.is_valid())

    def test_mixin_security_validation(self):
        """
        Test mixin security validation
        Following Security First Principle
        """
        class TestSerializer(SecurityValidationMixin, serializers.Serializer):
            message = serializers.CharField()

        serializer = TestSerializer(data={
            'message': '<script>alert("XSS")</script>'
        })

        self.assertFalse(serializer.is_valid())
        self.assertIn('security_validation', serializer.errors)