"""
Test suite for SQL Injection Protection System
Following SOLID principles and TDD approach
"""

import json
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase, TransactionTestCase
from django.db import connection, transaction
from django.core.exceptions import SuspiciousOperation
from django.test import Client
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from shared.security.sql_injection_protection import (
    SQLInjectionProtectionMiddleware,
    SQLInjectionValidator,
    DatabaseSecurityValidator,
    QueryAnalyzer,
    SQLInjectionTester
)
from shared.security.exceptions import SQLInjectionAttemptError

User = get_user_model()


class SQLInjectionValidatorTest(TestCase):
    """
    Test suite for SQLInjectionValidator
    Following SOLID principles with comprehensive test coverage
    """

    def setUp(self):
        """
        Set up test environment
        Following Single Responsibility Principle
        """
        self.validator = SQLInjectionValidator()

    def test_sql_injection_patterns_detection(self):
        """
        Test SQL injection pattern detection
        Following Security First Principle
        """
        injection_attempts = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "1' UNION SELECT username, password FROM users--",
            "'; INSERT INTO users (email) VALUES ('hacker@test.com');--",
            "'; UPDATE users SET password='hacked' WHERE id=1;--",
            "'; DELETE FROM contacts; --",
            "1' OR SLEEP(5)--",
            "'; EXEC xp_cmdshell('dir'); --",
            "1' UNION SELECT @@version--",
            "'; SHUTDOWN WITH NOWAIT; --",
            "'; ALTER TABLE users ADD COLUMN password VARCHAR(255); --",
            "'; CREATE TABLE hacked (data VARCHAR(255)); --",
            "'; TRUNCATE TABLE users; --",
            "'; GRANT ALL PRIVILEGES ON *.* TO 'hacker'@'%'; --",
            "'; LOAD_FILE('/etc/passwd'); --",
            "'; INTO OUTFILE '/tmp/hacked.txt'; --",
            "'; DUMPFILE '/etc/shadow'; --"
        ]

        for injection in injection_attempts:
            with self.assertRaises(SQLInjectionAttemptError):
                self.validator.validate_input(injection, field_name='test')

    def test_advanced_sql_injection_techniques(self):
        """
        Test advanced SQL injection techniques
        Following Security First Principle
        """
        advanced_attacks = [
            "1' AND (SELECT COUNT(*) FROM users) > 0--",
            "1' AND (SELECT SUBSTRING(password,1,1) FROM users WHERE id=1)='a'--",
            "1' AND (SELECT ASCII(SUBSTRING(password,1,1)) FROM users WHERE id=1)>64--",
            "1' WAITFOR DELAY '00:00:05'--",
            "1'; BEGIN DECLARE @var VARCHAR(255); SET @var=''; SELECT @var=name FROM users;--",
            "1' AND (SELECT * FROM (SELECT COUNT(*),CONCAT(version(),FLOOR(RAND(0)*2))x FROM information_schema.tables GROUP BY x)a)--",
            "1' UNION SELECT 1,2,3,4,5,6,7,8,9,10--",
            "1' PROCEDURE ANALYSE(EXTRACTVALUE(787,CONCAT(0x5e5e5e,version(),0x5e5e5e)),1)--",
            "1' AND (SELECT * FROM (SELECT COUNT(*),CONCAT((SELECT username FROM users LIMIT 1),FLOOR(RAND(0)*2))x FROM information_schema.tables GROUP BY x)a)--"
        ]

        for attack in advanced_attacks:
            with self.assertRaises(SQLInjectionAttemptError):
                self.validator.validate_input(attack, field_name='advanced_test')

    def test_blind_sql_injection_detection(self):
        """
        Test blind SQL injection detection
        Following Security First Principle
        """
        blind_attacks = [
            "1' AND 1=1--",
            "1' AND 1=2--",
            "1' AND 'a'='a'--",
            "1' AND 'a'='b'--",
            "1' AND (SELECT COUNT(*) FROM users)>0--",
            "1' AND (SELECT LENGTH(password) FROM users WHERE id=1)>5--",
            "1' AND SUBSTRING((SELECT password FROM users WHERE id=1),1,1)='a'--",
            "1' AND ASCII(SUBSTRING((SELECT password FROM users WHERE id=1),1,1))>64--",
            "1' AND BENCHMARK(50000000,ENCODE('MSG','by 5 seconds'))--",
            "1' AND SLEEP(5)--",
            "1' AND pg_sleep(5)--",
            "1' AND (SELECT COUNT(*) FROM information_schema.tables)>0--"
        ]

        for attack in blind_attacks:
            with self.assertRaises(SQLInjectionAttemptError):
                self.validator.validate_input(attack, field_name='blind_test')

    def test_second_order_sql_injection_detection(self):
        """
        Test second-order SQL injection detection
        Following Security First Principle
        """
        second_order_attacks = [
            "admin')--",
            "admin') OR '1'='1'--",
            "admin') UNION SELECT username,password FROM users--",
            "admin'; INSERT INTO audit_log (message) VALUES ('Hacked');--",
            "admin'; UPDATE users SET is_admin=1 WHERE email='admin@test.com';--",
            "admin'); DROP TABLE audit_log;--",
            "admin') AND (SELECT COUNT(*) FROM users)>0--",
            "admin') OR (SELECT SUBSTRING(password,1,1) FROM users WHERE id=1)='a'--"
        ]

        for attack in second_order_attacks:
            with self.assertRaises(SQLInjectionAttemptError):
                self.validator.validate_input(attack, field_name='second_order_test')

    def test_encoded_sql_injection_detection(self):
        """
        Test SQL injection detection with various encodings
        Following Security First Principle
        """
        encoded_attacks = [
            # URL encoded
            "%27%20OR%201%3D1--",
            "%3B%20DROP%20TABLE%20users--",
            # Double URL encoded
            "%2527%2520OR%25201%253D1--",
            # Hex encoded
            "0x27204f5220313d312d2d",
            # Unicode encoded
            "\\u0027\\u0020OR\\u00201\\u003d1\\u002d\\u002d",
            # Mixed case
            "' Or 1=1--",
            "' oR 1=1--",
            "' OR 1=1--"
        ]

        for attack in encoded_attacks:
            with self.assertRaises(SQLInjectionAttemptError):
                self.validator.validate_input(attack, field_name='encoded_test', decode_input=True)

    def test_time_based_sql_injection_detection(self):
        """
        Test time-based SQL injection detection
        Following Security First Principle
        """
        time_attacks = [
            "1' WAITFOR DELAY '00:00:05'--",
            "1'; WAITFOR DELAY '00:00:10'--",
            "1' AND SLEEP(5)--",
            "1' AND pg_sleep(5)--",
            "1' AND BENCHMARK(50000000,MD5('test'))--",
            "1' AND (SELECT COUNT(*) FROM information_schema.columns A, information_schema.columns B) AND 1='1",
            "1' AND (SELECT COUNT(*) FROM all_objects t1,all_objects t2,all_objects t3,all_objects t4,all_objects t5) AND 1='1"
        ]

        for attack in time_attacks:
            with self.assertRaises(SQLInjectionAttemptError):
                self.validator.validate_input(attack, field_name='time_test')

    def test_safe_inputs_validation(self):
        """
        Test validation of safe inputs
        Following Single Responsibility Principle
        """
        safe_inputs = [
            "John Doe",
            "john.doe@example.com",
            "Regular text without SQL keywords",
            "123456789",
            "This is a normal sentence",
            "Email with quotes: It's working fine",
            "Text with semicolons: Hello; world;",
            "Numbers: 1, 2, 3, 4, 5",
            "Mixed content: User123@email.com said: 'Hello world!'",
            "Long text with multiple sentences. This should be safe as long as it doesn't contain SQL patterns."
        ]

        for safe_input in safe_inputs:
            try:
                result = self.validator.validate_input(safe_input, field_name='safe_test')
                self.assertEqual(result, safe_input)
            except SQLInjectionAttemptError:
                self.fail(f"Safe input was flagged as SQL injection: {safe_input}")

    def test_context_aware_validation(self):
        """
        Test context-aware validation
        Following Single Responsibility Principle
        """
        # Test email context
        email_input = "test@example.com"
        result = self.validator.validate_input(email_input, field_name='email', context='email')
        self.assertEqual(result, email_input)

        # Test name context
        name_input = "John O'Connor"
        result = self.validator.validate_input(name_input, field_name='name', context='name')
        self.assertEqual(result, name_input)

        # Test search context (more restrictive)
        search_input = "search term"
        result = self.validator.validate_input(search_input, field_name='search', context='search')
        self.assertEqual(result, search_input)

    def test_custom_patterns_validation(self):
        """
        Test custom SQL injection patterns
        Following Open/Closed Principle
        """
        custom_patterns = [
            r"(?i)(custom_table)",
            r"(?i)(custom_column)",
            r"(?i)(custom_function)"
        ]

        validator = SQLInjectionValidator(custom_patterns=custom_patterns)

        # Should detect custom patterns
        with self.assertRaises(SQLInjectionAttemptError):
            validator.validate_input("SELECT * FROM custom_table", field_name='test')

        # Should allow normal inputs
        result = validator.validate_input("Normal user input", field_name='test')
        self.assertEqual(result, "Normal user input")

    def test_batch_validation(self):
        """
        Test batch validation of multiple inputs
        Following Single Responsibility Principle
        """
        test_data = {
            'name': 'John Doe',
            'email': 'john@example.com',
            'search': "normal search",
            'malicious': "'; DROP TABLE users; --"
        }

        result = self.validator.validate_batch(test_data)

        self.assertFalse(result['is_valid'])
        self.assertIn('malicious', [error['field'] for error in result['errors']])
        self.assertGreater(len(result['errors']), 0)

    def test_validation_statistics(self):
        """
        Test validation statistics
        Following Single Responsibility Principle
        """
        # Generate some validation activity
        for i in range(10):
            try:
                self.validator.validate_input(f"safe input {i}", field_name='test')
            except SQLInjectionAttemptError:
                pass

        try:
            self.validator.validate_input("'; DROP TABLE users; --", field_name='test')
        except SQLInjectionAttemptError:
            pass

        stats = self.validator.get_statistics()
        self.assertGreater(stats['total_validations'], 10)
        self.assertGreater(stats['blocked_attempts'], 0)


