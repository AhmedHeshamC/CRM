"""
Deal Repository Tests - Test-Driven Development Approach
Following enterprise-grade testing standards with comprehensive coverage
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta, date
from decimal import Decimal

from crm.shared.repositories.deal_repository import DealRepository
from crm.apps.deals.models import Deal
from crm.apps.contacts.models import Contact

User = get_user_model()


class DealRepositoryTest(TestCase):
    """Test DealRepository following TDD methodology"""

    def setUp(self):
        """Set up test data"""
        self.repository = DealRepository()
        self.user = User.objects.create_user(
            email='test@example.com',
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
        self.deal_data = {
            'title': 'Test Deal',
            'description': 'Test Description',
            'value': Decimal('10000.00'),
            'currency': 'USD',
            'stage': 'qualified',
            'expected_close_date': date.today() + timedelta(days=30),
            'contact': self.contact,
            'owner': self.user
        }

    def tearDown(self):
        """Clean up after tests"""
        cache.clear()

    def test_repository_initialization(self):
        """Test repository initialization"""
        # Assert
        self.assertEqual(self.repository.model, Deal)
        self.assertEqual(self.repository.cache_timeout, 300)
        self.assertEqual(self.repository.cache_prefix, 'deal_')

    def test_get_by_owner(self):
        """Test getting deals by owner"""
        # Arrange
        mock_deals = [Mock(spec=Deal), Mock(spec=Deal)]
        with patch('crm.shared.repositories.deal_repository.cache') as mock_cache:
            mock_cache.get.return_value = mock_deals

            # Act
            result = self.repository.get_by_owner(self.user.id)

            # Assert
            self.assertEqual(result, mock_deals)

    def test_get_by_contact(self):
        """Test getting deals by contact"""
        # Arrange
        mock_deals = [Mock(spec=Deal)]
        with patch('crm.shared.repositories.deal_repository.cache') as mock_cache:
            mock_cache.get.return_value = mock_deals

            # Act
            result = self.repository.get_by_contact(self.contact.id)

            # Assert
            self.assertEqual(result, mock_deals)

    def test_get_by_stage(self):
        """Test getting deals by stage"""
        # Arrange
        mock_deals = [Mock(spec=Deal)]
        with patch('crm.shared.repositories.deal_repository.cache') as mock_cache:
            mock_cache.get.return_value = mock_deals

            # Act
            result = self.repository.get_by_stage('qualified', self.user.id)

            # Assert
            self.assertEqual(result, mock_deals)
            mock_cache.get.assert_called_once_with('deal_stage_qualified_' + str(self.user.id))

    def test_get_open_deals(self):
        """Test getting open deals"""
        # Arrange
        mock_deals = [Mock(spec=Deal)]
        with patch('crm.shared.repositories.deal_repository.cache') as mock_cache:
            mock_cache.get.return_value = mock_deals

            # Act
            result = self.repository.get_open_deals(self.user.id)

            # Assert
            self.assertEqual(result, mock_deals)

    def test_get_won_deals(self):
        """Test getting won deals"""
        # Arrange
        mock_deals = [Mock(spec=Deal)]
        with patch('crm.shared.repositories.deal_repository.cache') as mock_cache:
            mock_cache.get.return_value = mock_deals

            # Act
            result = self.repository.get_won_deals(self.user.id, 30)

            # Assert
            self.assertEqual(result, mock_deals)

    def test_get_lost_deals(self):
        """Test getting lost deals"""
        # Arrange
        mock_deals = [Mock(spec=Deal)]
        with patch('crm.shared.repositories.deal_repository.cache') as mock_cache:
            mock_cache.get.return_value = mock_deals

            # Act
            result = self.repository.get_lost_deals(self.user.id, 30)

            # Assert
            self.assertEqual(result, mock_deals)

    def test_get_closing_soon(self):
        """Test getting deals closing soon"""
        # Arrange
        mock_deals = [Mock(spec=Deal)]
        with patch('crm.shared.repositories.deal_repository.cache') as mock_cache:
            mock_cache.get.return_value = mock_deals

            # Act
            result = self.repository.get_closing_soon(30, self.user.id)

            # Assert
            self.assertEqual(result, mock_deals)

    def test_get_overdue_deals(self):
        """Test getting overdue deals"""
        # Arrange
        mock_deals = [Mock(spec=Deal)]
        with patch('crm.shared.repositories.deal_repository.cache') as mock_cache:
            mock_cache.get.return_value = mock_deals

            # Act
            result = self.repository.get_overdue_deals(self.user.id)

            # Assert
            self.assertEqual(result, mock_deals)

    def test_get_deals_by_value_range(self):
        """Test getting deals by value range"""
        # Arrange
        mock_deals = [Mock(spec=Deal)]
        with patch('crm.shared.repositories.deal_repository.cache') as mock_cache:
            mock_cache.get.return_value = mock_deals

            # Act
            result = self.repository.get_deals_by_value_range(5000, 15000, self.user.id)

            # Assert
            self.assertEqual(result, mock_deals)

    def test_search_deals(self):
        """Test searching deals"""
        # Arrange
        mock_deals = [Mock(spec=Deal)]
        with patch('crm.shared.repositories.deal_repository.cache') as mock_cache:
            mock_cache.get.return_value = mock_deals

            # Act
            result = self.repository.search_deals('Test', self.user.id)

            # Assert
            self.assertEqual(result, mock_deals)
            mock_cache.get.assert_called_once_with('deal_search_test_' + str(self.user.id))

    def test_get_deal_statistics_with_cache(self):
        """Test getting deal statistics with cache"""
        # Arrange
        mock_stats = {
            'total_deals': 100,
            'open_deals': 50,
            'won_deals': 30,
            'conversion_rate': 30.0,
        }
        with patch('crm.shared.repositories.deal_repository.cache') as mock_cache:
            mock_cache.get.return_value = mock_stats

            # Act
            result = self.repository.get_deal_statistics(self.user.id)

            # Assert
            self.assertEqual(result, mock_stats)
            mock_cache.get.assert_called_once_with('deal_statistics_' + str(self.user.id))

    def test_get_deal_statistics_without_cache(self):
        """Test getting deal statistics without cache"""
        # Arrange
        with patch('crm.shared.repositories.deal_repository.cache') as mock_cache:
            mock_cache.get.return_value = None
            with patch.object(Deal.objects, 'count') as mock_count:
                mock_count.return_value = 100
                with patch.object(Deal.objects, 'filter') as mock_filter:
                    mock_queryset = Mock()
                    mock_queryset.count.return_value = 50
                    mock_filter.return_value = mock_queryset

                    # Act
                    result = self.repository.get_deal_statistics(self.user.id)

                    # Assert
                    self.assertIn('total_deals', result)
                    self.assertIn('open_deals', result)
                    self.assertEqual(result['total_deals'], 100)

    def test_get_pipeline_value_by_stage(self):
        """Test getting pipeline value by stage"""
        # Arrange
        mock_pipeline_values = {
            'prospect': 50000.0,
            'qualified': 75000.0,
            'proposal': 25000.0,
        }
        with patch('crm.shared.repositories.deal_repository.cache') as mock_cache:
            mock_cache.get.return_value = mock_pipeline_values

            # Act
            result = self.repository.get_pipeline_value_by_stage(self.user.id)

            # Assert
            self.assertEqual(result, mock_pipeline_values)

    def test_update_deal_stage_success(self):
        """Test successful deal stage update"""
        # Arrange
        mock_deal = Mock(spec=Deal)
        mock_deal.id = 1
        mock_deal.stage = 'qualified'
        mock_deal.uuid = 'test-uuid'
        mock_deal.can_transition_to.return_value = True

        with patch.object(Deal.objects, 'get') as mock_get:
            mock_get.return_value = mock_deal
            with patch.object(DealRepository, '_invalidate_cache_pattern') as mock_invalidate:

                # Act
                result = self.repository.update_deal_stage(1, 'proposal', self.user.id)

                # Assert
                self.assertTrue(result)
                self.assertEqual(mock_deal.stage, 'proposal')
                self.assertEqual(mock_deal._changed_by_user_id, self.user.id)
                mock_deal.save.assert_called_once()

    def test_update_deal_stage_invalid_transition(self):
        """Test deal stage update with invalid transition"""
        # Arrange
        mock_deal = Mock(spec=Deal)
        mock_deal.can_transition_to.return_value = False

        with patch.object(Deal.objects, 'get') as mock_get:
            mock_get.return_value = mock_deal

            # Act
            result = self.repository.update_deal_stage(1, 'closed_won', self.user.id)

            # Assert
            self.assertFalse(result)
            mock_deal.save.assert_not_called()

    def test_update_deal_stage_not_found(self):
        """Test updating stage when deal doesn't exist"""
        # Arrange
        with patch.object(Deal.objects, 'get') as mock_get:
            mock_get.side_effect = Deal.DoesNotExist()

            # Act
            result = self.repository.update_deal_stage(999, 'proposal', self.user.id)

            # Assert
            self.assertFalse(result)

    def test_close_deal_as_won_success(self):
        """Test closing deal as won"""
        # Arrange
        mock_deal = Mock(spec=Deal)
        mock_deal.id = 1
        mock_deal.uuid = 'test-uuid'

        with patch.object(Deal.objects, 'get') as mock_get:
            mock_get.return_value = mock_deal
            with patch.object(DealRepository, '_invalidate_cache_pattern') as mock_invalidate:

                # Act
                result = self.repository.close_deal_as_won(1, Decimal('12000.00'))

                # Assert
                self.assertTrue(result)
                mock_deal.close_as_won.assert_called_once_with(Decimal('12000.00'))

    def test_close_deal_as_lost_success(self):
        """Test closing deal as lost"""
        # Arrange
        mock_deal = Mock(spec=Deal)
        mock_deal.id = 1
        mock_deal.uuid = 'test-uuid'

        with patch.object(Deal.objects, 'get') as mock_get:
            mock_get.return_value = mock_deal
            with patch.object(DealRepository, '_invalidate_cache_pattern') as mock_invalidate:

                # Act
                result = self.repository.close_deal_as_lost(1, 'Competitor undercut')

                # Assert
                self.assertTrue(result)
                mock_deal.close_as_lost.assert_called_once_with('Competitor undercut')

    def test_clear_deal_cache(self):
        """Test clearing deal-specific cache"""
        # Arrange
        mock_deal = Mock(spec=Deal)
        mock_deal.id = 1
        mock_deal.owner_id = self.user.id
        mock_deal.contact_id = self.contact.id
        mock_deal.stage = 'qualified'
        mock_deal.uuid = 'test-uuid'

        with patch('crm.shared.repositories.deal_repository.cache') as mock_cache:

            # Act
            self.repository.clear_deal_cache(mock_deal)

            # Assert
            expected_cache_keys = [
                'deal_id_1',
                f'deal_owner_{self.user.id}',
                f'deal_contact_{self.contact.id}',
                'deal_stage_qualified',
                'deal_statistics',
                'deal_pipeline_value',
                'deal_uuid_test-uuid',
            ]

            # Check that delete was called for each expected cache key
            delete_calls = [call[0][0] for call in mock_cache.delete.call_args_list]
            for expected_key in expected_cache_keys:
                self.assertIn(expected_key, delete_calls)


