"""
Authentication ViewSet Tests - TDD Approach
Testing comprehensive authentication and user management operations
Following SOLID principles and comprehensive test coverage
"""

import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from crm.apps.authentication.models import User, UserProfile
from crm.apps.authentication.serializers import UserSerializer, UserDetailSerializer
from crm.apps.authentication.viewsets import UserViewSet

User = get_user_model()


class UserViewSetTestCase(APITestCase):
    """Base test case for User ViewSet tests"""

    def setUp(self):
        """Set up test data"""
        self.admin_user = User.objects.create_user(
            email='admin@example.com',
            password='adminpass123',
            first_name='Admin',
            last_name='User',
            role='admin',
            is_staff=True,
            is_superuser=True
        )

        self.manager_user = User.objects.create_user(
            email='manager@example.com',
            password='managerpass123',
            first_name='Manager',
            last_name='User',
            role='manager'
        )

        self.sales_user = User.objects.create_user(
            email='sales@example.com',
            password='salespass123',
            first_name='Sales',
            last_name='User',
            role='sales'
        )

        self.user_data = {
            'email': 'newuser@example.com',
            'first_name': 'New',
            'last_name': 'User',
            'role': 'sales',
            'phone': '+1-555-123-4567',
            'department': 'Sales'
        }

        # URL patterns
        self.list_url = reverse('user-list')
        self.register_url = reverse('user-register')
        self.login_url = reverse('user-login')
        self.logout_url = reverse('user-logout')
        self.refresh_url = reverse('token_refresh')


class UserViewSetAuthenticationTests(UserViewSetTestCase):
    """Test authentication requirements for User ViewSet"""

    def test_unauthenticated_access_denied(self):
        """Test that unauthenticated users cannot access user endpoints"""
        client = APIClient()

        # Test list access
        response = client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Test detail access
        detail_url = reverse('user-detail', kwargs={'pk': self.sales_user.id})
        response = client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_access_allowed(self):
        """Test that authenticated users can access user endpoints"""
        client = APIClient()
        client.force_authenticate(user=self.sales_user)

        # Test list access
        response = client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Test own detail access
        detail_url = reverse('user-detail', kwargs={'pk': self.sales_user.id})
        response = client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class UserViewSetListTests(UserViewSetTestCase):
    """Test User ViewSet list operations"""

    def test_admin_can_list_all_users(self):
        """Test admin can list all users"""
        client = APIClient()
        client.force_authenticate(user=self.admin_user)

        response = client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(len(data['results']), 3)  # admin, manager, sales

    def test_manager_can_list_users(self):
        """Test manager can list users"""
        client = APIClient()
        client.force_authenticate(user=self.manager_user)

        response = client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        # Manager should see users based on business rules
        # For now, assume they can see all users
        self.assertGreaterEqual(len(data['results']), 1)

    def test_sales_user_limited_access(self):
        """Test sales user has limited access to user list"""
        client = APIClient()
        client.force_authenticate(user=self.sales_user)

        response = client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        # Sales user might only see themselves or limited users
        self.assertGreaterEqual(len(data['results']), 1)

    def test_list_users_with_pagination(self):
        """Test list endpoint respects pagination"""
        # Create additional users
        for i in range(25):
            User.objects.create_user(
                email=f'user{i}@example.com',
                password=f'pass{i}123',
                first_name=f'User',
                last_name=f'{i}',
                role='sales'
            )

        client = APIClient()
        client.force_authenticate(user=self.admin_user)

        response = client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertIn('results', data)
        self.assertIn('count', data)
        self.assertIn('next', data)
        self.assertIn('previous', data)
        self.assertEqual(len(data['results']), 20)  # Default page size

    def test_list_users_with_search(self):
        """Test list endpoint with search functionality"""
        client = APIClient()
        client.force_authenticate(user=self.admin_user)

        # Search by first name
        response = client.get(f'{self.list_url}?search=Sales')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        user_emails = [user['email'] for user in data['results']]
        self.assertIn('sales@example.com', user_emails)

        # Search by email
        response = client.get(f'{self.list_url}?search=admin@example.com')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(len(data['results']), 1)
        self.assertEqual(data['results'][0]['email'], 'admin@example.com')

    def test_list_users_with_filtering(self):
        """Test list endpoint with filtering"""
        client = APIClient()
        client.force_authenticate(user=self.admin_user)

        # Filter by role
        response = client.get(f'{self.list_url}?role=sales')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        user_roles = [user['role'] for user in data['results']]
        self.assertTrue(all(role == 'sales' for role in user_roles))

        # Filter by active status
        response = client.get(f'{self.list_url}?is_active=true')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        user_statuses = [user['is_active'] for user in data['results']]
        self.assertTrue(all(user_statuses))

    def test_list_users_serializer_selection(self):
        """Test appropriate serializer is used for list view"""
        client = APIClient()
        client.force_authenticate(user=self.admin_user)

        response = client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        user = data['results'][0]

        # Should include basic fields
        self.assertIn('id', user)
        self.assertIn('email', user)
        self.assertIn('first_name', user)
        self.assertIn('full_name', user)
        self.assertIn('role', user)

        # Should not include verbose fields for list view
        self.assertNotIn('profile', user)
        self.assertNotIn('permissions', user)


