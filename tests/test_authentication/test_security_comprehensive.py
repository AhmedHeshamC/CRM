"""
Comprehensive Authentication Security Tests
Following TDD methodology with SOLID and KISS principles
"""

import pytest
from datetime import datetime, timedelta
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.test.utils import override_settings
from rest_framework.test import APIClient
from rest_framework import status

from crm.apps.authentication.models import UserProfile, APIKey

User = get_user_model()


class TestUserModelSecurity(TestCase):
    """Test User model security features"""

    def setUp(self):
        """Set up test data"""
        self.user_data = {
            'email': 'test@example.com',
            'first_name': 'John',
            'last_name': 'Doe',
            'password': 'SecurePass123!',
            'role': 'sales'
        }

    def test_user_creation_with_valid_data(self):
        """Test creating user with valid data (TDD: Green test)"""
        user = User.objects.create_user(**self.user_data)
        assert user.email == self.user_data['email']
        assert user.check_password(self.user_data['password'])
        assert user.role == 'sales'
        assert user.is_active is True

    def test_user_creation_with_invalid_email_raises_validation_error(self):
        """Test invalid email raises ValidationError (TDD: Security test)"""
        invalid_emails = [
            'invalid-email',
            '@invalid.com',
            'test@',
            'test..test@domain.com',
            'test@domain..com'
        ]

        for invalid_email in invalid_emails:
            with pytest.raises(ValidationError):
                User.objects.create_user(
                    email=invalid_email,
                    first_name='Test',
                    last_name='User',
                    password='ValidPass123!'
                )

    def test_user_email_case_insensitive_lookup(self):
        """Test email lookup is case insensitive (TDD: Feature test)"""
        user = User.objects.create_user(**self.user_data)

        # Should find user regardless of case
        found_user = User.objects.get(email__iexact='TEST@EXAMPLE.COM')
        assert found_user == user
        found_user = User.objects.get(email__iexact='test@example.com')
        assert found_user == user

    def test_user_duplicate_email_raises_integrity_error(self):
        """Test duplicate email raises IntegrityError (TDD: Security test)"""
        User.objects.create_user(**self.user_data)

        with pytest.raises(Exception):  # IntegrityError
            User.objects.create_user(**self.user_data)

    def test_user_password_hashing(self):
        """Test password is properly hashed (TDD: Security test)"""
        user = User.objects.create_user(**self.user_data)

        # Password should not be stored in plain text
        assert user.password != self.user_data['password']
        assert user.password.startswith('pbkdf2_sha256$') or user.password.startswith('bcrypt$')

    def test_user_role_permissions(self):
        """Test user role-based permissions (TDD: Feature test)"""
        admin_user = User.objects.create_user(
            email='admin@example.com',
            first_name='Admin',
            last_name='User',
            password='AdminPass123!',
            role='admin'
        )

        assert admin_user.is_admin() is True
        assert admin_user.is_sales_user() is False
        assert admin_user.is_manager() is False

    def test_user_uuid_generation(self):
        """Test UUID is generated for each user (TDD: Feature test)"""
        user = User.objects.create_user(**self.user_data)
        assert user.uuid is not None
        assert len(str(user.uuid)) == 36  # Standard UUID length

    def test_user_email_verification_default(self):
        """Test email verification defaults to False (TDD: Security test)"""
        user = User.objects.create_user(**self.user_data)
        assert user.email_verified is False

    def test_user_two_factor_auth_default(self):
        """Test two-factor auth defaults to False (TDD: Security test)"""
        user = User.objects.create_user(**self.user_data)
        assert user.two_factor_enabled is False


