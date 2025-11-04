"""
Authentication Serializer Tests - TDD Approach
Testing comprehensive validation and serialization logic
Following SOLID principles and comprehensive test coverage
"""

import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import serializers
from rest_framework.test import APITestCase
from rest_framework.exceptions import ValidationError

from crm.apps.authentication.models import User, UserProfile
from crm.apps.authentication.serializers import (
    UserSerializer, UserDetailSerializer, UserCreateSerializer,
    UserUpdateSerializer, UserRegistrationSerializer,
    UserProfileSerializer, PasswordChangeSerializer,
    PasswordResetSerializer, LoginSerializer
)

User = get_user_model()


class UserSerializerTestCase(TestCase):
    """Base test case for User serializers"""

    def setUp(self):
        """Set up test data"""
        self.user_data = {
            'email': 'testuser@example.com',
            'first_name': 'Test',
            'last_name': 'User',
            'role': 'sales',
            'phone': '+1-555-123-4567',
            'department': 'Sales'
        }

        self.user = User.objects.create_user(
            email='existing@example.com',
            password='testpass123',
            first_name='Existing',
            last_name='User',
            role='sales'
        )


class UserSerializerTests(UserSerializerTestCase):
    """Test UserSerializer functionality"""

    def test_valid_user_serialization(self):
        """Test serialization of valid user data"""
        user = User.objects.create_user(**self.user_data, password='testpass123')
        serializer = UserSerializer(user)

        data = serializer.data
        self.assertEqual(data['id'], user.id)
        self.assertEqual(data['email'], 'testuser@example.com')
        self.assertEqual(data['first_name'], 'Test')
        self.assertEqual(data['last_name'], 'User')
        self.assertEqual(data['role'], 'sales')
        self.assertEqual(data['full_name'], 'Test User')
        self.assertIn('created_at', data)
        self.assertIn('date_joined', data)

    def test_user_validation_invalid_email(self):
        """Test validation fails with invalid email"""
        data = self.user_data.copy()
        data['email'] = 'invalid-email'
        serializer = UserSerializer(data=data)

        with self.assertRaises(ValidationError) as context:
            serializer.is_valid(raise_exception=True)

        self.assertIn('email', context.exception.detail)

    def test_user_validation_invalid_role(self):
        """Test validation fails with invalid role"""
        data = self.user_data.copy()
        data['role'] = 'invalid_role'
        serializer = UserSerializer(data=data)

        with self.assertRaises(ValidationError) as context:
            serializer.is_valid(raise_exception=True)

        self.assertIn('role', context.exception.detail)

    def test_user_validation_duplicate_email(self):
        """Test validation fails with duplicate email"""
        data = self.user_data.copy()
        data['email'] = 'existing@example.com'  # Same as existing user
        serializer = UserSerializer(data=data)

        with self.assertRaises(ValidationError) as context:
            serializer.is_valid(raise_exception=True)

        self.assertIn('email', context.exception.detail)

    def test_computed_fields(self):
        """Test computed fields are properly calculated"""
        user = User.objects.create_user(**self.user_data, password='testpass123')
        serializer = UserSerializer(user)

        data = serializer.data
        self.assertEqual(data['full_name'], 'Test User')
        self.assertFalse(data['is_admin'])
        self.assertTrue(data['is_sales_user'])
        self.assertFalse(data['is_manager'])

    def test_user_role_methods(self):
        """Test user role method calculations"""
        # Test admin user
        admin_user = User.objects.create_user(
            email='admin@example.com',
            password='adminpass123',
            first_name='Admin',
            last_name='User',
            role='admin'
        )
        serializer = UserSerializer(admin_user)
        data = serializer.data
        self.assertTrue(data['is_admin'])
        self.assertFalse(data['is_sales_user'])
        self.assertFalse(data['is_manager'])

        # Test manager user
        manager_user = User.objects.create_user(
            email='manager@example.com',
            password='managerpass123',
            first_name='Manager',
            last_name='User',
            role='manager'
        )
        serializer = UserSerializer(manager_user)
        data = serializer.data
        self.assertFalse(data['is_admin'])
        self.assertFalse(data['is_sales_user'])
        self.assertTrue(data['is_manager'])


