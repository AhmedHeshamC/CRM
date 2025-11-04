"""
Advanced Security Testing for Enterprise Django CRM
Comprehensive security vulnerability testing with TDD approach
"""

import pytest
import re
import hashlib
import secrets
import time
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core import mail
from django.conf import settings
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch, MagicMock
import requests
import json

User = get_user_model()


class AuthenticationSecurityTests(TestCase):
    """
    Advanced authentication security testing
    """

    def setUp(self):
        """Set up security test environment"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='test@company.com',
            password='TestPass123!',
            first_name='Test',
            last_name='User',
            role='sales'
        )

    def test_password_strength_validation(self):
        """
        Security Test: Password strength requirements
        TDD: Implement strong password validation
        """
        weak_passwords = [
            '12345678',  # Only numbers
            'password',  # Common password
            'qwerty123',  # Keyboard pattern
            'admin123',   # Common admin pattern
            'Test1',      # Too short
            'testtest',   # No numbers or uppercase
            'TESTTEST',   # No lowercase or numbers
            '12345678',   # No letters
        ]

        for weak_password in weak_passwords:
            response = self.client.post('/api/v1/auth/register/', {
                'email': f'test{weak_password}@company.com',
                'first_name': 'Test',
                'last_name': 'User',
                'password': weak_password,
                'password_confirm': weak_password,
                'role': 'sales'
            })
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn('password', response.json())

    def test_brute_force_protection(self):
        """
        Security Test: Brute force attack protection
        TDD: Implement rate limiting and account lockout
        """
        failed_attempts = 0
        lockout_triggered = False

        for i in range(30):  # Try 30 failed attempts
            response = self.client.post('/api/v1/auth/login/', {
                'email': 'test@company.com',
                'password': f'wrongpassword{i}'
            })

            if response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
                lockout_triggered = True
                break

            failed_attempts += 1

        # Should trigger rate limiting before too many attempts
        self.assertTrue(lockout_triggered, "Brute force protection not triggered")
        self.assertLess(failed_attempts, 15, "Too many failed attempts allowed")

    def test_session_hijacking_protection(self):
        """
        Security Test: Session hijacking protection
        TDD: Implement secure session management
        """
        # Login to get token
        login_response = self.client.post('/api/v1/auth/login/', {
            'email': 'test@company.com',
            'password': 'TestPass123!'
        })

        token = login_response.json()['access_token']

        # Test token is not easily guessable
        # JWT tokens should be cryptographically random
        self.assertNotRegex(token, r'^[a-zA-Z0-9]{20,}$')  # Not simple alphanumeric

        # Test token expiration
        time.sleep(1)  # Wait to ensure different timestamps

        # Token should be valid immediately after login
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = self.client.get('/api/v1/auth/users/me/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_csrf_protection(self):
        """
        Security Test: CSRF protection
        TDD: Implement CSRF tokens for state-changing operations
        """
        # Test that CSRF protection is enabled
        # This would be tested in a browser environment
        # For API, we focus on JWT token security

        # Ensure sensitive operations require authentication
        sensitive_endpoints = [
            ('/api/v1/auth/users/', 'POST'),
            ('/api/v1/auth/users/1/', 'PATCH'),
            ('/api/v1/auth/users/1/', 'DELETE'),
        ]

        for endpoint, method in sensitive_endpoints:
            response = self.client.generic(method, endpoint, {})
            self.assertIn(response.status_code, [
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_403_FORBIDDEN
            ])

    def test_two_factor_authentication_security(self):
        """
        Security Test: Two-factor authentication
        TDD: Implement secure 2FA
        """
        # Enable 2FA for user
        self.user.two_factor_enabled = True
        self.user.save()

        # Test that regular login requires additional verification
        login_response = self.client.post('/api/v1/auth/login/', {
            'email': 'test@company.com',
            'password': 'TestPass123!'
        })

        # Should indicate 2FA is required
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        self.assertIn('two_factor_required', login_response.json())


class InputValidationSecurityTests(TestCase):
    """
    Advanced input validation security testing
    """

    def setUp(self):
        """Set up validation security test environment"""
        self.client = APIClient()
        self.admin_user = User.objects.create_user(
            email='admin@company.com',
            password='AdminPass123!',
            first_name='Admin',
            last_name='User',
            role='admin',
            is_staff=True
        )
        self.client.force_authenticate(user=self.admin_user)

    def test_sql_injection_protection(self):
        """
        Security Test: SQL injection protection
        TDD: Ensure all inputs are properly sanitized
        """
        sql_injection_payloads = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "' UNION SELECT * FROM auth_user --",
            "'; UPDATE auth_user SET is_superuser=True WHERE id=1; --",
            "' OR 1=1 #",
            "admin'--",
            "' OR 'x'='x",
        ]

        for payload in sql_injection_payloads:
            # Test login endpoint
            response = self.client.post('/api/v1/auth/login/', {
                'email': payload,
                'password': 'password'
            })
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

            # Test search endpoints
            response = self.client.get(f'/api/v1/auth/users/?search={payload}')
            self.assertNotEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

            # Verify database integrity
            self.assertEqual(User.objects.count(), 1)  # Only our test user should exist

    def test_xss_protection(self):
        """
        Security Test: Cross-site scripting protection
        TDD: Implement proper output encoding
        """
        xss_payloads = [
            '<script>alert("XSS")</script>',
            'javascript:alert("XSS")',
            '<img src="x" onerror="alert(1)">',
            '"><script>alert(1)</script>',
            '<svg onload="alert(1)">',
            '"><script>document.location="http://evil.com"</script>',
        ]

        for payload in xss_payloads:
            # Test user creation
            response = self.client.post('/api/v1/auth/users/', {
                'email': f'test{hashlib.md5(payload.encode()).hexdigest()}@company.com',
                'first_name': payload,
                'last_name': 'User',
                'password': 'SecurePass123!',
                'role': 'sales'
            })

            if response.status_code == status.HTTP_201_CREATED:
                user_id = response.json()['id']

                # Test that XSS payload is not executed in response
                response = self.client.get(f'/api/v1/auth/users/{user_id}/')
                self.assertEqual(response.status_code, status.HTTP_200_OK)

                # Check that script tags are not present in response
                response_text = json.dumps(response.json())
                self.assertNotIn('<script>', response_text)
                self.assertNotIn('javascript:', response_text)
                self.assertNotIn('onerror=', response_text)

    def test_command_injection_protection(self):
        """
        Security Test: Command injection protection
        TDD: Ensure system commands are not executed from user input
        """
        command_injection_payloads = [
            '; ls -la',
            '| cat /etc/passwd',
            '&& echo "Command executed"',
            '; rm -rf /',
            '`whoami`',
            '$(id)',
        ]

        for payload in command_injection_payloads:
            # Test in user search
            response = self.client.get(f'/api/v1/auth/users/?search={payload}')
            self.assertNotEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

            # Test in file upload (if applicable)
            response = self.client.post('/api/v1/contacts/', {
                'first_name': payload,
                'last_name': 'Test',
                'email': f'test{hashlib.md5(payload.encode()).hexdigest()}@company.com',
                'owner': self.admin_user.id
            })
            # Should either succeed (sanitized) or fail with validation error
            self.assertNotEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

    def test_file_upload_security(self):
        """
        Security Test: File upload security
        TDD: Implement secure file upload handling
        """
        malicious_files = [
            ('malicious.php', '<?php system($_GET["cmd"]); ?>'),
            ('shell.jsp', '<%@ page import="java.io.*" %><%=request.getParameter("cmd")%>'),
            ('exploit.html', '<script>alert("XSS")</script>'),
            ('large_file.txt', 'A' * (10 * 1024 * 1024)),  # 10MB file
        ]

        for filename, content in malicious_files:
            # Test file upload security
            # This would test actual file upload endpoints
            # For now, test that malicious file names are handled
            response = self.client.post('/api/v1/contacts/', {
                'first_name': 'Test',
                'last_name': filename,  # Test malicious filename
                'email': f'test{hashlib.md5(filename.encode()).hexdigest()}@company.com',
                'owner': self.admin_user.id
            })

            # Should handle malicious filenames safely
            self.assertNotEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)


class AuthorizationSecurityTests(TestCase):
    """
    Advanced authorization security testing
    """

    def setUp(self):
        """Set up authorization security test environment"""
        self.client = APIClient()

        # Create users with different roles
        self.admin_user = User.objects.create_user(
            email='admin@company.com',
            password='AdminPass123!',
            first_name='Admin',
            last_name='User',
            role='admin',
            is_staff=True
        )

        self.manager_user = User.objects.create_user(
            email='manager@company.com',
            password='ManagerPass123!',
            first_name='Manager',
            last_name='User',
            role='manager'
        )

        self.sales_user = User.objects.create_user(
            email='sales@company.com',
            password='SalesPass123!',
            first_name='Sales',
            last_name='User',
            role='sales'
        )

    def test_privilege_escalation_prevention(self):
        """
        Security Test: Privilege escalation prevention
        TDD: Ensure users cannot escalate their privileges
        """
        # Test regular user trying to access admin functions
        self.client.force_authenticate(user=self.sales_user)

        # Try to create admin user
        response = self.client.post('/api/v1/auth/users/', {
            'email': 'newadmin@company.com',
            'first_name': 'New',
            'last_name': 'Admin',
            'password': 'AdminPass123!',
            'role': 'admin'
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Try to upgrade own role
        response = self.client.patch(f'/api/v1/auth/users/{self.sales_user.id}/', {
            'role': 'admin'
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Verify user role hasn't changed
        self.sales_user.refresh_from_db()
        self.assertEqual(self.sales_user.role, 'sales')

    def test_horizontal_access_control(self):
        """
        Security Test: Horizontal access control
        TDD: Ensure users cannot access other users' data
        """
        # Create contacts for different users
        self.client.force_authenticate(user=self.admin_user)

        contact1_response = self.client.post('/api/v1/contacts/', {
            'first_name': 'Contact1',
            'last_name': 'User',
            'email': 'contact1@company.com',
            'owner': self.sales_user.id
        })
        contact1_id = contact1_response.json()['id']

        contact2_response = self.client.post('/api/v1/contacts/', {
            'first_name': 'Contact2',
            'last_name': 'User',
            'email': 'contact2@company.com',
            'owner': self.manager_user.id
        })
        contact2_id = contact2_response.json()['id']

        # Test that sales user cannot access manager's contacts
        self.client.force_authenticate(user=self.sales_user)

        response = self.client.get(f'/api/v1/contacts/{contact2_id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Test that sales user can access their own contacts
        response = self.client.get(f'/api/v1/contacts/{contact1_id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_insecure_direct_object_reference_prevention(self):
        """
        Security Test: Insecure Direct Object Reference (IDOR) prevention
        TDD: Ensure object references are properly authorized
        """
        self.client.force_authenticate(user=self.admin_user)

        # Create user and contact
        new_user = User.objects.create_user(
            email='newuser@company.com',
            password='NewPass123!',
            first_name='New',
            last_name='User',
            role='sales'
        )

        contact_response = self.client.post('/api/v1/contacts/', {
            'first_name': 'Contact',
            'last_name': 'User',
            'email': 'contact@company.com',
            'owner': new_user.id
        })
        contact_id = contact_response.json()['id']

        # Test that sales user cannot access contact by ID
        self.client.force_authenticate(user=self.sales_user)

        # Try different ID values that might exist
        for test_id in [1, 2, 999, contact_id]:
            response = self.client.get(f'/api/v1/contacts/{test_id}/')
            # Should either be 404 (not found) or 403 (forbidden)
            self.assertIn(response.status_code, [
                status.HTTP_404_NOT_FOUND,
                status.HTTP_403_FORBIDDEN
            ])

    def test_authorization_bypass_attempts(self):
        """
        Security Test: Authorization bypass attempts
        TDD: Ensure robust authorization checks
        """
        self.client.force_authenticate(user=self.sales_user)

        # Test HTTP method tampering
        response = self.client.patch('/api/v1/auth/users/', {
            'role': 'admin'
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Test parameter pollution
        response = self.client.get('/api/v1/auth/users/?id=1&id=999')
        self.assertNotEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Test path traversal
        response = self.client.get('/api/v1/auth/users/../admin/')
        self.assertNotEqual(response.status_code, status.HTTP_200_OK)


class CryptographicSecurityTests(TestCase):
    """
    Cryptographic security testing
    """

    def test_password_hashing_strength(self):
        """
        Security Test: Password hashing strength
        TDD: Ensure strong password hashing algorithms
        """
        user = User.objects.create_user(
            email='crypto@company.com',
            password='TestPass123!',
            first_name='Crypto',
            last_name='Test',
            role='sales'
        )

        # Check that password is hashed
        self.assertNotEqual(user.password, 'TestPass123!')

        # Check hash format (should be PBKDF2, bcrypt, or argon2)
        valid_hash_prefixes = ['pbkdf2_sha256$', 'bcrypt$', 'argon2$']
        self.assertTrue(
            any(user.password.startswith(prefix) for prefix in valid_hash_prefixes),
            f"Password hash doesn't use secure algorithm: {user.password[:20]}"
        )

        # Check hash complexity
        hash_parts = user.password.split('$')
        self.assertGreaterEqual(len(hash_parts), 4, "Hash should have algorithm, iterations, salt, and hash")

    def test_jwt_token_security(self):
        """
        Security Test: JWT token security
        TDD: Ensure secure JWT implementation
        """
        user = User.objects.create_user(
            email='jwt@company.com',
            password='TestPass123!',
            first_name='JWT',
            last_name='Test',
            role='sales'
        )

        # Login to get token
        client = APIClient()
        response = client.post('/api/v1/auth/login/', {
            'email': 'jwt@company.com',
            'password': 'TestPass123!'
        })

        token = response.json()['access_token']

        # Test token structure (should be 3 parts separated by dots)
        token_parts = token.split('.')
        self.assertEqual(len(token_parts), 3, "JWT should have header, payload, and signature")

        # Test that token is properly signed
        # This would require JWT library access to verify
        self.assertTrue(len(token) > 100, "JWT should be reasonably long")

        # Test token expiration
        # This would require decoding the JWT to check expiration claim
        # For now, just test basic structure

    def test_session_management_security(self):
        """
        Security Test: Session management security
        TDD: Ensure secure session handling
        """
        # Test session fixation prevention
        # This would be tested in browser environment
        pass

    def test_sensitive_data_protection(self):
        """
        Security Test: Sensitive data protection
        TDD: Ensure sensitive data is properly protected
        """
        # Create user with sensitive information
        user = User.objects.create_user(
            email='sensitive@company.com',
            password='TestPass123!',
            first_name='Sensitive',
            last_name='Data',
            role='sales'
        )

        # Test that password is not exposed in API responses
        client = APIClient()
        client.force_authenticate(user=user)

        response = client.get(f'/api/v1/auth/users/{user.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('password', response.json())

        # Test that other sensitive fields are protected
        self.assertNotIn('secret_key', response.json())  # If exists


class InfrastructureSecurityTests(TestCase):
    """
    Infrastructure and deployment security testing
    """

    def test_security_headers(self):
        """
        Security Test: Security headers
        TDD: Implement comprehensive security headers
        """
        client = APIClient()

        response = client.get('/api/v1/status/')

        # Check for important security headers
        expected_headers = [
            'X-Content-Type-Options',
            'X-Frame-Options',
            'X-XSS-Protection',
        ]

        for header in expected_headers:
            self.assertIn(header, response, f"Missing security header: {header}")

        # Check header values
        self.assertEqual(response['X-Content-Type-Options'], 'nosniff')
        self.assertEqual(response['X-Frame-Options'], 'DENY')

    def test_https_enforcement(self):
        """
        Security Test: HTTPS enforcement
        TDD: Ensure HTTPS is properly enforced
        """
        # This test would be in production environment
        # For development, test that HSTS header is set
        pass

    def test_error_handling_security(self):
        """
        Security Test: Secure error handling
        TDD: Ensure errors don't leak sensitive information
        """
        client = APIClient()

        # Test 404 errors don't leak information
        response = client.get('/api/v1/nonexistent/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Test that error messages don't contain sensitive information
        error_response = response.json()
        self.assertNotIn('traceback', str(error_response))
        self.assertNotIn('password', str(error_response))

    def test_logging_and_monitoring(self):
        """
        Security Test: Security logging and monitoring
        TDD: Implement comprehensive security logging
        """
        # Test that security events are logged
        # This would require log inspection
        pass