class SQLInjectionProtectionMiddlewareTest(TestCase):
    """
    Test suite for SQLInjectionProtectionMiddleware
    Following SOLID principles with comprehensive test coverage
    """

    def setUp(self):
        """
        Set up test environment
        Following Single Responsibility Principle
        """
        self.factory = Client()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            role='sales'
        )

    def test_middleware_protection_in_get_requests(self):
        """
        Test middleware protection in GET requests
        Following Security First Principle
        """
        # Test SQL injection in query parameters
        malicious_urls = [
            "/api/v1/contacts/?search='; DROP TABLE users; --",
            "/api/v1/contacts/?id=1' OR '1'='1",
            "/api/v1/contacts/?email=test@example.com' UNION SELECT * FROM users--"
        ]

        for url in malicious_urls:
            response = self.factory.get(url, HTTP_AUTHORIZATION=f'Bearer {self._get_token()}')
            # Should be blocked by middleware or return error
            self.assertIn(response.status_code, [400, 403, 429])

    def test_middleware_protection_in_post_requests(self):
        """
        Test middleware protection in POST requests
        Following Security First Principle
        """
        malicious_data = {
            'name': "'; DROP TABLE users; --",
            'email': 'test@example.com'
        }

        response = self.factory.post(
            '/api/v1/contacts/',
            data=json.dumps(malicious_data),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self._get_token()}'
        )

        # Should be blocked by middleware
        self.assertIn(response.status_code, [400, 403, 429])

    def test_middleware_exempt_paths(self):
        """
        Test middleware exempt paths
        Following Open/Closed Principle
        """
        exempt_paths = [
            '/health/',
            '/metrics/',
            '/api/schema/',
            '/admin/'
        ]

        for path in exempt_paths:
            # Should not be blocked even with malicious data
            response = self.factory.get(f"{path}?search='; DROP TABLE users; --")
            # Should not be blocked by SQL injection protection
            self.assertNotIn(response.status_code, [400, 403, 429])

    def test_middleware_logging(self):
        """
        Test middleware security logging
        Following Single Responsibility Principle
        """
        with patch('shared.security.sql_injection_protection.logger') as mock_logger:
            malicious_data = {
                'name': "'; DROP TABLE users; --",
                'email': 'test@example.com'
            }

            self.factory.post(
                '/api/v1/contacts/',
                data=json.dumps(malicious_data),
                content_type='application/json',
                HTTP_AUTHORIZATION=f'Bearer {self._get_token()}'
            )

            # Should log the attack attempt
            mock_logger.warning.assert_called()

    def _get_token(self):
        """Helper method to get auth token"""
        # Authenticate and get token
        response = self.factory.post('/api/v1/auth/auth/login/', {
            'email': 'test@example.com',
            'password': 'testpass123'
        })
        return response.json().get('access', 'test_token')


