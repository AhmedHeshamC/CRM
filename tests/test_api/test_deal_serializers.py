"""
Deal Serializer Tests - TDD Approach
Testing comprehensive validation and serialization logic
Following SOLID principles and comprehensive test coverage
"""

import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework.test import APITestCase
from rest_framework.exceptions import ValidationError

from crm.apps.deals.models import Deal, DealStageHistory
from crm.apps.contacts.models import Contact
from crm.apps.deals.serializers import (
    DealSerializer,
    DealDetailSerializer,
    DealCreateSerializer,
    DealUpdateSerializer,
    DealSummarySerializer,
    DealStageHistorySerializer
)

User = get_user_model()


class DealSerializerTestCase(TestCase):
    """Base test case for Deal serializers"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            email='testuser@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )

        self.contact = Contact.objects.create(
            first_name='John',
            last_name='Doe',
            email='john.doe@example.com',
            owner=self.user
        )

        tomorrow = date.today() + timedelta(days=1)
        self.deal_data = {
            'title': 'Test Deal',
            'description': 'This is a test deal',
            'value': '10000.00',
            'currency': 'USD',
            'probability': 25,
            'stage': 'qualified',
            'expected_close_date': tomorrow.isoformat(),
            'contact': self.contact.id,
            'owner': self.user.id
        }


class DealSerializerTests(DealSerializerTestCase):
    """Test DealSerializer functionality"""

    def test_valid_deal_serialization(self):
        """Test serialization of valid deal data"""
        deal = Deal.objects.create(**self.deal_data)
        serializer = DealSerializer(deal)

        data = serializer.data
        self.assertEqual(data['id'], deal.id)
        self.assertEqual(data['title'], 'Test Deal')
        self.assertEqual(data['value'], '10000.00')
        self.assertEqual(data['currency'], 'USD')
        self.assertEqual(data['probability'], 25)
        self.assertEqual(data['stage'], 'qualified')
        self.assertEqual(data['contact'], self.contact.id)
        self.assertEqual(data['owner'], self.user.id)
        self.assertIn('uuid', data)
        self.assertIn('created_at', data)
        self.assertIn('updated_at', data)

    def test_deal_validation_missing_required_fields(self):
        """Test validation fails with missing required fields"""
        invalid_data = {
            'title': 'Test Deal',
            # Missing value, stage, contact, owner
        }
        serializer = DealSerializer(data=invalid_data)

        with self.assertRaises(ValidationError) as context:
            serializer.is_valid(raise_exception=True)

        self.assertIn('value', context.exception.detail)
        self.assertIn('stage', context.exception.detail)
        self.assertIn('contact', context.exception.detail)
        self.assertIn('owner', context.exception.detail)

    def test_deal_validation_invalid_value(self):
        """Test validation fails with invalid deal value"""
        data = self.deal_data.copy()
        data['value'] = '-1000.00'
        serializer = DealSerializer(data=data)

        with self.assertRaises(ValidationError) as context:
            serializer.is_valid(raise_exception=True)

        self.assertIn('value', context.exception.detail)

    def test_deal_validation_invalid_probability(self):
        """Test validation fails with invalid probability"""
        data = self.deal_data.copy()
        data['probability'] = 150  # Over 100
        serializer = DealSerializer(data=data)

        with self.assertRaises(ValidationError) as context:
            serializer.is_valid(raise_exception=True)

        self.assertIn('probability', context.exception.detail)

    def test_deal_validation_invalid_stage(self):
        """Test validation fails with invalid stage"""
        data = self.deal_data.copy()
        data['stage'] = 'invalid_stage'
        serializer = DealSerializer(data=data)

        with self.assertRaises(ValidationError) as context:
            serializer.is_valid(raise_exception=True)

        self.assertIn('stage', context.exception.detail)

    def test_deal_validation_invalid_currency(self):
        """Test validation fails with invalid currency"""
        data = self.deal_data.copy()
        data['currency'] = 'INVALID'
        serializer = DealSerializer(data=data)

        with self.assertRaises(ValidationError) as context:
            serializer.is_valid(raise_exception=True)

        self.assertIn('currency', context.exception.detail)

    def test_deal_validation_past_close_date(self):
        """Test validation fails with past close date for open deals"""
        data = self.deal_data.copy()
        past_date = (date.today() - timedelta(days=1)).isoformat()
        data['expected_close_date'] = past_date
        serializer = DealSerializer(data=data)

        with self.assertRaises(ValidationError) as context:
            serializer.is_valid(raise_exception=True)

        self.assertIn('expected_close_date', context.exception.detail)

    def test_deal_validation_past_close_date_for_closed_deal(self):
        """Test validation allows past close date for closed deals"""
        data = self.deal_data.copy()
        past_date = (date.today() - timedelta(days=1)).isoformat()
        data['expected_close_date'] = past_date
        data['stage'] = 'closed_won'
        serializer = DealSerializer(data=data)

        self.assertTrue(serializer.is_valid())

    def test_deal_validation_negative_probability(self):
        """Test validation fails with negative probability"""
        data = self.deal_data.copy()
        data['probability'] = -10
        serializer = DealSerializer(data=data)

        with self.assertRaises(ValidationError) as context:
            serializer.is_valid(raise_exception=True)

        self.assertIn('probability', context.exception.detail)

    def test_optional_fields_handling(self):
        """Test proper handling of optional fields"""
        minimal_data = {
            'title': 'Minimal Deal',
            'value': '5000.00',
            'stage': 'prospect',
            'contact': self.contact.id,
            'owner': self.user.id,
            'expected_close_date': (date.today() + timedelta(days=30)).isoformat()
        }
        serializer = DealSerializer(data=minimal_data)
        self.assertTrue(serializer.is_valid())

        deal = serializer.save()
        self.assertEqual(deal.description, '')
        self.assertEqual(deal.probability, 0)  # Default for prospect
        self.assertEqual(deal.currency, 'USD')  # Default

    def test_computed_fields(self):
        """Test computed fields are properly calculated"""
        deal = Deal.objects.create(**self.deal_data)
        serializer = DealSerializer(deal)

        data = serializer.data
        self.assertEqual(data['formatted_value'], '$10,000.00')
        self.assertEqual(data['pipeline_position'], 2)  # qualified stage
        self.assertFalse(data['is_won'])
        self.assertFalse(data['is_lost'])
        self.assertTrue(data['is_open'])
        self.assertGreaterEqual(data['days_in_pipeline'], 0)


class DealCreateSerializerTests(DealSerializerTestCase):
    """Test DealCreateSerializer functionality"""

    def test_create_serializer_validates_required_fields(self):
        """Test create serializer enforces all required fields"""
        data = self.deal_data.copy()
        serializer = DealCreateSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_create_serializer_sets_defaults(self):
        """Test create serializer sets appropriate defaults"""
        data = {
            'title': 'New Deal',
            'value': '7500.00',
            'stage': 'prospect',
            'contact': self.contact.id,
            'owner': self.user.id,
            'expected_close_date': (date.today() + timedelta(days=30)).isoformat()
        }
        serializer = DealCreateSerializer(data=data)
        self.assertTrue(serializer.is_valid())

        deal = serializer.save()
        self.assertEqual(deal.probability, 10)  # Default for prospect
        self.assertEqual(deal.currency, 'USD')
        self.assertFalse(deal.is_archived)

    def test_create_sanitizes_data(self):
        """Test create serializer properly sanitizes input data"""
        data = {
            'title': '  Test Deal  ',
            'description': '  This is a test deal  ',
            'value': '10000.00',
            'stage': 'qualified',
            'contact': self.contact.id,
            'owner': self.user.id,
            'expected_close_date': (date.today() + timedelta(days=30)).isoformat()
        }
        serializer = DealCreateSerializer(data=data)
        self.assertTrue(serializer.is_valid())

        deal = serializer.save()
        self.assertEqual(deal.title, 'Test Deal')
        self.assertEqual(deal.description, 'This is a test deal')

    def test_create_automatic_probability_assignment(self):
        """Test create serializer automatically assigns probability based on stage"""
        stages_and_probabilities = [
            ('prospect', 10),
            ('qualified', 25),
            ('proposal', 50),
            ('negotiation', 75),
            ('closed_won', 100),
            ('closed_lost', 0),
        ]

        for stage, expected_prob in stages_and_probabilities:
            data = self.deal_data.copy()
            data['stage'] = stage
            data.pop('probability', None)  # Remove probability to test auto-assignment

            serializer = DealCreateSerializer(data=data)
            self.assertTrue(serializer.is_valid())

            deal = serializer.save()
            self.assertEqual(deal.probability, expected_prob)


class DealUpdateSerializerTests(DealSerializerTestCase):
    """Test DealUpdateSerializer functionality"""

    def setUp(self):
        super().setUp()
        self.deal = Deal.objects.create(**self.deal_data)

    def test_update_serializer_accepts_partial_data(self):
        """Test update serializer allows partial updates"""
        update_data = {
            'title': 'Updated Deal Title',
            'probability': 50
        }
        serializer = DealUpdateSerializer(
            self.deal,
            data=update_data,
            partial=True
        )
        self.assertTrue(serializer.is_valid())

    def test_update_sanitizes_provided_fields(self):
        """Test update serializer sanitizes only provided fields"""
        update_data = {
            'title': '  Updated Deal Title  ',
            'description': '  Updated description  ',
            'probability': 75
        }
        serializer = DealUpdateSerializer(
            self.deal,
            data=update_data,
            partial=True
        )
        self.assertTrue(serializer.is_valid())

        updated_deal = serializer.save()
        self.assertEqual(updated_deal.title, 'Updated Deal Title')
        self.assertEqual(updated_deal.description, 'Updated description')
        self.assertEqual(updated_deal.probability, 75)

    def test_update_preserves_unchanged_fields(self):
        """Test update preserves fields that weren't updated"""
        update_data = {'title': 'Updated Deal Title'}
        serializer = DealUpdateSerializer(
            self.deal,
            data=update_data,
            partial=True
        )
        self.assertTrue(serializer.is_valid())

        updated_deal = serializer.save()
        self.assertEqual(updated_deal.title, 'Updated Deal Title')
        self.assertEqual(updated_deal.value, Decimal('10000.00'))  # Unchanged
        self.assertEqual(updated_deal.stage, 'qualified')  # Unchanged

    def test_stage_transition_tracking(self):
        """Test update serializer tracks stage transitions"""
        update_data = {'stage': 'proposal'}
        serializer = DealUpdateSerializer(
            self.deal,
            data=update_data,
            partial=True
        )
        self.assertTrue(serializer.is_valid())

        updated_deal = serializer.save()

        # Check if stage history was created
        stage_history = DealStageHistory.objects.filter(deal=updated_deal).first()
        self.assertIsNotNone(stage_history)
        self.assertEqual(stage_history.old_stage, 'qualified')
        self.assertEqual(stage_history.new_stage, 'proposal')

    def test_closed_deal_date_setting(self):
        """Test update serializer sets closed date when deal is closed"""
        update_data = {'stage': 'closed_won'}
        serializer = DealUpdateSerializer(
            self.deal,
            data=update_data,
            partial=True
        )
        self.assertTrue(serializer.is_valid())

        updated_deal = serializer.save()
        self.assertIsNotNone(updated_deal.closed_date)
        self.assertEqual(updated_deal.probability, 100)