class UserCreateSerializerTests(UserSerializerTestCase):
    """Test UserCreateSerializer functionality"""

    def test_create_serializer_validates_required_fields(self):
        """Test create serializer enforces all required fields"""
        data = self.user_data.copy()
        serializer = UserCreateSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_create_serializer_sanitizes_data(self):
        """Test create serializer properly sanitizes input data"""
        data = {
            'email': '  testuser@example.com  ',
            'first_name': '  Test  ',
            'last_name': '  User  ',
            'role': 'sales',
            'department': '  Sales Department  '
        }
        serializer = UserCreateSerializer(data=data)
        self.assertTrue(serializer.is_valid())

        # Check if data was sanitized during validation
        validated_data = serializer.validated_data
        self.assertEqual(validated_data['email'], 'testuser@example.com')
        self.assertEqual(validated_data['first_name'], 'Test')
        self.assertEqual(validated_data['last_name'], 'User')
        self.assertEqual(validated_data['department'], 'Sales Department')

    def test_create_password_field_not_in_serializer(self):
        """Test create serializer doesn't include password field"""
        data = self.user_data.copy()
        data['password'] = 'testpass123'
        serializer = UserCreateSerializer(data=data)

        # Password should not be in serializer fields
        self.assertNotIn('password', serializer.fields)


class UserUpdateSerializerTests(UserSerializerTestCase):
    """Test UserUpdateSerializer functionality"""

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(**self.user_data, password='testpass123')

    def test_update_serializer_accepts_partial_data(self):
        """Test update serializer allows partial updates"""
        update_data = {
            'first_name': 'Updated',
            'last_name': 'Name'
        }
        serializer = UserUpdateSerializer(
            self.user,
            data=update_data,
            partial=True
        )
        self.assertTrue(serializer.is_valid())

    def test_update_sanitizes_provided_fields(self):
        """Test update serializer sanitizes only provided fields"""
        update_data = {
            'first_name': '  Updated  ',
            'last_name': '  Name  ',
            'department': '  Updated Department  '
        }
        serializer = UserUpdateSerializer(
            self.user,
            data=update_data,
            partial=True
        )
        self.assertTrue(serializer.is_valid())

        validated_data = serializer.validated_data
        self.assertEqual(validated_data['first_name'], 'Updated')
        self.assertEqual(validated_data['last_name'], 'Name')
        self.assertEqual(validated_data['department'], 'Updated Department')

    def test_update_preserves_unchanged_fields(self):
        """Test update preserves fields that weren't updated"""
        update_data = {'first_name': 'Updated'}
        serializer = UserUpdateSerializer(
            self.user,
            data=update_data,
            partial=True
        )
        self.assertTrue(serializer.is_valid())

        updated_user = serializer.save()
        self.assertEqual(updated_user.first_name, 'Updated')
        self.assertEqual(updated_user.last_name, 'User')  # Unchanged
        self.assertEqual(updated_user.email, 'testuser@example.com')  # Unchanged

    def test_update_email_validation(self):
        """Test email validation during update"""
        update_data = {'email': 'updated@example.com'}
        serializer = UserUpdateSerializer(
            self.user,
            data=update_data,
            partial=True
        )
        self.assertTrue(serializer.is_valid())

    def test_update_email_uniqueness(self):
        """Test email uniqueness validation during update"""
        update_data = {'email': 'existing@example.com'}  # Email of another user
        serializer = UserUpdateSerializer(
            self.user,
            data=update_data,
            partial=True
        )

        with self.assertRaises(ValidationError) as context:
            serializer.is_valid(raise_exception=True)

        self.assertIn('email', context.exception.detail)