class DatabaseSecurityValidatorTest(TransactionTestCase):
    """
    Test suite for DatabaseSecurityValidator
    Following SOLID principles with comprehensive test coverage
    """

    def setUp(self):
        """
        Set up test environment
        Following Single Responsibility Principle
        """
        self.validator = DatabaseSecurityValidator()

    def test_query_analysis_for_sql_injection(self):
        """
        Test query analysis for SQL injection patterns
        Following Security First Principle
        """
        safe_queries = [
            "SELECT * FROM contacts WHERE name = %s",
            "INSERT INTO contacts (name, email) VALUES (%s, %s)",
            "UPDATE contacts SET name = %s WHERE id = %s",
            "DELETE FROM contacts WHERE id = %s"
        ]

        for query in safe_queries:
            result = self.validator.validate_query(query)
            self.assertTrue(result['is_safe'])

    def test_suspicious_query_detection(self):
        """
        Test suspicious query detection
        Following Security First Principle
        """
        suspicious_queries = [
            "SELECT * FROM contacts WHERE name = ' OR 1=1 --",
            "DROP TABLE users",
            "INSERT INTO contacts (name) VALUES (''; DROP TABLE users; --')",
            "UPDATE contacts SET name = 'test' WHERE 1=1"
        ]

        for query in suspicious_queries:
            result = self.validator.validate_query(query)
            self.assertFalse(result['is_safe'])
            self.assertIn('sql_injection', result['threat_types'])

    def test_parameterized_query_validation(self):
        """
        Test parameterized query validation
        Following Security First Principle
        """
        # Parameterized queries should be safe
        parameterized_query = "SELECT * FROM contacts WHERE name = %s AND email = %s"
        parameters = ["John Doe", "john@example.com"]

        result = self.validator.validate_parameterized_query(parameterized_query, parameters)
        self.assertTrue(result['is_safe'])

    def test_dynamic_query_validation(self):
        """
        Test dynamic query validation
        Following Security First Principle
        """
        # Safe dynamic queries
        safe_dynamic_queries = [
            "SELECT * FROM contacts WHERE {field} = %s".format(field='name'),
            "SELECT * FROM contacts ORDER BY {order_field}".format(order_field='created_at')
        ]

        for query in safe_dynamic_queries:
            result = self.validator.validate_dynamic_query(query, allowed_fields=['name', 'email', 'created_at'])
            self.assertTrue(result['is_safe'])

        # Unsafe dynamic queries
        unsafe_dynamic_queries = [
            "SELECT * FROM contacts WHERE {field} = %s".format(field='name; DROP TABLE users; --'),
        ]

        for query in unsafe_dynamic_queries:
            result = self.validator.validate_dynamic_query(query, allowed_fields=['name', 'email'])
            self.assertFalse(result['is_safe'])

    def test_database_connection_security(self):
        """
        Test database connection security
        Following Security First Principle
        """
        with connection.cursor() as cursor:
            # Test that connection uses secure settings
            security_check = self.validator.check_connection_security(cursor)
            self.assertTrue(security_check['secure_connection'])


