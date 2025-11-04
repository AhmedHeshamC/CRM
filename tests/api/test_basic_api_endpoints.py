"""
Basic API Endpoint Tests
Following TDD, SOLID, and KISS principles

Red-Green-Refactor approach:
1. RED: Write failing API tests
2. GREEN: Implement minimal API to pass tests
3. REFACTOR: Improve API structure and error handling
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


class TestUserAuthAPI(TestCase):
    """
    Test User Authentication API endpoints
    Following KISS principle - simple, focused tests
    """

    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        self.user_data = {
            'email': 'test@example.com',
            'password': 'TestPass123!',
            'password_confirm': 'TestPass123!',
            'first_name': 'Test',
            'last_name': 'User'
        }

    def test_user_registration_api(self):
        """
        RED: Test user registration endpoint
        This should drive the user registration API implementation
        """
        url = reverse('user-register')  # This URL doesn't exist yet

        response = self.client.post(url, self.user_data, format='json')

        
        # Test successful registration
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertEqual(response.data['user']['email'], self.user_data['email'])

        # Verify user was created in database
        user = User.objects.get(email=self.user_data['email'])
        self.assertEqual(user.first_name, self.user_data['first_name'])

    def test_user_login_api(self):
        """
        RED: Test user login endpoint
        This should drive the user login API implementation
        """
        # Create user first
        user = User.objects.create_user(
            email=self.user_data['email'],
            password=self.user_data['password'],
            first_name=self.user_data['first_name'],
            last_name=self.user_data['last_name']
        )

        url = reverse('user-login')  # This URL doesn't exist yet
        login_data = {
            'email': self.user_data['email'],
            'password': self.user_data['password']
        }

        response = self.client.post(url, login_data, format='json')

        # Test successful login
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertEqual(response.data['user']['email'], self.user_data['email'])

    def test_user_profile_api(self):
        """
        RED: Test user profile endpoint
        This should drive the user profile API implementation
        """
        # Create and authenticate user
        user = User.objects.create_user(
            email='profile@example.com',
            password='TestPass123!',
            first_name='Profile',
            last_name='User'
        )

        # Get JWT token
        refresh = RefreshToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

        url = reverse('user-profile')  # This URL doesn't exist yet

        response = self.client.get(url)

        # Test profile retrieval
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'profile@example.com')
        self.assertEqual(response.data['first_name'], 'Profile')
        self.assertEqual(response.data['last_name'], 'User')


class TestContactAPI(TestCase):
    """
    Test Contact API endpoints
    Following SOLID Single Responsibility principle
    """

    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='contact@example.com',
            password='TestPass123!',
            first_name='Contact',
            last_name='Manager'
        )

        # Authenticate user
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

        self.contact_data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john@example.com',
            'phone': '+1-555-555-0123',
            'company': 'Test Corp'
        }

    def test_create_contact_api(self):
        """
        RED: Test contact creation endpoint
        This should drive the contact creation API implementation
        """
        url = reverse('contact-list-simple')  # This URL doesn't exist yet

        response = self.client.post(url, self.contact_data, format='json')

        # Test successful creation
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['first_name'], self.contact_data['first_name'])
        self.assertEqual(response.data['email'], self.contact_data['email'])
        self.assertEqual(response.data['owner'], self.user.id)

    def test_list_contacts_api(self):
        """
        RED: Test contact listing endpoint
        This should drive the contact listing API implementation
        """
        from crm.apps.contacts.models import Contact

        # Create test contacts
        Contact.objects.create(
            first_name='Jane',
            last_name='Smith',
            email='jane@example.com',
            owner=self.user
        )

        Contact.objects.create(
            first_name='Bob',
            last_name='Johnson',
            email='bob@example.com',
            owner=self.user
        )

        url = reverse('contact-list-simple')  # This URL doesn't exist yet

        response = self.client.get(url)

        # Test successful listing
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(response.data['count'], 2)

    def test_get_contact_detail_api(self):
        """
        RED: Test contact detail endpoint
        This should drive the contact detail API implementation
        """
        from crm.apps.contacts.models import Contact

        contact = Contact.objects.create(
            first_name='Detail',
            last_name='Test',
            email='detail@example.com',
            owner=self.user
        )

        url = reverse('contact-detail-simple', kwargs={'pk': contact.pk})  # This URL doesn't exist yet

        response = self.client.get(url)

        # Test successful detail retrieval
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], contact.id)
        self.assertEqual(response.data['email'], 'detail@example.com')

    def test_update_contact_api(self):
        """
        RED: Test contact update endpoint
        This should drive the contact update API implementation
        """
        from crm.apps.contacts.models import Contact

        contact = Contact.objects.create(
            first_name='Update',
            last_name='Test',
            email='update@example.com',
            owner=self.user
        )

        url = reverse('contact-detail-simple', kwargs={'pk': contact.pk})  # This URL doesn't exist yet
        update_data = {
            'first_name': 'Updated',
            'last_name': 'Name',
            'email': 'updated@example.com'
        }

        response = self.client.patch(url, update_data, format='json')

        # Test successful update
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['first_name'], 'Updated')
        self.assertEqual(response.data['email'], 'updated@example.com')

    def test_delete_contact_api(self):
        """
        RED: Test contact deletion endpoint (soft delete)
        This should drive the contact soft delete API implementation
        """
        from crm.apps.contacts.models import Contact

        contact = Contact.objects.create(
            first_name='Delete',
            last_name='Test',
            email='delete@example.com',
            owner=self.user
        )

        url = reverse('contact-detail-simple', kwargs={'pk': contact.pk})  # This URL doesn't exist yet

        response = self.client.delete(url)

        # Test successful soft delete
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Verify contact is soft deleted
        self.assertFalse(Contact.objects.filter(id=contact.id).exists())
        self.assertTrue(Contact.all_objects.filter(id=contact.id).exists())


class TestDealAPI(TestCase):
    """
    Test Deal API endpoints
    Following KISS principle - simple, focused tests
    """

    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='deal@example.com',
            password='TestPass123!',
            first_name='Deal',
            last_name='Manager'
        )

        # Authenticate user
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

        # Create contact for deal
        from crm.apps.contacts.models import Contact
        self.contact = Contact.objects.create(
            first_name='Deal',
            last_name='Contact',
            email='dealcontact@example.com',
            owner=self.user
        )

        self.deal_data = {
            'title': 'Test Deal',
            'description': 'A test deal for API testing',
            'value': '50000.00',
            'currency': 'USD',
            'stage': 'prospect',
            'probability': 25,
            'expected_close_date': '2025-12-31',
            'contact': self.contact.id
        }

    def test_create_deal_api(self):
        """
        RED: Test deal creation endpoint
        This should drive the deal creation API implementation
        """
        url = '/api/v1/deals/'  # Simple URL path for now

        response = self.client.post(url, self.deal_data, format='json')

        # Test successful creation
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['title'], self.deal_data['title'])
        self.assertEqual(response.data['value'], self.deal_data['value'])
        self.assertEqual(response.data['owner'], self.user.id)

    def test_list_deals_api(self):
        """
        RED: Test deal listing endpoint
        This should drive the deal listing API implementation
        """
        from crm.apps.deals.models import Deal

        # Create test deals
        Deal.objects.create(
            title='Deal 1',
            value=25000.00,
            stage='prospect',
            expected_close_date='2024-12-31',
            contact=self.contact,
            owner=self.user
        )

        Deal.objects.create(
            title='Deal 2',
            value=75000.00,
            stage='qualified',
            expected_close_date='2024-11-30',
            contact=self.contact,
            owner=self.user
        )

        url = '/api/v1/deals/'  # Simple URL path for now

        response = self.client.get(url)

        # Test successful listing
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(response.data['count'], 2)

    def test_update_deal_stage_api(self):
        """
        RED: Test deal stage update endpoint
        This should drive the deal stage update API implementation
        """
        from crm.apps.deals.models import Deal

        deal = Deal.objects.create(
            title='Stage Test Deal',
            value=50000.00,
            stage='prospect',
            expected_close_date='2024-12-31',
            contact=self.contact,
            owner=self.user
        )

        url = f'/api/v1/deals/{deal.pk}/'  # Simple URL path for now
        update_data = {'stage': 'qualified'}

        response = self.client.patch(url, update_data, format='json')

        # Test successful stage update
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['stage'], 'qualified')

        # Verify stage change was tracked
        deal.refresh_from_db()
        self.assertEqual(deal.stage, 'qualified')


class TestActivityAPI(TestCase):
    """
    Test Activity API endpoints
    Following SOLID Single Responsibility principle
    """

    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='activity@example.com',
            password='TestPass123!',
            first_name='Activity',
            last_name='Manager'
        )

        # Authenticate user
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

        # Create contact and deal for activity
        from crm.apps.contacts.models import Contact
        from crm.apps.deals.models import Deal

        self.contact = Contact.objects.create(
            first_name='Activity',
            last_name='Contact',
            email='activity@example.com',
            owner=self.user
        )

        self.deal = Deal.objects.create(
            title='Activity Deal',
            value=25000.00,
            stage='qualified',
            expected_close_date='2024-12-31',
            contact=self.contact,
            owner=self.user
        )

        self.activity_data = {
            'type': 'call',
            'title': 'Test Call',
            'description': 'Test call description',
            'contact': self.contact.id,
            'deal': self.deal.id,
            'scheduled_at': '2025-11-15T14:30:00Z',
            'duration_minutes': 30
        }

    def test_create_activity_api(self):
        """
        RED: Test activity creation endpoint
        This should drive the activity creation API implementation
        """
        url = '/api/v1/activities/'  # Simple URL path for now

        response = self.client.post(url, self.activity_data, format='json')

        # Test successful creation
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['title'], self.activity_data['title'])
        self.assertEqual(response.data['type_display'], 'Phone Call')  # Display value
        self.assertEqual(response.data['owner'], self.user.id)

    def test_list_activities_api(self):
        """
        RED: Test activity listing endpoint
        This should drive the activity listing API implementation
        """
        from crm.apps.activities.models import Activity
        from django.utils import timezone

        # Create test activities
        Activity.objects.create(
            type='call',
            title='Call 1',
            contact=self.contact,
            deal=self.deal,
            owner=self.user,
            scheduled_at=timezone.now() + timezone.timedelta(hours=1)
        )

        Activity.objects.create(
            type='meeting',
            title='Meeting 1',
            contact=self.contact,
            deal=self.deal,
            owner=self.user,
            scheduled_at=timezone.now() + timezone.timedelta(days=1)
        )

        url = '/api/v1/activities/'  # Simple URL path for now

        response = self.client.get(url)

        # Test successful listing
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(response.data['count'], 2)