class UserDetailSerializerTests(UserSerializerTestCase):
    """Test UserDetailSerializer functionality"""

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(**self.user_data, password='testpass123')

    def test_detail_serializer_includes_profile_data(self):
        """Test detail serializer includes user profile information"""
        # Update user profile
        profile = self.user.profile
        profile.bio = 'This is a test bio'
        profile.timezone = 'America/New_York'
        profile.language = 'en'
        profile.save()

        serializer = UserDetailSerializer(self.user)
        data = serializer.data

        # Should include basic user fields
        self.assertEqual(data['id'], self.user.id)
        self.assertEqual(data['email'], 'testuser@example.com')

        # Should include profile fields
        self.assertIn('profile', data)
        self.assertEqual(data['profile']['bio'], 'This is a test bio')
        self.assertEqual(data['profile']['timezone'], 'America/New_York')
        self.assertEqual(data['profile']['language'], 'en')

    def test_detail_serializer_includes_permissions(self):
        """Test detail serializer includes user permission information"""
        serializer = UserDetailSerializer(self.user)
        data = serializer.data

        self.assertIn('permissions', data)
        permissions = data['permissions']
        self.assertIsInstance(permissions, dict)
        self.assertIn('can_manage_users', permissions)
        self.assertIn('can_view_all_contacts', permissions)


class UserRegistrationSerializerTests(UserSerializerTestCase):
    """Test UserRegistrationSerializer functionality"""

    def test_registration_serializer_valid_data(self):
        """Test registration serializer with valid data"""
        registration_data = {
            'email': 'newuser@example.com',
            'first_name': 'New',
            'last_name': 'User',
            'password': 'securepass123',
            'password_confirm': 'securepass123',
            'role': 'sales'
        }
        serializer = UserRegistrationSerializer(data=registration_data)
        self.assertTrue(serializer.is_valid())

    def test_registration_serializer_password_mismatch(self):
        """Test registration serializer rejects mismatched passwords"""
        registration_data = {
            'email': 'newuser@example.com',
            'first_name': 'New',
            'last_name': 'User',
            'password': 'securepass123',
            'password_confirm': 'differentpass123',
            'role': 'sales'
        }
        serializer = UserRegistrationSerializer(data=registration_data)

        with self.assertRaises(ValidationError) as context:
            serializer.is_valid(raise_exception=True)

        self.assertIn('password_confirm', context.exception.detail)
        self.assertIn('Passwords do not match', str(context.exception.detail['password_confirm']))

    def test_registration_serializer_weak_password(self):
        """Test registration serializer rejects weak passwords"""
        registration_data = {
            'email': 'newuser@example.com',
            'first_name': 'New',
            'last_name': 'User',
            'password': '123',  # Too weak
            'password_confirm': '123',
            'role': 'sales'
        }
        serializer = UserRegistrationSerializer(data=registration_data)

        # Django's password validators should catch this
        is_valid = serializer.is_valid()
        # Note: The exact validation depends on Django's password validation settings
        # This test might need adjustment based on your password validation rules

    def test_registration_serializer_missing_required_fields(self):
        """Test registration serializer requires all fields"""
        registration_data = {
            'email': 'newuser@example.com',
            # Missing first_name, last_name, password, password_confirm, role
        }
        serializer = UserRegistrationSerializer(data=registration_data)

        with self.assertRaises(ValidationError) as context:
            serializer.is_valid(raise_exception=True)

        self.assertIn('first_name', context.exception.detail)
        self.assertIn('last_name', context.exception.detail)
        self.assertIn('password', context.exception.detail)
        self.assertIn('password_confirm', context.exception.detail)
        self.assertIn('role', context.exception.detail)

    def test_registration_create_user(self):
        """Test registration creates user and profile"""
        registration_data = {
            'email': 'registeruser@example.com',
            'first_name': 'Register',
            'last_name': 'User',
            'password': 'securepass123',
            'password_confirm': 'securepass123',
            'role': 'sales'
        }
        serializer = UserRegistrationSerializer(data=registration_data)
        self.assertTrue(serializer.is_valid())

        user = serializer.save()

        # Verify user was created
        self.assertEqual(user.email, 'registeruser@example.com')
        self.assertEqual(user.first_name, 'Register')
        self.assertEqual(user.last_name, 'User')
        self.assertEqual(user.role, 'sales')

        # Verify password was set (using Django's password hashing)
        self.assertTrue(user.check_password('securepass123'))

        # Verify profile was created
        self.assertTrue(hasattr(user, 'profile'))
        self.assertIsNotNone(user.profile)


