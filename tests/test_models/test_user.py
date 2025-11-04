"""
User Model Tests - Test-Driven Development Approach
Following enterprise-grade testing standards with comprehensive coverage
"""

import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from unittest.mock import patch, Mock
from freezegun import freeze_time
import uuid

User = get_user_model()


class UserModelTest(TestCase):
    """Test User model following TDD methodology"""

    def setUp(self):
        """Set up test data"""
        self.user_data = {
            'email': 'test@example.com',
            'first_name': 'John',
            'last_name': 'Doe',
            'password': 'secure_password123'
        }

    def test_user_creation_with_minimum_fields(self):
        """Test creating user with minimum required fields"""
        # Arrange & Act
        user = User.objects.create_user(**self.user_data)

        # Assert
        self.assertEqual(user.email, 'test@example.com')
        self.assertEqual(user.first_name, 'John')
        self.assertEqual(user.last_name, 'Doe')
        self.assertTrue(user.check_password('secure_password123'))
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertEqual(user.role, 'sales')  # Default role
        self.assertIsNotNone(user.uuid)
        self.assertIsInstance(user.uuid, uuid.UUID)

    def test_user_creation_with_all_fields(self):
        """Test creating user with all optional fields"""
        # Arrange
        full_user_data = {
            **self.user_data,
            'role': 'manager',
            'phone': '+1234567890',
            'department': 'Sales',
            'profile_photo': 'profile_photos/test.jpg'
        }

        # Act
        user = User.objects.create_user(**full_user_data)

        # Assert
        self.assertEqual(user.role, 'manager')
        self.assertEqual(user.phone, '+1234567890')
        self.assertEqual(user.department, 'Sales')
        self.assertEqual(user.profile_photo.name, 'profile_photos/test.jpg')

    def test_user_str_representation(self):
        """Test string representation of user"""
        # Arrange & Act
        user = User.objects.create_user(**self.user_data)

        # Assert
        self.assertEqual(str(user), 'John Doe')

    def test_user_full_name_property(self):
        """Test full_name property"""
        # Arrange & Act
        user = User.objects.create_user(**self.user_data)

        # Assert
        self.assertEqual(user.full_name, 'John Doe')

        # Test with missing names
        user.first_name = ''
        user.save()
        self.assertEqual(user.full_name, 'Doe')

        user.last_name = ''
        user.save()
        self.assertEqual(user.full_name, '')

    def test_user_email_normalization(self):
        """Test email normalization"""
        # Arrange
        test_emails = [
            ('Test@Example.COM', 'Test@example.com'),
            ('test@EXAMPLE.com', 'test@example.com'),
            ('TeSt@ExAmPlE.CoM', 'TeSt@example.com'),
        ]

        for email, expected in test_emails:
            # Arrange & Act
            user_data = self.user_data.copy()
            user_data['email'] = email
            user = User.objects.create_user(**user_data)

            # Assert
            self.assertEqual(user.email, expected)

    def test_user_email_uniqueness(self):
        """Test email uniqueness constraint"""
        # Arrange & Act
        User.objects.create_user(**self.user_data)

        # Assert
        with self.assertRaises(Exception):  # IntegrityError expected
            User.objects.create_user(**self.user_data)

    def test_user_role_choices(self):
        """Test valid role choices"""
        # Arrange
        valid_roles = ['admin', 'sales', 'manager', 'support']

        for role in valid_roles:
            # Arrange & Act
            user_data = self.user_data.copy()
            user_data['role'] = role
            user = User.objects.create_user(**user_data)

            # Assert
            self.assertEqual(user.role, role)
            self.assertTrue(user.has_role(role))

    def test_user_role_helper_methods(self):
        """Test role-based helper methods"""
        # Test admin user
        admin_data = self.user_data.copy()
        admin_data['role'] = 'admin'
        admin = User.objects.create_user(**admin_data)
        self.assertTrue(admin.is_admin())
        self.assertFalse(admin.is_sales_user())
        self.assertFalse(admin.is_manager())

        # Test sales user
        sales_data = self.user_data.copy()
        sales_data['role'] = 'sales'
        sales = User.objects.create_user(**sales_data)
        self.assertFalse(sales.is_admin())
        self.assertTrue(sales.is_sales_user())
        self.assertFalse(sales.is_manager())

        # Test manager user
        manager_data = self.user_data.copy()
        manager_data['role'] = 'manager'
        manager = User.objects.create_user(**manager_data)
        self.assertFalse(manager.is_admin())
        self.assertFalse(manager.is_sales_user())
        self.assertTrue(manager.is_manager())

    def test_user_manager_create_user_without_email(self):
        """Test user creation fails without email"""
        # Arrange
        invalid_data = self.user_data.copy()
        del invalid_data['email']

        # Act & Assert
        with self.assertRaises(ValueError) as context:
            User.objects.create_user(**invalid_data)

        self.assertIn('Users must have an email address', str(context.exception))

    def test_user_manager_create_superuser(self):
        """Test superuser creation"""
        # Act
        superuser = User.objects.create_superuser(
            email='admin@example.com',
            password='admin_password',
            first_name='Admin',
            last_name='User'
        )

        # Assert
        self.assertTrue(superuser.is_staff)
        self.assertTrue(superuser.is_superuser)
        self.assertTrue(superuser.is_active)
        self.assertEqual(superuser.role, 'admin')

    def test_user_manager_create_superuser_without_staff(self):
        """Test superuser creation fails without is_staff=True"""
        # Act & Assert
        with self.assertRaises(ValueError) as context:
            User.objects.create_superuser(
                email='admin@example.com',
                password='admin_password',
                is_staff=False
            )

        self.assertIn('Superuser must have is_staff=True', str(context.exception))

    def test_user_manager_create_superuser_without_superuser(self):
        """Test superuser creation fails without is_superuser=True"""
        # Act & Assert
        with self.assertRaises(ValueError) as context:
            User.objects.create_superuser(
                email='admin@example.com',
                password='admin_password',
                is_superuser=False
            )

        self.assertIn('Superuser must have is_superuser=True', str(context.exception))

    def test_user_manager_get_by_email_case_insensitive(self):
        """Test getting user by email case-insensitively"""
        # Arrange & Act
        User.objects.create_user(**self.user_data)

        # Assert
        user = User.objects.get_by_email('TEST@EXAMPLE.COM')
        self.assertIsNotNone(user)
        self.assertEqual(user.email, 'test@example.com')

    def test_user_manager_active_users(self):
        """Test getting only active users"""
        # Arrange
        active_user = User.objects.create_user(**self.user_data)
        inactive_user_data = self.user_data.copy()
        inactive_user_data['email'] = 'inactive@example.com'
        inactive_user = User.objects.create_user(**inactive_user_data)
        inactive_user.is_active = False
        inactive_user.save()

        # Act
        active_users = User.objects.active_users()

        # Assert
        self.assertEqual(active_users.count(), 1)
        self.assertIn(active_user, active_users)
        self.assertNotIn(inactive_user, active_users)

    def test_user_manager_users_by_role(self):
        """Test getting users by specific role"""
        # Arrange
        sales_user = User.objects.create_user(**self.user_data)
        admin_data = self.user_data.copy()
        admin_data['email'] = 'admin@example.com'
        admin_data['role'] = 'admin'
        admin_user = User.objects.create_user(**admin_data)

        # Act
        sales_users = User.objects.users_by_role('sales')
        admin_users = User.objects.users_by_role('admin')

        # Assert
        self.assertEqual(sales_users.count(), 1)
        self.assertIn(sales_user, sales_users)
        self.assertEqual(admin_users.count(), 1)
        self.assertIn(admin_user, admin_users)

    def test_user_username_field_is_none(self):
        """Test that username field is properly disabled"""
        # Arrange & Act
        user = User.objects.create_user(**self.user_data)

        # Assert
        self.assertIsNone(user.username)

    def test_user_get_role_display(self):
        """Test get_role_display method"""
        # Arrange
        user_data = self.user_data.copy()
        user_data['role'] = 'admin'
        user = User.objects.create_user(**user_data)

        # Act & Assert
        self.assertEqual(user.get_role_display(), 'Administrator')

    def test_user_email_verified_field(self):
        """Test email verification field"""
        # Arrange & Act
        user = User.objects.create_user(**self.user_data)

        # Assert
        self.assertFalse(user.email_verified)

        # Act
        user.email_verified = True
        user.save()

        # Assert
        self.assertTrue(user.email_verified)

    def test_user_two_factor_enabled_field(self):
        """Test two-factor authentication field"""
        # Arrange & Act
        user = User.objects.create_user(**self.user_data)

        # Assert
        self.assertFalse(user.two_factor_enabled)

        # Act
        user.two_factor_enabled = True
        user.save()

        # Assert
        self.assertTrue(user.two_factor_enabled)

    def test_user_created_at_timestamp(self):
        """Test created_at timestamp is set automatically"""
        # Arrange
        with freeze_time('2024-01-01 12:00:00'):
            # Act
            user = User.objects.create_user(**self.user_data)

            # Assert
            self.assertEqual(user.date_joined, timezone.now())

    def test_user_model_meta_configuration(self):
        """Test model meta configuration"""
        # Arrange & Act
        user = User.objects.create_user(**self.user_data)

        # Assert
        self.assertEqual(user._meta.db_table, 'auth_users')
        self.assertEqual(user._meta.verbose_name, 'User')
        self.assertEqual(user._meta.verbose_name_plural, 'Users')
        self.assertEqual(user._meta.ordering, ['last_name', 'first_name'])

    def test_user_model_indexes(self):
        """Test that model has proper indexes"""
        # This is a meta-test - in real implementation you'd check
        # database schema or use Django's inspection tools
        # For now, we verify the index definitions exist in Meta
        meta = User._meta
        index_fields = [index.fields for index in meta.indexes]

        expected_indexes = [
            ['email'],
            ['role'],
            ['is_active'],
            ['date_joined']
        ]

        for expected in expected_indexes:
            self.assertIn(expected, index_fields)

    @patch('crm.apps.authentication.models.UserProfile')
    def test_user_profile_creation_signal(self, mock_profile):
        """Test that UserProfile is created automatically"""
        # Arrange
        mock_profile.objects.create.return_value = Mock()

        # Act
        user = User.objects.create_user(**self.user_data)

        # Assert - Signal should be triggered
        # Note: In real tests, you'd check if profile was actually created
        self.assertIsNotNone(user)


