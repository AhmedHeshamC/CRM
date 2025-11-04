"""
Contact Serializer Tests - TDD Approach
Testing comprehensive validation and serialization logic
Following SOLID principles and comprehensive test coverage
"""

import pytest
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework.test import APITestCase
from rest_framework.exceptions import ValidationError

from crm.apps.contacts.models import Contact, ContactInteraction
from crm.apps.contacts.serializers import (
    ContactSerializer,
    ContactDetailSerializer,
    ContactCreateSerializer,
    ContactUpdateSerializer,
    ContactInteractionSerializer,
    ContactSummarySerializer
)

User = get_user_model()


class ContactSerializerTestCase(TestCase):
    """Base test case for Contact serializers"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            email='testuser@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
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
            'linkedin_url': 'https://linkedin.com/in/johndoe',
            'twitter_url': 'https://twitter.com/johndoe',
            'tags': ['vip', 'prospect'],
            'lead_source': 'Website',
            'is_active': True,
            'owner': self.user.id
        }


class ContactSerializerTests(ContactSerializerTestCase):
    """Test ContactSerializer functionality"""

    def test_valid_contact_serialization(self):
        """Test serialization of valid contact data"""
        contact = Contact.objects.create(**self.contact_data)
        serializer = ContactSerializer(contact)

        data = serializer.data
        self.assertEqual(data['id'], contact.id)
        self.assertEqual(data['first_name'], 'John')
        self.assertEqual(data['last_name'], 'Doe')
        self.assertEqual(data['email'], 'john.doe@example.com')
        self.assertEqual(data['full_name'], 'John Doe')
        self.assertEqual(data['company'], 'Acme Corp')
        self.assertEqual(data['tags'], ['vip', 'prospect'])
        self.assertTrue(data['is_active'])
        self.assertIn('uuid', data)
        self.assertIn('created_at', data)
        self.assertIn('updated_at', data)

    def test_contact_validation_missing_required_fields(self):
        """Test validation fails with missing required fields"""
        invalid_data = {
            'first_name': 'John',
            # Missing last_name, email, owner
        }
        serializer = ContactSerializer(data=invalid_data)

        with self.assertRaises(ValidationError) as context:
            serializer.is_valid(raise_exception=True)

        self.assertIn('last_name', context.exception.detail)
        self.assertIn('email', context.exception.detail)
        self.assertIn('owner', context.exception.detail)

    def test_contact_validation_invalid_email(self):
        """Test validation fails with invalid email"""
        data = self.contact_data.copy()
        data['email'] = 'invalid-email'
        serializer = ContactSerializer(data=data)

        with self.assertRaises(ValidationError) as context:
            serializer.is_valid(raise_exception=True)

        self.assertIn('email', context.exception.detail)

    def test_contact_validation_invalid_phone(self):
        """Test validation fails with invalid phone number"""
        data = self.contact_data.copy()
        data['phone'] = 'invalid-phone'
        serializer = ContactSerializer(data=data)

        with self.assertRaises(ValidationError) as context:
            serializer.is_valid(raise_exception=True)

        self.assertIn('phone', context.exception.detail)

    def test_contact_validation_invalid_website(self):
        """Test validation fails with invalid website URL"""
        data = self.contact_data.copy()
        data['website'] = 'invalid-url'
        serializer = ContactSerializer(data=data)

        with self.assertRaises(ValidationError) as context:
            serializer.is_valid(raise_exception=True)

        self.assertIn('website', context.exception.detail)

    def test_contact_validation_invalid_tags(self):
        """Test validation fails with non-list tags"""
        data = self.contact_data.copy()
        data['tags'] = 'not-a-list'
        serializer = ContactSerializer(data=data)

        with self.assertRaises(ValidationError) as context:
            serializer.is_valid(raise_exception=True)

        self.assertIn('tags', context.exception.detail)

    def test_optional_fields_handling(self):
        """Test proper handling of optional fields"""
        minimal_data = {
            'first_name': 'Jane',
            'last_name': 'Smith',
            'email': 'jane.smith@example.com',
            'owner': self.user.id
        }
        serializer = ContactSerializer(data=minimal_data)
        self.assertTrue(serializer.is_valid())

        contact = serializer.save()
        self.assertEqual(contact.phone, '')
        self.assertEqual(contact.company, '')
        self.assertEqual(contact.tags, [])

    def test_tags_sanitization(self):
        """Test tags are properly sanitized"""
        data = self.contact_data.copy()
        data['tags'] = ['  vip  ', 'prospect', '', '  ', 'customer  ']
        serializer = ContactSerializer(data=data)

        self.assertTrue(serializer.is_valid())
        contact = serializer.save()
        self.assertEqual(contact.tags, ['vip', 'prospect', 'customer'])

    def test_email_uniqueness_validation(self):
        """Test email uniqueness validation"""
        Contact.objects.create(**self.contact_data)

        duplicate_data = self.contact_data.copy()
        duplicate_data['first_name'] = 'Jane'  # Different name, same email

        serializer = ContactSerializer(data=duplicate_data)
        with self.assertRaises(ValidationError) as context:
            serializer.is_valid(raise_exception=True)

        self.assertIn('email', context.exception.detail)


class ContactCreateSerializerTests(ContactSerializerTestCase):
    """Test ContactCreateSerializer functionality"""

    def test_create_serializer_validates_required_fields(self):
        """Test create serializer enforces all required fields"""
        data = self.contact_data.copy()
        serializer = ContactCreateSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_create_serializer_sets_defaults(self):
        """Test create serializer sets appropriate defaults"""
        data = {
            'first_name': 'Alice',
            'last_name': 'Johnson',
            'email': 'alice@example.com',
            'owner': self.user.id
        }
        serializer = ContactCreateSerializer(data=data)
        self.assertTrue(serializer.is_valid())

        contact = serializer.save()
        self.assertTrue(contact.is_active)
        self.assertFalse(contact.is_deleted)

    def test_create_sanitizes_data(self):
        """Test create serializer properly sanitizes input data"""
        data = {
            'first_name': '  Alice  ',
            'last_name': '  Johnson  ',
            'email': '  ALICE@EXAMPLE.COM  ',
            'company': '  Acme Corp  ',
            'tags': ['  vip  ', '  prospect  '],
            'owner': self.user.id
        }
        serializer = ContactCreateSerializer(data=data)
        self.assertTrue(serializer.is_valid())

        contact = serializer.save()
        self.assertEqual(contact.first_name, 'Alice')
        self.assertEqual(contact.last_name, 'Johnson')
        self.assertEqual(contact.email, 'alice@example.com')
        self.assertEqual(contact.company, 'Acme Corp')
        self.assertEqual(contact.tags, ['vip', 'prospect'])


class ContactUpdateSerializerTests(ContactSerializerTestCase):
    """Test ContactUpdateSerializer functionality"""

    def setUp(self):
        super().setUp()
        self.contact = Contact.objects.create(**self.contact_data)

    def test_update_serializer_accepts_partial_data(self):
        """Test update serializer allows partial updates"""
        update_data = {
            'first_name': 'Johnathan',
            'company': 'New Corp'
        }
        serializer = ContactUpdateSerializer(
            self.contact,
            data=update_data,
            partial=True
        )
        self.assertTrue(serializer.is_valid())

    def test_update_sanitizes_provided_fields(self):
        """Test update serializer sanitizes only provided fields"""
        update_data = {
            'first_name': '  Johnathan  ',
            'company': '  New Corp  ',
            'tags': ['  updated  ', '  vip  ']
        }
        serializer = ContactUpdateSerializer(
            self.contact,
            data=update_data,
            partial=True
        )
        self.assertTrue(serializer.is_valid())

        updated_contact = serializer.save()
        self.assertEqual(updated_contact.first_name, 'Johnathan')
        self.assertEqual(updated_contact.company, 'New Corp')
        self.assertEqual(updated_contact.tags, ['updated', 'vip'])
        # Unchanged fields should remain the same
        self.assertEqual(updated_contact.last_name, 'Doe')

    def test_update_preserves_unchanged_fields(self):
        """Test update preserves fields that weren't updated"""
        update_data = {'first_name': 'Johnathan'}
        serializer = ContactUpdateSerializer(
            self.contact,
            data=update_data,
            partial=True
        )
        self.assertTrue(serializer.is_valid())

        updated_contact = serializer.save()
        self.assertEqual(updated_contact.first_name, 'Johnathan')
        self.assertEqual(updated_contact.last_name, 'Doe')  # Unchanged
        self.assertEqual(updated_contact.email, 'john.doe@example.com')  # Unchanged


