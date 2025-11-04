"""
Contact Repository Tests - Test-Driven Development Approach
Following enterprise-grade testing standards with comprehensive coverage
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta

from crm.shared.repositories.contact_repository import ContactRepository
from crm.apps.contacts.models import Contact

User = get_user_model()


class ContactRepositoryTest(TestCase):
    """Test ContactRepository following TDD methodology"""

    def setUp(self):
        """Set up test data"""
        self.repository = ContactRepository()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        self.contact_data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john.doe@example.com',
            'company': 'Test Corp',
            'owner': self.user
        }

    def tearDown(self):
        """Clean up after tests"""
        cache.clear()

    def test_repository_initialization(self):
        """Test repository initialization"""
        # Assert
        self.assertEqual(self.repository.model, Contact)
        self.assertEqual(self.repository.cache_timeout, 300)
        self.assertEqual(self.repository.cache_prefix, 'contact_')

    def test_get_by_email_cache_hit(self):
        """Test getting contact by email with cache hit"""
        # Arrange
        mock_contact = Mock(spec=Contact)
        with patch('crm.shared.repositories.contact_repository.cache') as mock_cache:
            mock_cache.get.return_value = mock_contact

            # Act
            result = self.repository.get_by_email('john.doe@example.com')

            # Assert
            self.assertEqual(result, mock_contact)
            mock_cache.get.assert_called_once_with('contact_email_john.doe@example.com')

    def test_get_by_email_cache_miss(self):
        """Test getting contact by email with cache miss"""
        # Arrange
        mock_contact = Mock(spec=Contact)
        with patch('crm.shared.repositories.contact_repository.cache') as mock_cache:
            mock_cache.get.return_value = None
            with patch.object(Contact.objects, 'get') as mock_get:
                mock_get.return_value = mock_contact

                # Act
                result = self.repository.get_by_email('john.doe@example.com', use_cache=True)

                # Assert
                self.assertEqual(result, mock_contact)
                mock_get.assert_called_once_with(email__iexact='john.doe@example.com')
                mock_cache.set.assert_called_once_with(
                    'contact_email_john.doe@example.com', mock_contact, 300
                )

    def test_get_by_email_not_found(self):
        """Test getting contact by email when not found"""
        # Arrange
        with patch.object(Contact.objects, 'get') as mock_get:
            mock_get.side_effect = Contact.DoesNotExist()

            # Act
            result = self.repository.get_by_email('nonexistent@example.com')

            # Assert
            self.assertIsNone(result)

    def test_get_by_owner(self):
        """Test getting contacts by owner"""
        # Arrange
        mock_contacts = [Mock(spec=Contact), Mock(spec=Contact)]
        with patch('crm.shared.repositories.contact_repository.cache') as mock_cache:
            mock_cache.get.return_value = mock_contacts

            # Act
            result = self.repository.get_by_owner(self.user.id)

            # Assert
            self.assertEqual(result, mock_contacts)

    def test_search_contacts(self):
        """Test searching contacts"""
        # Arrange
        mock_contacts = [Mock(spec=Contact)]
        with patch('crm.shared.repositories.contact_repository.cache') as mock_cache:
            mock_cache.get.return_value = mock_contacts

            # Act
            result = self.repository.search_contacts('john', self.user.id)

            # Assert
            self.assertEqual(result, mock_contacts)
            mock_cache.get.assert_called_once_with('contact_search_john_' + str(self.user.id))

    def test_get_contacts_by_company(self):
        """Test getting contacts by company"""
        # Arrange
        mock_contacts = [Mock(spec=Contact)]
        with patch('crm.shared.repositories.contact_repository.cache') as mock_cache:
            mock_cache.get.return_value = mock_contacts

            # Act
            result = self.repository.get_contacts_by_company('Test Corp')

            # Assert
            self.assertEqual(result, mock_contacts)

    def test_get_contacts_with_tags(self):
        """Test getting contacts with specific tags"""
        # Arrange
        mock_contacts = [Mock(spec=Contact)]
        tags = ['vip', 'client']
        with patch('crm.shared.repositories.contact_repository.cache') as mock_cache:
            mock_cache.get.return_value = mock_contacts

            # Act
            result = self.repository.get_contacts_with_tags(tags, self.user.id)

            # Assert
            self.assertEqual(result, mock_contacts)

    def test_get_recent_contacts(self):
        """Test getting recent contacts"""
        # Arrange
        mock_contacts = [Mock(spec=Contact)]
        with patch('crm.shared.repositories.contact_repository.cache') as mock_cache:
            mock_cache.get.return_value = mock_contacts

            # Act
            result = self.repository.get_recent_contacts(30, self.user.id)

            # Assert
            self.assertEqual(result, mock_contacts)

    def test_get_contacts_by_lead_source(self):
        """Test getting contacts by lead source"""
        # Arrange
        mock_contacts = [Mock(spec=Contact)]
        with patch('crm.shared.repositories.contact_repository.cache') as mock_cache:
            mock_cache.get.return_value = mock_contacts

            # Act
            result = self.repository.get_contacts_by_lead_source('website')

            # Assert
            self.assertEqual(result, mock_contacts)

    def test_get_active_contacts(self):
        """Test getting active contacts"""
        # Arrange
        mock_contacts = [Mock(spec=Contact)]
        with patch('crm.shared.repositories.contact_repository.cache') as mock_cache:
            mock_cache.get.return_value = mock_contacts

            # Act
            result = self.repository.get_active_contacts(self.user.id)

            # Assert
            self.assertEqual(result, mock_contacts)

    def test_get_contact_statistics_with_cache(self):
        """Test getting contact statistics with cache"""
        # Arrange
        mock_stats = {
            'total_contacts': 100,
            'active_contacts': 80,
            'company_distribution': [],
        }
        with patch('crm.shared.repositories.contact_repository.cache') as mock_cache:
            mock_cache.get.return_value = mock_stats

            # Act
            result = self.repository.get_contact_statistics(self.user.id)

            # Assert
            self.assertEqual(result, mock_stats)
            mock_cache.get.assert_called_once_with('contact_statistics_' + str(self.user.id))

    def test_get_contact_statistics_without_cache(self):
        """Test getting contact statistics without cache"""
        # Arrange
        with patch('crm.shared.repositories.contact_repository.cache') as mock_cache:
            mock_cache.get.return_value = None
            with patch.object(Contact.objects, 'count') as mock_count:
                mock_count.return_value = 100
                with patch.object(Contact.objects, 'filter') as mock_filter:
                    mock_queryset = Mock()
                    mock_queryset.count.return_value = 80
                    mock_filter.return_value = mock_queryset

                    # Act
                    result = self.repository.get_contact_statistics(self.user.id)

                    # Assert
                    self.assertIn('total_contacts', result)
                    self.assertIn('active_contacts', result)
                    self.assertEqual(result['total_contacts'], 100)

    def test_bulk_create_contacts(self):
        """Test bulk creating contacts"""
        # Arrange
        contacts_data = [
            {
                'first_name': 'John',
                'last_name': 'Doe',
                'email': 'john@example.com',
                'owner': self.user
            },
            {
                'first_name': 'Jane',
                'last_name': 'Smith',
                'email': 'jane@example.com',
                'owner': self.user
            }
        ]
        mock_contacts = [Mock(spec=Contact), Mock(spec=Contact)]

        with patch.object(ContactRepository, 'bulk_create') as mock_bulk_create:
            mock_bulk_create.return_value = mock_contacts
            with patch.object(ContactRepository, '_invalidate_cache_pattern') as mock_invalidate:

                # Act
                result = self.repository.bulk_create_contacts(contacts_data)

                # Assert
                self.assertEqual(len(result), 2)
                mock_bulk_create.assert_called_once_with(contacts_data)
                # Check cache invalidation
                invalidate_calls = [call[0][0] for call in mock_invalidate.call_args_list]
                self.assertIn('statistics', invalidate_calls)
                self.assertIn('active', invalidate_calls)

    def test_update_contact_tags_success(self):
        """Test successful contact tags update"""
        # Arrange
        mock_contact = Mock(spec=Contact)
        mock_contact.id = 1
        mock_contact.tags = ['old_tag']
        mock_contact.uuid = 'test-uuid'

        with patch.object(Contact.objects, 'get') as mock_get:
            mock_get.return_value = mock_contact
            with patch.object(ContactRepository, '_invalidate_cache_pattern') as mock_invalidate:

                # Act
                result = self.repository.update_contact_tags(1, ['vip', 'client'])

                # Assert
                self.assertTrue(result)
                self.assertEqual(mock_contact.tags, ['vip', 'client'])
                mock_contact.save.assert_called_once()

    def test_update_contact_tags_not_found(self):
        """Test updating tags when contact doesn't exist"""
        # Arrange
        with patch.object(Contact.objects, 'get') as mock_get:
            mock_get.side_effect = Contact.DoesNotExist()

            # Act
            result = self.repository.update_contact_tags(999, ['vip'])

            # Assert
            self.assertFalse(result)

    def test_clear_contact_cache(self):
        """Test clearing contact-specific cache"""
        # Arrange
        mock_contact = Mock(spec=Contact)
        mock_contact.id = 1
        mock_contact.email = 'test@example.com'
        mock_contact.owner_id = self.user.id
        mock_contact.company = 'Test Corp'
        mock_contact.uuid = 'test-uuid'

        with patch('crm.shared.repositories.contact_repository.cache') as mock_cache:

            # Act
            self.repository.clear_contact_cache(mock_contact)

            # Assert
            expected_cache_keys = [
                'contact_id_1',
                'contact_email_test@example.com',
                f'contact_owner_{self.user.id}',
                'contact_company_Test Corp',
                'contact_active',
                'contact_statistics',
                'contact_uuid_test-uuid',
            ]

            # Check that delete was called for each expected cache key
            delete_calls = [call[0][0] for call in mock_cache.delete.call_args_list]
            for expected_key in expected_cache_keys:
                self.assertIn(expected_key, delete_calls)

    def test_email_case_insensitive_cache_key(self):
        """Test that email cache keys are case-insensitive"""
        # Arrange & Act
        cache_key1 = self.repository.get_cache_key("email_John.Doe@Example.COM")
        cache_key2 = self.repository.get_cache_key("email_john.doe@example.com")

        # Assert
        self.assertEqual(cache_key1, cache_key2)

    def test_soft_delete_functionality(self):
        """Test that ContactRepository supports soft delete"""
        # This tests that the repository inherits from SoftDeleteRepository
        # and has the soft delete functionality

        # Assert that the repository has soft delete methods
        self.assertTrue(hasattr(self.repository, 'soft_delete'))
        self.assertTrue(hasattr(self.repository, 'restore'))
        self.assertTrue(hasattr(self.repository, 'get_deleted'))


