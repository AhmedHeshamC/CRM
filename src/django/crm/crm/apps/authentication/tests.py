from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()


class UserModelTest(TestCase):
    def test_create_user(self):
        """Test creating a basic user"""
        user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        self.assertEqual(user.email, 'test@example.com')
        self.assertEqual(user.first_name, 'Test')
        self.assertEqual(user.last_name, 'User')
        self.assertTrue(user.check_password('testpass123'))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_create_superuser(self):
        """Test creating a superuser"""
        user = User.objects.create_superuser(
            email='admin@example.com',
            password='adminpass123',
            first_name='Admin',
            last_name='User'
        )
        self.assertEqual(user.email, 'admin@example.com')
        self.assertEqual(user.first_name, 'Admin')
        self.assertEqual(user.last_name, 'User')
        self.assertTrue(user.check_password('adminpass123'))
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)


class AuthenticationAPITest(TestCase):
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            email='testuser@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )

    def test_user_creation_and_authentication(self):
        """Test basic user creation and authentication flow"""
        # Create a new user
        new_user = User.objects.create_user(
            email='newuser@example.com',
            password='newpass123',
            first_name='New',
            last_name='User'
        )

        self.assertEqual(new_user.email, 'newuser@example.com')
        self.assertTrue(new_user.check_password('newpass123'))
        self.assertFalse(new_user.is_staff)
        self.assertFalse(new_user.is_superuser)
        self.assertTrue(new_user.is_active)

    def test_user_role_management(self):
        """Test user role assignments"""
        # Test different user roles
        admin_user = User.objects.create_user(
            email='admin@example.com',
            password='admin123',
            first_name='Admin',
            last_name='User',
            role='admin'
        )

        sales_user = User.objects.create_user(
            email='sales@example.com',
            password='sales123',
            first_name='Sales',
            last_name='Rep',
            role='sales'
        )

        self.assertEqual(admin_user.role, 'admin')
        self.assertEqual(sales_user.role, 'sales')

        # Count users by role
        admin_count = User.objects.filter(role='admin').count()
        sales_count = User.objects.filter(role='sales').count()

        self.assertGreaterEqual(admin_count, 1)
        self.assertGreaterEqual(sales_count, 1)

    def test_user_email_uniqueness(self):
        """Test that emails are unique"""
        # Try to create user with duplicate email
        with self.assertRaises(Exception):  # Should raise IntegrityError or similar
            User.objects.create_user(
                email='testuser@example.com',  # Same as setUp user
                password='password123',
                first_name='Duplicate',
                last_name='User'
            )


class DatabaseConnectionTest(TestCase):
    def test_database_connection(self):
        """Test that database connection is working"""
        from django.db import connection
        cursor = connection.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        self.assertEqual(result[0], 1)