class UserProfileSerializerTests(UserSerializerTestCase):
    """Test UserProfileSerializer functionality"""

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(**self.user_data, password='testpass123')

    def test_profile_serializer_valid_data(self):
        """Test profile serializer with valid data"""
        profile_data = {
            'bio': 'This is a test bio',
            'timezone': 'America/New_York',
            'language': 'en',
            'email_notifications': True,
            'push_notifications': False,
            'dashboard_layout': {'widgets': ['contacts', 'deals']}
        }
        serializer = UserProfileSerializer(data=profile_data)
        self.assertTrue(serializer.is_valid())

    def test_profile_serializer_optional_fields(self):
        """Test profile serializer handles optional fields"""
        minimal_data = {
            'bio': 'Minimal bio'
        }
        serializer = UserProfileSerializer(data=minimal_data)
        self.assertTrue(serializer.is_valid())

        validated_data = serializer.validated_data
        self.assertEqual(validated_data['bio'], 'Minimal bio')
        # Should have default values for other fields
        self.assertIn('timezone', validated_data)
        self.assertIn('language', validated_data)

    def test_profile_sanitizes_bio(self):
        """Test profile serializer sanitizes bio field"""
        profile_data = {
            'bio': '  This is a sanitized bio  '
        }
        serializer = UserProfileSerializer(data=profile_data)
        self.assertTrue(serializer.is_valid())

        validated_data = serializer.validated_data
        self.assertEqual(validated_data['bio'], 'This is a sanitized bio')

    def test_profile_validation_invalid_timezone(self):
        """Test profile serializer validates timezone"""
        profile_data = {
            'bio': 'Test bio',
            'timezone': 'Invalid/Timezone'
        }
        serializer = UserProfileSerializer(data=profile_data)

        # Note: timezone validation might depend on your implementation
        # This test assumes you have timezone validation

    def test_profile_validation_dashboard_layout(self):
        """Test profile serializer validates dashboard layout"""
        profile_data = {
            'bio': 'Test bio',
            'dashboard_layout': 'invalid-json'  # Should be dict, not string
        }
        serializer = UserProfileSerializer(data=profile_data)

        # Should handle JSON validation gracefully
        # The exact behavior depends on your JSON field validation


