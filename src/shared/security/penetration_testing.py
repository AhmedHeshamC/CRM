"""
Comprehensive Penetration Testing Suite for Security Validation
Following SOLID principles and enterprise-grade security standards
"""

import json
import time
import logging
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass
from enum import Enum
from django.test import Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from shared.security.exceptions import SecurityError

logger = logging.getLogger(__name__)

User = get_user_model()


class PenetrationTestType(Enum):
    """
    Penetration test types
    Following Single Responsibility Principle for test categorization
    """
    AUTHENTICATION_BYPASS = "authentication_bypass"
    AUTHORIZATION_BYPASS = "authorization_bypass"
    SQL_INJECTION = "sql_injection"
    XSS_ATTACKS = "xss_attacks"
    CSRF_ATTACKS = "csrf_attacks"
    RATE_LIMITING_BYPASS = "rate_limiting_bypass"
    CORS_VIOLATIONS = "cors_violations"
    SECURITY_HEADERS = "security_headers"
    INPUT_VALIDATION = "input_validation"
    API_SECURITY = "api_security"
    SESSION_MANAGEMENT = "session_management"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    DATA_EXFILTRATION = "data_exfiltration"
    DENIAL_OF_SERVICE = "denial_of_service"


class TestResult(Enum):
    """
    Test result types
    Following Single Responsibility Principle for result classification
    """
    PASSED = "passed"
    FAILED = "failed"
    BLOCKED = "blocked"  # Attack was blocked (good for security)
    VULNERABLE = "vulnerable"  # System is vulnerable
    ERROR = "error"
    SKIPPED = "skipped"