class DealDetailSerializerTests(DealSerializerTestCase):
    """Test DealDetailSerializer functionality"""

    def setUp(self):
        super().setUp()
        self.deal = Deal.objects.create(**self.deal_data)

    def test_detail_serializer_includes_additional_fields(self):
        """Test detail serializer includes comprehensive deal information"""
        serializer = DealDetailSerializer(self.deal)
        data = serializer.data

        # Should include basic fields
        self.assertEqual(data['id'], self.deal.id)
        self.assertEqual(data['title'], 'Test Deal')

        # Should include computed fields
        self.assertEqual(data['formatted_value'], '$10,000.00')
        self.assertEqual(data['days_in_pipeline'], self.deal.days_in_pipeline)
        self.assertEqual(data['pipeline_position'], 2)

        # Should include relationship data
        self.assertIn('contact_details', data)
        self.assertIn('owner_details', data)
        self.assertEqual(data['contact_details']['id'], self.contact.id)
        self.assertEqual(data['owner_details']['id'], self.user.id)

        # Should include timestamps
        self.assertIn('created_at', data)
        self.assertIn('updated_at', data)
        self.assertIn('closed_date', data)

    def test_detail_serializer_includes_stage_history(self):
        """Test detail serializer includes stage history"""
        # Create some stage history
        DealStageHistory.objects.create(
            deal=self.deal,
            old_stage='prospect',
            new_stage='qualified',
            changed_by=self.user
        )

        serializer = DealDetailSerializer(self.deal)
        data = serializer.data

        self.assertIn('stage_history', data)
        self.assertEqual(len(data['stage_history']), 1)
        self.assertEqual(data['stage_history'][0]['old_stage'], 'prospect')
        self.assertEqual(data['stage_history'][0]['new_stage'], 'qualified')