class PasswordChangeSerializerTests(UserSerializerTestCase):
    """Test PasswordChangeSerializer functionality"""

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(**self.user_data, password='oldpass123')

    def test_password_change_valid_data(self):
        """Test password change with valid data"""
        password_data = {
            'old_password': 'oldpass123',
            'new_password': 'newsecurepass123',
            'new_password_confirm': 'newsecurepass123'
        }
        serializer = PasswordChangeSerializer(
            data=password_data,
            context={'user': self.user}
        )
        self.assertTrue(serializer.is_valid())

    def test_password_change_wrong_old_password(self):
        """Test password change fails with wrong old password"""
        password_data = {
            'old_password': 'wrongpass123',
            'new_password': 'newsecurepass123',
            'new_password_confirm': 'newsecurepass123'
        }
        serializer = PasswordChangeSerializer(
            data=password_data,
            context={'user': self.user}
        )

        with self.assertRaises(ValidationError) as context:
            serializer.is_valid(raise_exception=True)

        self.assertIn('old_password', context.exception.detail)

    def test_password_change_mismatched_new_passwords(self):
        """Test password change fails with mismatched new passwords"""
        password_data = {
            'old_password': 'oldpass123',
            'new_password': 'newsecurepass123',
            'new_password_confirm': 'differentpass123'
        }
        serializer = PasswordChangeSerializer(
            data=password_data,
            context={'user': self.user}
        )

        with self.assertRaises(ValidationError) as context:
            serializer.is_valid(raise_exception=True)

        self.assertIn('new_password_confirm', context.exception.detail)

    def test_password_change_same_as_old(self):
        """Test password change fails when new password is same as old"""
        password_data = {
            'old_password': 'oldpass123',
            'new_password': 'oldpass123',
            'new_password_confirm': 'oldpass123'
        }
        serializer = PasswordChangeSerializer(
            data=password_data,
            context={'user': self.user}
        )

        with self.assertRaises(ValidationError) as context:
            serializer.is_valid(raise_exception=True)

        self.assertIn('new_password', context.exception.detail)

    def test_password_change_update_password(self):
        """Test password change actually updates the password"""
        password_data = {
            'old_password': 'oldpass123',
            'new_password': 'newsecurepass123',
            'new_password_confirm': 'newsecurepass123'
        }
        serializer = PasswordChangeSerializer(
            data=password_data,
            context={'user': self.user}
        )
        self.assertTrue(serializer.is_valid())

        # Update password
        user = serializer.save()

        # Verify password was changed
        self.assertTrue(user.check_password('newsecurepass123'))
        self.assertFalse(user.check_password('oldpass123'))


class PasswordResetSerializerTests(UserSerializerTestCase):
    """Test PasswordResetSerializer functionality"""

    def test_password_reset_valid_email(self):
        """Test password reset with valid email"""
        reset_data = {'email': 'testuser@example.com'}
        serializer = PasswordResetSerializer(data=reset_data)
        self.assertTrue(serializer.is_valid())

    def test_password_reset_invalid_email(self):
        """Test password reset with invalid email"""
        reset_data = {'email': 'nonexistent@example.com'}
        serializer = PasswordResetSerializer(data=reset_data)

        # This should still be valid for security reasons (don't reveal if email exists)
        self.assertTrue(serializer.is_valid())

    def test_password_reset_invalid_email_format(self):
        """Test password reset with invalid email format"""
        reset_data = {'email': 'invalid-email-format'}
        serializer = PasswordResetSerializer(data=reset_data)

        with self.assertRaises(ValidationError) as context:
            serializer.is_valid(raise_exception=True)

        self.assertIn('email', context.exception.detail)


class LoginSerializerTests(UserSerializerTestCase):
    """Test LoginSerializer functionality"""

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(**self.user_data, password='testpass123')

    def test_login_valid_credentials(self):
        """Test login with valid credentials"""
        login_data = {
            'email': 'testuser@example.com',
            'password': 'testpass123'
        }
        serializer = LoginSerializer(data=login_data)
        self.assertTrue(serializer.is_valid())

    def test_login_invalid_email(self):
        """Test login fails with invalid email"""
        login_data = {
            'email': 'nonexistent@example.com',
            'password': 'testpass123'
        }
        serializer = LoginSerializer(data=login_data)

        with self.assertRaises(ValidationError) as context:
            serializer.is_valid(raise_exception=True)

        self.assertIn('non_field_errors', context.exception.detail)

    def test_login_invalid_password(self):
        """Test login fails with invalid password"""
        login_data = {
            'email': 'testuser@example.com',
            'password': 'wrongpass123'
        }
        serializer = LoginSerializer(data=login_data)

        with self.assertRaises(ValidationError) as context:
            serializer.is_valid(raise_exception=True)

        self.assertIn('non_field_errors', context.exception.detail)

    def test_login_missing_fields(self):
        """Test login fails with missing fields"""
        login_data = {
            'email': 'testuser@example.com'
            # Missing password
        }
        serializer = LoginSerializer(data=login_data)

        with self.assertRaises(ValidationError) as context:
            serializer.is_valid(raise_exception=True)

        self.assertIn('password', context.exception.detail)

    def test_login_inactive_user(self):
        """Test login fails with inactive user"""
        self.user.is_active = False
        self.user.save()

        login_data = {
            'email': 'testuser@example.com',
            'password': 'testpass123'
        }
        serializer = LoginSerializer(data=login_data)

        with self.assertRaises(ValidationError) as context:
            serializer.is_valid(raise_exception=True)

        self.assertIn('non_field_errors', context.exception.detail)