class ContactRepositoryIntegrationTest(TestCase):
    """Integration tests for ContactRepository with actual database"""

    def setUp(self):
        """Set up test data"""
        self.repository = ContactRepository()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )

    def tearDown(self):
        """Clean up after tests"""
        cache.clear()

    def test_create_and_retrieve_contact(self):
        """Test creating and retrieving a contact"""
        # Arrange & Act
        contact = Contact.objects.create(
            first_name='John',
            last_name='Doe',
            email='john.doe@example.com',
            owner=self.user
        )

        # Retrieve through repository
        retrieved = self.repository.get_by_id(contact.id)

        # Assert
        self.assertEqual(retrieved.first_name, 'John')
        self.assertEqual(retrieved.last_name, 'Doe')
        self.assertEqual(retrieved.email, 'john.doe@example.com')

    def test_get_by_email_integration(self):
        """Test getting contact by email with actual database"""
        # Arrange
        contact = Contact.objects.create(
            first_name='Jane',
            last_name='Smith',
            email='jane.smith@example.com',
            owner=self.user
        )

        # Act
        retrieved = self.repository.get_by_email('JANE.SMITH@example.com')

        # Assert
        self.assertEqual(retrieved.id, contact.id)
        self.assertEqual(retrieved.email, 'jane.smith@example.com')

    def test_search_contacts_integration(self):
        """Test searching contacts with actual database"""
        # Arrange
        Contact.objects.create(
            first_name='John',
            last_name='Doe',
            email='john@example.com',
            company='TechCorp',
            owner=self.user
        )
        Contact.objects.create(
            first_name='Jane',
            last_name='Johnson',
            email='jane@example.com',
            company='TechCorp',
            owner=self.user
        )

        # Act
        results = self.repository.search_contacts('TechCorp', self.user.id)

        # Assert
        self.assertEqual(len(results), 2)

    def test_get_active_contacts_integration(self):
        """Test getting active contacts with actual database"""
        # Arrange
        active_contact = Contact.objects.create(
            first_name='Active',
            last_name='User',
            email='active@example.com',
            is_active=True,
            owner=self.user
        )
        inactive_contact = Contact.objects.create(
            first_name='Inactive',
            last_name='User',
            email='inactive@example.com',
            is_active=False,
            owner=self.user
        )

        # Act
        active_contacts = self.repository.get_active_contacts(self.user.id)

        # Assert
        self.assertEqual(len(active_contacts), 1)
        self.assertEqual(active_contacts[0].id, active_contact.id)

    def test_soft_delete_integration(self):
        """Test soft delete functionality with actual database"""
        # Arrange
        contact = Contact.objects.create(
            first_name='To Delete',
            last_name='Contact',
            email='delete@example.com',
            owner=self.user
        )

        # Act
        success = self.repository.soft_delete(contact.id)

        # Retrieve normally (should not find it)
        not_found = self.repository.get_by_id(contact.id)

        # Retrieve including deleted
        all_objects = self.repository.all_objects()
        deleted_contact = all_objects.get(id=contact.id)

        # Assert
        self.assertTrue(success)
        self.assertIsNone(not_found)
        self.assertTrue(deleted_contact.is_deleted)
        self.assertIsNotNone(deleted_contact.deleted_at)

    def test_restore_soft_deleted_contact(self):
        """Test restoring a soft-deleted contact"""
        # Arrange
        contact = Contact.objects.create(
            first_name='To Restore',
            last_name='Contact',
            email='restore@example.com',
            owner=self.user
        )
        self.repository.soft_delete(contact.id)

        # Act
        success = self.repository.restore(contact.id)

        # Retrieve after restore
        restored_contact = self.repository.get_by_id(contact.id)

        # Assert
        self.assertTrue(success)
        self.assertIsNotNone(restored_contact)
        self.assertFalse(restored_contact.is_deleted)
        self.assertIsNone(restored_contact.deleted_at)