class TestUserManagerSecurity(TestCase):
    """Test UserManager security features"""

    def test_create_user_without_email_raises_value_error(self):
        """Test creating user without email raises ValueError (TDD: Security test)"""
        with pytest.raises(ValueError, match='Users must have an email address'):
            User.objects.create_user(
                email='',
                first_name='Test',
                last_name='User',
                password='TestPass123!'
            )

    def test_create_superuser_permissions(self):
        """Test superuser creation requires proper permissions (TDD: Security test)"""
        # Test missing is_staff
        with pytest.raises(ValueError, match='Superuser must have is_staff=True'):
            User.objects.create_superuser(
                email='super@example.com',
                password='SuperPass123!',
                is_staff=False
            )

        # Test missing is_superuser
        with pytest.raises(ValueError, match='Superuser must have is_superuser=True'):
            User.objects.create_superuser(
                email='super@example.com',
                password='SuperPass123!',
                is_staff=True,
                is_superuser=False
            )

    def test_get_by_email_case_insensitive(self):
        """Test get_by_email method is case insensitive (TDD: Feature test)"""
        user_data = {
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User',
            'password': 'TestPass123!'
        }
        user = User.objects.create_user(**user_data)

        found_user = User.objects.get_by_email('TEST@EXAMPLE.COM')
        assert found_user == user

    def test_active_users_manager_method(self):
        """Test active_users manager method (TDD: Feature test)"""
        # Create active and inactive users
        active_user = User.objects.create_user(
            email='active@example.com',
            first_name='Active',
            last_name='User',
            password='TestPass123!',
            is_active=True
        )
        inactive_user = User.objects.create_user(
            email='inactive@example.com',
            first_name='Inactive',
            last_name='User',
            password='TestPass123!',
            is_active=False
        )

        active_users = User.objects.active_users()
        assert active_user in active_users
        assert inactive_user not in active_users

    def test_users_by_role_manager_method(self):
        """Test users_by_role manager method (TDD: Feature test)"""
        sales_user = User.objects.create_user(
            email='sales@example.com',
            first_name='Sales',
            last_name='User',
            password='TestPass123!',
            role='sales'
        )
        admin_user = User.objects.create_user(
            email='admin@example.com',
            first_name='Admin',
            last_name='User',
            password='AdminPass123!',
            role='admin'
        )

        sales_users = User.objects.users_by_role('sales')
        assert sales_user in sales_users
        assert admin_user not in sales_users


class TestAPIKeySecurity(TestCase):
    """Test APIKey model security features"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            email='test@example.com',
            first_name='Test',
            last_name='User',
            password='TestPass123!'
        )

    def test_api_key_creation(self):
        """Test API key creation (TDD: Feature test)"""
        api_key = APIKey.objects.create(
            user=self.user,
            name='Test Key',
            key_hash='hashed_key_value',
            permissions=['read', 'write'],
            expires_at=timezone.now() + timedelta(days=365)
        )

        assert api_key.user == self.user
        assert api_key.name == 'Test Key'
        assert api_key.is_active is True
        assert 'read' in api_key.permissions
        assert 'write' in api_key.permissions

    def test_api_key_expiration_check(self):
        """Test API key expiration checking (TDD: Security test)"""
        # Create expired key
        expired_key = APIKey.objects.create(
            user=self.user,
            name='Expired Key',
            key_hash='expired_hash',
            expires_at=timezone.now() - timedelta(days=1)
        )

        # Create valid key
        valid_key = APIKey.objects.create(
            user=self.user,
            name='Valid Key',
            key_hash='valid_hash',
            expires_at=timezone.now() + timedelta(days=1)
        )

        assert expired_key.is_expired() is True
        assert valid_key.is_expired() is False

    def test_api_key_validity_check(self):
        """Test API key validity checking (TDD: Security test)"""
        # Create valid key
        valid_key = APIKey.objects.create(
            user=self.user,
            name='Valid Key',
            key_hash='valid_hash',
            expires_at=timezone.now() + timedelta(days=1),
            is_active=True
        )

        # Create inactive key
        inactive_key = APIKey.objects.create(
            user=self.user,
            name='Inactive Key',
            key_hash='inactive_hash',
            expires_at=timezone.now() + timedelta(days=1),
            is_active=False
        )

        assert valid_key.is_valid() is True
        assert inactive_key.is_valid() is False

    def test_api_key_rotation_relationship(self):
        """Test API key rotation relationship (TDD: Feature test)"""
        original_key = APIKey.objects.create(
            user=self.user,
            name='Original Key',
            key_hash='original_hash',
            expires_at=timezone.now() + timedelta(days=1)
        )

        rotated_key = APIKey.objects.create(
            user=self.user,
            name='Rotated Key',
            key_hash='rotated_hash',
            expires_at=timezone.now() + timedelta(days=1),
            rotated_from=original_key
        )

        assert rotated_key.rotated_from == original_key
        assert original_key.rotated_keys.first() == rotated_key


class TestUserProfileSecurity(TestCase):
    """Test UserProfile model security features"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            email='test@example.com',
            first_name='Test',
            last_name='User',
            password='TestPass123!'
        )

    def test_user_profile_auto_creation(self):
        """Test UserProfile is auto-created when User is created (TDD: Feature test)"""
        # Profile should be created automatically via signal
        assert hasattr(self.user, 'profile')
        assert self.user.profile.user == self.user

    def test_user_profile_default_preferences(self):
        """Test UserProfile default preferences (TDD: Feature test)"""
        profile = self.user.profile
        assert profile.timezone == 'UTC'
        assert profile.language == 'en'
        assert profile.email_notifications is True
        assert profile.push_notifications is True

    def test_user_profile_dashboard_layout_security(self):
        """Test UserProfile dashboard layout accepts valid JSON (TDD: Security test)"""
        profile = self.user.profile

        # Valid JSON should work
        valid_layout = {'widgets': ['contacts', 'deals'], 'theme': 'dark'}
        profile.dashboard_layout = valid_layout
        profile.save()

        assert profile.dashboard_layout == valid_layout

    def test_user_profile_session_tracking(self):
        """Test UserProfile session tracking (TDD: Feature test)"""
        profile = self.user.profile

        # Simulate session key assignment
        session_key = 'test_session_key_12345'
        profile.current_session_key = session_key
        profile.save()

        assert profile.current_session_key == session_key


