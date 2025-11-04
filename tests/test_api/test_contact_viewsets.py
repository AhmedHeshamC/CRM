"""
Contact ViewSet Tests - TDD Approach
Testing comprehensive CRUD operations and business logic
Following SOLID principles and comprehensive test coverage
"""

import pytest
from decimal import Decimal
from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from rest_framework.exceptions import NotAuthenticated, PermissionDenied

from crm.apps.contacts.models import Contact, ContactInteraction
from crm.apps.contacts.serializers import ContactSerializer, ContactDetailSerializer
from crm.apps.contacts.viewsets import ContactViewSet

User = get_user_model()


class ContactViewSetTestCase(APITestCase):
    """Base test case for Contact ViewSet tests"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            email='testuser@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )

        self.admin_user = User.objects.create_user(
            email='admin@example.com',
            password='adminpass123',
            first_name='Admin',
            last_name='User',
            role='admin'
        )

        self.contact_data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john.doe@example.com',
            'phone': '+1-555-123-4567',
            'company': 'Acme Corp',
            'title': 'CEO',
            'website': 'https://acme.com',
            'address': '123 Main St',
            'city': 'New York',
            'state': 'NY',
            'country': 'USA',
            'postal_code': '10001',
            'tags': ['vip', 'prospect'],
            'lead_source': 'Website'
        }

        self.contact = Contact.objects.create(
            owner=self.user,
            **self.contact_data
        )

        # URL patterns
        self.list_url = reverse('contact-list')
        self.detail_url = reverse('contact-detail', kwargs={'pk': self.contact.id})


class ContactViewSetAuthenticationTests(ContactViewSetTestCase):
    """Test authentication requirements for Contact ViewSet"""

    def test_unauthenticated_access_denied(self):
        """Test that unauthenticated users cannot access contact endpoints"""
        client = APIClient()

        # Test list access
        response = client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Test detail access
        response = client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Test create access
        response = client.post(self.list_url, self.contact_data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_access_allowed(self):
        """Test that authenticated users can access contact endpoints"""
        client = APIClient()
        client.force_authenticate(user=self.user)

        # Test list access
        response = client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Test detail access
        response = client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class ContactViewSetListTests(ContactViewSetTestCase):
    """Test Contact ViewSet list operations"""

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(user=self.user)

    def test_list_contacts_returns_user_contacts_only(self):
        """Test list endpoint returns only contacts owned by the user"""
        # Create contacts for different users
        other_user = User.objects.create_user(
            email='other@example.com',
            password='otherpass123',
            first_name='Other',
            last_name='User'
        )

        Contact.objects.create(
            owner=other_user,
            first_name='Other',
            last_name='Contact',
            email='other.contact@example.com'
        )

        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(len(data['results']), 1)
        self.assertEqual(data['results'][0]['id'], self.contact.id)

    def test_list_contacts_with_pagination(self):
        """Test list endpoint respects pagination"""
        # Create additional contacts
        for i in range(25):
            Contact.objects.create(
                owner=self.user,
                first_name=f'Contact {i}',
                last_name=f'Test {i}',
                email=f'contact{i}@example.com'
            )

        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertIn('results', data)
        self.assertIn('count', data)
        self.assertIn('next', data)
        self.assertIn('previous', data)
        self.assertEqual(len(data['results']), 20)  # Default page size

    def test_list_contacts_with_search(self):
        """Test list endpoint with search functionality"""
        # Create additional contacts
        Contact.objects.create(
            owner=self.user,
            first_name='Jane',
            last_name='Smith',
            email='jane.smith@example.com',
            company='Test Corp'
        )

        # Search by first name
        response = self.client.get(f'{self.list_url}?search=jane')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(len(data['results']), 1)
        self.assertEqual(data['results'][0]['first_name'], 'Jane')

        # Search by company
        response = self.client.get(f'{self.list_url}?search=acme')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(len(data['results']), 1)
        self.assertEqual(data['results'][0]['company'], 'Acme Corp')

    def test_list_contacts_with_filtering(self):
        """Test list endpoint with filtering"""
        # Create contacts with different statuses
        inactive_contact = Contact.objects.create(
            owner=self.user,
            first_name='Inactive',
            last_name='Contact',
            email='inactive@example.com',
            is_active=False
        )

        # Filter by active status
        response = self.client.get(f'{self.list_url}?is_active=true')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        contact_ids = [contact['id'] for contact in data['results']]
        self.assertNotIn(inactive_contact.id, contact_ids)

        # Filter by company
        response = self.client.get(f'{self.list_url}?company=Acme Corp')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(len(data['results']), 1)
        self.assertEqual(data['results'][0]['company'], 'Acme Corp')

    def test_list_contacts_with_ordering(self):
        """Test list endpoint with ordering"""
        # Create contacts with different names
        Contact.objects.create(
            owner=self.user,
            first_name='Alice',
            last_name='Zimmerman',
            email='alice@example.com'
        )
        Contact.objects.create(
            owner=self.user,
            first_name='Bob',
            last_name='Anderson',
            email='bob@example.com'
        )

        # Order by first name
        response = self.client.get(f'{self.list_url}?ordering=first_name')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        names = [contact['first_name'] for contact in data['results']]
        self.assertEqual(names, sorted(names))

        # Order by last name descending
        response = self.client.get(f'{self.list_url}?ordering=-last_name')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        names = [contact['last_name'] for contact in data['results']]
        self.assertEqual(names, sorted(names, reverse=True))

    def test_list_contacts_serializer_selection(self):
        """Test appropriate serializer is used for list view"""
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        contact = data['results'][0]

        # Should include basic fields
        self.assertIn('id', contact)
        self.assertIn('first_name', contact)
        self.assertIn('email', contact)

        # Should not include verbose fields for list view
        self.assertNotIn('description', contact)
        self.assertNotIn('owner_details', contact)


class ContactViewSetCreateTests(ContactViewSetTestCase):
    """Test Contact ViewSet create operations"""

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(user=self.user)

    def test_create_contact_valid_data(self):
        """Test creating contact with valid data"""
        new_contact_data = {
            'first_name': 'Jane',
            'last_name': 'Smith',
            'email': 'jane.smith@example.com',
            'company': 'Tech Corp',
            'tags': ['new', 'lead']
        }

        response = self.client.post(self.list_url, new_contact_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        data = response.json()
        self.assertEqual(data['first_name'], 'Jane')
        self.assertEqual(data['last_name'], 'Smith')
        self.assertEqual(data['email'], 'jane.smith@example.com')
        self.assertEqual(data['company'], 'Tech Corp')
        self.assertEqual(data['tags'], ['new', 'lead'])
        self.assertTrue(data['is_active'])

        # Verify contact was created in database
        contact = Contact.objects.get(id=data['id'])
        self.assertEqual(contact.owner, self.user)

    def test_create_contact_invalid_data(self):
        """Test creating contact with invalid data"""
        invalid_data = {
            'first_name': 'Jane',
            # Missing last_name, email
            'email': 'invalid-email'
        }

        response = self.client.post(self.list_url, invalid_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        data = response.json()
        self.assertIn('last_name', data)
        self.assertIn('email', data)

    def test_create_contact_duplicate_email(self):
        """Test creating contact with duplicate email"""
        duplicate_data = self.contact_data.copy()
        duplicate_data['first_name'] = 'Jane'  # Different name, same email

        response = self.client.post(self.list_url, duplicate_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        data = response.json()
        self.assertIn('email', data)

    def test_create_contact_sanitizes_data(self):
        """Test create endpoint sanitizes input data"""
        new_contact_data = {
            'first_name': '  Jane  ',
            'last_name': '  Smith  ',
            'email': '  JANE.SMITH@EXAMPLE.COM  ',
            'company': '  Tech Corp  ',
            'tags': ['  vip  ', '  prospect  ', '']
        }

        response = self.client.post(self.list_url, new_contact_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        data = response.json()
        self.assertEqual(data['first_name'], 'Jane')
        self.assertEqual(data['last_name'], 'Smith')
        self.assertEqual(data['email'], 'jane.smith@example.com')
        self.assertEqual(data['company'], 'Tech Corp')
        self.assertEqual(data['tags'], ['vip', 'prospect'])

    def test_create_contact_owner_assignment(self):
        """Test contact owner is automatically set to current user"""
        new_contact_data = {
            'first_name': 'Jane',
            'last_name': 'Smith',
            'email': 'jane.smith@example.com'
        }

        response = self.client.post(self.list_url, new_contact_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        data = response.json()
        contact = Contact.objects.get(id=data['id'])
        self.assertEqual(contact.owner, self.user)


class ContactViewSetRetrieveTests(ContactViewSetTestCase):
    """Test Contact ViewSet retrieve operations"""

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(user=self.user)

    def test_retrieve_own_contact(self):
        """Test retrieving own contact"""
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(data['id'], self.contact.id)
        self.assertEqual(data['first_name'], 'John')
        self.assertEqual(data['last_name'], 'Doe')

    def test_retrieve_other_user_contact_denied(self):
        """Test retrieving other user's contact is denied"""
        other_user = User.objects.create_user(
            email='other@example.com',
            password='otherpass123',
            first_name='Other',
            last_name='User'
        )

        other_contact = Contact.objects.create(
            owner=other_user,
            first_name='Other',
            last_name='Contact',
            email='other.contact@example.com'
        )

        other_detail_url = reverse('contact-detail', kwargs={'pk': other_contact.id})
        response = self.client.get(other_detail_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_admin_can_access_any_contact(self):
        """Test admin can access any contact"""
        other_user = User.objects.create_user(
            email='other@example.com',
            password='otherpass123',
            first_name='Other',
            last_name='User'
        )

        other_contact = Contact.objects.create(
            owner=other_user,
            first_name='Other',
            last_name='Contact',
            email='other.contact@example.com'
        )

        admin_client = APIClient()
        admin_client.force_authenticate(user=self.admin_user)

        other_detail_url = reverse('contact-detail', kwargs={'pk': other_contact.id})
        response = admin_client.get(other_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(data['id'], other_contact.id)

    def test_retrieve_nonexistent_contact(self):
        """Test retrieving non-existent contact returns 404"""
        fake_url = reverse('contact-detail', kwargs={'pk': 99999})
        response = self.client.get(fake_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_uses_detail_serializer(self):
        """Test retrieve endpoint uses detail serializer"""
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        # Should include detail-specific fields
        self.assertIn('deals_count', data)
        self.assertIn('total_deal_value', data)
        self.assertIn('owner_details', data)
        self.assertIn('full_name', data)


class ContactViewSetUpdateTests(ContactViewSetTestCase):
    """Test Contact ViewSet update operations"""

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(user=self.user)

    def test_update_own_contact(self):
        """Test updating own contact"""
        update_data = {
            'first_name': 'Johnathan',
            'company': 'Updated Corp',
            'tags': ['updated', 'vip']
        }

        response = self.client.patch(self.detail_url, update_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(data['first_name'], 'Johnathan')
        self.assertEqual(data['company'], 'Updated Corp')
        self.assertEqual(data['tags'], ['updated', 'vip'])
        self.assertEqual(data['last_name'], 'Doe')  # Unchanged

    def test_update_other_user_contact_denied(self):
        """Test updating other user's contact is denied"""
        other_user = User.objects.create_user(
            email='other@example.com',
            password='otherpass123',
            first_name='Other',
            last_name='User'
        )

        other_contact = Contact.objects.create(
            owner=other_user,
            first_name='Other',
            last_name='Contact',
            email='other.contact@example.com'
        )

        other_detail_url = reverse('contact-detail', kwargs={'pk': other_contact.id})
        update_data = {'first_name': 'Updated'}

        response = self.client.patch(other_detail_url, update_data)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_contact_invalid_data(self):
        """Test updating contact with invalid data"""
        update_data = {
            'email': 'invalid-email',
            'website': 'invalid-url'
        }

        response = self.client.patch(self.detail_url, update_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        data = response.json()
        self.assertIn('email', data)
        self.assertIn('website', data)

    def test_update_contact_sanitizes_data(self):
        """Test update endpoint sanitizes input data"""
        update_data = {
            'first_name': '  Johnathan  ',
            'company': '  Updated Corp  ',
            'tags': ['  updated  ', '  sanitized  ', '']
        }

        response = self.client.patch(self.detail_url, update_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(data['first_name'], 'Johnathan')
        self.assertEqual(data['company'], 'Updated Corp')
        self.assertEqual(data['tags'], ['updated', 'sanitized'])

    def test_admin_can_update_any_contact(self):
        """Test admin can update any contact"""
        other_user = User.objects.create_user(
            email='other@example.com',
            password='otherpass123',
            first_name='Other',
            last_name='User'
        )

        other_contact = Contact.objects.create(
            owner=other_user,
            first_name='Other',
            last_name='Contact',
            email='other.contact@example.com'
        )

        admin_client = APIClient()
        admin_client.force_authenticate(user=self.admin_user)

        other_detail_url = reverse('contact-detail', kwargs={'pk': other_contact.id})
        update_data = {'first_name': 'AdminUpdated'}

        response = admin_client.patch(other_detail_url, update_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(data['first_name'], 'AdminUpdated')


class ContactViewSetDeleteTests(ContactViewSetTestCase):
    """Test Contact ViewSet delete operations"""

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(user=self.user)

    def test_soft_delete_own_contact(self):
        """Test soft deleting own contact"""
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Contact should be soft deleted
        self.contact.refresh_from_db()
        self.assertTrue(self.contact.is_deleted)
        self.assertIsNotNone(self.contact.deleted_at)

        # Should not appear in normal list
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        contact_ids = [contact['id'] for contact in data['results']]
        self.assertNotIn(self.contact.id, contact_ids)

    def test_delete_other_user_contact_denied(self):
        """Test deleting other user's contact is denied"""
        other_user = User.objects.create_user(
            email='other@example.com',
            password='otherpass123',
            first_name='Other',
            last_name='User'
        )

        other_contact = Contact.objects.create(
            owner=other_user,
            first_name='Other',
            last_name='Contact',
            email='other.contact@example.com'
        )

        other_detail_url = reverse('contact-detail', kwargs={'pk': other_contact.id})
        response = self.client.delete(other_detail_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_admin_can_delete_any_contact(self):
        """Test admin can delete any contact"""
        other_user = User.objects.create_user(
            email='other@example.com',
            password='otherpass123',
            first_name='Other',
            last_name='User'
        )

        other_contact = Contact.objects.create(
            owner=other_user,
            first_name='Other',
            last_name='Contact',
            email='other.contact@example.com'
        )

        admin_client = APIClient()
        admin_client.force_authenticate(user=self.admin_user)

        other_detail_url = reverse('contact-detail', kwargs={'pk': other_contact.id})
        response = admin_client.delete(other_detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        other_contact.refresh_from_db()
        self.assertTrue(other_contact.is_deleted)


class ContactViewSetCustomActionsTests(ContactViewSetTestCase):
    """Test Contact ViewSet custom actions"""

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(user=self.user)

    def test_restore_contact_action(self):
        """Test restore contact action"""
        # Soft delete contact first
        self.contact.is_deleted = True
        self.contact.deleted_at = timezone.now()
        self.contact.save()

        restore_url = reverse('contact-restore', kwargs={'pk': self.contact.id})
        response = self.client.post(restore_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertIn('message', data)
        self.assertEqual(data['message'], 'Contact restored successfully')

        # Contact should be restored
        self.contact.refresh_from_db()
        self.assertFalse(self.contact.is_deleted)
        self.assertIsNone(self.contact.deleted_at)

    def test_restore_non_deleted_contact(self):
        """Test restoring non-deleted contact"""
        restore_url = reverse('contact-restore', kwargs={'pk': self.contact.id})
        response = self.client.post(restore_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        data = response.json()
        self.assertIn('error', data)

    def test_get_contact_deals_action(self):
        """Test get contact deals action"""
        from crm.apps.deals.models import Deal
        Deal.objects.create(
            title='Test Deal',
            value=Decimal('1000.00'),
            contact=self.contact,
            owner=self.user
        )

        deals_url = reverse('contact-deals', kwargs={'pk': self.contact.id})
        response = self.client.get(deals_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['title'], 'Test Deal')

    def test_update_tags_action(self):
        """Test update tags action"""
        update_tags_url = reverse('contact-update-tags', kwargs={'pk': self.contact.id})
        tags_data = {'tags': ['updated', 'vip', 'customer']}

        response = self.client.post(update_tags_url, tags_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(data['tags'], ['updated', 'vip', 'customer'])

        # Verify tags were updated
        self.contact.refresh_from_db()
        self.assertEqual(self.contact.tags, ['updated', 'vip', 'customer'])

    def test_bulk_operations_action(self):
        """Test bulk operations action"""
        # Create additional contacts
        contact2 = Contact.objects.create(
            owner=self.user,
            first_name='Jane',
            last_name='Smith',
            email='jane.smith@example.com'
        )

        bulk_url = reverse('contact-bulk-operations')
        bulk_data = {
            'contact_ids': [self.contact.id, contact2.id],
            'operation': 'deactivate'
        }

        response = self.client.post(bulk_url, bulk_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertIn('message', data)
        self.assertEqual(data['updated_count'], 2)

        # Verify contacts were deactivated
        self.contact.refresh_from_db()
        contact2.refresh_from_db()
        self.assertFalse(self.contact.is_active)
        self.assertFalse(contact2.is_active)

    def test_bulk_operations_invalid_operation(self):
        """Test bulk operations with invalid operation"""
        bulk_url = reverse('contact-bulk-operations')
        bulk_data = {
            'contact_ids': [self.contact.id],
            'operation': 'invalid_operation'
        }

        response = self.client.post(bulk_url, bulk_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_contact_statistics_action(self):
        """Test contact statistics action"""
        stats_url = reverse('contact-statistics')
        response = self.client.get(stats_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertIn('total_contacts', data)
        self.assertIn('active_contacts', data)
        self.assertIn('recent_contacts', data)


class ContactViewSetPermissionTests(ContactViewSetTestCase):
    """Test Contact ViewSet permission logic"""

    def test_manager_can_access_team_contacts(self):
        """Test manager can access team member contacts"""
        manager_user = User.objects.create_user(
            email='manager@example.com',
            password='managerpass123',
            first_name='Manager',
            last_name='User',
            role='manager'
        )

        manager_client = APIClient()
        manager_client.force_authenticate(user=manager_user)

        response = manager_client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Manager should see their own contacts
        data = response.json()
        self.assertEqual(len(data['results']), 0)  # Manager has no contacts

    def test_sales_user_access_restricted(self):
        """Test sales user access is restricted to their contacts"""
        sales_client = APIClient()
        sales_client.force_authenticate(user=self.user)

        response = sales_client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Should only see their own contacts
        data = response.json()
        self.assertEqual(len(data['results']), 1)
        self.assertEqual(data['results'][0]['id'], self.contact.id)


class ContactViewSetIntegrationTests(ContactViewSetTestCase):
    """Integration tests for Contact ViewSet"""

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(user=self.user)

    def test_full_crud_workflow(self):
        """Test complete CRUD workflow"""
        # Create
        create_data = {
            'first_name': 'Workflow',
            'last_name': 'Test',
            'email': 'workflow@example.com',
            'company': 'Workflow Corp'
        }

        response = self.client.post(self.list_url, create_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        contact_data = response.json()
        contact_id = contact_data['id']

        # Retrieve
        detail_url = reverse('contact-detail', kwargs={'pk': contact_id})
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Update
        update_data = {'first_name': 'Updated', 'tags': ['workflow', 'test']}
        response = self.client.patch(detail_url, update_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Delete
        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Verify soft delete
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_error_handling_consistency(self):
        """Test consistent error handling across endpoints"""
        # Test with invalid data
        invalid_data = {'email': 'invalid-email'}

        # Create error
        response = self.client.post(self.list_url, invalid_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIsInstance(response.json(), dict)

        # Update error
        response = self.client.patch(self.detail_url, invalid_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIsInstance(response.json(), dict)

    def test_response_format_consistency(self):
        """Test consistent response format across endpoints"""
        # List response format
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        list_data = response.json()
        self.assertIn('results', list_data)
        self.assertIn('count', list_data)

        # Detail response format
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        detail_data = response.json()
        self.assertIsInstance(detail_data, dict)
        self.assertIn('id', detail_data)