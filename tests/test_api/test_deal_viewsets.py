"""
Deal ViewSet Tests - TDD Approach
Testing comprehensive CRUD operations and business logic
Following SOLID principles and comprehensive test coverage
"""

import pytest
from decimal import Decimal
from datetime import date, timedelta, datetime
from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from rest_framework.exceptions import NotAuthenticated, PermissionDenied

from crm.apps.deals.models import Deal, DealStageHistory
from crm.apps.contacts.models import Contact
from crm.apps.deals.serializers import DealSerializer, DealDetailSerializer
from crm.apps.deals.viewsets import DealViewSet

User = get_user_model()


class DealViewSetTestCase(APITestCase):
    """Base test case for Deal ViewSet tests"""

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

        self.contact = Contact.objects.create(
            first_name='John',
            last_name='Doe',
            email='john.doe@example.com',
            owner=self.user
        )

        tomorrow = date.today() + timedelta(days=30)
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

        self.deal = Deal.objects.create(**self.deal_data)

        # URL patterns
        self.list_url = reverse('deal-list')
        self.detail_url = reverse('deal-detail', kwargs={'pk': self.deal.id})


class DealViewSetAuthenticationTests(DealViewSetTestCase):
    """Test authentication requirements for Deal ViewSet"""

    def test_unauthenticated_access_denied(self):
        """Test that unauthenticated users cannot access deal endpoints"""
        client = APIClient()

        # Test list access
        response = client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Test detail access
        response = client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Test create access
        response = client.post(self.list_url, self.deal_data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_access_allowed(self):
        """Test that authenticated users can access deal endpoints"""
        client = APIClient()
        client.force_authenticate(user=self.user)

        # Test list access
        response = client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Test detail access
        response = client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class DealViewSetListTests(DealViewSetTestCase):
    """Test Deal ViewSet list operations"""

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(user=self.user)

    def test_list_deals_returns_user_deals_only(self):
        """Test list endpoint returns only deals owned by the user"""
        # Create deals for different users
        other_user = User.objects.create_user(
            email='other@example.com',
            password='otherpass123',
            first_name='Other',
            last_name='User'
        )

        other_contact = Contact.objects.create(
            first_name='Other',
            last_name='Contact',
            email='other.contact@example.com',
            owner=other_user
        )

        Deal.objects.create(
            owner=other_user,
            contact=other_contact,
            title='Other Deal',
            value=Decimal('5000.00'),
            stage='prospect',
            expected_close_date=date.today() + timedelta(days=30)
        )

        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(len(data['results']), 1)
        self.assertEqual(data['results'][0]['id'], self.deal.id)

    def test_list_deals_with_pagination(self):
        """Test list endpoint respects pagination"""
        # Create additional deals
        for i in range(25):
            Deal.objects.create(
                owner=self.user,
                contact=self.contact,
                title=f'Deal {i}',
                value=Decimal(f'{(i+1)*1000}.00'),
                stage='prospect',
                expected_close_date=date.today() + timedelta(days=30)
            )

        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertIn('results', data)
        self.assertIn('count', data)
        self.assertIn('next', data)
        self.assertIn('previous', data)
        self.assertEqual(len(data['results']), 20)  # Default page size

    def test_list_deals_with_search(self):
        """Test list endpoint with search functionality"""
        # Create additional deals
        Deal.objects.create(
            owner=self.user,
            contact=self.contact,
            title='Enterprise Deal',
            value=Decimal('50000.00'),
            stage='proposal',
            expected_close_date=date.today() + timedelta(days=30)
        )

        # Search by title
        response = self.client.get(f'{self.list_url}?search=enterprise')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(len(data['results']), 1)
        self.assertEqual(data['results'][0]['title'], 'Enterprise Deal')

        # Search by value (should work on numeric fields)
        response = self.client.get(f'{self.list_url}?search=50000')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(len(data['results']), 1)

    def test_list_deals_with_filtering(self):
        """Test list endpoint with filtering"""
        # Create deals with different stages and values
        large_deal = Deal.objects.create(
            owner=self.user,
            contact=self.contact,
            title='Large Deal',
            value=Decimal('100000.00'),
            stage='negotiation',
            expected_close_date=date.today() + timedelta(days=30)
        )

        # Filter by stage
        response = self.client.get(f'{self.list_url}?stage=qualified')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        deal_ids = [deal['id'] for deal in data['results']]
        self.assertIn(self.deal.id, deal_ids)
        self.assertNotIn(large_deal.id, deal_ids)

        # Filter by currency
        response = self.client.get(f'{self.list_url}?currency=USD')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(len(data['results']), 2)  # Both deals are USD

    def test_list_deals_with_ordering(self):
        """Test list endpoint with ordering"""
        # Create deals with different values
        small_deal = Deal.objects.create(
            owner=self.user,
            contact=self.contact,
            title='Small Deal',
            value=Decimal('1000.00'),
            stage='prospect',
            expected_close_date=date.today() + timedelta(days=30)
        )

        large_deal = Deal.objects.create(
            owner=self.user,
            contact=self.contact,
            title='Large Deal',
            value=Decimal('100000.00'),
            stage='negotiation',
            expected_close_date=date.today() + timedelta(days=30)
        )

        # Order by value ascending
        response = self.client.get(f'{self.list_url}?ordering=value')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        values = [deal['value'] for deal in data['results']]
        self.assertEqual(values, sorted(values))

        # Order by value descending
        response = self.client.get(f'{self.list_url}?ordering=-value')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        values = [deal['value'] for deal in data['results']]
        self.assertEqual(values, sorted(values, reverse=True))

    def test_list_deals_serializer_selection(self):
        """Test appropriate serializer is used for list view"""
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        deal = data['results'][0]

        # Should include basic fields
        self.assertIn('id', deal)
        self.assertIn('title', deal)
        self.assertIn('value', deal)
        self.assertIn('formatted_value', deal)

        # Should include summary-specific fields
        self.assertIn('pipeline_position', deal)
        self.assertIn('contact', deal)

        # Should not include verbose fields for list view
        self.assertNotIn('description', deal)
        self.assertNotIn('stage_history', deal)


class DealViewSetCreateTests(DealViewSetTestCase):
    """Test Deal ViewSet create operations"""

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(user=self.user)

    def test_create_deal_valid_data(self):
        """Test creating deal with valid data"""
        new_deal_data = {
            'title': 'New Deal',
            'description': 'This is a new deal',
            'value': '15000.00',
            'currency': 'USD',
            'stage': 'proposal',
            'expected_close_date': (date.today() + timedelta(days=60)).isoformat(),
            'contact': self.contact.id,
            'owner': self.user.id
        }

        response = self.client.post(self.list_url, new_deal_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        data = response.json()
        self.assertEqual(data['title'], 'New Deal')
        self.assertEqual(data['value'], '15000.00')
        self.assertEqual(data['stage'], 'proposal')
        self.assertEqual(data['probability'], 50)  # Auto-set based on stage

        # Verify deal was created in database
        deal = Deal.objects.get(id=data['id'])
        self.assertEqual(deal.owner, self.user)
        self.assertEqual(deal.contact, self.contact)

    def test_create_deal_invalid_data(self):
        """Test creating deal with invalid data"""
        invalid_data = {
            'title': 'Invalid Deal',
            'value': '-1000.00',  # Negative value
            'stage': 'invalid_stage',  # Invalid stage
            'expected_close_date': '2020-01-01',  # Past date
            'contact': self.contact.id,
            'owner': self.user.id
        }

        response = self.client.post(self.list_url, invalid_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        data = response.json()
        self.assertIn('value', data)
        self.assertIn('stage', data)
        self.assertIn('expected_close_date', data)

    def test_create_deal_auto_probability_assignment(self):
        """Test creating deal auto-assigns probability based on stage"""
        stages_and_probabilities = [
            ('prospect', 10),
            ('qualified', 25),
            ('proposal', 50),
            ('negotiation', 75),
            ('closed_won', 100),
            ('closed_lost', 0),
        ]

        for stage, expected_prob in stages_and_probabilities:
            deal_data = self.deal_data.copy()
            deal_data['title'] = f'Deal for {stage}'
            deal_data['stage'] = stage
            deal_data.pop('probability', None)  # Remove probability

            response = self.client.post(self.list_url, deal_data)
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

            created_deal = Deal.objects.get(id=response.json()['id'])
            self.assertEqual(created_deal.probability, expected_prob)

    def test_create_deal_sanitizes_data(self):
        """Test create endpoint sanitizes input data"""
        new_deal_data = {
            'title': '  Sanitized Deal  ',
            'description': '  This is a sanitized deal  ',
            'value': '25000.00',
            'stage': 'qualified',
            'expected_close_date': (date.today() + timedelta(days=45)).isoformat(),
            'contact': self.contact.id,
            'owner': self.user.id
        }

        response = self.client.post(self.list_url, new_deal_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        data = response.json()
        self.assertEqual(data['title'], 'Sanitized Deal')
        self.assertEqual(data['description'], 'This is a sanitized deal')

    def test_create_deal_owner_assignment(self):
        """Test deal owner is automatically set to current user"""
        new_deal_data = {
            'title': 'Owner Test Deal',
            'value': '8000.00',
            'stage': 'prospect',
            'expected_close_date': (date.today() + timedelta(days=30)).isoformat(),
            'contact': self.contact.id
        }

        response = self.client.post(self.list_url, new_deal_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        data = response.json()
        deal = Deal.objects.get(id=data['id'])
        self.assertEqual(deal.owner, self.user)

    def test_create_deal_stage_transition_validation(self):
        """Test creating deal with closed stage sets appropriate values"""
        closed_deal_data = {
            'title': 'Already Closed Deal',
            'value': '20000.00',
            'stage': 'closed_won',
            'expected_close_date': date.today().isoformat(),  # Can be past for closed deals
            'contact': self.contact.id,
            'owner': self.user.id
        }

        response = self.client.post(self.list_url, closed_deal_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        data = response.json()
        self.assertEqual(data['probability'], 100)  # Auto-set for closed won
        self.assertIsNotNone(data['closed_date'])


class DealViewSetRetrieveTests(DealViewSetTestCase):
    """Test Deal ViewSet retrieve operations"""

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(user=self.user)

    def test_retrieve_own_deal(self):
        """Test retrieving own deal"""
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(data['id'], self.deal.id)
        self.assertEqual(data['title'], 'Test Deal')
        self.assertEqual(data['value'], '10000.00')

    def test_retrieve_other_user_deal_denied(self):
        """Test retrieving other user's deal is denied"""
        other_user = User.objects.create_user(
            email='other@example.com',
            password='otherpass123',
            first_name='Other',
            last_name='User'
        )

        other_contact = Contact.objects.create(
            first_name='Other',
            last_name='Contact',
            email='other.contact@example.com',
            owner=other_user
        )

        other_deal = Deal.objects.create(
            owner=other_user,
            contact=other_contact,
            title='Other Deal',
            value=Decimal('5000.00'),
            stage='prospect',
            expected_close_date=date.today() + timedelta(days=30)
        )

        other_detail_url = reverse('deal-detail', kwargs={'pk': other_deal.id})
        response = self.client.get(other_detail_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_admin_can_access_any_deal(self):
        """Test admin can access any deal"""
        other_user = User.objects.create_user(
            email='other@example.com',
            password='otherpass123',
            first_name='Other',
            last_name='User'
        )

        other_contact = Contact.objects.create(
            first_name='Other',
            last_name='Contact',
            email='other.contact@example.com',
            owner=other_user
        )

        other_deal = Deal.objects.create(
            owner=other_user,
            contact=other_contact,
            title='Other Deal',
            value=Decimal('5000.00'),
            stage='prospect',
            expected_close_date=date.today() + timedelta(days=30)
        )

        admin_client = APIClient()
        admin_client.force_authenticate(user=self.admin_user)

        other_detail_url = reverse('deal-detail', kwargs={'pk': other_deal.id})
        response = admin_client.get(other_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(data['id'], other_deal.id)

    def test_retrieve_nonexistent_deal(self):
        """Test retrieving non-existent deal returns 404"""
        fake_url = reverse('deal-detail', kwargs={'pk': 99999})
        response = self.client.get(fake_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_uses_detail_serializer(self):
        """Test retrieve endpoint uses detail serializer"""
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        # Should include detail-specific fields
        self.assertIn('stage_history', data)
        self.assertIn('contact_details', data)
        self.assertIn('owner_details', data)
        self.assertIn('days_in_pipeline', data)
        self.assertIn('days_to_close', data)


class DealViewSetUpdateTests(DealViewSetTestCase):
    """Test Deal ViewSet update operations"""

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(user=self.user)

    def test_update_own_deal(self):
        """Test updating own deal"""
        update_data = {
            'title': 'Updated Deal Title',
            'probability': 75,
            'stage': 'negotiation'
        }

        response = self.client.patch(self.detail_url, update_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(data['title'], 'Updated Deal Title')
        self.assertEqual(data['probability'], 75)
        self.assertEqual(data['stage'], 'negotiation')

    def test_update_stage_creates_history(self):
        """Test updating deal stage creates stage history"""
        update_data = {'stage': 'proposal'}

        response = self.client.patch(self.detail_url, update_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check stage history was created
        stage_history = DealStageHistory.objects.filter(deal=self.deal).first()
        self.assertIsNotNone(stage_history)
        self.assertEqual(stage_history.old_stage, 'qualified')
        self.assertEqual(stage_history.new_stage, 'proposal')
        self.assertEqual(stage_history.changed_by, self.user)

    def test_update_close_deal_sets_closed_date(self):
        """Test updating deal to closed stage sets closed date"""
        update_data = {
            'stage': 'closed_won',
            'closed_value': '12000.00'
        }

        response = self.client.patch(self.detail_url, update_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(data['stage'], 'closed_won')
        self.assertEqual(data['probability'], 100)  # Auto-set
        self.assertEqual(data['closed_value'], '12000.00')
        self.assertIsNotNone(data['closed_date'])

    def test_update_other_user_deal_denied(self):
        """Test updating other user's deal is denied"""
        other_user = User.objects.create_user(
            email='other@example.com',
            password='otherpass123',
            first_name='Other',
            last_name='User'
        )

        other_contact = Contact.objects.create(
            first_name='Other',
            last_name='Contact',
            email='other.contact@example.com',
            owner=other_user
        )

        other_deal = Deal.objects.create(
            owner=other_user,
            contact=other_contact,
            title='Other Deal',
            value=Decimal('5000.00'),
            stage='prospect',
            expected_close_date=date.today() + timedelta(days=30)
        )

        other_detail_url = reverse('deal-detail', kwargs={'pk': other_deal.id})
        update_data = {'title': 'Updated'}

        response = self.client.patch(other_detail_url, update_data)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_deal_invalid_data(self):
        """Test updating deal with invalid data"""
        update_data = {
            'value': '-5000.00',
            'probability': 150,
            'stage': 'invalid_stage'
        }

        response = self.client.patch(self.detail_url, update_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        data = response.json()
        self.assertIn('value', data)
        self.assertIn('probability', data)
        self.assertIn('stage', data)

    def test_admin_can_update_any_deal(self):
        """Test admin can update any deal"""
        other_user = User.objects.create_user(
            email='other@example.com',
            password='otherpass123',
            first_name='Other',
            last_name='User'
        )

        other_contact = Contact.objects.create(
            first_name='Other',
            last_name='Contact',
            email='other.contact@example.com',
            owner=other_user
        )

        other_deal = Deal.objects.create(
            owner=other_user,
            contact=other_contact,
            title='Other Deal',
            value=Decimal('5000.00'),
            stage='prospect',
            expected_close_date=date.today() + timedelta(days=30)
        )

        admin_client = APIClient()
        admin_client.force_authenticate(user=self.admin_user)

        other_detail_url = reverse('deal-detail', kwargs={'pk': other_deal.id})
        update_data = {'title': 'Admin Updated'}

        response = admin_client.patch(other_detail_url, update_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(data['title'], 'Admin Updated')


class DealViewSetDeleteTests(DealViewSetTestCase):
    """Test Deal ViewSet delete operations"""

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(user=self.user)

    def test_delete_own_deal(self):
        """Test deleting own deal"""
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Deal should be deleted (hard delete)
        with self.assertRaises(Deal.DoesNotExist):
            Deal.objects.get(id=self.deal.id)

    def test_delete_other_user_deal_denied(self):
        """Test deleting other user's deal is denied"""
        other_user = User.objects.create_user(
            email='other@example.com',
            password='otherpass123',
            first_name='Other',
            last_name='User'
        )

        other_contact = Contact.objects.create(
            first_name='Other',
            last_name='Contact',
            email='other.contact@example.com',
            owner=other_user
        )

        other_deal = Deal.objects.create(
            owner=other_user,
            contact=other_contact,
            title='Other Deal',
            value=Decimal('5000.00'),
            stage='prospect',
            expected_close_date=date.today() + timedelta(days=30)
        )

        other_detail_url = reverse('deal-detail', kwargs={'pk': other_deal.id})
        response = self.client.delete(other_detail_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Deal should still exist
        self.assertTrue(Deal.objects.filter(id=other_deal.id).exists())

    def test_admin_can_delete_any_deal(self):
        """Test admin can delete any deal"""
        other_user = User.objects.create_user(
            email='other@example.com',
            password='otherpass123',
            first_name='Other',
            last_name='User'
        )

        other_contact = Contact.objects.create(
            first_name='Other',
            last_name='Contact',
            email='other.contact@example.com',
            owner=other_user
        )

        other_deal = Deal.objects.create(
            owner=other_user,
            contact=other_contact,
            title='Other Deal',
            value=Decimal('5000.00'),
            stage='prospect',
            expected_close_date=date.today() + timedelta(days=30)
        )

        admin_client = APIClient()
        admin_client.force_authenticate(user=self.admin_user)

        other_detail_url = reverse('deal-detail', kwargs={'pk': other_deal.id})
        response = admin_client.delete(other_detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Deal should be deleted
        with self.assertRaises(Deal.DoesNotExist):
            Deal.objects.get(id=other_deal.id)


class DealViewSetCustomActionsTests(DealViewSetTestCase):
    """Test Deal ViewSet custom actions"""

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(user=self.user)

    def test_change_stage_action(self):
        """Test change stage action"""
        change_stage_url = reverse('deal-change-stage', kwargs={'pk': self.deal.id})
        stage_data = {'new_stage': 'proposal'}

        response = self.client.post(change_stage_url, stage_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertIn('message', data)
        self.assertEqual(data['new_stage'], 'proposal')

        # Verify stage was changed
        self.deal.refresh_from_db()
        self.assertEqual(self.deal.stage, 'proposal')
        self.assertEqual(self.deal.probability, 50)  # Auto-updated

    def test_close_deal_action(self):
        """Test close deal action"""
        close_url = reverse('deal-close', kwargs={'pk': self.deal.id})
        close_data = {
            'outcome': 'won',
            'final_value': '12000.00',
            'notes': 'Successfully closed deal'
        }

        response = self.client.post(close_url, close_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertIn('message', data)
        self.assertEqual(data['outcome'], 'won')

        # Verify deal was closed
        self.deal.refresh_from_db()
        self.assertEqual(self.deal.stage, 'closed_won')
        self.assertEqual(self.deal.probability, 100)
        self.assertEqual(self.deal.closed_value, Decimal('12000.00'))
        self.assertIsNotNone(self.deal.closed_date)

    def test_bulk_operations_action(self):
        """Test bulk operations action"""
        # Create additional deals
        deal2 = Deal.objects.create(
            owner=self.user,
            contact=self.contact,
            title='Second Deal',
            value=Decimal('8000.00'),
            stage='prospect',
            expected_close_date=date.today() + timedelta(days=30)
        )

        bulk_url = reverse('deal-bulk-operations')
        bulk_data = {
            'deal_ids': [self.deal.id, deal2.id],
            'operation': 'stage_change',
            'new_stage': 'proposal'
        }

        response = self.client.post(bulk_url, bulk_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertIn('message', data)
        self.assertEqual(data['updated_count'], 2)

        # Verify deals were updated
        self.deal.refresh_from_db()
        deal2.refresh_from_db()
        self.assertEqual(self.deal.stage, 'proposal')
        self.assertEqual(deal2.stage, 'proposal')

    def test_pipeline_statistics_action(self):
        """Test pipeline statistics action"""
        stats_url = reverse('deal-pipeline-statistics')
        response = self.client.get(stats_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertIn('total_deals', data)
        self.assertIn('total_value', data)
        self.assertIn('average_deal_size', data)
        self.assertIn('win_rate', data)
        self.assertIn('deals_by_stage', data)

    def test_deal_forecast_action(self):
        """Test deal forecast action"""
        forecast_url = reverse('deal-forecast')
        response = self.client.get(f'{forecast_url}?period=current_quarter')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertIn('forecast_value', data)
        self.assertIn('confidence_level', data)
        self.assertIn('deals_count', data)
        self.assertIn('weighted_value', data)

    def test_get_deal_activities_action(self):
        """Test get deal activities action"""
        from crm.apps.activities.models import Activity
        activity = Activity.objects.create(
            owner=self.user,
            contact=self.contact,
            deal=self.deal,
            type='call',
            title='Deal discussion call',
            scheduled_at=timezone.now() + timedelta(hours=1)
        )

        activities_url = reverse('deal-activities', kwargs={'pk': self.deal.id})
        response = self.client.get(activities_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['id'], activity.id)


class DealViewSetIntegrationTests(DealViewSetTestCase):
    """Integration tests for Deal ViewSet"""

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(user=self.user)

    def test_full_crud_workflow(self):
        """Test complete CRUD workflow"""
        # Create
        create_data = {
            'title': 'Workflow Deal',
            'value': '25000.00',
            'stage': 'qualified',
            'expected_close_date': (date.today() + timedelta(days=45)).isoformat(),
            'contact': self.contact.id
        }

        response = self.client.post(self.list_url, create_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        deal_data = response.json()
        deal_id = deal_data['id']

        # Retrieve
        detail_url = reverse('deal-detail', kwargs={'pk': deal_id})
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Update
        update_data = {'stage': 'proposal', 'probability': 50}
        response = self.client.patch(detail_url, update_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Delete
        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Verify deletion
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_deal_stage_progression_workflow(self):
        """Test deal progression through stages"""
        # Create initial deal
        create_data = {
            'title': 'Progression Deal',
            'value': '30000.00',
            'stage': 'prospect',
            'expected_close_date': (date.today() + timedelta(days=60)).isoformat(),
            'contact': self.contact.id
        }

        response = self.client.post(self.list_url, create_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        deal_data = response.json()
        deal_id = deal_data['id']
        detail_url = reverse('deal-detail', kwargs={'pk': deal_id})

        # Progress through stages
        stages = ['qualified', 'proposal', 'negotiation', 'closed_won']
        expected_probabilities = [25, 50, 75, 100]

        for stage, expected_prob in zip(stages, expected_probabilities):
            update_data = {'stage': stage}
            response = self.client.patch(detail_url, update_data)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            updated_data = response.json()
            self.assertEqual(updated_data['stage'], stage)
            self.assertEqual(updated_data['probability'], expected_prob)

        # Verify stage history was created for each change
        stage_history_count = DealStageHistory.objects.filter(deal_id=deal_id).count()
        self.assertEqual(stage_history_count, len(stages))

    def test_error_handling_consistency(self):
        """Test consistent error handling across endpoints"""
        # Test with invalid data
        invalid_data = {
            'value': 'invalid_value',
            'stage': 'invalid_stage'
        }

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