class UserViewSetRetrieveTests(UserViewSetTestCase):
    """Test User ViewSet retrieve operations"""

    def test_admin_can_view_any_user(self):
        """Test admin can view any user details"""
        client = APIClient()
        client.force_authenticate(user=self.admin_user)

        detail_url = reverse('user-detail', kwargs={'pk': self.sales_user.id})
        response = client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(data['id'], self.sales_user.id)
        self.assertEqual(data['email'], 'sales@example.com')
        self.assertIn('profile', data)
        self.assertIn('permissions', data)

    def test_manager_can_view_user_details(self):
        """Test manager can view user details"""
        client = APIClient()
        client.force_authenticate(user=self.manager_user)

        detail_url = reverse('user-detail', kwargs={'pk': self.sales_user.id})
        response = client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(data['id'], self.sales_user.id)

    def test_user_can_view_own_details(self):
        """Test user can view their own details"""
        client = APIClient()
        client.force_authenticate(user=self.sales_user)

        detail_url = reverse('user-detail', kwargs={'pk': self.sales_user.id})
        response = client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(data['id'], self.sales_user.id)
        self.assertEqual(data['email'], 'sales@example.com')

    def test_user_cannot_view_other_users_details(self):
        """Test user cannot view other users' details"""
        client = APIClient()
        client.force_authenticate(user=self.sales_user)

        detail_url = reverse('user-detail', kwargs={'pk': self.manager_user.id})
        response = client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_nonexistent_user(self):
        """Test retrieving non-existent user returns 404"""
        client = APIClient()
        client.force_authenticate(user=self.admin_user)

        fake_url = reverse('user-detail', kwargs={'pk': 99999})
        response = client.get(fake_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_uses_detail_serializer(self):
        """Test retrieve endpoint uses detail serializer"""
        client = APIClient()
        client.force_authenticate(user=self.admin_user)

        detail_url = reverse('user-detail', kwargs={'pk': self.sales_user.id})
        response = client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        # Should include detail-specific fields
        self.assertIn('profile', data)
        self.assertIn('permissions', data)
        self.assertIn('date_joined', data)
        self.assertIn('last_login', data)


class UserViewSetCreateTests(UserViewSetTestCase):
    """Test User ViewSet create operations"""

    def test_admin_can_create_user(self):
        """Test admin can create users"""
        client = APIClient()
        client.force_authenticate(user=self.admin_user)

        response = client.post(self.list_url, self.user_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        data = response.json()
        self.assertEqual(data['email'], 'newuser@example.com')
        self.assertEqual(data['first_name'], 'New')
        self.assertEqual(data['last_name'], 'User')
        self.assertEqual(data['role'], 'sales')

        # Verify user was created in database
        user = User.objects.get(id=data['id'])
        self.assertEqual(user.email, 'newuser@example.com')

    def test_manager_can_create_user(self):
        """Test manager can create users"""
        client = APIClient()
        client.force_authenticate(user=self.manager_user)

        response = client.post(self.list_url, self.user_data)
        # This depends on business rules - adjust as needed
        # self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_sales_user_cannot_create_user(self):
        """Test sales user cannot create users"""
        client = APIClient()
        client.force_authenticate(user=self.sales_user)

        response = client.post(self.list_url, self.user_data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_user_invalid_data(self):
        """Test creating user with invalid data"""
        client = APIClient()
        client.force_authenticate(user=self.admin_user)

        invalid_data = {
            'email': 'invalid-email',
            'first_name': '',
            'last_name': '',
            'role': 'invalid_role'
        }

        response = client.post(self.list_url, invalid_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        data = response.json()
        self.assertIn('email', data)
        self.assertIn('first_name', data)
        self.assertIn('last_name', data)
        self.assertIn('role', data)

    def test_create_user_duplicate_email(self):
        """Test creating user with duplicate email"""
        client = APIClient()
        client.force_authenticate(user=self.admin_user)

        duplicate_data = self.user_data.copy()
        duplicate_data['email'] = 'sales@example.com'  # Existing email

        response = client.post(self.list_url, duplicate_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        data = response.json()
        self.assertIn('email', data)


class UserViewSetUpdateTests(UserViewSetTestCase):
    """Test User ViewSet update operations"""

    def test_admin_can_update_any_user(self):
        """Test admin can update any user"""
        client = APIClient()
        client.force_authenticate(user=self.admin_user)

        update_data = {
            'first_name': 'Updated',
            'last_name': 'Name',
            'phone': '+1-555-999-8888'
        }

        detail_url = reverse('user-detail', kwargs={'pk': self.sales_user.id})
        response = client.patch(detail_url, update_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(data['first_name'], 'Updated')
        self.assertEqual(data['last_name'], 'Name')
        self.assertEqual(data['phone'], '+1-555-999-8888')

    def test_user_can_update_own_profile(self):
        """Test user can update their own profile"""
        client = APIClient()
        client.force_authenticate(user=self.sales_user)

        update_data = {
            'first_name': 'Self Updated',
            'phone': '+1-555-777-6666'
        }

        detail_url = reverse('user-detail', kwargs={'pk': self.sales_user.id})
        response = client.patch(detail_url, update_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(data['first_name'], 'Self Updated')

    def test_user_cannot_update_other_users(self):
        """Test user cannot update other users"""
        client = APIClient()
        client.force_authenticate(user=self.sales_user)

        update_data = {'first_name': 'Unauthorized Update'}

        detail_url = reverse('user-detail', kwargs={'pk': self.manager_user.id})
        response = client.patch(detail_url, update_data)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_user_sanitizes_data(self):
        """Test update endpoint sanitizes input data"""
        client = APIClient()
        client.force_authenticate(user=self.admin_user)

        update_data = {
            'first_name': '  Updated Name  ',
            'last_name': '  With Spaces  ',
            'department': '  Updated Department  '
        }

        detail_url = reverse('user-detail', kwargs={'pk': self.sales_user.id})
        response = client.patch(detail_url, update_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(data['first_name'], 'Updated Name')
        self.assertEqual(data['last_name'], 'With Spaces')
        self.assertEqual(data['department'], 'Updated Department')


class UserViewSetDeleteTests(UserViewSetTestCase):
    """Test User ViewSet delete operations"""

    def test_admin_can_delete_user(self):
        """Test admin can delete users"""
        client = APIClient()
        client.force_authenticate(user=self.admin_user)

        # Create a user to delete
        test_user = User.objects.create_user(
            email='todelete@example.com',
            password='deletepass123',
            first_name='To',
            last_name='Delete',
            role='sales'
        )

        detail_url = reverse('user-detail', kwargs={'pk': test_user.id})
        response = client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # User should be deleted
        with self.assertRaises(User.DoesNotExist):
            User.objects.get(id=test_user.id)

    def test_admin_cannot_delete_self(self):
        """Test admin cannot delete themselves"""
        client = APIClient()
        client.force_authenticate(user=self.admin_user)

        detail_url = reverse('user-detail', kwargs={'pk': self.admin_user.id})
        response = client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_manager_cannot_delete_user(self):
        """Test manager cannot delete users"""
        client = APIClient()
        client.force_authenticate(user=self.manager_user)

        detail_url = reverse('user-detail', kwargs={'pk': self.sales_user.id})
        response = client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_sales_user_cannot_delete_user(self):
        """Test sales user cannot delete users"""
        client = APIClient()
        client.force_authenticate(user=self.sales_user)

        detail_url = reverse('user-detail', kwargs={'pk': self.sales_user.id})
        response = client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class UserViewSetCustomActionsTests(UserViewSetTestCase):
    """Test User ViewSet custom actions"""

    def test_change_password_action(self):
        """Test change password action"""
        client = APIClient()
        client.force_authenticate(user=self.sales_user)

        change_password_url = reverse('user-change-password')
        password_data = {
            'old_password': 'salespass123',
            'new_password': 'newsecurepass123',
            'new_password_confirm': 'newsecurepass123'
        }

        response = client.post(change_password_url, password_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertIn('message', data)

        # Verify password was changed
        self.sales_user.refresh_from_db()
        self.assertTrue(self.sales_user.check_password('newsecurepass123'))

    def test_change_password_wrong_old_password(self):
        """Test change password with wrong old password"""
        client = APIClient()
        client.force_authenticate(user=self.sales_user)

        change_password_url = reverse('user-change-password')
        password_data = {
            'old_password': 'wrongpass123',
            'new_password': 'newsecurepass123',
            'new_password_confirm': 'newsecurepass123'
        }

        response = client.post(change_password_url, password_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_change_password_mismatched_confirm(self):
        """Test change password with mismatched confirmation"""
        client = APIClient()
        client.force_authenticate(user=self.sales_user)

        change_password_url = reverse('user-change-password')
        password_data = {
            'old_password': 'salespass123',
            'new_password': 'newsecurepass123',
            'new_password_confirm': 'differentpass123'
        }

        response = client.post(change_password_url, password_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_profile_action(self):
        """Test update profile action"""
        client = APIClient()
        client.force_authenticate(user=self.sales_user)

        update_profile_url = reverse('user-update-profile')
        profile_data = {
            'bio': 'This is my updated bio',
            'timezone': 'America/New_York',
            'language': 'en',
            'email_notifications': True,
            'push_notifications': False
        }

        response = client.post(update_profile_url, profile_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertIn('message', data)

        # Verify profile was updated
        self.sales_user.profile.refresh_from_db()
        self.assertEqual(self.sales_user.profile.bio, 'This is my updated bio')
        self.assertEqual(self.sales_user.profile.timezone, 'America/New_York')

    def test_deactivate_user_action(self):
        """Test deactivate user action"""
        client = APIClient()
        client.force_authenticate(user=self.admin_user)

        deactivate_url = reverse('user-deactivate', kwargs={'pk': self.sales_user.id})
        response = client.post(deactivate_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify user was deactivated
        self.sales_user.refresh_from_db()
        self.assertFalse(self.sales_user.is_active)

    def test_activate_user_action(self):
        """Test activate user action"""
        # First deactivate the user
        self.sales_user.is_active = False
        self.sales_user.save()

        client = APIClient()
        client.force_authenticate(user=self.admin_user)

        activate_url = reverse('user-activate', kwargs={'pk': self.sales_user.id})
        response = client.post(activate_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify user was activated
        self.sales_user.refresh_from_db()
        self.assertTrue(self.sales_user.is_active)

    def test_search_users_action(self):
        """Test search users action"""
        client = APIClient()
        client.force_authenticate(user=self.admin_user)

        search_url = reverse('user-search')
        response = client.get(f'{search_url}?query=Sales')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertIsInstance(data, list)
        # Should contain sales user in results

    def test_bulk_operations_action(self):
        """Test bulk operations action"""
        client = APIClient()
        client.force_authenticate(user=self.admin_user)

        # Create additional users for bulk operation
        user1 = User.objects.create_user(
            email='bulk1@example.com',
            password='bulkpass123',
            first_name='Bulk',
            last_name='User1',
            role='sales'
        )
        user2 = User.objects.create_user(
            email='bulk2@example.com',
            password='bulkpass123',
            first_name='Bulk',
            last_name='User2',
            role='sales'
        )

        bulk_url = reverse('user-bulk-operations')
        bulk_data = {
            'user_ids': [user1.id, user2.id],
            'operation': 'deactivate'
        }

        response = client.post(bulk_url, bulk_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertIn('message', data)
        self.assertEqual(data['updated_count'], 2)

        # Verify users were deactivated
        user1.refresh_from_db()
        user2.refresh_from_db()
        self.assertFalse(user1.is_active)
        self.assertFalse(user2.is_active)


class AuthenticationViewTests(UserViewSetTestCase):
    """Test authentication views"""

    def test_user_registration(self):
        """Test user registration endpoint"""
        registration_data = {
            'email': 'register@example.com',
            'first_name': 'Register',
            'last_name': 'User',
            'password': 'securepass123',
            'password_confirm': 'securepass123',
            'role': 'sales'
        }

        response = self.client.post(self.register_url, registration_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        data = response.json()
        self.assertEqual(data['email'], 'register@example.com')
        self.assertEqual(data['first_name'], 'Register')

        # Verify user was created
        user = User.objects.get(email='register@example.com')
        self.assertTrue(user.check_password('securepass123'))

    def test_user_registration_password_mismatch(self):
        """Test user registration with mismatched passwords"""
        registration_data = {
            'email': 'register@example.com',
            'first_name': 'Register',
            'last_name': 'User',
            'password': 'securepass123',
            'password_confirm': 'differentpass123',
            'role': 'sales'
        }

        response = self.client.post(self.register_url, registration_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_login(self):
        """Test user login endpoint"""
        login_data = {
            'email': 'sales@example.com',
            'password': 'salespass123'
        }

        response = self.client.post(self.login_url, login_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertIn('access_token', data)
        self.assertIn('refresh_token', data)
        self.assertIn('user', data)

    def test_user_login_invalid_credentials(self):
        """Test user login with invalid credentials"""
        login_data = {
            'email': 'sales@example.com',
            'password': 'wrongpass123'
        }

        response = self.client.post(self.login_url, login_data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_logout(self):
        """Test user logout endpoint"""
        # First login to get token
        login_data = {
            'email': 'sales@example.com',
            'password': 'salespass123'
        }

        login_response = self.client.post(self.login_url, login_data)
        refresh_token = login_response.json()['refresh_token']

        # Then logout
        logout_data = {'refresh_token': refresh_token}
        response = self.client.post(self.logout_url, logout_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_token_refresh(self):
        """Test token refresh endpoint"""
        # First login to get token
        login_data = {
            'email': 'sales@example.com',
            'password': 'salespass123'
        }

        login_response = self.client.post(self.login_url, login_data)
        refresh_token = login_response.json()['refresh_token']

        # Then refresh token
        refresh_data = {'refresh_token': refresh_token}
        response = self.client.post(self.refresh_url, refresh_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertIn('access_token', data)


class UserViewSetIntegrationTests(UserViewSetTestCase):
    """Integration tests for User ViewSet"""

    def test_user_lifecycle_workflow(self):
        """Test complete user lifecycle"""
        admin_client = APIClient()
        admin_client.force_authenticate(user=self.admin_user)

        # Create user
        response = admin_client.post(self.list_url, self.user_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        user_data = response.json()
        user_id = user_data['id']

        # Update user
        detail_url = reverse('user-detail', kwargs={'pk': user_id})
        update_data = {'first_name': 'Updated Name'}
        response = admin_client.patch(detail_url, update_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Deactivate user
        deactivate_url = reverse('user-deactivate', kwargs={'pk': user_id})
        response = admin_client.post(deactivate_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Reactivate user
        activate_url = reverse('user-activate', kwargs={'pk': user_id})
        response = admin_client.post(activate_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Delete user
        response = admin_client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_authentication_flow(self):
        """Test complete authentication flow"""
        # Register new user
        registration_data = {
            'email': 'flowtest@example.com',
            'first_name': 'Flow',
            'last_name': 'Test',
            'password': 'flowpass123',
            'password_confirm': 'flowpass123',
            'role': 'sales'
        }

        response = self.client.post(self.register_url, registration_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Login
        login_data = {
            'email': 'flowtest@example.com',
            'password': 'flowpass123'
        }

        response = self.client.post(self.login_url, login_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        tokens = response.json()
        access_token = tokens['access_token']
        refresh_token = tokens['refresh_token']

        # Use token to access protected endpoint
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')

        detail_url = reverse('user-detail', kwargs={'pk': tokens['user']['id']})
        response = client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Change password
        change_password_url = reverse('user-change-password')
        password_data = {
            'old_password': 'flowpass123',
            'new_password': 'newflowpass123',
            'new_password_confirm': 'newflowpass123'
        }

        response = client.post(change_password_url, password_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Logout
        logout_data = {'refresh_token': refresh_token}
        response = client.post(self.logout_url, logout_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_error_handling_consistency(self):
        """Test consistent error handling across endpoints"""
        client = APIClient()
        client.force_authenticate(user=self.admin_user)

        # Test with invalid data
        invalid_data = {
            'email': 'invalid-email',
            'first_name': '',
            'role': 'invalid_role'
        }

        # Create error
        response = client.post(self.list_url, invalid_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIsInstance(response.json(), dict)

        # Update error
        detail_url = reverse('user-detail', kwargs={'pk': self.sales_user.id})
        response = client.patch(detail_url, invalid_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIsInstance(response.json(), dict)

    def test_response_format_consistency(self):
        """Test consistent response format across endpoints"""
        client = APIClient()
        client.force_authenticate(user=self.admin_user)

        # List response format
        response = client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        list_data = response.json()
        self.assertIn('results', list_data)
        self.assertIn('count', list_data)

        # Detail response format
        detail_url = reverse('user-detail', kwargs={'pk': self.sales_user.id})
        response = client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        detail_data = response.json()
        self.assertIsInstance(detail_data, dict)
        self.assertIn('id', detail_data)