class DealSummarySerializerTests(DealSerializerTestCase):
    """Test DealSummarySerializer functionality"""

    def setUp(self):
        super().setUp()
        self.deal = Deal.objects.create(**self.deal_data)

    def test_summary_serializer_includes_essential_fields(self):
        """Test summary serializer includes only essential fields"""
        serializer = DealSummarySerializer(self.deal)
        data = serializer.data

        # Should include essential identification fields
        self.assertIn('id', data)
        self.assertIn('uuid', data)
        self.assertEqual(data['title'], 'Test Deal')
        self.assertEqual(data['value'], '10000.00')
        self.assertEqual(data['stage'], 'qualified')
        self.assertEqual(data['probability'], 25)

        # Should include computed summary fields
        self.assertIn('formatted_value', data)
        self.assertIn('pipeline_position', data)

        # Should not include verbose fields
        self.assertNotIn('description', data)
        self.assertNotIn('created_at', data)
        self.assertNotIn('updated_at', data)
        self.assertNotIn('stage_history', data)

    def test_summary_serializer_includes_contact_summary(self):
        """Test summary serializer includes brief contact information"""
        serializer = DealSummarySerializer(self.deal)
        data = serializer.data

        self.assertIn('contact', data)
        self.assertEqual(data['contact']['id'], self.contact.id)
        self.assertEqual(data['contact']['full_name'], 'John Doe')
        self.assertEqual(data['contact']['company'], '')  # Empty company