class ContactDetailSerializerTests(ContactSerializerTestCase):
    """Test ContactDetailSerializer functionality"""

    def setUp(self):
        super().setUp()
        self.contact = Contact.objects.create(**self.contact_data)

    def test_detail_serializer_includes_additional_fields(self):
        """Test detail serializer includes comprehensive contact information"""
        serializer = ContactDetailSerializer(self.contact)
        data = serializer.data

        # Should include basic fields
        self.assertEqual(data['id'], self.contact.id)
        self.assertEqual(data['first_name'], 'John')

        # Should include computed fields
        self.assertEqual(data['full_name'], 'John Doe')
        self.assertEqual(data['deals_count'], 0)
        self.assertEqual(data['total_deal_value'], '0.00')

        # Should include timestamps
        self.assertIn('created_at', data)
        self.assertIn('updated_at', data)
        self.assertIn('deleted_at', data)

    def test_detail_serializer_includes_deals_summary(self):
        """Test detail serializer includes deals-related summary"""
        # Create some deals for the contact
        from crm.apps.deals.models import Deal
        Deal.objects.create(
            title='Deal 1',
            value=Decimal('1000.00'),
            contact=self.contact,
            owner=self.user
        )
        Deal.objects.create(
            title='Deal 2',
            value=Decimal('2000.00'),
            contact=self.contact,
            owner=self.user
        )

        serializer = ContactDetailSerializer(self.contact)
        data = serializer.data

        self.assertEqual(data['deals_count'], 2)
        self.assertEqual(data['total_deal_value'], '3000.00')


