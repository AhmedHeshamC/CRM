"""
Deal Model Tests - Test-Driven Development Approach
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
from decimal import Decimal

from crm.apps.contacts.models import Contact
from crm.apps.deals.models import Deal, DealStageHistory

User = get_user_model()


class DealModelTest(TestCase):
    """Test Deal model following TDD methodology"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            email='sales@example.com',
            first_name='Sales',
            last_name='User',
            password='testpass123'
        )

        self.contact = Contact.objects.create(
            first_name='John',
            last_name='Client',
            email='client@example.com',
            company='Client Corp',
            owner=self.user
        )

        self.deal_data = {
            'title': 'Enterprise Software Deal',
            'description': 'Large enterprise software license',
            'value': Decimal('50000.00'),
            'currency': 'USD',
            'probability': 25,
            'stage': 'qualified',
            'expected_close_date': timezone.now().date() + timezone.timedelta(days=90),
            'contact': self.contact,
            'owner': self.user
        }

    def test_deal_creation_with_minimum_fields(self):
        """Test creating deal with minimum required fields"""
        # Arrange & Act
        deal = Deal.objects.create(
            title='Test Deal',
            value=Decimal('10000.00'),
            expected_close_date=timezone.now().date() + timezone.timedelta(days=30),
            contact=self.contact,
            owner=self.user
        )

        # Assert
        self.assertEqual(deal.title, 'Test Deal')
        self.assertEqual(deal.value, Decimal('10000.00'))
        self.assertEqual(deal.currency, 'USD')  # Default currency
        self.assertEqual(deal.stage, 'prospect')  # Default stage
        self.assertEqual(deal.probability, 10)  # Default probability
        self.assertEqual(deal.contact, self.contact)
        self.assertEqual(deal.owner, self.user)
        self.assertFalse(deal.is_archived)
        self.assertIsNotNone(deal.uuid)
        self.assertIsInstance(deal.uuid, uuid.UUID)

    def test_deal_creation_with_all_fields(self):
        """Test creating deal with all fields"""
        # Arrange & Act
        deal = Deal.objects.create(**self.deal_data)

        # Assert
        self.assertEqual(deal.description, 'Large enterprise software license')
        self.assertEqual(deal.currency, 'USD')
        self.assertEqual(deal.probability, 25)
        self.assertEqual(deal.stage, 'qualified')

    def test_deal_str_representation(self):
        """Test string representation of deal"""
        # Arrange & Act
        deal = Deal.objects.create(**self.deal_data)

        # Assert
        self.assertEqual(str(deal), 'Enterprise Software Deal - USD 50,000.00')

    def test_deal_value_validation_positive(self):
        """Test deal value must be positive"""
        # Arrange
        deal = Deal(**self.deal_data)

        # Act & Assert
        deal.value = Decimal('0')
        with self.assertRaises(ValidationError) as context:
            deal.full_clean()
        self.assertIn('Deal value must be positive', str(context.exception))

        deal.value = Decimal('-1000')
        with self.assertRaises(ValidationError):
            deal.full_clean()

    def test_deal_probability_validation_range(self):
        """Test probability must be between 0 and 100"""
        # Arrange
        deal = Deal(**self.deal_data)

        # Act & Assert
        invalid_probabilities = [-1, 101, 150]
        for prob in invalid_probabilities:
            deal.probability = prob
            with self.assertRaises(ValidationError):
                deal.full_clean()

        # Test valid probabilities
        valid_probabilities = [0, 50, 100]
        for prob in valid_probabilities:
            deal.probability = prob
            try:
                deal.full_clean()  # Should not raise exception
            except ValidationError:
                self.fail(f"Probability {prob} should be valid")

    def test_deal_expected_close_date_validation(self):
        """Test expected close date validation"""
        # Arrange
        deal = Deal(**self.deal_data)
        past_date = timezone.now().date() - timezone.timedelta(days=10)

        # Act & Assert
        deal.expected_close_date = past_date
        with self.assertRaises(ValidationError) as context:
            deal.full_clean()
        self.assertIn('Expected close date cannot be in the past', str(context.exception))

    def test_deal_stage_choices(self):
        """Test valid stage choices"""
        valid_stages = ['prospect', 'qualified', 'proposal', 'negotiation', 'closed_won', 'closed_lost']

        for stage in valid_stages:
            # Arrange & Act
            deal_data = self.deal_data.copy()
            deal_data['stage'] = stage
            deal_data['title'] = f'Test Deal {stage}'
            deal = Deal.objects.create(**deal_data)

            # Assert
            self.assertEqual(deal.stage, stage)

    def test_deal_currency_choices(self):
        """Test valid currency choices"""
        valid_currencies = ['USD', 'EUR', 'GBP', 'CAD', 'AUD']

        for currency in valid_currencies:
            # Arrange & Act
            deal_data = self.deal_data.copy()
            deal_data['currency'] = currency
            deal_data['title'] = f'Test Deal {currency}'
            deal = Deal.objects.create(**deal_data)

            # Assert
            self.assertEqual(deal.currency, currency)

    def test_deal_properties(self):
        """Test deal property methods"""
        # Arrange & Act
        won_deal_data = self.deal_data.copy()
        won_deal_data['stage'] = 'closed_won'
        won_deal_data['title'] = 'Won Deal'
        won_deal = Deal.objects.create(**won_deal_data)

        lost_deal_data = self.deal_data.copy()
        lost_deal_data['stage'] = 'closed_lost'
        lost_deal_data['title'] = 'Lost Deal'
        lost_deal = Deal.objects.create(**lost_deal_data)

        open_deal = Deal.objects.create(**self.deal_data)

        # Assert
        self.assertTrue(won_deal.is_won)
        self.assertFalse(won_deal.is_lost)
        self.assertFalse(won_deal.is_open)

        self.assertFalse(lost_deal.is_won)
        self.assertTrue(lost_deal.is_lost)
        self.assertFalse(lost_deal.is_open)

        self.assertFalse(open_deal.is_won)
        self.assertFalse(open_deal.is_lost)
        self.assertTrue(open_deal.is_open)

    def test_deal_days_in_pipeline(self):
        """Test days_in_pipeline property"""
        # Arrange & Act
        with freeze_time('2024-01-01'):
            deal = Deal.objects.create(**self.deal_data)
            self.assertEqual(deal.days_in_pipeline, 0)

        # Advance time
        with freeze_time('2024-01-11'):
            deal.refresh_from_db()
            self.assertEqual(deal.days_in_pipeline, 10)

    def test_deal_days_to_close(self):
        """Test days_to_close property"""
        # Arrange & Act
        future_date = timezone.now().date() + timezone.timedelta(days=30)
        deal_data = self.deal_data.copy()
        deal_data['expected_close_date'] = future_date
        deal = Deal.objects.create(**deal_data)

        # Assert
        self.assertEqual(deal.days_to_close, 30)

        # Test with None
        deal.expected_close_date = None
        deal.save()
        self.assertIsNone(deal.days_to_close)

    def test_deal_get_formatted_value(self):
        """Test get_formatted_value method"""
        # Arrange & Act
        deal = Deal.objects.create(**self.deal_data)

        # Assert
        self.assertEqual(deal.get_formatted_value(), 'USD 50,000.00')
        self.assertEqual(deal.get_formatted_value(include_currency=False), '50,000.00')

    def test_deal_get_pipeline_position(self):
        """Test get_pipeline_position method"""
        # Arrange & Act
        stages = ['prospect', 'qualified', 'proposal', 'negotiation', 'closed_won', 'closed_lost']

        for i, stage in enumerate(stages, 1):
            deal_data = self.deal_data.copy()
            deal_data['stage'] = stage
            deal_data['title'] = f'Deal {stage}'
            deal = Deal.objects.create(**deal_data)

            # Assert
            self.assertEqual(deal.get_pipeline_position(), i)

    def test_deal_can_transition_to(self):
        """Test deal stage transition validation"""
        # Arrange & Act
        deal = Deal.objects.create(**self.deal_data)

        # Assert
        # From prospect can go to qualified or closed_lost
        self.assertTrue(deal.can_transition_to('qualified'))
        self.assertTrue(deal.can_transition_to('closed_lost'))
        self.assertFalse(deal.can_transition_to('proposal'))
        self.assertFalse(deal.can_transition_to('negotiation'))
        self.assertFalse(deal.can_transition_to('closed_won'))

        # From qualified can go to proposal, prospect, or closed_lost
        deal.stage = 'qualified'
        deal.save()
        self.assertTrue(deal.can_transition_to('proposal'))
        self.assertTrue(deal.can_transition_to('prospect'))
        self.assertTrue(deal.can_transition_to('closed_lost'))
        self.assertFalse(deal.can_transition_to('negotiation'))
        self.assertFalse(deal.can_transition_to('closed_won'))

    def test_deal_close_as_won(self):
        """Test closing deal as won"""
        # Arrange & Act
        deal = Deal.objects.create(**self.deal_data)
        deal.close_as_won(Decimal('55000.00'))

        # Assert
        deal.refresh_from_db()
        self.assertEqual(deal.stage, 'closed_won')
        self.assertEqual(deal.probability, 100)
        self.assertEqual(deal.closed_value, Decimal('55000.00'))
        self.assertIsNotNone(deal.closed_date)

    def test_deal_close_as_lost(self):
        """Test closing deal as lost"""
        # Arrange & Act
        deal = Deal.objects.create(**self.deal_data)
        deal.close_as_lost('Client chose competitor')

        # Assert
        deal.refresh_from_db()
        self.assertEqual(deal.stage, 'closed_lost')
        self.assertEqual(deal.probability, 0)
        self.assertEqual(deal.loss_reason, 'Client chose competitor')
        self.assertIsNotNone(deal.closed_date)

    def test_deal_auto_probability_update_on_stage_change(self):
        """Test automatic probability update on stage change"""
        # Arrange & Act
        deal = Deal.objects.create(**self.deal_data)
        original_probability = deal.probability

        # Change stage
        deal.stage = 'proposal'
        deal.save()

        # Assert
        deal.refresh_from_db()
        self.assertEqual(deal.probability, 50)  # Should auto-update to proposal probability
        self.assertNotEqual(deal.probability, original_probability)

    def test_deal_closed_date_auto_set(self):
        """Test closed_date is automatically set when deal is won or lost"""
        # Arrange & Act
        with freeze_time('2024-01-15 10:30:00'):
            deal = Deal.objects.create(**self.deal_data)
            deal.stage = 'closed_won'
            deal.save()

            # Assert
            deal.refresh_from_db()
            self.assertEqual(deal.closed_date, timezone.now())

    def test_deal_manager_methods(self):
        """Test custom manager methods"""
        # Arrange
        prospect_deal = Deal.objects.create(**self.deal_data)

        qualified_deal_data = self.deal_data.copy()
        qualified_deal_data['stage'] = 'qualified'
        qualified_deal_data['title'] = 'Qualified Deal'
        qualified_deal = Deal.objects.create(**qualified_deal_data)

        won_deal_data = self.deal_data.copy()
        won_deal_data['stage'] = 'closed_won'
        won_deal_data['title'] = 'Won Deal'
        won_deal = Deal.objects.create(**won_deal_data)

        lost_deal_data = self.deal_data.copy()
        lost_deal_data['stage'] = 'closed_lost'
        lost_deal_data['title'] = 'Lost Deal'
        lost_deal = Deal.objects.create(**lost_deal_data)

        archived_deal_data = self.deal_data.copy()
        archived_deal_data['title'] = 'Archived Deal'
        archived_deal = Deal.objects.create(**archived_deal_data)
        archived_deal.is_archived = True
        archived_deal.save()

        # Test by_owner()
        owner_deals = Deal.objects.by_owner(self.user)
        self.assertIn(prospect_deal, owner_deals)
        self.assertIn(qualified_deal, owner_deals)
        self.assertIn(won_deal, owner_deals)
        self.assertIn(lost_deal, owner_deals)
        self.assertNotIn(archived_deal, owner_deals)  # Archived excluded by default

        # Test by_stage()
        qualified_deals = Deal.objects.by_stage('qualified')
        self.assertIn(qualified_deal, qualified_deals)
        self.assertNotIn(prospect_deal, qualified_deals)

        # Test open_deals()
        open_deals = Deal.objects.open_deals()
        self.assertIn(prospect_deal, open_deals)
        self.assertIn(qualified_deal, open_deals)
        self.assertNotIn(won_deal, open_deals)
        self.assertNotIn(lost_deal, open_deals)

        # Test won_deals()
        won_deals = Deal.objects.won_deals()
        self.assertIn(won_deal, won_deals)
        self.assertNotIn(prospect_deal, won_deals)

        # Test lost_deals()
        lost_deals = Deal.objects.lost_deals()
        self.assertIn(lost_deal, lost_deals)
        self.assertNotIn(prospect_deal, lost_deals)

        # Test all_objects()
        all_deals = Deal.objects.all_objects()
        self.assertIn(archived_deal, all_deals)  # Now included

    def test_deal_closing_soon(self):
        """Test deals closing soon method"""
        # Arrange
        soon_deal_data = self.deal_data.copy()
        soon_deal_data['expected_close_date'] = timezone.now().date() + timezone.timedelta(days=15)
        soon_deal_data['stage'] = 'qualified'
        soon_deal = Deal.objects.create(**soon_deal_data)

        far_deal_data = self.deal_data.copy()
        far_deal_data['expected_close_date'] = timezone.now().date() + timezone.timedelta(days=60)
        far_deal = Deal.objects.create(**far_deal_data)

        # Act
        closing_soon = Deal.objects.closing_soon(days=30)

        # Assert
        self.assertIn(soon_deal, closing_soon)
        self.assertNotIn(far_deal, closing_soon)

    def test_deal_model_indexes(self):
        """Test that model has proper indexes"""
        meta = Deal._meta
        index_fields = [index.fields for index in meta.indexes]

        expected_indexes = [
            ['title'],
            ['stage'],
            ['probability'],
            ['expected_close_date'],
            ['contact'],
            ['owner'],
            ['created_at'],
            ['value'],
        ]

        for expected in expected_indexes:
            self.assertIn(expected, index_fields)