@dataclass
class PenetrationTestResult:
    """
    Penetration test result data structure
    Following Single Responsibility Principle for test result management
    """
    test_type: PenetrationTestType
    test_name: str
    result: TestResult
    description: str
    evidence: Optional[Dict[str, Any]] = None
    vulnerability_details: Optional[Dict[str, Any]] = None
    recommendations: Optional[List[str]] = None
    execution_time: float = 0.0
    timestamp: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert test result to dictionary"""
        return {
            'test_type': self.test_type.value,
            'test_name': self.test_name,
            'result': self.result.value,
            'description': self.description,
            'evidence': self.evidence,
            'vulnerability_details': self.vulnerability_details,
            'recommendations': self.recommendations,
            'execution_time': self.execution_time,
            'timestamp': self.timestamp
        }


class AuthenticationBypassTester:
    """
    Authentication Bypass Penetration Tester
    Following Single Responsibility Principle for authentication security testing

    Features:
    - Weak password testing
    - Brute force simulation
    - Session fixation testing
    - Token manipulation
    - Authentication bypass attempts
    """

    def __init__(self):
        """Initialize authentication bypass tester"""
        self.client = Client()
        self.test_results = []

    def run_all_tests(self) -> List[PenetrationTestResult]:
        """Run all authentication bypass tests"""
        tests = [
            self.test_weak_passwords,
            self.test_brute_force_protection,
            self.test_session_fixation,
            self.test_token_manipulation,
            self.test_authentication_bypass,
            self.test_password_reset_abuse,
            self.test_account_lockout_bypass
        ]

        results = []
        for test in tests:
            try:
                result = test()
                results.append(result)
            except Exception as e:
                logger.error(f"Error in authentication test {test.__name__}: {str(e)}")
                results.append(PenetrationTestResult(
                    test_type=PenetrationTestType.AUTHENTICATION_BYPASS,
                    test_name=test.__name__,
                    result=TestResult.ERROR,
                    description=f"Test execution error: {str(e)}"
                ))

        return results

    def test_weak_passwords(self) -> PenetrationTestResult:
        """Test for weak password vulnerabilities"""
        start_time = time.time()
        weak_passwords = [
            'password', '123456', 'admin', 'welcome', 'qwerty',
            'letmein', 'dragon', 'password1', '123456789', 'abc123'
        ]

        weak_password_users = []

        for password in weak_passwords:
            # Create test user with weak password
            email = f"test_{password}@example.com"
            try:
                user = User.objects.create_user(
                    email=email,
                    password=password,
                    role='sales'
                )

                # Try to login with weak password
                response = self.client.post('/api/v1/auth/auth/login/', {
                    'email': email,
                    'password': password
                })

                if response.status_code == 200:
                    weak_password_users.append({
                        'email': email,
                        'password': password,
                        'weakness': 'Weak password allowed'
                    })

                # Clean up
                user.delete()

            except Exception:
                continue

        execution_time = time.time() - start_time

        if weak_password_users:
            return PenetrationTestResult(
                test_type=PenetrationTestType.AUTHENTICATION_BYPASS,
                test_name="Weak Password Test",
                result=TestResult.VULNERABLE,
                description="Weak passwords are allowed in the system",
                evidence={'weak_password_users': weak_password_users},
                vulnerability_details={
                    'severity': 'medium',
                    'cvss_score': 5.0,
                    'affected_users': len(weak_password_users)
                },
                recommendations=[
                    "Implement strong password policies",
                    "Add password complexity requirements",
                    "Use password strength validation",
                    "Implement password blacklisting"
                ],
                execution_time=execution_time
            )
        else:
            return PenetrationTestResult(
                test_type=PenetrationTestType.AUTHENTICATION_BYPASS,
                test_name="Weak Password Test",
                result=TestResult.PASSED,
                description="Weak passwords are properly rejected",
                execution_time=execution_time
            )

    def test_brute_force_protection(self) -> PenetrationTestResult:
        """Test brute force protection mechanisms"""
        start_time = time.time()
        email = "bruteforce_test@example.com"

        # Create test user
        user = User.objects.create_user(
            email=email,
            password="StrongPassword123!",
            role='sales'
        )

        failed_attempts = 0
        login_blocked = False

        # Attempt multiple failed logins
        for i in range(20):
            response = self.client.post('/api/v1/auth/auth/login/', {
                'email': email,
                'password': f"WrongPassword{i}"
            })

            if response.status_code == 429:  # Too Many Requests
                login_blocked = True
                break

            failed_attempts += 1

        # Clean up
        user.delete()

        execution_time = time.time() - start_time

        if login_blocked:
            return PenetrationTestResult(
                test_type=PenetrationTestType.AUTHENTICATION_BYPASS,
                test_name="Brute Force Protection Test",
                result=TestResult.PASSED,
                description="Brute force protection is working",
                evidence={
                    'failed_attempts_before_block': failed_attempts,
                    'login_blocked': login_blocked
                },
                execution_time=execution_time
            )
        else:
            return PenetrationTestResult(
                test_type=PenetrationTestType.AUTHENTICATION_BYPASS,
                test_name="Brute Force Protection Test",
                result=TestResult.VULNERABLE,
                description="No brute force protection detected",
                evidence={
                    'failed_attempts': failed_attempts,
                    'login_blocked': login_blocked
                },
                vulnerability_details={
                    'severity': 'high',
                    'cvss_score': 7.5,
                    'failed_attempts_allowed': failed_attempts
                },
                recommendations=[
                    "Implement account lockout after failed attempts",
                    "Add progressive delays for failed attempts",
                    "Implement CAPTCHA after multiple failures",
                    "Monitor and alert on suspicious login patterns"
                ],
                execution_time=execution_time
            )

    def test_session_fixation(self) -> PenetrationTestResult:
        """Test for session fixation vulnerabilities"""
        start_time = time.time()

        # Get initial session
        response = self.client.get('/api/v1/contacts/')
        initial_session_id = self.client.session.session_key

        # Simulate login (this should regenerate session)
        user = User.objects.create_user(
            email="session_test@example.com",
            password="TestPassword123!",
            role='sales'
        )

        self.client.post('/api/v1/auth/auth/login/', {
            'email': "session_test@example.com",
            'password': "TestPassword123!"
        })

        new_session_id = self.client.session.session_key

        user.delete()
        execution_time = time.time() - start_time

        if initial_session_id == new_session_id:
            return PenetrationTestResult(
                test_type=PenetrationTestType.AUTHENTICATION_BYPASS,
                test_name="Session Fixation Test",
                result=TestResult.VULNERABLE,
                description="Session ID is not regenerated on login",
                evidence={
                    'initial_session_id': initial_session_id,
                    'post_login_session_id': new_session_id
                },
                vulnerability_details={
                    'severity': 'medium',
                    'cvss_score': 5.5
                },
                recommendations=[
                    "Regenerate session ID on authentication",
                    "Implement session timeout mechanisms",
                    "Use secure session handling practices"
                ],
                execution_time=execution_time
            )
        else:
            return PenetrationTestResult(
                test_type=PenetrationTestType.AUTHENTICATION_BYPASS,
                test_name="Session Fixation Test",
                result=TestResult.PASSED,
                description="Session ID is properly regenerated on login",
                evidence={
                    'session_regenerated': True
                },
                execution_time=execution_time
            )

    def test_token_manipulation(self) -> PenetrationTestResult:
        """Test JWT token manipulation attacks"""
        start_time = time.time()

        # Create and login user
        user = User.objects.create_user(
            email="token_test@example.com",
            password="TestPassword123!",
            role='sales'
        )

        response = self.client.post('/api/v1/auth/auth/login/', {
            'email': "token_test@example.com",
            'password': "TestPassword123!"
        })

        original_token = response.json().get('access')
        token_manipulation_results = []

        # Test token manipulation scenarios
        manipulation_scenarios = [
            ("Token truncation", original_token[:20]),
            ("Token extension", original_token + "extra"),
            ("Token character replacement", original_token.replace('a', 'b')),
            ("Invalid token format", "invalid.token.here"),
            ("Expired token format", "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.invalid")
        ]

        for scenario_name, manipulated_token in manipulation_scenarios:
            self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {manipulated_token}')
            response = self.client.get('/api/v1/contacts/')

            token_manipulation_results.append({
                'scenario': scenario_name,
                'status_code': response.status_code,
                'access_granted': response.status_code == 200
            })

        user.delete()
        execution_time = time.time() - start_time

        unauthorized_access = [r for r in token_manipulation_results if r['access_granted']]

        if unauthorized_access:
            return PenetrationTestResult(
                test_type=PenetrationTestType.AUTHENTICATION_BYPASS,
                test_name="Token Manipulation Test",
                result=TestResult.VULNERABLE,
                description="Token manipulation grants unauthorized access",
                evidence={'unauthorized_access': unauthorized_access},
                vulnerability_details={
                    'severity': 'critical',
                    'cvss_score': 9.0,
                    'vulnerabilities_found': len(unauthorized_access)
                },
                recommendations=[
                    "Implement proper JWT token validation",
                    "Use strong cryptographic signatures",
                    "Validate token structure and format",
                    "Implement token revocation mechanisms"
                ],
                execution_time=execution_time
            )
        else:
            return PenetrationTestResult(
                test_type=PenetrationTestType.AUTHENTICATION_BYPASS,
                test_name="Token Manipulation Test",
                result=TestResult.PASSED,
                description="Token manipulation is properly blocked",
                evidence={'all_attempts_blocked': True},
                execution_time=execution_time
            )

    def test_authentication_bypass(self) -> PenetrationTestResult:
        """Test for authentication bypass vulnerabilities"""
        start_time = time.time()

        bypass_attempts = [
            ("Direct API access without auth", lambda: self.client.get('/api/v1/contacts/')),
            ("Null authentication header", lambda: self.client.get('/api/v1/contacts/', HTTP_AUTHORIZATION='')),
            ("Empty authentication header", lambda: self.client.get('/api/v1/contacts/', HTTP_AUTHORIZATION='Bearer ')),
            ("Invalid authentication scheme", lambda: self.client.get('/api/v1/contacts/', HTTP_AUTHORIZATION='Basic dGVzdA==')),
            ("Malformed bearer token", lambda: self.client.get('/api/v1/contacts/', HTTP_AUTHORIZATION='Bearer malformed.token')),
        ]

        bypass_results = []

        for attempt_name, attempt_func in bypass_attempts:
            try:
                response = attempt_func()
                bypass_results.append({
                    'attempt': attempt_name,
                    'status_code': response.status_code,
                    'bypass_successful': response.status_code == 200
                })
            except Exception as e:
                bypass_results.append({
                    'attempt': attempt_name,
                    'status_code': 'error',
                    'bypass_successful': False,
                    'error': str(e)
                })

        execution_time = time.time() - start_time

        successful_bypasses = [r for r in bypass_results if r['bypass_successful']]

        if successful_bypasses:
            return PenetrationTestResult(
                test_type=PenetrationTestType.AUTHENTICATION_BYPASS,
                test_name="Authentication Bypass Test",
                result=TestResult.VULNERABLE,
                description="Authentication bypass vulnerabilities detected",
                evidence={'successful_bypasses': successful_bypasses},
                vulnerability_details={
                    'severity': 'critical',
                    'cvss_score': 10.0,
                    'bypasses_found': len(successful_bypasses)
                },
                recommendations=[
                    "Implement proper authentication middleware",
                    "Validate authentication on all API endpoints",
                    "Use strict authentication checks",
                    "Implement defense in depth security layers"
                ],
                execution_time=execution_time
            )
        else:
            return PenetrationTestResult(
                test_type=PenetrationTestType.AUTHENTICATION_BYPASS,
                test_name="Authentication Bypass Test",
                result=TestResult.PASSED,
                description="Authentication is properly enforced",
                evidence={'all_attempts_blocked': True},
                execution_time=execution_time
            )

    def test_password_reset_abuse(self) -> PenetrationTestResult:
        """Test password reset abuse vulnerabilities"""
        start_time = time.time()

        # Test password reset enumeration
        test_emails = [
            "existing@example.com",
            "nonexistent@example.com",
            "admin@example.com",
            "test@example.com"
        ]

        reset_responses = []
        for email in test_emails:
            response = self.client.post('/api/v1/auth/auth/password-reset/', {
                'email': email
            })
            reset_responses.append({
                'email': email,
                'status_code': response.status_code,
                'response_time': response.get('Content-Type', '')
            })

        execution_time = time.time() - start_time

        # Check if responses reveal email existence
        consistent_responses = len(set(r['status_code'] for r in reset_responses)) == 1

        if not consistent_responses:
            return PenetrationTestResult(
                test_type=PenetrationTestType.AUTHENTICATION_BYPASS,
                test_name="Password Reset Abuse Test",
                result=TestResult.VULNERABLE,
                description="Password reset responses reveal email existence",
                evidence={'reset_responses': reset_responses},
                vulnerability_details={
                    'severity': 'low',
                    'cvss_score': 3.0,
                    'issue': 'Email enumeration possible'
                },
                recommendations=[
                    "Use consistent responses for password reset",
                    "Don't reveal email existence in responses",
                    "Implement rate limiting for password reset"
                ],
                execution_time=execution_time
            )
        else:
            return PenetrationTestResult(
                test_type=PenetrationTestType.AUTHENTICATION_BYPASS,
                test_name="Password Reset Abuse Test",
                result=TestResult.PASSED,
                description="Password reset responses are consistent",
                evidence={'consistent_responses': True},
                execution_time=execution_time
            )

    def test_account_lockout_bypass(self) -> PenetrationTestResult:
        """Test account lockout bypass vulnerabilities"""
        start_time = time.time()

        # This test would require setting up an account with failed attempts
        # and then testing various bypass techniques
        execution_time = time.time() - start_time

        return PenetrationTestResult(
            test_type=PenetrationTestType.AUTHENTICATION_BYPASS,
            test_name="Account Lockout Bypass Test",
            result=TestResult.SKIPPED,
            description="Account lockout bypass test not implemented",
            execution_time=execution_time
        )


class APISecurityTester:
    """
    API Security Penetration Tester
    Following Single Responsibility Principle for API security testing

    Features:
    - API endpoint security testing
    - Parameter pollution testing
    - Mass assignment testing
    - API versioning security
    - Resource enumeration testing
    """

    def __init__(self):
        """Initialize API security tester"""
        self.client = Client()
        self.test_results = []

    def run_all_tests(self) -> List[PenetrationTestResult]:
        """Run all API security tests"""
        tests = [
            self.test_api_endpoint_security,
            self.test_parameter_pollution,
            self.test_mass_assignment,
            self.test_resource_enumeration,
            self.test_api_versioning_security,
            self.test_http_method_security,
            self.test_request_size_limits,
            self.test_response_data_leakage
        ]

        results = []
        for test in tests:
            try:
                result = test()
                results.append(result)
            except Exception as e:
                logger.error(f"Error in API security test {test.__name__}: {str(e)}")
                results.append(PenetrationTestResult(
                    test_type=PenetrationTestType.API_SECURITY,
                    test_name=test.__name__,
                    result=TestResult.ERROR,
                    description=f"Test execution error: {str(e)}"
                ))

        return results

    def test_api_endpoint_security(self) -> PenetrationTestResult:
        """Test API endpoint security"""
        start_time = time.time()

        # Test various endpoint security aspects
        security_tests = [
            # Test non-existent endpoints
            ("/api/v1/nonexistent/", 404, "Non-existent endpoint"),
            ("/api/v2/contacts/", 404, "Different API version"),

            # Test HTTP method restrictions
            ("/api/v1/contacts/", "OPTIONS", "OPTIONS method"),
            ("/api/v1/contacts/", "TRACE", "TRACE method"),
            ("/api/v1/contacts/", "CONNECT", "CONNECT method"),
        ]

        test_results = []
        for endpoint, expected, test_name in security_tests:
            if isinstance(expected, int):
                response = self.client.get(endpoint)
                status_code = response.status_code
            else:  # HTTP method
                if hasattr(self.client, expected.lower()):
                    response = getattr(self.client, expected.lower())(endpoint)
                    status_code = response.status_code
                else:
                    status_code = 405  # Method Not Allowed

            test_results.append({
                'test': test_name,
                'endpoint': endpoint,
                'expected': expected if isinstance(expected, int) else expected,
                'actual': status_code,
                'passed': status_code in [404, 405]  # Expected for non-existent/blocked
            })

        execution_time = time.time() - start_time
        failed_tests = [t for t in test_results if not t['passed']]

        if failed_tests:
            return PenetrationTestResult(
                test_type=PenetrationTestType.API_SECURITY,
                test_name="API Endpoint Security Test",
                result=TestResult.VULNERABLE,
                description="API endpoint security issues found",
                evidence={'failed_tests': failed_tests},
                vulnerability_details={
                    'severity': 'medium',
                    'cvss_score': 5.5,
                    'issues_found': len(failed_tests)
                },
                recommendations=[
                    "Implement proper endpoint security",
                    "Restrict HTTP methods appropriately",
                    "Handle non-existent endpoints securely",
                    "Use API gateway for security controls"
                ],
                execution_time=execution_time
            )
        else:
            return PenetrationTestResult(
                test_type=PenetrationTestType.API_SECURITY,
                test_name="API Endpoint Security Test",
                result=TestResult.PASSED,
                description="API endpoints are properly secured",
                evidence={'all_tests_passed': True},
                execution_time=execution_time
            )

    def test_parameter_pollution(self) -> PenetrationTestResult:
        """Test HTTP parameter pollution vulnerabilities"""
        start_time = time.time()

        pollution_tests = [
            # Duplicate parameters
            ("name=John&name=Admin", "Duplicate name parameter"),
            ("id=1&id=999", "Duplicate ID parameter"),
            ("email=user@test.com&email=admin@test.com", "Duplicate email parameter"),

            # Parameter injection
            ("name=John&role=admin", "Role parameter injection"),
            ("name=John&is_admin=true", "Admin flag injection"),
            ("contact_id=1&user_id=1", "ID manipulation"),
        ]

        test_results = []
        for params, test_name in pollution_tests:
            response = self.client.post('/api/v1/contacts/', params, content_type='application/x-www-form-urlencoded')
            test_results.append({
                'test': test_name,
                'params': params,
                'status_code': response.status_code,
                'response_data': response.json() if response.content else None
            })

        execution_time = time.time() - start_time

        # Check for parameter pollution vulnerabilities
        vulnerable_responses = []
        for result in test_results:
            if result['status_code'] == 200 and result['response_data']:
                # Check if response indicates privilege escalation or unexpected behavior
                response_data = result['response_data']
                if any(key in str(response_data).lower() for key in ['admin', 'role', 'privilege']):
                    vulnerable_responses.append(result)

        if vulnerable_responses:
            return PenetrationTestResult(
                test_type=PenetrationTestType.API_SECURITY,
                test_name="Parameter Pollution Test",
                result=TestResult.VULNERABLE,
                description="HTTP parameter pollution vulnerabilities detected",
                evidence={'vulnerable_responses': vulnerable_responses},
                vulnerability_details={
                    'severity': 'high',
                    'cvss_score': 7.0,
                    'vulnerabilities_found': len(vulnerable_responses)
                },
                recommendations=[
                    "Validate and sanitize all input parameters",
                    "Use parameter whitelisting",
                    "Implement input validation middleware",
                    "Use API parameter validation frameworks"
                ],
                execution_time=execution_time
            )
        else:
            return PenetrationTestResult(
                test_type=PenetrationTestType.API_SECURITY,
                test_name="Parameter Pollution Test",
                result=TestResult.PASSED,
                description="Parameter pollution attacks are properly blocked",
                evidence={'all_tests_passed': True},
                execution_time=execution_time
            )

    def test_mass_assignment(self) -> PenetrationTestResult:
        """Test for mass assignment vulnerabilities"""
        start_time = time.time()

        # Test data with potentially dangerous fields
        dangerous_payloads = [
            {
                "name": "Test Contact",
                "email": "test@example.com",
                "role": "admin",  # Should not be assignable
                "is_active": True,  # Should not be assignable
                "created_at": "2023-01-01T00:00:00Z",  # Should not be assignable
            },
            {
                "name": "Test Contact 2",
                "email": "test2@example.com",
                "user_id": 1,  # Should not be assignable
                "deleted": False,  # Should not be assignable
                "id": 999,  # Should not be assignable
            },
        ]

        test_results = []
        for i, payload in enumerate(dangerous_payloads):
            response = self.client.post('/api/v1/contacts/', payload, content_type='application/json')
            test_results.append({
                'payload': payload,
                'status_code': response.status_code,
                'response_data': response.json() if response.content else None,
                'field_assignment_successful': response.status_code == 201
            })

        execution_time = time.time() - start_time

        successful_assignments = [r for r in test_results if r['field_assignment_successful']]

        if successful_assignments:
            return PenetrationTestResult(
                test_type=PenetrationTestType.API_SECURITY,
                test_name="Mass Assignment Test",
                result=TestResult.VULNERABLE,
                description="Mass assignment vulnerabilities detected",
                evidence={'successful_assignments': successful_assignments},
                vulnerability_details={
                    'severity': 'high',
                    'cvss_score': 7.5,
                    'vulnerabilities_found': len(successful_assignments)
                },
                recommendations=[
                    "Use explicit field whitelisting in serializers",
                    "Implement field-level permissions",
                    "Use mass assignment protection frameworks",
                    "Validate all assignable fields"
                ],
                execution_time=execution_time
            )
        else:
            return PenetrationTestResult(
                test_type=PenetrationTestType.API_SECURITY,
                test_name="Mass Assignment Test",
                result=TestResult.PASSED,
                description="Mass assignment attacks are properly blocked",
                evidence={'all_attempts_blocked': True},
                execution_time=execution_time
            )

    def test_resource_enumeration(self) -> PenetrationTestResult:
        """Test for resource enumeration vulnerabilities"""
        start_time = time.time()

        # Test resource ID enumeration
        enumeration_tests = [
            # Test consecutive IDs
            [1, 2, 3, 4, 5],
            # Test common IDs
            [1, 10, 100, 1000],
            # Test potential admin/user IDs
            [1, 2, 9999, 10000],
            # Test negative and zero IDs
            [-1, 0],
        ]

        test_results = []
        for id_list in enumeration_tests:
            enumeration_results = []
            for test_id in id_list:
                response = self.client.get(f'/api/v1/contacts/{test_id}/')
                enumeration_results.append({
                    'id': test_id,
                    'status_code': response.status_code,
                    'data_exposed': response.status_code == 200 and response.content
                })

            test_results.append({
                'id_list': id_list,
                'results': enumeration_results,
                'resources_found': len([r for r in enumeration_results if r['data_exposed']])
            })

        execution_time = time.time() - start_time

        # Check for excessive resource enumeration
        total_resources_found = sum(t['resources_found'] for t in test_results)

        if total_resources_found > 10:  # Threshold for "excessive" enumeration
            return PenetrationTestResult(
                test_type=PenetrationTestType.API_SECURITY,
                test_name="Resource Enumeration Test",
                result=TestResult.VULNERABLE,
                description="Resource enumeration vulnerabilities detected",
                evidence={'enumeration_results': test_results},
                vulnerability_details={
                    'severity': 'medium',
                    'cvss_score': 5.0,
                    'resources_enumerated': total_resources_found
                },
                recommendations=[
                    "Implement resource access controls",
                    "Use UUIDs instead of sequential IDs",
                    "Implement rate limiting for enumeration",
                    "Add authorization checks for all resources"
                ],
                execution_time=execution_time
            )
        else:
            return PenetrationTestResult(
                test_type=PenetrationTestType.API_SECURITY,
                test_name="Resource Enumeration Test",
                result=TestResult.PASSED,
                description="Resource enumeration is properly controlled",
                evidence={'enumeration_controlled': True},
                execution_time=execution_time
            )

    def test_api_versioning_security(self) -> PenetrationTestResult:
        """Test API versioning security"""
        start_time = time.time()

        versioning_tests = [
            # Test different API versions
            "/api/v1/contacts/",
            "/api/v2/contacts/",
            "/api/v999/contacts/",
            # Test version manipulation
            "/api/v1.0/contacts/",
            "/api/v1.1/contacts/",
            "/api/v1-beta/contacts/",
            # Test missing version
            "/api/contacts/",
        ]

        test_results = []
        for endpoint in versioning_tests:
            response = self.client.get(endpoint)
            test_results.append({
                'endpoint': endpoint,
                'status_code': response.status_code,
                'response_available': response.content is not None
            })

        execution_time = time.time() - start_time

        # Check for versioning vulnerabilities
        unexpected_responses = [r for r in test_results if r['response_available'] and r['status_code'] == 200]

        if len(unexpected_responses) > 1:  # More than just the expected v1
            return PenetrationTestResult(
                test_type=PenetrationTestType.API_SECURITY,
                test_name="API Versioning Security Test",
                result=TestResult.VULNERABLE,
                description="API versioning security issues found",
                evidence={'unexpected_responses': unexpected_responses},
                vulnerability_details={
                    'severity': 'low',
                    'cvss_score': 3.5,
                    'unauthorized_versions': len(unexpected_responses)
                },
                recommendations=[
                    "Implement strict API version control",
                    "Use API gateway for version management",
                    "Deprecate old API versions properly",
                    "Document supported API versions"
                ],
                execution_time=execution_time
            )
        else:
            return PenetrationTestResult(
                test_type=PenetrationTestType.API_SECURITY,
                test_name="API Versioning Security Test",
                result=TestResult.PASSED,
                description="API versioning is properly implemented",
                evidence={'versioning_secure': True},
                execution_time=execution_time
            )

    def test_http_method_security(self) -> PenetrationTestResult:
        """Test HTTP method security"""
        start_time = time.time()

        dangerous_methods = [
            "TRACE", "CONNECT", "PATCH", "PROPFIND", "PROPPATCH",
            "MKCOL", "COPY", "MOVE", "LOCK", "UNLOCK"
        ]

        test_results = []
        for method in dangerous_methods:
            try:
                if hasattr(self.client, method.lower()):
                    response = getattr(self.client, method.lower())('/api/v1/contacts/')
                    test_results.append({
                        'method': method,
                        'status_code': response.status_code,
                        'allowed': response.status_code != 405
                    })
                else:
                    # Test with custom method
                    response = self.client.generic(method, '/api/v1/contacts/')
                    test_results.append({
                        'method': method,
                        'status_code': response.status_code,
                        'allowed': response.status_code != 405
                    })
            except Exception as e:
                test_results.append({
                    'method': method,
                    'status_code': 'error',
                    'allowed': False,
                    'error': str(e)
                })

        execution_time = time.time() - start_time

        allowed_dangerous_methods = [r for r in test_results if r.get('allowed', False)]

        if allowed_dangerous_methods:
            return PenetrationTestResult(
                test_type=PenetrationTestType.API_SECURITY,
                test_name="HTTP Method Security Test",
                result=TestResult.VULNERABLE,
                description="Dangerous HTTP methods are allowed",
                evidence={'allowed_methods': allowed_dangerous_methods},
                vulnerability_details={
                    'severity': 'medium',
                    'cvss_score': 5.0,
                    'dangerous_methods_allowed': len(allowed_dangerous_methods)
                },
                recommendations=[
                    "Disable dangerous HTTP methods",
                    "Use proper HTTP method validation",
                    "Configure web server security headers",
                    "Implement API gateway controls"
                ],
                execution_time=execution_time
            )
        else:
            return PenetrationTestResult(
                test_type=PenetrationTestType.API_SECURITY,
                test_name="HTTP Method Security Test",
                result=TestResult.PASSED,
                description="Dangerous HTTP methods are properly blocked",
                evidence={'all_dangerous_methods_blocked': True},
                execution_time=execution_time
            )

    def test_request_size_limits(self) -> PenetrationTestResult:
        """Test request size limits"""
        start_time = time.time()

        # Test large payloads
        large_payload = "x" * 10 * 1024 * 1024  # 10MB

        size_tests = [
            ("large_json", {"data": large_payload}, "application/json"),
            ("large_form", {"data": large_payload}, "application/x-www-form-urlencoded"),
        ]

        test_results = []
        for test_name, payload, content_type in size_tests:
            response = self.client.post('/api/v1/contacts/', payload, content_type=content_type)
            test_results.append({
                'test': test_name,
                'payload_size': len(str(payload)),
                'status_code': response.status_code,
                'accepted': response.status_code not in [400, 413, 414]
            })

        execution_time = time.time() - start_time

        accepted_large_requests = [r for r in test_results if r['accepted']]

        if accepted_large_requests:
            return PenetrationTestResult(
                test_type=PenetrationTestType.API_SECURITY,
                test_name="Request Size Limits Test",
                result=TestResult.VULNERABLE,
                description="Request size limits not properly enforced",
                evidence={'accepted_large_requests': accepted_large_requests},
                vulnerability_details={
                    'severity': 'medium',
                    'cvss_score': 5.0,
                    'oversized_requests_accepted': len(accepted_large_requests)
                },
                recommendations=[
                    "Implement request size limits",
                    "Configure web server limits",
                    "Use API gateway throttling",
                    "Monitor for DoS attacks"
                ],
                execution_time=execution_time
            )
        else:
            return PenetrationTestResult(
                test_type=PenetrationTestType.API_SECURITY,
                test_name="Request Size Limits Test",
                result=TestResult.PASSED,
                description="Request size limits are properly enforced",
                evidence={'all_large_requests_blocked': True},
                execution_time=execution_time
            )

    def test_response_data_leakage(self) -> PenetrationTestResult:
        """Test for sensitive data leakage in responses"""
        start_time = time.time()

        # Test error responses for information leakage
        error_tests = [
            ("Invalid endpoint", "/api/v1/nonexistent/"),
            ("Invalid method", lambda: self.client.delete('/api/v1/contacts/')),
            ("Invalid JSON", "/api/v1/contacts/", {"invalid": "json"}, "application/json"),
            ("Malformed data", "/api/v1/contacts/", "not-json", "application/json"),
        ]

        test_results = []
        for test_name, *test_args in error_tests:
            if len(test_args) == 1:
                response = self.client.get(test_args[0])
            elif len(test_args) == 2 and callable(test_args[1]):
                response = test_args[1]()
            elif len(test_args) == 3:
                response = self.client.post(test_args[0], test_args[1], content_type=test_args[2])

            response_content = response.content.decode('utf-8', errors='ignore').lower()
            sensitive_info = []

            # Check for sensitive information in error responses
            sensitive_patterns = [
                'traceback', 'exception', 'error:', 'file path', 'line number',
                'database', 'sql', 'query', 'internal server error',
                'stack trace', 'debug', 'python', 'django'
            ]

            for pattern in sensitive_patterns:
                if pattern in response_content:
                    sensitive_info.append(pattern)

            test_results.append({
                'test': test_name,
                'status_code': response.status_code,
                'response_length': len(response_content),
                'sensitive_info_found': sensitive_info
            })

        execution_time = time.time() - start_time

        leaking_responses = [r for r in test_results if r['sensitive_info_found']]

        if leaking_responses:
            return PenetrationTestResult(
                test_type=PenetrationTestType.API_SECURITY,
                test_name="Response Data Leakage Test",
                result=TestResult.VULNERABLE,
                description="Sensitive information leakage in responses",
                evidence={'leaking_responses': leaking_responses},
                vulnerability_details={
                    'severity': 'medium',
                    'cvss_score': 4.5,
                    'leaking_responses': len(leaking_responses)
                },
                recommendations=[
                    "Sanitize error responses",
                    "Use generic error messages",
                    "Implement proper error handling",
                    "Disable debug mode in production"
                ],
                execution_time=execution_time
            )
        else:
            return PenetrationTestResult(
                test_type=PenetrationTestType.API_SECURITY,
                test_name="Response Data Leakage Test",
                result=TestResult.PASSED,
                description="No sensitive information leakage detected",
                evidence={'all_responses_sanitized': True},
                execution_time=execution_time
            )


class PenetrationTestingSuite:
    """
    Comprehensive Penetration Testing Suite
    Following Single Responsibility Principle for penetration testing orchestration

    Features:
    - Multiple test categories
    - Comprehensive vulnerability scanning
    - Detailed reporting
    - Security scoring
    - Remediation recommendations
    """

    def __init__(self):
        """Initialize penetration testing suite"""
        self.testers = {
            'authentication': AuthenticationBypassTester(),
            'api_security': APISecurityTester(),
        }
        self.test_results = []

    def run_all_tests(self) -> Dict[str, Any]:
        """Run all penetration tests"""
        start_time = time.time()

        all_results = []
        test_categories = {}

        for category, tester in self.testers.items():
            try:
                category_results = tester.run_all_tests()
                all_results.extend(category_results)
                test_categories[category] = category_results
                logger.info(f"Completed {category} penetration tests: {len(category_results)} tests run")
            except Exception as e:
                logger.error(f"Error running {category} penetration tests: {str(e)}")
                test_categories[category] = []

        execution_time = time.time() - start_time

        # Analyze results
        analysis = self._analyze_test_results(all_results)

        # Generate report
        report = self._generate_test_report(test_categories, analysis, execution_time)

        return report

    def _analyze_test_results(self, results: List[PenetrationTestResult]) -> Dict[str, Any]:
        """Analyze test results and generate security metrics"""
        total_tests = len(results)
        passed_tests = len([r for r in results if r.result == TestResult.PASSED])
        failed_tests = len([r for r in results if r.result == TestResult.VULNERABLE])
        blocked_tests = len([r for r in results if r.result == TestResult.BLOCKED])
        error_tests = len([r for r in results if r.result == TestResult.ERROR])
        skipped_tests = len([r for r in results if r.result == TestResult.SKIPPED])

        # Calculate security score
        security_score = ((passed_tests + blocked_tests) / total_tests) * 100 if total_tests > 0 else 0

        # Count vulnerabilities by severity
        vulnerability_counts = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
        for result in results:
            if result.result == TestResult.VULNERABLE and result.vulnerability_details:
                severity = result.vulnerability_details.get('severity', 'low')
                if severity in vulnerability_counts:
                    vulnerability_counts[severity] += 1

        return {
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': failed_tests,
            'blocked_tests': blocked_tests,
            'error_tests': error_tests,
            'skipped_tests': skipped_tests,
            'security_score': security_score,
            'vulnerability_counts': vulnerability_counts,
            'vulnerabilities_found': failed_tests
        }

    def _generate_test_report(self, test_categories: Dict[str, List[PenetrationTestResult]],
                             analysis: Dict[str, Any], execution_time: float) -> Dict[str, Any]:
        """Generate comprehensive test report"""
        # Determine overall security level
        security_score = analysis['security_score']
        if security_score >= 90:
            security_level = 'Excellent'
        elif security_score >= 75:
            security_level = 'Good'
        elif security_score >= 60:
            security_level = 'Fair'
        else:
            security_level = 'Poor'

        # Collect all recommendations
        all_recommendations = []
        for category_results in test_categories.values():
            for result in category_results:
                if result.recommendations:
                    all_recommendations.extend(result.recommendations)

        # Remove duplicates
        unique_recommendations = list(set(all_recommendations))

        # Get critical vulnerabilities
        critical_vulnerabilities = []
        for category_results in test_categories.values():
            for result in category_results:
                if (result.result == TestResult.VULNERABLE and
                    result.vulnerability_details and
                    result.vulnerability_details.get('severity') == 'critical'):
                    critical_vulnerabilities.append({
                        'test_name': result.test_name,
                        'description': result.description,
                        'vulnerability_details': result.vulnerability_details,
                        'recommendations': result.recommendations
                    })

        return {
            'test_summary': {
                'total_tests': analysis['total_tests'],
                'passed_tests': analysis['passed_tests'],
                'vulnerabilities_found': analysis['vulnerabilities_found'],
                'security_score': security_score,
                'security_level': security_level,
                'execution_time_seconds': execution_time,
                'test_categories': list(test_categories.keys())
            },
            'vulnerability_analysis': {
                'severity_breakdown': analysis['vulnerability_counts'],
                'critical_vulnerabilities': critical_vulnerabilities,
                'total_cvss_score': self._calculate_total_cvss(test_categories)
            },
            'test_results_by_category': {
                category: [result.to_dict() for result in results]
                for category, results in test_categories.items()
            },
            'recommendations': {
                'immediate_actions': [r for r in unique_recommendations if 'critical' in r.lower() or 'immediate' in r.lower()],
                'short_term_improvements': [r for r in unique_recommendations if any(word in r.lower() for word in ['implement', 'add', 'enable'])],
                'long_term_enhancements': [r for r in unique_recommendations if any(word in r.lower() for word in ['consider', 'enhance', 'improve'])]
            },
            'compliance_status': {
                'security_standards': self._check_compliance_standards(analysis),
                'best_practices': self._check_best_practices(test_categories)
            },
            'test_metadata': {
                'timestamp': timezone.now().isoformat(),
                'test_environment': 'development',  # This could be configurable
                'test_version': '1.0.0'
            }
        }

    def _calculate_total_cvss(self, test_categories: Dict[str, List[PenetrationTestResult]]) -> float:
        """Calculate total CVSS score for all vulnerabilities"""
        total_cvss = 0.0
        vulnerability_count = 0

        for category_results in test_categories.values():
            for result in category_results:
                if (result.result == TestResult.VULNERABLE and
                    result.vulnerability_details and
                    'cvss_score' in result.vulnerability_details):
                    total_cvss += result.vulnerability_details['cvss_score']
                    vulnerability_count += 1

        return total_cvss / vulnerability_count if vulnerability_count > 0 else 0.0

    def _check_compliance_standards(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Check compliance against security standards"""
        return {
            'owasp_top_10': {
                'compliant': analysis['vulnerabilities_found'] == 0,
                'issues_found': max(0, analysis['vulnerabilities_found'] - 2)  # Some tolerance
            },
            'ciso_standards': {
                'compliant': analysis['security_score'] >= 80,
                'score': analysis['security_score']
            },
            'iso_27001': {
                'compliant': analysis['vulnerability_counts']['critical'] == 0,
                'critical_issues': analysis['vulnerability_counts']['critical']
            }
        }

    def _check_best_practices(self, test_categories: Dict[str, List[PenetrationTestResult]]) -> Dict[str, bool]:
        """Check adherence to security best practices"""
        best_practices = {
            'authentication_security': True,
            'input_validation': True,
            'error_handling': True,
            'access_controls': True,
            'security_headers': True
        }

        # This is a simplified check - in reality, this would be more comprehensive
        for category_results in test_categories.values():
            for result in category_results:
                if result.result == TestResult.VULNERABLE:
                    if 'authentication' in result.test_name.lower():
                        best_practices['authentication_security'] = False
                    elif 'input' in result.test_name.lower() or 'validation' in result.test_name.lower():
                        best_practices['input_validation'] = False
                    elif 'error' in result.test_name.lower():
                        best_practices['error_handling'] = False

        return best_practices

    def generate remediation_plan(self, test_report: Dict[str, Any]) -> Dict[str, Any]:
        """Generate prioritized remediation plan"""
        critical_vulnerabilities = test_report['vulnerability_analysis']['critical_vulnerabilities']
        recommendations = test_report['recommendations']

        # Prioritize critical issues
        remediation_priority = []

        # Add critical vulnerabilities first
        for vuln in critical_vulnerabilities:
            remediation_priority.append({
                'priority': 'Critical',
                'issue': vuln['description'],
                'recommendations': vuln['recommendations'],
                'estimated_effort': 'High',
                'impact': 'Critical Security Risk'
            })

        # Add high-priority recommendations
        for rec in recommendations['immediate_actions']:
            remediation_priority.append({
                'priority': 'High',
                'issue': rec,
                'recommendations': [rec],
                'estimated_effort': 'Medium',
                'impact': 'Security Improvement'
            })

        return {
            'remediation_plan': remediation_priority,
            'timeline_suggestion': {
                'critical_issues': 'Immediate (within 24 hours)',
                'high_priority': 'Within 1 week',
                'medium_priority': 'Within 1 month',
                'low_priority': 'Within 3 months'
            },
            'resource_requirements': {
                'development_team': 'Required for code changes',
                'security_team': 'Required for review and validation',
                'devops_team': 'Required for deployment and monitoring'
            }
        }


# Global penetration testing suite instance
penetration_testing_suite = PenetrationTestingSuite()


def run_penetration_tests() -> Dict[str, Any]:
    """
    Run comprehensive penetration tests
    Following Single Responsibility Principle
    """
    return penetration_testing_suite.run_all_tests()


def generate_security_report() -> Dict[str, Any]:
    """
    Generate security assessment report
    Following Single Responsibility Principle
    """
    test_results = run_penetration_tests()
    return penetration_testing_suite.generate_remediation_plan(test_results)