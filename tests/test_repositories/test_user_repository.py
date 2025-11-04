"""
User Repository Tests - Test-Driven Development Approach
Following enterprise-grade testing standards with comprehensive coverage
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta

from crm.shared.repositories.user_repository import UserRepository

User = get_user_model()


class UserRepositoryTest(TestCase):
    """Test UserRepository following TDD methodology"""

    def setUp(self):
        """Set up test data"""
        self.repository = UserRepository()
        self.user_data = {
            'email': 'test@example.com',
            'first_name': 'John',
            'last_name': 'Doe',
            'password': 'testpass123',
            'role': 'sales'
        }

    def tearDown(self):
        """Clean up after tests"""
        cache.clear()

    def test_repository_initialization(self):
        """Test repository initialization"""
        # Assert
        self.assertEqual(self.repository.model, User)
        self.assertEqual(self.repository.cache_timeout, 300)
        self.assertEqual(self.repository.cache_prefix, 'user_')

    @patch('crm.shared.repositories.user_repository.cache')
    @patch.object(User.objects, 'get')
    def test_get_by_email_cache_hit(self, mock_get, mock_cache):
        """Test getting user by email with cache hit"""
        # Arrange
        mock_user = Mock(spec=User)
        mock_cache.get.return_value = mock_user

        # Act
        result = self.repository.get_by_email('test@example.com')

        # Assert
        self.assertEqual(result, mock_user)
        mock_cache.get.assert_called_once_with('user_email_test@example.com')
        mock_get.assert_not_called()

    @patch('crm.shared.repositories.user_repository.cache')
    @patch.object(User.objects, 'get')
    def test_get_by_email_cache_miss(self, mock_get, mock_cache):
        """Test getting user by email with cache miss"""
        # Arrange
        mock_user = Mock(spec=User)
        mock_cache.get.return_value = None
        mock_get.return_value = mock_user

        # Act
        result = self.repository.get_by_email('test@example.com', use_cache=True)

        # Assert
        self.assertEqual(result, mock_user)
        mock_cache.get.assert_called_once_with('user_email_test@example.com')
        mock_get.assert_called_once_with(email__iexact='test@example.com')
        mock_cache.set.assert_called_once_with('user_email_test@example.com', mock_user, 300)

    @patch.object(User.objects, 'get')
    def test_get_by_email_not_found(self, mock_get):
        """Test getting user by email when not found"""
        # Arrange
        mock_get.side_effect = User.DoesNotExist()

        # Act
        result = self.repository.get_by_email('nonexistent@example.com')

        # Assert
        self.assertIsNone(result)

    @patch('crm.shared.repositories.user_repository.cache')
    def test_get_active_users_with_cache(self, mock_cache):
        """Test getting active users with cache"""
        # Arrange
        mock_users = [Mock(spec=User), Mock(spec=User)]
        mock_cache.get.return_value = mock_users

        # Act
        result = self.repository.get_active_users(use_cache=True)

        # Assert
        self.assertEqual(result, mock_users)
        mock_cache.get.assert_called_once_with('user_active_users')

    @patch.object(User.objects, 'filter')
    def test_get_active_users_without_cache(self, mock_filter):
        """Test getting active users without cache"""
        # Arrange
        mock_users = [Mock(spec=User), Mock(spec=User)]
        mock_queryset = Mock()
        mock_queryset.__iter__ = Mock(return_value=iter(mock_users))
        mock_filter.return_value = mock_queryset

        # Act
        result = self.repository.get_active_users(use_cache=False)

        # Assert
        self.assertEqual(result, mock_users)
        mock_filter.assert_called_once_with(is_active=True)

    @patch('crm.shared.repositories.user_repository.cache')
    @patch.object(User.objects, 'filter')
    def test_get_users_by_role_with_cache(self, mock_filter, mock_cache):
        """Test getting users by role with cache"""
        # Arrange
        mock_users = [Mock(spec=User)]
        mock_queryset = Mock()
        mock_queryset.filter.return_value = mock_users
        mock_filter.return_value = mock_queryset
        mock_cache.get.return_value = mock_users

        # Act
        result = self.repository.get_users_by_role('sales')

        # Assert
        self.assertEqual(result, mock_users)
        mock_cache.get.assert_called_once_with('user_role_sales')

    @patch('crm.shared.repositories.user_repository.cache')
    @patch.object(User.objects, 'filter')
    def test_search_users_with_cache(self, mock_filter, mock_cache):
        """Test searching users with cache"""
        # Arrange
        mock_users = [Mock(spec=User)]
        mock_queryset = Mock()
        mock_queryset.filter.return_value = mock_users
        mock_filter.return_value = mock_queryset
        mock_cache.get.return_value = mock_users

        # Act
        result = self.repository.search_users('john')

        # Assert
        self.assertEqual(result, mock_users)
        mock_cache.get.assert_called_once_with('user_search_john')

    @patch.object(User.objects, 'create_user')
    @patch.object(UserRepository, '_invalidate_cache_pattern')
    def test_create_user(self, mock_invalidate, mock_create_user):
        """Test creating user"""
        # Arrange
        mock_user = Mock(spec=User)
        mock_user.role = 'sales'
        mock_user.email = 'test@example.com'
        mock_create_user.return_value = mock_user

        # Act
        result = self.repository.create_user(
            email='test@example.com',
            password='testpass123',
            first_name='John',
            last_name='Doe'
        )

        # Assert
        self.assertEqual(result, mock_user)
        mock_create_user.assert_called_once_with(
            email='test@example.com',
            password='testpass123',
            first_name='John',
            last_name='Doe'
        )

        # Check cache invalidation calls
        expected_invalidate_calls = [
            ('active_users',),
            ('role_sales',),
            ('email_test@example.com',)
        ]
        actual_calls = [call[0] for call in mock_invalidate.call_args_list]
        for expected_call in expected_invalidate_calls:
            self.assertIn(expected_call, actual_calls)

    @patch.object(User.objects, 'create_superuser')
    @patch.object(UserRepository, '_invalidate_cache_pattern')
    def test_create_superuser(self, mock_invalidate, mock_create_superuser):
        """Test creating superuser"""
        # Arrange
        mock_superuser = Mock(spec=User)
        mock_superuser.email = 'admin@example.com'
        mock_create_superuser.return_value = mock_superuser

        # Act
        result = self.repository.create_superuser(
            email='admin@example.com',
            password='adminpass123',
            first_name='Admin',
            last_name='User'
        )

        # Assert
        self.assertEqual(result, mock_superuser)
        mock_create_superuser.assert_called_once_with(
            email='admin@example.com',
            password='adminpass123',
            first_name='Admin',
            last_name='User'
        )

    @patch.object(User.objects, 'get')
    @patch.object(UserRepository, '_invalidate_cache_pattern')
    def test_update_password_success(self, mock_invalidate, mock_get):
        """Test successful password update"""
        # Arrange
        mock_user = Mock(spec=User)
        mock_user.id = 1
        mock_user.email = 'test@example.com'
        mock_user.uuid = 'test-uuid'
        mock_get.return_value = mock_user

        # Act
        result = self.repository.update_password(1, 'newpassword123')

        # Assert
        self.assertTrue(result)
        mock_get.assert_called_once_with(id=1)
        mock_user.set_password.assert_called_once_with('newpassword123')
        mock_user.save.assert_called_once()

    @patch.object(User.objects, 'get')
    def test_update_password_not_found(self, mock_get):
        """Test updating password when user doesn't exist"""
        # Arrange
        mock_get.side_effect = User.DoesNotExist()

        # Act
        result = self.repository.update_password(999, 'newpassword123')

        # Assert
        self.assertFalse(result)

    @patch.object(User.objects, 'get')
    @patch.object(UserRepository, '_invalidate_cache_pattern')
    def test_deactivate_user_success(self, mock_invalidate, mock_get):
        """Test successful user deactivation"""
        # Arrange
        mock_user = Mock(spec=User)
        mock_user.id = 1
        mock_user.email = 'test@example.com'
        mock_user.role = 'sales'
        mock_user.uuid = 'test-uuid'
        mock_get.return_value = mock_user

        # Act
        result = self.repository.deactivate_user(1)

        # Assert
        self.assertTrue(result)
        mock_get.assert_called_once_with(id=1)
        self.assertFalse(mock_user.is_active)
        mock_user.save.assert_called_once()

    @patch.object(User.objects, 'get')
    def test_deactivate_user_not_found(self, mock_get):
        """Test deactivating user that doesn't exist"""
        # Arrange
        mock_get.side_effect = User.DoesNotExist()

        # Act
        result = self.repository.deactivate_user(999)

        # Assert
        self.assertFalse(result)

    @patch.object(User.objects, 'get')
    @patch.object(UserRepository, '_invalidate_cache_pattern')
    def test_activate_user_success(self, mock_invalidate, mock_get):
        """Test successful user activation"""
        # Arrange
        mock_user = Mock(spec=User)
        mock_user.id = 1
        mock_user.email = 'test@example.com'
        mock_user.role = 'sales'
        mock_user.uuid = 'test-uuid'
        mock_get.return_value = mock_user

        # Act
        result = self.repository.activate_user(1)

        # Assert
        self.assertTrue(result)
        mock_get.assert_called_once_with(id=1)
        self.assertTrue(mock_user.is_active)
        mock_user.save.assert_called_once()

    @patch.object(User.objects, 'get')
    @patch.object(UserRepository, '_invalidate_cache_pattern')
    def test_update_last_login_success(self, mock_invalidate, mock_get):
        """Test successful last login update"""
        # Arrange
        mock_user = Mock(spec=User)
        mock_user.id = 1
        mock_user.uuid = 'test-uuid'
        mock_get.return_value = mock_user

        # Act
        result = self.repository.update_last_login(1)

        # Assert
        self.assertTrue(result)
        mock_get.assert_called_once_with(id=1)
        mock_user.save.assert_called_once_with(update_fields=['last_login'])

    @patch.object(User.objects, 'filter')
    @patch('crm.shared.repositories.user_repository.cache')
    def test_get_users_created_between(self, mock_cache, mock_filter):
        """Test getting users created between dates"""
        # Arrange
        start_date = timezone.now() - timedelta(days=30)
        end_date = timezone.now()
        mock_users = [Mock(spec=User)]
        mock_queryset = Mock()
        mock_queryset.order_by.return_value = mock_queryset
        mock_queryset.__iter__ = Mock(return_value=iter(mock_users))
        mock_filter.return_value = mock_queryset
        mock_cache.get.return_value = None

        # Act
        result = self.repository.get_users_created_between(start_date, end_date)

        # Assert
        self.assertEqual(result, mock_users)
        mock_filter.assert_called_once_with(date_joined__range=[start_date, end_date])
        mock_queryset.order_by.assert_called_once_with('-date_joined')

    @patch('crm.shared.repositories.user_repository.cache')
    @patch.object(User.objects, 'count')
    @patch.object(User.objects, 'filter')
    def test_get_user_statistics_with_cache(self, mock_filter, mock_count, mock_cache):
        """Test getting user statistics with cache"""
        # Arrange
        mock_stats = {
            'total_users': 100,
            'active_users': 80,
            'users_by_role': {'admin': 5, 'sales': 50},
        }
        mock_cache.get.return_value = mock_stats

        # Act
        result = self.repository.get_user_statistics()

        # Assert
        self.assertEqual(result, mock_stats)
        mock_cache.get.assert_called_once_with('user_statistics')
        mock_filter.assert_not_called()
        mock_count.assert_not_called()

    @patch('crm.shared.repositories.user_repository.cache')
    @patch.object(User.objects, 'count')
    @patch.object(User.objects, 'filter')
    def test_get_user_statistics_without_cache(self, mock_filter, mock_count, mock_cache):
        """Test getting user statistics without cache"""
        # Arrange
        mock_cache.get.return_value = None
        mock_count.side_effect = [100, 80, 5, 50, 20, 5]  # Various counts
        mock_queryset = Mock()
        mock_filter.return_value = mock_queryset

        # Act
        result = self.repository.get_user_statistics()

        # Assert
        self.assertIn('total_users', result)
        self.assertIn('active_users', result)
        self.assertIn('users_by_role', result)
        self.assertIn('recent_users', result)
        self.assertIn('last_updated', result)
        self.assertEqual(result['total_users'], 100)
        self.assertEqual(result['active_users'], 80)

    @patch.object(User.objects, 'create_user')
    @patch.object(UserRepository, '_invalidate_cache_pattern')
    def test_bulk_create_users(self, mock_invalidate, mock_create_user):
        """Test bulk creating users"""
        # Arrange
        users_data = [
            {'email': 'user1@example.com', 'first_name': 'User', 'last_name': 'One', 'password': 'pass123'},
            {'email': 'user2@example.com', 'first_name': 'User', 'last_name': 'Two', 'password': 'pass123'},
        ]
        mock_users = [Mock(spec=User), Mock(spec=User)]
        mock_create_user.side_effect = mock_users

        # Act
        result = self.repository.bulk_create_users(users_data)

        # Assert
        self.assertEqual(len(result), 2)
        self.assertEqual(result, mock_users)
        self.assertEqual(mock_create_user.call_count, 2)

    @patch('crm.shared.repositories.user_repository.cache')
    def test_clear_user_cache(self, mock_cache):
        """Test clearing user-specific cache"""
        # Arrange
        mock_user = Mock(spec=User)
        mock_user.id = 1
        mock_user.email = 'test@example.com'
        mock_user.role = 'sales'
        mock_user.uuid = 'test-uuid'

        # Act
        self.repository.clear_user_cache(mock_user)

        # Assert
        expected_cache_keys = [
            'user_id_1',
            'user_email_test@example.com',
            'user_active_users',
            'user_role_sales',
            'user_statistics',
            'user_uuid_test-uuid',
        ]

        # Check that delete was called for each expected cache key
        delete_calls = [call[0][0] for call in mock_cache.delete.call_args_list]
        for expected_key in expected_cache_keys:
            self.assertIn(expected_key, delete_calls)

    def test_email_case_insensitive_cache_key(self):
        """Test that email cache keys are case-insensitive"""
        # Arrange & Act
        cache_key1 = self.repository.get_cache_key("email_Test@Example.COM")
        cache_key2 = self.repository.get_cache_key("email_test@example.com")

        # Assert
        self.assertEqual(cache_key1, cache_key2)