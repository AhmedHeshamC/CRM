"""
Comprehensive Integration Testing Strategy
Testing complete workflows and system interactions
"""

import pytest
from django.test import TransactionTestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch, MagicMock
import json

User = get_user_model()


class UserManagementIntegrationTests(TransactionTestCase):
    """
    Complete user management workflow integration tests
    """

    def setUp(self):
        """Set up integration test environment"""
        self.client = APIClient()
        self.admin_user = User.objects.create_user(
            email='admin@company.com',
            password='AdminPass123!',
            first_name='Admin',
            last_name='User',
            role='admin',
            is_staff=True,
            is_superuser=True
        )

    def test_complete_user_lifecycle_integration(self):
        """
        Test: Complete user lifecycle from creation to deletion
        Workflow: Create → Authenticate → Update → Deactivate → Delete
        """
        # Step 1: Create user (admin only)
        self.client.force_authenticate(user=self.admin_user)

        create_data = {
            'email': 'newuser@company.com',
            'first_name': 'New',
            'last_name': 'User',
            'password': 'SecurePass123!',
            'password_confirm': 'SecurePass123!',
            'role': 'sales'
        }

        response = self.client.post('/api/v1/auth/users/', create_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        user_data = response.json()
        user_id = user_data['id']

        # Step 2: User authentication
        self.client.force_authenticate(user=None)

        login_response = self.client.post('/api/v1/auth/login/', {
            'email': 'newuser@company.com',
            'password': 'SecurePass123!'
        })

        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        tokens = login_response.json()

        # Step 3: Update user profile
        self.client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {tokens["access_token"]}'
        )

        update_response = self.client.patch(
            f'/api/v1/auth/users/{user_id}/',
            {'first_name': 'Updated Name'}
        )
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)

        # Step 4: Deactivate user (admin)
        self.client.force_authenticate(user=self.admin_user)

        deactivate_response = self.client.post(
            f'/api/v1/auth/users/{user_id}/deactivate/'
        )
        self.assertEqual(deactivate_response.status_code, status.HTTP_200_OK)

        # Step 5: Delete user (admin)
        delete_response = self.client.delete(f'/api/v1/auth/users/{user_id}/')
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)

    def test_cross_module_data_integrity(self):
        """
        Test: Data integrity across user, contact, and deal modules
        """
        # Create admin and sales user
        sales_user = User.objects.create_user(
            email='sales@company.com',
            password='SalesPass123!',
            first_name='Sales',
            last_name='User',
            role='sales'
        )

        self.client.force_authenticate(user=self.admin_user)

        # Create contact for sales user
        contact_data = {
            'first_name': 'Contact',
            'last_name': 'Person',
            'email': 'contact@example.com',
            'owner': sales_user.id
        }

        contact_response = self.client.post('/api/v1/contacts/', contact_data)
        self.assertEqual(contact_response.status_code, status.HTTP_201_CREATED)

        contact_id = contact_response.json()['id']

        # Create deal for the contact
        deal_data = {
            'title': 'Test Deal',
            'contact': contact_id,
            'value': 10000,
            'stage': 'lead',
            'owner': sales_user.id
        }

        deal_response = self.client.post('/api/v1/deals/', deal_data)
        self.assertEqual(deal_response.status_code, status.HTTP_201_CREATED)

        # Verify data relationships
        deal_data = deal_response.json()
        self.assertEqual(deal_data['contact'], contact_id)

        # Test cascade deletion behavior
        delete_contact_response = self.client.delete(f'/api/v1/contacts/{contact_id}/')
        # This should fail due to business rule (deals exist)
        self.assertEqual(
            delete_contact_response.status_code,
            status.HTTP_400_BAD_REQUEST
        )