class SQLInjectionTesterTest(TestCase):
    """
    Test suite for SQLInjectionTester
    Following SOLID principles with comprehensive test coverage
    """

    def setUp(self):
        """
        Set up test environment
        Following Single Responsibility Principle
        """
        self.tester = SQLInjectionTester()

    def test_sql_injection_test_suite(self):
        """
        Test comprehensive SQL injection test suite
        Following Security First Principle
        """
        test_results = self.tester.run_all_tests()

        # Should run all test categories
        self.assertIn('union_based', test_results)
        self.assertIn('boolean_based_blind', test_results)
        self.assertIn('time_based_blind', test_results)
        self.assertIn('error_based', test_results)
        self.assertIn('stacked_queries', test_results)

        # All tests should pass (vulnerabilities should be blocked)
        for test_category, results in test_results.items():
            if isinstance(results, dict) and 'passed' in results:
                self.assertTrue(results['passed'], f"{test_category} tests failed")

    def test_injection_pattern_testing(self):
        """
        Test specific injection pattern testing
        Following Security First Principle
        """
        # Test union-based injection
        union_result = self.tester.test_union_based_injection("test_input")
        self.assertTrue(union_result['blocked'])

        # Test boolean-based blind injection
        boolean_result = self.tester.test_boolean_blind_injection("test_input")
        self.assertTrue(boolean_result['blocked'])

        # Test time-based blind injection
        time_result = self.tester.test_time_blind_injection("test_input")
        self.assertTrue(time_result['blocked'])

    def test_security_validation_report(self):
        """
        Test security validation report generation
        Following Single Responsibility Principle
        """
        report = self.tester.generate_security_report()

        self.assertIn('test_summary', report)
        self.assertIn('vulnerability_assessment', report)
        self.assertIn('recommendations', report)
        self.assertIn('test_timestamp', report)

        # Should indicate good security (no vulnerabilities found)
        self.assertEqual(report['vulnerability_assessment']['critical_vulnerabilities'], 0)