class DealStageHistoryModelTest(TestCase):
    """Test DealStageHistory model"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            email='sales@example.com',
            first_name='Sales',
            last_name='User',
            password='testpass123'
        )

        self.contact = Contact.objects.create(
            first_name='John',
            last_name='Client',
            email='client@example.com',
            owner=self.user
        )

        self.deal = Deal.objects.create(
            title='Test Deal',
            value=Decimal('10000.00'),
            expected_close_date=timezone.now().date() + timezone.timedelta(days=30),
            contact=self.contact,
            owner=self.user
        )

    def test_stage_history_creation(self):
        """Test creating stage history record"""
        # Arrange & Act
        history = DealStageHistory.objects.create(
            deal=self.deal,
            old_stage='prospect',
            new_stage='qualified',
            changed_by=self.user
        )

        # Assert
        self.assertEqual(history.deal, self.deal)
        self.assertEqual(history.old_stage, 'prospect')
        self.assertEqual(history.new_stage, 'qualified')
        self.assertEqual(history.changed_by, self.user)

    def test_stage_history_str_representation(self):
        """Test string representation of stage history"""
        # Arrange & Act
        history = DealStageHistory.objects.create(
            deal=self.deal,
            old_stage='prospect',
            new_stage='qualified',
            changed_by=self.user
        )

        # Assert
        self.assertEqual(str(history), 'Test Deal: prospect → qualified')

    def test_stage_history_ordering(self):
        """Test that stage history is ordered by changed_at descending"""
        # Arrange & Act
        with freeze_time('2024-01-01 12:00:00'):
            history1 = DealStageHistory.objects.create(
                deal=self.deal,
                old_stage='prospect',
                new_stage='qualified',
                changed_by=self.user
            )

        with freeze_time('2024-01-01 13:00:00'):
            history2 = DealStageHistory.objects.create(
                deal=self.deal,
                old_stage='qualified',
                new_stage='proposal',
                changed_by=self.user
            )

        # Assert
        histories = list(DealStageHistory.objects.all())
        self.assertEqual(histories[0], history2)
        self.assertEqual(histories[1], history1)