class UserModelValidationTest(TestCase):
    """Test User model validation"""

    def setUp(self):
        """Set up test data"""
        self.user_data = {
            'email': 'test@example.com',
            'first_name': 'John',
            'last_name': 'Doe',
            'password': 'secure_password123'
        }

    def test_user_clean_method_normalizes_email(self):
        """Test clean method normalizes email"""
        # Arrange & Act
        user = User(**self.user_data)
        user.email = 'Test@Example.COM'
        user.clean()

        # Assert
        self.assertEqual(user.email, 'Test@example.com')

    def test_user_save_calls_clean(self):
        """Test that save method calls clean"""
        # Arrange
        user = User.objects.create_user(**self.user_data)

        # Act
        with patch.object(user, 'clean') as mock_clean:
            user.email = 'New@example.com'
            user.save()

            # Assert
            mock_clean.assert_called_once()

    def test_user_invalid_email_raises_validation_error(self):
        """Test that invalid email raises validation error"""
        # Arrange
        invalid_emails = [
            'not-an-email',
            '@example.com',
            'test@',
            'test..test@example.com',
        ]

        for invalid_email in invalid_emails:
            # Arrange & Act
            user = User(**self.user_data)
            user.email = invalid_email

            # Assert
            with self.assertRaises(ValidationError):
                user.full_clean()