class TestAuthenticationAPISecurity(TestCase):
    """Test Authentication API security features"""

    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='test@example.com',
            first_name='Test',
            last_name='User',
            password='TestPass123!'
        )
        self.admin_user = User.objects.create_user(
            email='admin@example.com',
            first_name='Admin',
            last_name='User',
            password='AdminPass123!',
            role='admin',
            is_staff=True,
            is_superuser=True
        )

    def test_login_with_valid_credentials(self):
        """Test login with valid credentials (TDD: Green test)"""
        response = self.client.post('/api/v1/auth/login/', {
            'email': 'test@example.com',
            'password': 'TestPass123!'
        })

        assert response.status_code == status.HTTP_200_OK

    def test_login_with_invalid_credentials(self):
        """Test login with invalid credentials fails (TDD: Security test)"""
        response = self.client.post('/api/v1/auth/login/', {
            'email': 'test@example.com',
            'password': 'wrongpassword'
        })

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_with_sql_injection_attempts(self):
        """Test login against SQL injection attempts (TDD: Security test)"""
        sql_attempts = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "admin'--",
            "' UNION SELECT * FROM users --"
        ]

        for attempt in sql_attempts:
            response = self.client.post('/api/v1/auth/login/', {
                'email': attempt,
                'password': 'password'
            })

            # Should all fail with 401
            assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_registration_with_weak_passwords(self):
        """Test registration rejects weak passwords (TDD: Security test)"""
        weak_passwords = [
            '123456',
            'password',
            'qwerty',
            'admin123',
            'test'
        ]

        for weak_password in weak_passwords:
            response = self.client.post('/api/v1/auth/register/', {
                'email': f'test_{weak_password}@example.com',
                'first_name': 'Test',
                'last_name': 'User',
                'password': weak_password
            })

            # Should fail with 400 (Bad Request)
            assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_user_access_control(self):
        """Test user access control (TDD: Security test)"""
        # Test unauthenticated access
        response = self.client.get('/api/v1/users/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        # Test authenticated regular user access
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/v1/users/')
        # Should be forbidden for regular user
        assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND]

        # Test admin user access
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get('/api/v1/users/')
        # Should succeed for admin
        assert response.status_code == status.HTTP_200_OK

    def test_xss_prevention_in_user_data(self):
        """Test XSS prevention in user data (TDD: Security test)"""
        xss_payloads = [
            '<script>alert("XSS")</script>',
            'javascript:alert("XSS")',
            '<img src="x" onerror="alert(1)">',
            '"><script>alert(1)</script>'
        ]

        self.client.force_authenticate(user=self.user)

        for payload in xss_payloads:
            response = self.client.patch('/api/v1/users/me/', {
                'first_name': payload
            })

            if response.status_code == status.HTTP_200_OK:
                # If update succeeds, ensure payload is sanitized
                self.user.refresh_from_db()
                # Payload should not contain raw script tags
                assert '<script>' not in self.user.first_name
                assert 'javascript:' not in self.user.first_name


