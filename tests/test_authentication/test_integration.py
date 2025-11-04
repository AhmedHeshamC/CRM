"""
Integration Tests for Authentication and Authorization
Following TDD approach and SOLID principles
"""

import pytest
import json
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from unittest.mock import patch, MagicMock
from shared.authentication.permissions import (
    IsAdminUser,
    IsManagerOrAdminUser,
    IsSalesOrAboveUser,
    ContactPermission,
    DealPermission,
    ActivityPermission,
)

User = get_user_model()


class AuthenticationIntegrationTest(TestCase):
    """Integration tests for authentication flow"""

    def setUp(self):
        """Set up test environment"""
        self.client = APIClient()

        # Create test users
        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            first_name='Admin',
            last_name='User',
            role='admin'
        )

        self.manager_user = User.objects.create_user(
            email='manager@test.com',
            password='testpass123',
            first_name='Manager',
            last_name='User',
            role='manager'
        )

        self.sales_user = User.objects.create_user(
            email='sales@test.com',
            password='testpass123',
            first_name='Sales',
            last_name='User',
            role='sales'
        )

        self.support_user = User.objects.create_user(
            email='support@test.com',
            password='testpass123',
            first_name='Support',
            last_name='User',
            role='support'
        )

    def test_user_registration_flow(self):
        """Test complete user registration flow"""
        registration_data = {
            'email': 'newuser@test.com',
            'password': 'newpass123',
            'first_name': 'New',
            'last_name': 'User',
            'role': 'sales'
        }

        response = self.client.post(
            '/api/v1/auth/auth/register/',
            registration_data,
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('email', response.data)
        self.assertEqual(response.data['email'], 'newuser@test.com')

        # Verify user was created
        new_user = User.objects.get(email='newuser@test.com')
        self.assertTrue(new_user.check_password('newpass123'))
        self.assertEqual(new_user.role, 'sales')

    def test_user_login_flow(self):
        """Test complete user login flow"""
        login_data = {
            'email': 'sales@test.com',
            'password': 'testpass123'
        }

        response = self.client.post(
            '/api/v1/auth/auth/login/',
            login_data,
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access_token', response.data)
        self.assertIn('refresh_token', response.data)
        self.assertIn('user', response.data)

        # Verify token structure
        access_token = response.data['access_token']
        self.assertIsInstance(access_token, str)
        self.assertTrue(len(access_token) > 0)

    def test_protected_endpoint_access_with_valid_token(self):
        """Test accessing protected endpoints with valid JWT token"""
        # Login to get token
        login_data = {
            'email': 'sales@test.com',
            'password': 'testpass123'
        }

        login_response = self.client.post(
            '/api/v1/auth/auth/login/',
            login_data,
            format='json'
        )

        access_token = login_response.data['access_token']

        # Access protected endpoint with token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        response = self.client.get('/api/v1/auth/users/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_protected_endpoint_access_without_token(self):
        """Test accessing protected endpoints without JWT token"""
        response = self.client.get('/api/v1/auth/users/')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_protected_endpoint_access_with_invalid_token(self):
        """Test accessing protected endpoints with invalid JWT token"""
        self.client.credentials(HTTP_AUTHORIZATION='Bearer invalid.token.here')
        response = self.client.get('/api/v1/auth/users/')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_token_refresh_flow(self):
        """Test token refresh flow"""
        # Login to get tokens
        login_data = {
            'email': 'sales@test.com',
            'password': 'testpass123'
        }

        login_response = self.client.post(
            '/api/v1/auth/auth/login/',
            login_data,
            format='json'
        )

        refresh_token = login_response.data['refresh_token']

        # Refresh token
        refresh_data = {
            'refresh': refresh_token
        }

        response = self.client.post(
            '/api/v1/auth/auth/refresh/',
            refresh_data,
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)

    def test_user_logout_flow(self):
        """Test user logout flow"""
        # Login to get tokens
        login_data = {
            'email': 'sales@test.com',
            'password': 'testpass123'
        }

        login_response = self.client.post(
            '/api/v1/auth/auth/login/',
            login_data,
            format='json'
        )

        refresh_token = login_response.data['refresh_token']

        # Logout with refresh token
        logout_data = {
            'refresh_token': refresh_token
        }

        response = self.client.post(
            '/api/v1/auth/auth/logout/',
            logout_data,
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)


class RoleBasedAccessControlIntegrationTest(TestCase):
    """Integration tests for role-based access control"""

    def setUp(self):
        """Set up test environment"""
        self.client = APIClient()

        # Create test users
        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            role='admin'
        )

        self.manager_user = User.objects.create_user(
            email='manager@test.com',
            password='testpass123',
            role='manager'
        )

        self.sales_user = User.objects.create_user(
            email='sales@test.com',
            password='testpass123',
            role='sales'
        )

        self.support_user = User.objects.create_user(
            email='support@test.com',
            password='testpass123',
            role='support'
        )

    def _authenticate_user(self, user):
        """Helper method to authenticate user"""
        login_data = {
            'email': user.email,
            'password': 'testpass123'
        }

        login_response = self.client.post(
            '/api/v1/auth/auth/login/',
            login_data,
            format='json'
        )

        token = login_response.data['access_token']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def test_admin_user_can_access_all_endpoints(self):
        """Test that admin users can access all endpoints"""
        self._authenticate_user(self.admin_user)

        # Test user management endpoints
        response = self.client.get('/api/v1/auth/users/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.post('/api/v1/auth/users/', {
            'email': 'newadmin@test.com',
            'password': 'testpass123',
            'first_name': 'New',
            'last_name': 'Admin',
            'role': 'sales'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_manager_user_can_access_limited_endpoints(self):
        """Test that manager users have limited access"""
        self._authenticate_user(self.manager_user)

        # Test user management (should be allowed for managers)
        response = self.client.get('/api/v1/auth/users/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Test creating users (should be allowed for managers)
        response = self.client.post('/api/v1/auth/users/', {
            'email': 'newsales@test.com',
            'password': 'testpass123',
            'first_name': 'New',
            'last_name': 'Sales',
            'role': 'sales'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_sales_user_has_restricted_access(self):
        """Test that sales users have restricted access"""
        self._authenticate_user(self.sales_user)

        # Test user management (should be limited to own user)
        response = self.client.get('/api/v1/auth/users/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Should only see their own user
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['email'], 'sales@test.com')

        # Test creating other users (should be denied)
        response = self.client.post('/api/v1/auth/users/', {
            'email': 'unauthorized@test.com',
            'password': 'testpass123',
            'first_name': 'Unauthorized',
            'last_name': 'User',
            'role': 'sales'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_support_user_has_minimal_access(self):
        """Test that support users have minimal access"""
        self._authenticate_user(self.support_user)

        # Test user management (should be limited to own user)
        response = self.client.get('/api/v1/auth/users/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Should only see their own user
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['email'], 'support@test.com')

    def test_user_cannot_access_other_user_profile(self):
        """Test that users cannot access other user profiles"""
        self._authenticate_user(self.sales_user)

        # Try to access admin user profile
        response = self.client.get(f'/api/v1/auth/users/{self.admin_user.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Try to access own profile
        response = self.client.get(f'/api/v1/auth/users/{self.sales_user.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_admin_can_access_any_user_profile(self):
        """Test that admin can access any user profile"""
        self._authenticate_user(self.admin_user)

        # Access sales user profile
        response = self.client.get(f'/api/v1/auth/users/{self.sales_user.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Access manager user profile
        response = self.client.get(f'/api/v1/auth/users/{self.manager_user.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class PermissionClassIntegrationTest(TestCase):
    """Integration tests for custom permission classes"""

    def setUp(self):
        """Set up test environment"""
        self.client = APIClient()

        # Create test users
        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            role='admin'
        )

        self.manager_user = User.objects.create_user(
            email='manager@test.com',
            password='testpass123',
            role='manager'
        )

        self.sales_user = User.objects.create_user(
            email='sales@test.com',
            password='testpass123',
            role='sales'
        )

    def _authenticate_user(self, user):
        """Helper method to authenticate user"""
        login_data = {
            'email': user.email,
            'password': 'testpass123'
        }

        login_response = self.client.post(
            '/api/v1/auth/auth/login/',
            login_data,
            format='json'
        )

        token = login_response.data['access_token']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def test_contact_permission_class_integration(self):
        """Test ContactPermission class integration"""
        self._authenticate_user(self.sales_user)

        # Test GET request (should be allowed for all authenticated users)
        response = self.client.get('/api/v1/contacts/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Test POST request (should be allowed for sales users)
        response = self.client.post('/api/v1/contacts/', {
            'first_name': 'Test',
            'last_name': 'Contact',
            'email': 'test@contact.com'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_deal_permission_class_integration(self):
        """Test DealPermission class integration"""
        self._authenticate_user(self.sales_user)

        # Test GET request (should be allowed for all authenticated users)
        response = self.client.get('/api/v1/deals/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Test POST request (should be allowed for sales users)
        response = self.client.post('/api/v1/deals/', {
            'title': 'Test Deal',
            'value': 10000,
            'stage': 'lead'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_activity_permission_class_integration(self):
        """Test ActivityPermission class integration"""
        self._authenticate_user(self.sales_user)

        # Test GET request (should be allowed for all authenticated users)
        response = self.client.get('/api/v1/activities/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Test POST request (should be allowed for all authenticated users)
        response = self.client.post('/api/v1/activities/', {
            'title': 'Test Activity',
            'activity_type': 'call',
            'due_date': '2024-12-31T10:00:00Z'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class ErrorHandlingIntegrationTest(TestCase):
    """Integration tests for error handling"""

    def setUp(self):
        """Set up test environment"""
        self.client = APIClient()

        self.sales_user = User.objects.create_user(
            email='sales@test.com',
            password='testpass123',
            role='sales'
        )

    def test_401_error_response_format(self):
        """Test 401 error response format"""
        response = self.client.get('/api/v1/contacts/')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_403_error_response_format(self):
        """Test 403 error response format"""
        # Authenticate as sales user
        login_data = {
            'email': 'sales@test.com',
            'password': 'testpass123'
        }

        login_response = self.client.post(
            '/api/v1/auth/auth/login/',
            login_data,
            format='json'
        )

        token = login_response.data['access_token']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        # Try to perform admin operation
        response = self.client.post('/api/v1/auth/users/', {
            'email': 'unauthorized@test.com',
            'password': 'testpass123',
            'first_name': 'Unauthorized',
            'last_name': 'User',
            'role': 'sales'
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_404_error_response_format(self):
        """Test 404 error response format"""
        # Authenticate user
        login_data = {
            'email': 'sales@test.com',
            'password': 'testpass123'
        }

        login_response = self.client.post(
            '/api/v1/auth/auth/login/',
            login_data,
            format='json'
        )

        token = login_response.data['access_token']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        # Try to access non-existent user
        response = self.client.get('/api/v1/auth/users/99999/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class SecurityHeadersIntegrationTest(TestCase):
    """Integration tests for security headers"""

    def setUp(self):
        """Set up test environment"""
        self.client = APIClient()

    def test_security_headers_in_responses(self):
        """Test that security headers are present in responses"""
        response = self.client.get('/api/v1/auth/auth/login/')

        # Check for security headers
        self.assertIn('X-Content-Type-Options', response)
        self.assertEqual(response['X-Content-Type-Options'], 'nosniff')

        self.assertIn('X-Frame-Options', response)
        self.assertEqual(response['X-Frame-Options'], 'DENY')

        self.assertIn('X-XSS-Protection', response)
        self.assertEqual(response['X-XSS-Protection'], '1; mode=block')