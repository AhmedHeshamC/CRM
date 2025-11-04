"""
Contact Model Tests - Test-Driven Development Approach
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

from crm.apps.contacts.models import Contact, ContactInteraction

User = get_user_model()


class ContactModelTest(TestCase):
    """Test Contact model following TDD methodology"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            email='test@example.com',
            first_name='John',
            last_name='Doe',
            password='testpass123'
        )

        self.contact_data = {
            'first_name': 'Jane',
            'last_name': 'Smith',
            'email': 'jane.smith@example.com',
            'phone': '+1234567890',
            'company': 'Tech Corp',
            'title': 'CEO',
            'owner': self.user
        }

    def test_contact_creation_with_minimum_fields(self):
        """Test creating contact with minimum required fields"""
        # Arrange & Act
        contact = Contact.objects.create(
            first_name='John',
            last_name='Doe',
            email='john@example.com',
            owner=self.user
        )

        # Assert
        self.assertEqual(contact.first_name, 'John')
        self.assertEqual(contact.last_name, 'Doe')
        self.assertEqual(contact.email, 'john@example.com')
        self.assertEqual(contact.owner, self.user)
        self.assertTrue(contact.is_active)
        self.assertFalse(contact.is_deleted)
        self.assertIsNotNone(contact.uuid)
        self.assertIsInstance(contact.uuid, uuid.UUID)

    def test_contact_creation_with_all_fields(self):
        """Test creating contact with all optional fields"""
        # Arrange & Act
        contact = Contact.objects.create(**self.contact_data)

        # Assert
        self.assertEqual(contact.phone, '+1234567890')
        self.assertEqual(contact.company, 'Tech Corp')
        self.assertEqual(contact.title, 'CEO')
        self.assertTrue(contact.is_active)

    def test_contact_str_representation(self):
        """Test string representation of contact"""
        # Arrange & Act
        contact = Contact.objects.create(**self.contact_data)

        # Assert
        self.assertEqual(str(contact), 'Jane Smith - Tech Corp')

    def test_contact_str_without_company(self):
        """Test string representation without company"""
        # Arrange & Act
        contact_data = self.contact_data.copy()
        del contact_data['company']
        contact = Contact.objects.create(**contact_data)

        # Assert
        self.assertEqual(str(contact), 'Jane Smith')

    def test_contact_full_name_property(self):
        """Test full_name property"""
        # Arrange & Act
        contact = Contact.objects.create(**self.contact_data)

        # Assert
        self.assertEqual(contact.full_name, 'Jane Smith')

    def test_contact_email_uniqueness_per_owner(self):
        """Test email uniqueness constraint per owner"""
        # Arrange & Act
        Contact.objects.create(**self.contact_data)

        # Assert
        with self.assertRaises(Exception):  # IntegrityError expected
            Contact.objects.create(**self.contact_data)

    def test_contact_email_uniqueness_different_owners(self):
        """Test same email allowed for different owners"""
        # Arrange
        other_user = User.objects.create_user(
            email='other@example.com',
            first_name='Other',
            last_name='User',
            password='testpass123'
        )

        contact_data = self.contact_data.copy()
        contact_data['owner'] = other_user

        # Act & Assert - Should not raise exception
        contact = Contact.objects.create(**contact_data)
        self.assertIsNotNone(contact)

    def test_contact_phone_validation(self):
        """Test phone number validation"""
        # Test valid phone numbers
        valid_phones = [
            '+1234567890',
            '(123) 456-7890',
            '123-456-7890',
            '123.456.7890',
            '123 456 7890'
        ]

        for phone in valid_phones:
            # Arrange & Act
            contact_data = self.contact_data.copy()
            contact_data['phone'] = phone
            contact_data['email'] = f'test_{phone}@example.com'

            # Assert - Should not raise exception
            contact = Contact.objects.create(**contact_data)
            self.assertEqual(contact.phone, phone)

        # Test invalid phone numbers
        invalid_phones = [
            '1234567',  # Too short
            'abc1234567',  # Contains letters
            '123-456-78901',  # Too long
        ]

        for phone in invalid_phones:
            # Arrange & Act
            contact = Contact(**self.contact_data)
            contact.phone = phone

            # Assert
            with self.assertRaises(ValidationError):
                contact.full_clean()

    def test_contact_tag_operations(self):
        """Test tag management methods"""
        # Arrange & Act
        contact = Contact.objects.create(**self.contact_data)

        # Test adding tags
        contact.add_tag('vip')
        contact.add_tag('prospect')
        contact.refresh_from_db()

        self.assertIn('vip', contact.tags)
        self.assertIn('prospect', contact.tags)

        # Test checking tags
        self.assertTrue(contact.has_tag('vip'))
        self.assertFalse(contact.has_tag('inactive'))

        # Test removing tags
        contact.remove_tag('prospect')
        contact.refresh_from_db()
        self.assertNotIn('prospect', contact.tags)
        self.assertIn('vip', contact.tags)

    def test_contact_soft_delete(self):
        """Test soft delete functionality"""
        # Arrange & Act
        contact = Contact.objects.create(**self.contact_data)
        contact_id = contact.id

        # Act
        contact.delete()

        # Assert
        contact.refresh_from_db()
        self.assertTrue(contact.is_deleted)
        self.assertIsNotNone(contact.deleted_at)

        # Should not appear in default queryset
        self.assertNotIn(contact, Contact.objects.all())

        # Should appear in all_objects
        self.assertIn(contact, Contact.objects.all_objects())

    def test_contact_restore(self):
        """Test restore functionality"""
        # Arrange & Act
        contact = Contact.objects.create(**self.contact_data)
        contact.delete()
        contact.restore()

        # Assert
        contact.refresh_from_db()
        self.assertFalse(contact.is_deleted)
        self.assertIsNone(contact.deleted_at)
        self.assertIn(contact, Contact.objects.all())

    def test_contact_get_deals_count(self):
        """Test getting deals count for contact"""
        # Arrange
        contact = Contact.objects.create(**self.contact_data)

        # This would require Deal model to be implemented
        # For now, test the method exists and returns 0
        # Act & Assert
        self.assertEqual(contact.get_deals_count(), 0)

    def test_contact_get_total_deal_value(self):
        """Test getting total deal value for contact"""
        # Arrange
        contact = Contact.objects.create(**self.contact_data)

        # Act & Assert
        self.assertEqual(contact.get_total_deal_value(), 0)

    def test_contact_get_latest_activity(self):
        """Test getting latest activity for contact"""
        # Arrange
        contact = Contact.objects.create(**self.contact_data)

        # Act & Assert
        self.assertIsNone(contact.get_latest_activity())

    def test_contact_manager_methods(self):
        """Test custom manager methods"""
        # Arrange
        contact1 = Contact.objects.create(**self.contact_data)

        inactive_contact_data = self.contact_data.copy()
        inactive_contact_data['email'] = 'inactive@example.com'
        inactive_contact_data['is_active'] = False
        contact2 = Contact.objects.create(**inactive_contact_data)

        deleted_contact_data = self.contact_data.copy()
        deleted_contact_data['email'] = 'deleted@example.com'
        contact3 = Contact.objects.create(**deleted_contact_data)
        contact3.delete()

        # Test active()
        active_contacts = Contact.objects.active()
        self.assertIn(contact1, active_contacts)
        self.assertNotIn(contact2, active_contacts)

        # Test by_owner()
        owner_contacts = Contact.objects.by_owner(self.user)
        self.assertIn(contact1, owner_contacts)
        self.assertIn(contact2, owner_contacts)
        self.assertIn(contact3, owner_contacts)  # Deleted included by default

        # Test by_company()
        company_contacts = Contact.objects.by_company('Tech Corp')
        self.assertIn(contact1, company_contacts)
        self.assertIn(contact2, company_contacts)

        # Test tagged_with()
        contact1.add_tag('test')
        tagged_contacts = Contact.objects.tagged_with('test')
        self.assertIn(contact1, tagged_contacts)
        self.assertNotIn(contact2, tagged_contacts)

        # Test search()
        search_results = Contact.objects.search('Jane')
        self.assertIn(contact1, search_results)

    def test_contact_model_indexes(self):
        """Test that model has proper indexes"""
        meta = Contact._meta
        index_fields = [index.fields for index in meta.indexes]

        expected_indexes = [
            ['first_name'],
            ['last_name'],
            ['email'],
            ['company'],
            ['owner'],
            ['created_at'],
            ['is_active'],
            ['tags'],
        ]

        for expected in expected_indexes:
            self.assertIn(expected, index_fields)

    def test_contact_created_at_timestamp(self):
        """Test created_at timestamp is set automatically"""
        # Arrange & Act
        with freeze_time('2024-01-01 12:00:00'):
            contact = Contact.objects.create(**self.contact_data)

            # Assert
            self.assertEqual(contact.created_at, timezone.now())

    def test_contact_updated_at_timestamp(self):
        """Test updated_at timestamp updates on save"""
        # Arrange & Act
        contact = Contact.objects.create(**self.contact_data)
        original_updated_at = contact.updated_at

        # Wait a moment and update
        with freeze_time('2024-01-01 13:00:00'):
            contact.title = 'Updated Title'
            contact.save()

            # Assert
            self.assertNotEqual(contact.updated_at, original_updated_at)
            self.assertEqual(contact.updated_at, timezone.now())