class DealRepositoryIntegrationTest(TestCase):
    """Integration tests for DealRepository with actual database"""

    def setUp(self):
        """Set up test data"""
        self.repository = DealRepository()
        self.user = User.objects.create_user(
            email='test@example.com',
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

    def tearDown(self):
        """Clean up after tests"""
        cache.clear()

    def test_create_and_retrieve_deal(self):
        """Test creating and retrieving a deal"""
        # Arrange & Act
        deal = Deal.objects.create(
            title='Test Deal',
            value=Decimal('10000.00'),
            stage='qualified',
            expected_close_date=date.today() + timedelta(days=30),
            contact=self.contact,
            owner=self.user
        )

        # Retrieve through repository
        retrieved = self.repository.get_by_id(deal.id)

        # Assert
        self.assertEqual(retrieved.title, 'Test Deal')
        self.assertEqual(retrieved.value, Decimal('10000.00'))
        self.assertEqual(retrieved.stage, 'qualified')

    def test_get_deals_by_stage_integration(self):
        """Test getting deals by stage with actual database"""
        # Arrange
        Deal.objects.create(
            title='Qualified Deal 1',
            value=Decimal('5000.00'),
            stage='qualified',
            expected_close_date=date.today() + timedelta(days=30),
            contact=self.contact,
            owner=self.user
        )
        Deal.objects.create(
            title='Qualified Deal 2',
            value=Decimal('7500.00'),
            stage='qualified',
            expected_close_date=date.today() + timedelta(days=45),
            contact=self.contact,
            owner=self.user
        )
        Deal.objects.create(
            title='Won Deal',
            value=Decimal('12000.00'),
            stage='closed_won',
            expected_close_date=date.today() + timedelta(days=60),
            contact=self.contact,
            owner=self.user
        )

        # Act
        qualified_deals = self.repository.get_by_stage('qualified', self.user.id)

        # Assert
        self.assertEqual(len(qualified_deals), 2)

    def test_search_deals_integration(self):
        """Test searching deals with actual database"""
        # Arrange
        Deal.objects.create(
            title='Software License',
            value=Decimal('10000.00'),
            stage='qualified',
            expected_close_date=date.today() + timedelta(days=30),
            contact=self.contact,
            owner=self.user
        )
        Deal.objects.create(
            title='Consulting Services',
            value=Decimal('5000.00'),
            stage='proposal',
            expected_close_date=date.today() + timedelta(days=20),
            contact=self.contact,
            owner=self.user
        )

        # Act
        results = self.repository.search_deals('Software', self.user.id)

        # Assert
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].title, 'Software License')

    def test_update_deal_stage_integration(self):
        """Test updating deal stage with actual database"""
        # Arrange
        deal = Deal.objects.create(
            title='Test Deal',
            value=Decimal('10000.00'),
            stage='qualified',
            expected_close_date=date.today() + timedelta(days=30),
            contact=self.contact,
            owner=self.user
        )

        # Act
        success = self.repository.update_deal_stage(deal.id, 'proposal', self.user.id)

        # Retrieve updated deal
        updated_deal = Deal.objects.get(id=deal.id)

        # Assert
        self.assertTrue(success)
        self.assertEqual(updated_deal.stage, 'proposal')

    def test_close_deal_as_won_integration(self):
        """Test closing deal as won with actual database"""
        # Arrange
        deal = Deal.objects.create(
            title='Test Deal',
            value=Decimal('10000.00'),
            stage='negotiation',
            expected_close_date=date.today() + timedelta(days=30),
            contact=self.contact,
            owner=self.user
        )

        # Act
        success = self.repository.close_deal_as_won(deal.id, Decimal('11000.00'))

        # Retrieve updated deal
        updated_deal = Deal.objects.get(id=deal.id)

        # Assert
        self.assertTrue(success)
        self.assertEqual(updated_deal.stage, 'closed_won')
        self.assertEqual(updated_deal.closed_value, Decimal('11000.00'))
        self.assertIsNotNone(updated_deal.closed_date)

    def test_get_deal_statistics_integration(self):
        """Test getting deal statistics with actual database"""
        # Arrange
        # Create deals with different stages
        Deal.objects.create(
            title='Open Deal 1',
            value=Decimal('5000.00'),
            stage='qualified',
            expected_close_date=date.today() + timedelta(days=30),
            contact=self.contact,
            owner=self.user
        )
        Deal.objects.create(
            title='Open Deal 2',
            value=Decimal('7500.00'),
            stage='proposal',
            expected_close_date=date.today() + timedelta(days=20),
            contact=self.contact,
            owner=self.user
        )
        Deal.objects.create(
            title='Won Deal',
            value=Decimal('12000.00'),
            stage='closed_won',
            expected_close_date=date.today() + timedelta(days=60),
            contact=self.contact,
            owner=self.user
        )
        Deal.objects.create(
            title='Lost Deal',
            value=Decimal('3000.00'),
            stage='closed_lost',
            expected_close_date=date.today() + timedelta(days=15),
            contact=self.contact,
            owner=self.user
        )

        # Act
        stats = self.repository.get_deal_statistics(self.user.id)

        # Assert
        self.assertEqual(stats['total_deals'], 4)
        self.assertEqual(stats['open_deals'], 2)
        self.assertEqual(stats['won_deals'], 1)
        self.assertEqual(stats['lost_deals'], 1)
        self.assertEqual(stats['conversion_rate'], 25.0)  # 1 won out of 4 total