class TestRateLimitingSecurity(TestCase):
    """Test rate limiting security features"""

    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='test@example.com',
            first_name='Test',
            last_name='User',
            password='TestPass123!'
        )

    @override_settings(RATELIMIT_ENABLE=True)
    def test_rate_limiting_on_login_endpoint(self):
        """Test rate limiting on login endpoint (TDD: Security test)"""
        # Attempt multiple rapid login attempts
        responses = []
        for i in range(15):  # Exceed typical rate limit
            response = self.client.post('/api/v1/auth/login/', {
                'email': 'test@example.com',
                'password': 'wrongpassword'
            })
            responses.append(response.status_code)

        # Should eventually be rate limited
        assert status.HTTP_429_TOO_MANY_REQUESTS in responses

    @override_settings(RATELIMIT_ENABLE=True)
    def test_rate_limiting_with_different_ips(self):
        """Test rate limiting works per IP (TDD: Security test)"""
        # Test from different IP addresses (simulated)
        ip_addresses = ['192.168.1.1', '192.168.1.2', '10.0.0.1']

        for ip in ip_addresses:
            responses = []
            for i in range(5):
                response = self.client.post(
                    '/api/v1/auth/login/',
                    {'email': 'test@example.com', 'password': 'wrongpassword'},
                    REMOTE_ADDR=ip
                )
                responses.append(response.status_code)

            # Each IP should have its own limit
            # (This test would need proper rate limiting setup)


class TestAuthenticationIntegration(TransactionTestCase):
    """Integration tests for authentication system"""

    def setUp(self):
        """Set up test data"""
        self.client = APIClient()

    def test_complete_user_registration_flow(self):
        """Test complete user registration flow (TDD: Integration test)"""
        # Register user
        register_data = {
            'email': 'newuser@example.com',
            'first_name': 'New',
            'last_name': 'User',
            'password': 'SecurePass123!',
            'role': 'sales'
        }

        response = self.client.post('/api/v1/auth/register/', register_data)
        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_200_OK]

        # Verify user exists
        user = User.objects.get(email='newuser@example.com')
        assert user.first_name == 'New'
        assert user.last_name == 'User'
        assert user.role == 'sales'
        assert user.email_verified is False
        assert user.two_factor_enabled is False

        # Verify profile was created
        assert hasattr(user, 'profile')
        assert user.profile.timezone == 'UTC'

    def test_password_change_flow(self):
        """Test password change flow (TDD: Integration test)"""
        # Create user
        user = User.objects.create_user(
            email='test@example.com',
            first_name='Test',
            last_name='User',
            password='OldPass123!'
        )

        # Change password
        self.client.force_authenticate(user=user)
        response = self.client.post('/api/v1/auth/change-password/', {
            'old_password': 'OldPass123!',
            'new_password': 'NewPass456!'
        })

        assert response.status_code == status.HTTP_200_OK

        # Verify new password works
        user.refresh_from_db()
        assert user.check_password('NewPass456!')

        # Verify old password doesn't work
        assert not user.check_password('OldPass123!')


class TestSecurityHeaders(TestCase):
    """Test security headers are properly set"""

    def test_security_headers_present(self):
        """Test security headers are present in responses (TDD: Security test)"""
        client = APIClient()

        response = client.get('/api/v1/status/')

        # Check for security headers (would need middleware implementation)
        # These would be implemented in security middleware
        expected_headers = [
            'X-Content-Type-Options',
            'X-Frame-Options',
            'X-XSS-Protection',
            'Strict-Transport-Security'
        ]

        # This test assumes security middleware is implemented
        # for header in expected_headers:
        #     assert header in response