class DealStageHistorySerializerTests(DealSerializerTestCase):
    """Test DealStageHistorySerializer functionality"""

    def setUp(self):
        super().setUp()
        self.deal = Deal.objects.create(**self.deal_data)
        self.stage_history = DealStageHistory.objects.create(
            deal=self.deal,
            old_stage='prospect',
            new_stage='qualified',
            changed_by=self.user
        )

    def test_stage_history_serialization(self):
        """Test stage history serialization"""
        serializer = DealStageHistorySerializer(self.stage_history)
        data = serializer.data

        self.assertEqual(data['id'], self.stage_history.id)
        self.assertEqual(data['old_stage'], 'prospect')
        self.assertEqual(data['new_stage'], 'qualified')
        self.assertEqual(data['changed_by'], self.user.id)
        self.assertIn('changed_at', data)

    def test_stage_history_validation(self):
        """Test stage history validation"""
        invalid_data = {
            'deal': self.deal.id,
            # Missing old_stage, new_stage
        }
        serializer = DealStageHistorySerializer(data=invalid_data)

        with self.assertRaises(ValidationError) as context:
            serializer.is_valid(raise_exception=True)

        self.assertIn('old_stage', context.exception.detail)
        self.assertIn('new_stage', context.exception.detail)


class DealSerializerIntegrationTests(DealSerializerTestCase):
    """Integration tests for Deal serializers"""

    def test_serializer_with_contact_object(self):
        """Test serializer works with Contact object instead of ID"""
        data = self.deal_data.copy()
        data['contact'] = self.contact
        data['owner'] = self.user
        serializer = DealSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_serializer_field_validation_order(self):
        """Test field validation happens in correct order"""
        data = self.deal_data.copy()
        data['value'] = '-1000.00'
        data['probability'] = 150
        data['stage'] = 'invalid_stage'

        serializer = DealSerializer(data=data)
        with self.assertRaises(ValidationError) as context:
            serializer.is_valid(raise_exception=True)

        # Should catch all validation errors
        self.assertIn('value', context.exception.detail)
        self.assertIn('probability', context.exception.detail)
        self.assertIn('stage', context.exception.detail)

    def test_serializer_error_messages_are_user_friendly(self):
        """Test serializer provides user-friendly error messages"""
        data = self.deal_data.copy()
        data['value'] = 'not-a-number'

        serializer = DealSerializer(data=data)
        with self.assertRaises(ValidationError) as context:
            serializer.is_valid(raise_exception=True)

        value_error = context.exception.detail['value'][0]
        self.assertIsInstance(value_error, str)
        self.assertTrue(len(value_error) > 0)

    def test_currency_validation(self):
        """Test currency field validation"""
        valid_currencies = ['USD', 'EUR', 'GBP', 'CAD', 'AUD']

        for currency in valid_currencies:
            data = self.deal_data.copy()
            data['currency'] = currency
            serializer = DealSerializer(data=data)
            self.assertTrue(serializer.is_valid(), f"Failed for currency: {currency}")

        invalid_currencies = ['XXX', 'USDD', '']

        for currency in invalid_currencies:
            data = self.deal_data.copy()
            data['currency'] = currency
            serializer = DealSerializer(data=data)
            self.assertFalse(serializer.is_valid(), f"Should have failed for currency: {currency}")

    def test_stage_probability_consistency(self):
        """Test probability is consistent with stage expectations"""
        # Test that closed won deals must have 100% probability
        data = self.deal_data.copy()
        data['stage'] = 'closed_won'
        data['probability'] = 50  # Inconsistent with closed won

        serializer = DealSerializer(data=data)
        # This should be valid as the probability will be auto-corrected
        self.assertTrue(serializer.is_valid())

    def test_deal_value_decimal_precision(self):
        """Test deal value maintains decimal precision"""
        data = self.deal_data.copy()
        data['value'] = '12345.6789'  # More than 2 decimal places

        serializer = DealSerializer(data=data)
        self.assertTrue(serializer.is_valid())

        deal = serializer.save()
        self.assertEqual(str(deal.value), '12345.68')  # Should be rounded to 2 decimal places