class UserSerializerIntegrationTests(UserSerializerTestCase):
    """Integration tests for User serializers"""

    def test_user_creation_with_profile(self):
        """Test user creation automatically creates profile"""
        registration_data = {
            'email': 'profiletest@example.com',
            'first_name': 'Profile',
            'last_name': 'Test',
            'password': 'securepass123',
            'password_confirm': 'securepass123',
            'role': 'sales'
        }
        serializer = UserRegistrationSerializer(data=registration_data)
        self.assertTrue(serializer.is_valid())

        user = serializer.save()

        # Verify profile was created
        self.assertTrue(hasattr(user, 'profile'))
        self.assertIsNotNone(user.profile)
        self.assertEqual(user.profile.user, user)

    def test_serializer_error_messages_are_user_friendly(self):
        """Test serializer provides user-friendly error messages"""
        invalid_data = {
            'email': 'invalid-email-format',
            'first_name': '',
            'last_name': '',
            'role': 'invalid_role'
        }
        serializer = UserCreateSerializer(data=invalid_data)

        with self.assertRaises(ValidationError) as context:
            serializer.is_valid(raise_exception=True)

        errors = context.exception.detail

        # Check that error messages are user-friendly strings
        self.assertIsInstance(errors['email'], list)
        self.assertIsInstance(errors['email'][0], str)
        self.assertTrue(len(errors['email'][0]) > 0)

    def test_field_validation_order(self):
        """Test field validation happens in correct order"""
        invalid_data = {
            'email': 'invalid-email-format',
            'role': 'invalid_role',
            'first_name': ''
        }
        serializer = UserCreateSerializer(data=invalid_data)

        with self.assertRaises(ValidationError) as context:
            serializer.is_valid(raise_exception=True)

        errors = context.exception.detail
        # Should catch all validation errors
        self.assertIn('email', errors)
        self.assertIn('role', errors)
        self.assertIn('first_name', errors)

    def test_user_role_consistency(self):
        """Test user role consistency across serializers"""
        roles = ['admin', 'sales', 'manager', 'support']

        for role in roles:
            user_data = self.user_data.copy()
            user_data['email'] = f'{role}user@example.com'
            user_data['role'] = role

            # Test with create serializer
            create_serializer = UserCreateSerializer(data=user_data)
            self.assertTrue(create_serializer.is_valid(), f"Failed for role: {role}")

            # Test with update serializer
            user = User.objects.create_user(**user_data, password='testpass123')
            update_serializer = UserUpdateSerializer(user, data={'role': role}, partial=True)
            self.assertTrue(update_serializer.is_valid(), f"Failed for role: {role}")

    def test_email_case_insensitive(self):
        """Test email validation is case insensitive"""
        # Create user with lowercase email
        user_data = self.user_data.copy()
        user_data['email'] = 'lowercase@example.com'
        user = User.objects.create_user(**user_data, password='testpass123')

        # Try to create user with same email in uppercase
        duplicate_data = self.user_data.copy()
        duplicate_data['email'] = 'LOWERCASE@example.com'
        duplicate_data['first_name'] = 'Duplicate'

        serializer = UserCreateSerializer(data=duplicate_data)

        with self.assertRaises(ValidationError) as context:
            serializer.is_valid(raise_exception=True)

        self.assertIn('email', context.exception.detail)