class ContactInteractionModelTest(TestCase):
    """Test ContactInteraction model"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            email='test@example.com',
            first_name='John',
            last_name='Doe',
            password='testpass123'
        )

        self.contact = Contact.objects.create(
            first_name='Jane',
            last_name='Smith',
            email='jane@example.com',
            owner=self.user
        )

        self.interaction_data = {
            'contact': self.contact,
            'interaction_type': 'call',
            'title': 'Initial Call',
            'description': 'Had a great conversation about their needs',
            'created_by': self.user
        }

    def test_interaction_creation(self):
        """Test creating interaction"""
        # Arrange & Act
        interaction = ContactInteraction.objects.create(**self.interaction_data)

        # Assert
        self.assertEqual(interaction.contact, self.contact)
        self.assertEqual(interaction.interaction_type, 'call')
        self.assertEqual(interaction.title, 'Initial Call')
        self.assertEqual(interaction.created_by, self.user)

    def test_interaction_str_representation(self):
        """Test string representation of interaction"""
        # Arrange & Act
        interaction = ContactInteraction.objects.create(**self.interaction_data)

        # Assert
        self.assertEqual(str(interaction), 'call: Initial Call - Jane Smith')

    def test_interaction_type_choices(self):
        """Test valid interaction types"""
        valid_types = ['call', 'email', 'meeting', 'note', 'task', 'demo']

        for interaction_type in valid_types:
            # Arrange & Act
            interaction_data = self.interaction_data.copy()
            interaction_data['interaction_type'] = interaction_type
            interaction_data['title'] = f'Test {interaction_type}'

            # Assert
            interaction = ContactInteraction.objects.create(**interaction_data)
            self.assertEqual(interaction.interaction_type, interaction_type)

    def test_interaction_model_ordering(self):
        """Test that interactions are ordered by created_at descending"""
        # Arrange & Act
        with freeze_time('2024-01-01 12:00:00'):
            interaction1 = ContactInteraction.objects.create(**self.interaction_data)

        with freeze_time('2024-01-01 13:00:00'):
            interaction_data = self.interaction_data.copy()
            interaction_data['title'] = 'Second Interaction'
            interaction2 = ContactInteraction.objects.create(**interaction_data)

        # Assert
        interactions = list(ContactInteraction.objects.all())
        self.assertEqual(interactions[0], interaction2)
        self.assertEqual(interactions[1], interaction1)