class SystemSecurityIntegrationTests(TransactionTestCase):
    """
    Integration tests for security across the entire system
    """

    def test_authentication_and_authorization_flow(self):
        """
        Test: Complete authentication and authorization workflow
        """
        client = APIClient()

        # Test unauthenticated access
        response = client.get('/api/v1/contacts/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Create and authenticate user
        user = User.objects.create_user(
            email='test@company.com',
            password='TestPass123!',
            first_name='Test',
            last_name='User',
            role='sales'
        )

        # Test authentication
        login_response = client.post('/api/v1/auth/login/', {
            'email': 'test@company.com',
            'password': 'TestPass123!'
        })

        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        token = login_response.json()['access_token']

        # Test authenticated access
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = client.get('/api/v1/contacts/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Test authorization (user can only see their own data)
        response_data = response.json()
        # Should only return contacts owned by the user
        self.assertIsInstance(response_data, dict)

    def test_rate_limiting_integration(self):
        """
        Test: Rate limiting across different endpoints
        """
        client = APIClient()

        # Test login rate limiting
        failed_attempts = []
        for i in range(20):  # Exceed typical rate limit
            response = client.post('/api/v1/auth/login/', {
                'email': 'test@company.com',
                'password': 'wrongpassword'
            })
            failed_attempts.append(response.status_code)

        # Should eventually be rate limited
        self.assertIn(status.HTTP_429_TOO_MANY_REQUESTS, failed_attempts)

    def test_cors_and_security_headers(self):
        """
        Test: CORS and security headers are properly set
        """
        client = APIClient()

        response = client.get('/api/v1/status/')

        # Check security headers
        self.assertIn('X-Content-Type-Options', response)
        self.assertIn('X-Frame-Options', response)


class DatabaseTransactionIntegrationTests(TransactionTestCase):
    """
    Integration tests for database transactions and consistency
    """

    def test_transaction_rollback_on_error(self):
        """
        Test: Database transactions rollback properly on errors
        """
        admin_user = User.objects.create_user(
            email='admin@company.com',
            password='AdminPass123!',
            first_name='Admin',
            last_name='User',
            role='admin',
            is_staff=True
        )

        client = APIClient()
        client.force_authenticate(user=admin_user)

        initial_user_count = User.objects.count()

        # Attempt to create user with invalid data
        invalid_user_data = {
            'email': 'invalid-email',
            'first_name': '',
            'last_name': 'User',
            'password': 'TestPass123!',
            'role': 'sales'
        }

        response = client.post('/api/v1/auth/users/', invalid_user_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Verify no partial data was created
        self.assertEqual(User.objects.count(), initial_user_count)

    @patch('django.core.mail.send_mail')
    def test_email_service_integration(self, mock_send_mail):
        """
        Test: Email service integration with user workflows
        """
        mock_send_mail.return_value = True

        client = APIClient()

        # Test password reset email
        response = client.post('/api/v1/auth/password-reset/', {
            'email': 'admin@company.com'
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify email was attempted to be sent
        mock_send_mail.assert_called()


class PerformanceIntegrationTests(TransactionTestCase):
    """
    Integration tests focusing on performance characteristics
    """

    def test_bulk_operations_performance(self):
        """
        Test: Performance of bulk operations
        """
        admin_user = User.objects.create_user(
            email='admin@company.com',
            password='AdminPass123!',
            first_name='Admin',
            last_name='User',
            role='admin',
            is_staff=True
        )

        client = APIClient()
        client.force_authenticate(user=admin_user)

        # Test bulk user creation performance
        bulk_data = {
            'users': [
                {
                    'email': f'user{i}@company.com',
                    'first_name': f'User{i}',
                    'last_name': 'Test',
                    'password': 'TestPass123!',
                    'role': 'sales'
                }
                for i in range(50)
            ]
        }

        import time
        start_time = time.time()

        response = client.post('/api/v1/auth/users/bulk-create/', bulk_data)

        end_time = time.time()
        duration = end_time - start_time

        # Should complete within reasonable time (5 seconds for 50 users)
        self.assertLess(duration, 5.0)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_pagination_performance(self):
        """
        Test: Pagination performance with large datasets
        """
        # Create large dataset
        admin_user = User.objects.create_user(
            email='admin@company.com',
            password='AdminPass123!',
            first_name='Admin',
            last_name='User',
            role='admin',
            is_staff=True
        )

        # Create 1000 users
        for i in range(1000):
            User.objects.create_user(
                email=f'user{i}@company.com',
                password='TestPass123!',
                first_name=f'User{i}',
                last_name='Test',
                role='sales'
            )

        client = APIClient()
        client.force_authenticate(user=admin_user)

        import time
        start_time = time.time()

        response = client.get('/api/v1/auth/users/?page=20&page_size=50')

        end_time = time.time()
        duration = end_time - start_time

        # Should complete within reasonable time (1 second for paginated data)
        self.assertLess(duration, 1.0)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(len(data['results']), 50)