class ContactSummarySerializerTests(ContactSerializerTestCase):
    """Test ContactSummarySerializer functionality"""

    def setUp(self):
        super().setUp()
        self.contact = Contact.objects.create(**self.contact_data)

    def test_summary_serializer_includes_essential_fields(self):
        """Test summary serializer includes only essential fields"""
        serializer = ContactSummarySerializer(self.contact)
        data = serializer.data

        # Should include essential identification fields
        self.assertIn('id', data)
        self.assertIn('uuid', data)
        self.assertEqual(data['first_name'], 'John')
        self.assertEqual(data['last_name'], 'Doe')
        self.assertEqual(data['email'], 'john.doe@example.com')
        self.assertEqual(data['full_name'], 'John Doe')

        # Should include company information if present
        self.assertEqual(data['company'], 'Acme Corp')

        # Should not include verbose fields
        self.assertNotIn('address', data)
        self.assertNotIn('description', data)
        self.assertNotIn('created_at', data)


class ContactInteractionSerializerTests(ContactSerializerTestCase):
    """Test ContactInteractionSerializer functionality"""

    def setUp(self):
        super().setUp()
        self.contact = Contact.objects.create(**self.contact_data)
        self.interaction_data = {
            'contact': self.contact.id,
            'interaction_type': 'call',
            'title': 'Initial consultation call',
            'description': 'Discussed requirements and timeline',
            'created_by': self.user.id
        }

    def test_interaction_serializer_validation(self):
        """Test interaction serializer validates required fields"""
        serializer = ContactInteractionSerializer(data=self.interaction_data)
        self.assertTrue(serializer.is_valid())

    def test_interaction_serializer_missing_required_fields(self):
        """Test interaction serializer fails with missing required fields"""
        invalid_data = {
            'contact': self.contact.id,
            # Missing interaction_type, title, created_by
        }
        serializer = ContactInteractionSerializer(data=invalid_data)

        with self.assertRaises(ValidationError) as context:
            serializer.is_valid(raise_exception=True)

        self.assertIn('interaction_type', context.exception.detail)
        self.assertIn('title', context.exception.detail)
        self.assertIn('created_by', context.exception.detail)

    def test_interaction_serializer_invalid_type(self):
        """Test interaction serializer rejects invalid interaction types"""
        data = self.interaction_data.copy()
        data['interaction_type'] = 'invalid_type'
        serializer = ContactInteractionSerializer(data=data)

        with self.assertRaises(ValidationError) as context:
            serializer.is_valid(raise_exception=True)

        self.assertIn('interaction_type', context.exception.detail)

    def test_interaction_creation(self):
        """Test successful interaction creation"""
        serializer = ContactInteractionSerializer(data=self.interaction_data)
        self.assertTrue(serializer.is_valid())

        interaction = serializer.save()
        self.assertEqual(interaction.contact, self.contact)
        self.assertEqual(interaction.interaction_type, 'call')
        self.assertEqual(interaction.title, 'Initial consultation call')
        self.assertEqual(interaction.created_by, self.user)


class ContactSerializerIntegrationTests(ContactSerializerTestCase):
    """Integration tests for Contact serializers"""

    def test_serializer_with_user_object(self):
        """Test serializer works with User object instead of ID"""
        data = self.contact_data.copy()
        data['owner'] = self.user
        serializer = ContactSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_serializer_field_validation_order(self):
        """Test field validation happens in correct order"""
        data = self.contact_data.copy()
        data['email'] = 'invalid'
        data['website'] = 'invalid-url'

        serializer = ContactSerializer(data=data)
        with self.assertRaises(ValidationError) as context:
            serializer.is_valid(raise_exception=True)

        # Should catch both validation errors
        self.assertIn('email', context.exception.detail)
        self.assertIn('website', context.exception.detail)

    def test_serializer_error_messages_are_user_friendly(self):
        """Test serializer provides user-friendly error messages"""
        data = self.contact_data.copy()
        data['email'] = 'not-an-email'

        serializer = ContactSerializer(data=data)
        with self.assertRaises(ValidationError) as context:
            serializer.is_valid(raise_exception=True)

        email_error = context.exception.detail['email'][0]
        self.assertIsInstance(email_error, str)
        self.assertTrue(len(email_error) > 0)