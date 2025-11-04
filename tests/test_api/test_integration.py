"""
API Integration Tests - Complete CRM Workflow Testing
Testing comprehensive API endpoint interactions and business logic
Following SOLID principles and comprehensive test coverage
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from crm.apps.authentication.models import User, UserProfile
from crm.apps.contacts.models import Contact, ContactInteraction
from crm.apps.deals.models import Deal, DealStageHistory
from crm.apps.activities.models import Activity, ActivityComment

User = get_user_model()


class CRMIntegrationTestCase(APITestCase):
    """Base test case for CRM integration tests"""

    def setUp(self):
        """Set up test data for integration testing"""
        # Create users with different roles
        self.admin_user = User.objects.create_user(
            email='admin@example.com',
            password='adminpass123',
            first_name='Admin',
            last_name='User',
            role='admin',
            is_staff=True,
            is_superuser=True
        )

        self.manager_user = User.objects.create_user(
            email='manager@example.com',
            password='managerpass123',
            first_name='Manager',
            last_name='User',
            role='manager'
        )

        self.sales_user = User.objects.create_user(
            email='sales@example.com',
            password='salespass123',
            first_name='Sales',
            last_name='User',
            role='sales'
        )

        # Create contacts
        self.contact1 = Contact.objects.create(
            first_name='John',
            last_name='Doe',
            email='john.doe@example.com',
            phone='+1-555-123-4567',
            company='Acme Corp',
            title='CEO',
            tags=['vip', 'prospect'],
            owner=self.sales_user
        )

        self.contact2 = Contact.objects.create(
            first_name='Jane',
            last_name='Smith',
            email='jane.smith@example.com',
            phone='+1-555-987-6543',
            company='Tech Solutions',
            title='CTO',
            tags=['prospect', 'technology'],
            owner=self.sales_user
        )

        # Create deals
        self.deal1 = Deal.objects.create(
            title='Enterprise Deal',
            description='Large enterprise software license',
            value=Decimal('50000.00'),
            currency='USD',
            stage='qualified',
            probability=25,
            expected_close_date=timezone.now().date() + timedelta(days=90),
            contact=self.contact1,
            owner=self.sales_user
        )

        self.deal2 = Deal.objects.create(
            title='SMB Deal',
            description='Small business solution package',
            value=Decimal('10000.00'),
            currency='USD',
            stage='proposal',
            probability=50,
            expected_close_date=timezone.now().date() + timedelta(days=60),
            contact=self.contact2,
            owner=self.sales_user
        )

        # Create activities
        tomorrow = timezone.now() + timedelta(days=1)
        self.activity1 = Activity.objects.create(
            owner=self.sales_user,
            contact=self.contact1,
            deal=self.deal1,
            type='call',
            title='Initial Consultation',
            description='Discovery call with client',
            scheduled_at=tomorrow,
            duration_minutes=60,
            priority='high',
            location='Conference Room A'
        )

        self.activity2 = Activity.objects.create(
            owner=self.sales_user,
            contact=self.contact2,
            type='email',
            title='Follow-up Email',
            description='Send proposal information',
            scheduled_at=timezone.now() + timedelta(hours=2),
            priority='medium'
        )


class UserAuthenticationIntegrationTests(CRMIntegrationTestCase):
    """Test user authentication and authorization integration"""

    def test_complete_user_lifecycle(self):
        """Test complete user lifecycle from registration to API usage"""
        client = APIClient()

        # 1. Register new user
        registration_data = {
            'email': 'newuser@example.com',
            'first_name': 'New',
            'last_name': 'User',
            'password': 'securepass123',
            'password_confirm': 'securepass123',
            'role': 'sales'
        }

        response = client.post('/api/v1/auth/register/', registration_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        user_data = response.json()
        self.assertEqual(user_data['email'], 'newuser@example.com')

        # 2. Login user
        login_data = {
            'email': 'newuser@example.com',
            'password': 'securepass123'
        }

        response = client.post('/api/v1/auth/login/', login_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        tokens = response.json()
        access_token = tokens['access_token']
        refresh_token = tokens['refresh_token']

        # 3. Use token to access protected endpoints
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')

        # Test user can access their own profile
        response = client.get('/api/v1/users/me/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # 4. Update user profile
        profile_data = {
            'bio': 'Sales professional with 5 years experience',
            'timezone': 'America/New_York',
            'email_notifications': True
        }

        response = client.post('/api/v1/users/me/update-profile/', profile_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # 5. Change password
        password_data = {
            'old_password': 'securepass123',
            'new_password': 'newsecurepass123',
            'new_password_confirm': 'newsecurepass123'
        }

        response = client.post('/api/v1/users/me/change-password/', password_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # 6. Logout
        logout_data = {'refresh_token': refresh_token}
        response = client.post('/api/v1/auth/logout/', logout_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_role_based_access_control(self):
        """Test role-based access control across endpoints"""
        # Test admin access
        admin_client = APIClient()
        admin_client.force_authenticate(user=self.admin_user)

        response = admin_client.get('/api/v1/users/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.json()['results']), 3)  # All users

        # Test manager access
        manager_client = APIClient()
        manager_client.force_authenticate(user=self.manager_user)

        response = manager_client.get('/api/v1/users/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Test sales user limited access
        sales_client = APIClient()
        sales_client.force_authenticate(user=self.sales_user)

        response = sales_client.get('/api/v1/users/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should only see themselves or limited users
        self.assertGreaterEqual(len(response.json()['results']), 1)

    def test_cross_user_data_isolation(self):
        """Test that users cannot access other users' data"""
        # Create another sales user
        other_sales_user = User.objects.create_user(
            email='other@example.com',
            password='otherpass123',
            first_name='Other',
            last_name='Sales',
            role='sales'
        )

        # Create contact for other user
        other_contact = Contact.objects.create(
            first_name='Other',
            last_name='Contact',
            email='other.contact@example.com',
            owner=other_sales_user
        )

        # Test that main sales user cannot access other user's contact
        sales_client = APIClient()
        sales_client.force_authenticate(user=self.sales_user)

        response = sales_client.get(f'/api/v1/contacts/{other_contact.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Test that admin can access all contacts
        admin_client = APIClient()
        admin_client.force_authenticate(user=self.admin_user)

        response = admin_client.get(f'/api/v1/contacts/{other_contact.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class ContactDealActivityIntegrationTests(CRMIntegrationTestCase):
    """Test integration between contacts, deals, and activities"""

    def test_complete_sales_pipeline_workflow(self):
        """Test complete sales pipeline from contact to closed deal"""
        client = APIClient()
        client.force_authenticate(user=self.sales_user)

        # 1. Create new contact
        contact_data = {
            'first_name': 'Pipeline',
            'last_name': 'Contact',
            'email': 'pipeline@example.com',
            'company': 'Pipeline Corp',
            'title': 'Purchasing Manager',
            'tags': ['new', 'prospect'],
            'phone': '+1-555-555-5555'
        }

        response = client.post('/api/v1/contacts/', contact_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        contact = response.json()
        contact_id = contact['id']

        # 2. Create interaction with contact
        interaction_data = {
            'contact': contact_id,
            'interaction_type': 'call',
            'title': 'Initial Discovery Call',
            'description': 'Discussed pain points and requirements'
        }

        response = client.post('/api/v1/interactions/', interaction_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # 3. Create deal from contact
        deal_data = {
            'title': 'Pipeline Deal',
            'description': 'Software solution for Pipeline Corp',
            'value': '25000.00',
            'stage': 'prospect',
            'expected_close_date': (timezone.now().date() + timedelta(days=75)).isoformat(),
            'contact': contact_id
        }

        response = client.post('/api/v1/deals/', deal_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        deal = response.json()
        deal_id = deal['id']

        # 4. Create follow-up activity
        activity_data = {
            'type': 'meeting',
            'title': 'Product Demo',
            'description': 'Live demo of software features',
            'scheduled_at': (timezone.now() + timedelta(days=3)).isoformat(),
            'duration_minutes': 90,
            'priority': 'high',
            'contact': contact_id,
            'deal': deal_id,
            'location': 'Virtual Meeting Room'
        }

        response = client.post('/api/v1/activities/', activity_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        activity = response.json()
        activity_id = activity['id']

        # 5. Progress deal through stages
        stage_progression = [
            ('qualified', 'Qualified after initial call'),
            ('proposal', 'Proposal sent and reviewed'),
            ('negotiation', 'Negotiating contract terms'),
            ('closed_won', 'Deal successfully closed')
        ]

        for stage, notes in stage_progression:
            # Change deal stage
            stage_data = {'new_stage': stage}
            response = client.post(f'/api/v1/deals/{deal_id}/change-stage/', stage_data)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            # Add activity comment
            comment_data = {'comment': notes}
            response = client.post(f'/api/v1/activities/{activity_id}/add-comment/', comment_data)
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # 6. Verify final state
        response = client.get(f'/api/v1/deals/{deal_id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        final_deal = response.json()
        self.assertEqual(final_deal['stage'], 'closed_won')
        self.assertEqual(final_deal['probability'], 100)
        self.assertIsNotNone(final_deal['closed_date'])

        # 7. Verify contact has updated deal information
        response = client.get(f'/api/v1/contacts/{contact_id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        final_contact = response.json()
        self.assertEqual(final_contact['deals_count'], 1)
        self.assertGreater(float(final_contact['total_deal_value']), 0)

    def test_activity_management_across_contacts_and_deals(self):
        """Test activity creation and management across contacts and deals"""
        client = APIClient()
        client.force_authenticate(user=self.sales_user)

        # 1. Create activity with only contact
        contact_activity_data = {
            'type': 'call',
            'title': 'Check-in Call',
            'description': 'Regular check-in with existing contact',
            'scheduled_at': (timezone.now() + timedelta(hours=2)).isoformat(),
            'contact': self.contact1.id,
            'priority': 'medium'
        }

        response = client.post('/api/v1/activities/', contact_activity_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # 2. Create activity with both contact and deal
        deal_activity_data = {
            'type': 'meeting',
            'title': 'Deal Review Meeting',
            'description': 'Review deal progress and next steps',
            'scheduled_at': (timezone.now() + timedelta(days=1)).isoformat(),
            'contact': self.contact2.id,
            'deal': self.deal2.id,
            'priority': 'high',
            'location': 'Main Office'
        }

        response = client.post('/api/v1/activities/', deal_activity_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # 3. Get activities by contact
        response = client.get(f'/api/v1/activities/by-contact/?contact_id={self.contact1.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        contact_activities = response.json()
        self.assertGreater(len(contact_activities), 0)

        # 4. Get activities by deal
        response = client.get(f'/api/v1/activities/by-deal/?deal_id={self.deal2.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        deal_activities = response.json()
        self.assertGreater(len(deal_activities), 0)

        # 5. Test bulk activity operations
        # Get all activity IDs
        response = client.get('/api/v1/activities/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        all_activities = response.json()['results']
        activity_ids = [activity['id'] for activity in all_activities]

        # Bulk complete activities
        bulk_data = {
            'activity_ids': activity_ids[:3],  # Complete first 3 activities
            'operation': 'complete',
            'completion_notes': 'Bulk completed via API'
        }

        response = client.post('/api/v1/activities/bulk-operations/', bulk_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        bulk_result = response.json()
        self.assertEqual(bulk_result['updated_count'], 3)

    def test_deal_pipeline_analytics(self):
        """Test deal pipeline analytics and reporting"""
        client = APIClient()
        client.force_authenticate(user=self.sales_user)

        # 1. Get pipeline statistics
        response = client.get('/api/v1/deals/pipeline-statistics/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        stats = response.json()
        self.assertIn('total_deals', stats)
        self.assertIn('total_value', stats)
        self.assertIn('win_rate', stats)
        self.assertIn('deals_by_stage', stats)

        # 2. Get sales forecast
        response = client.get('/api/v1/deals/forecast/?period=current_quarter')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        forecast = response.json()
        self.assertIn('forecast_value', forecast)
        self.assertIn('confidence_level', forecast)
        self.assertIn('deals_count', forecast)

        # 3. Get closing soon deals
        response = client.get('/api/v1/deals/closing-soon/?days=30')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        closing_soon = response.json()
        self.assertIsInstance(closing_soon, list)

        # 4. Get stalled deals
        response = client.get('/api/v1/deals/stalled/?days=30')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        stalled = response.json()
        self.assertIsInstance(stalled, list)


class SearchAndFilteringIntegrationTests(CRMIntegrationTestCase):
    """Test search and filtering functionality across all endpoints"""

    def test_global_search_functionality(self):
        """Test search functionality across different entity types"""
        client = APIClient()
        client.force_authenticate(user=self.sales_user)

        # 1. Search contacts
        response = client.get('/api/v1/contacts/?search=Acme')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        contact_results = response.json()['results']
        self.assertGreater(len(contact_results), 0)
        # Should find contact with "Acme Corp"

        # 2. Search deals
        response = client.get('/api/v1/deals/?search=Enterprise')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        deal_results = response.json()['results']
        self.assertGreater(len(deal_results), 0)
        # Should find "Enterprise Deal"

        # 3. Search activities
        response = client.get('/api/v1/activities/?search=Consultation')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        activity_results = response.json()['results']
        self.assertGreater(len(activity_results), 0)
        # Should find activity with "Consultation"

    def test_advanced_filtering_combinations(self):
        """Test complex filtering combinations"""
        client = APIClient()
        client.force_authenticate(user=self.sales_user)

        # 1. Filter contacts by company and tags
        response = client.get('/api/v1/contacts/?company=Acme&tags=vip')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        filtered_contacts = response.json()['results']
        for contact in filtered_contacts:
            self.assertEqual(contact['company'], 'Acme Corp')
            self.assertIn('vip', contact['tags'])

        # 2. Filter deals by stage and value range
        response = client.get('/api/v1/deals/?stage=qualified&value_min=10000')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        filtered_deals = response.json()['results']
        for deal in filtered_deals:
            self.assertEqual(deal['stage'], 'qualified')
            self.assertGreaterEqual(float(deal['value']), 10000)

        # 3. Filter activities by type and priority
        response = client.get('/api/v1/activities/?type=call&priority=high')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        filtered_activities = response.json()['results']
        for activity in filtered_activities:
            self.assertEqual(activity['type'], 'call')
            self.assertEqual(activity['priority'], 'high')

    def test_sorting_and_ordering(self):
        """Test sorting and ordering functionality"""
        client = APIClient()
        client.force_authenticate(user=self.sales_user)

        # 1. Sort contacts by name
        response = client.get('/api/v1/contacts/?ordering=last_name')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        contacts = response.json()['results']
        # Verify alphabetical order
        last_names = [contact['last_name'] for contact in contacts]
        self.assertEqual(last_names, sorted(last_names))

        # 2. Sort deals by value descending
        response = client.get('/api/v1/deals/?ordering=-value')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        deals = response.json()['results']
        # Verify descending order by value
        values = [float(deal['value']) for deal in deals]
        self.assertEqual(values, sorted(values, reverse=True))

        # 3. Sort activities by scheduled time
        response = client.get('/api/v1/activities/?ordering=scheduled_at')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        activities = response.json()['results']
        # Verify chronological order
        scheduled_times = [activity['scheduled_at'] for activity in activities]
        self.assertEqual(scheduled_times, sorted(scheduled_times))


class BusinessLogicIntegrationTests(CRMIntegrationTestCase):
    """Test business logic integration across entities"""

    def test_contact_deal_relationship_consistency(self):
        """Test consistency between contact and deal relationships"""
        client = APIClient()
        client.force_authenticate(user=self.sales_user)

        # Create new contact
        contact_data = {
            'first_name=': 'Test',
            'last_name': 'Contact',
            'email': 'test.contact@example.com',
            'owner': self.sales_user.id
        }

        response = client.post('/api/v1/contacts/', contact_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        contact = response.json()
        contact_id = contact['id']

        # Create deal for contact
        deal_data = {
            'title': 'Test Deal',
            'value': '15000.00',
            'stage': 'qualified',
            'contact': contact_id,
            'owner': self.sales_user.id
        }

        response = client.post('/api/v1/deals/', deal_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Verify contact shows updated deal count
        response = client.get(f'/api/v1/contacts/{contact_id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        updated_contact = response.json()
        self.assertEqual(updated_contact['deals_count'], 1)
        self.assertEqual(updated_contact['total_deal_value'], '15000.00')

    def test_activity_reminder_automation(self):
        """Test activity reminder automation"""
        client = APIClient()
        client.force_authenticate(user=self.sales_user)

        # Create activity with reminder
        future_time = timezone.now() + timedelta(hours=2)
        activity_data = {
            'type': 'call',
            'title': 'Call with Reminder',
            'scheduled_at': future_time.isoformat(),
            'reminder_minutes': 30,
            'contact': self.contact1.id,
            'owner': self.sales_user.id
        }

        response = client.post('/api/v1/activities/', activity_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        activity = response.json()
        self.assertEqual(activity['reminder_minutes'], 30)
        self.assertIsNotNone(activity['reminder_at'])

        # Verify reminder time is calculated correctly
        expected_reminder = future_time - timedelta(minutes=30)
        actual_reminder = datetime.fromisoformat(activity['reminder_at'].replace('Z', '+00:00'))
        time_diff = abs(actual_reminder - expected_reminder)
        self.assertLess(time_diff, timedelta(seconds=1))

    def test_deal_stage_progression_tracking(self):
        """Test deal stage progression tracking"""
        client = APIClient()
        client.force_authenticate(user=self.sales_user)

        # Create new deal
        deal_data = {
            'title': 'Progression Test Deal',
            'value': '20000.00',
            'stage': 'prospect',
            'contact': self.contact1.id,
            'owner': self.sales_user.id
        }

        response = client.post('/api/v1/deals/', deal_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        deal = response.json()
        deal_id = deal['id']

        # Progress deal through stages
        stages = ['qualified', 'proposal', 'negotiation']
        for stage in stages:
            stage_data = {'new_stage': stage}
            response = client.post(f'/api/v1/deals/{deal_id}/change-stage/', stage_data)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify stage history was tracked
        response = client.get(f'/api/v1/deals/{deal_id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        final_deal = response.json()
        self.assertIn('stage_history', final_deal)
        self.assertGreater(len(final_deal['stage_history']), 0)

        # Verify probability was updated automatically
        self.assertGreater(final_deal['probability'], 0)

    def test_bulk_operations_consistency(self):
        """Test bulk operations maintain data consistency"""
        client = APIClient()
        client.force_authenticate(user=self.sales_user)

        # Create multiple contacts for bulk operation
        contact_ids = []
        for i in range(3):
            contact_data = {
                'first_name': f'Bulk {i}',
                'last_name': f'Contact {i}',
                'email': f'bulk{i}@example.com',
                'owner': self.sales_user.id
            }

            response = client.post('/api/v1/contacts/', contact_data)
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            contact_ids.append(response.json()['id'])

        # Perform bulk deactivation
        bulk_data = {
            'contact_ids': contact_ids,
            'operation': 'deactivate'
        }

        response = client.post('/api/v1/contacts/bulk-operations/', bulk_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        bulk_result = response.json()
        self.assertEqual(bulk_result['updated_count'], 3)

        # Verify all contacts were deactivated
        for contact_id in contact_ids:
            response = client.get(f'/api/v1/contacts/{contact_id}/')
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)  # Inactive contacts not returned


class ErrorHandlingIntegrationTests(CRMIntegrationTestCase):
    """Test error handling and edge cases"""

    def test_404_handling_across_endpoints(self):
        """Test consistent 404 handling"""
        client = APIClient()
        client.force_authenticate(user=self.sales_user)

        # Test non-existent contact
        response = client.get('/api/v1/contacts/99999/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Test non-existent deal
        response = client.get('/api/v1/deals/99999/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Test non-existent activity
        response = client.get('/api/v1/activities/99999/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_validation_error_consistency(self):
        """Test consistent validation error responses"""
        client = APIClient()
        client.force_authenticate(user=self.sales_user)

        # Test contact validation errors
        invalid_contact = {
            'first_name': '',  # Required field empty
            'last_name': '',   # Required field empty
            'email': 'invalid-email'  # Invalid format
        }

        response = client.post('/api/v1/contacts/', invalid_contact)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        errors = response.json()
        self.assertIn('first_name', errors)
        self.assertIn('last_name', errors)
        self.assertIn('email', errors)

        # Test deal validation errors
        invalid_deal = {
            'title': '',  # Required field empty
            'value': '-1000',  # Negative value
            'stage': 'invalid_stage'  # Invalid choice
        }

        response = client.post('/api/v1/deals/', invalid_deal)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        errors = response.json()
        self.assertIn('title', errors)
        self.assertIn('value', errors)
        self.assertIn('stage', errors)

    def test_permission_denied_consistency(self):
        """Test consistent permission denied handling"""
        # Test unauthorized access
        client = APIClient()  # Not authenticated

        response = client.get('/api/v1/contacts/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Test cross-user access
        sales_client = APIClient()
        sales_client.force_authenticate(user=self.sales_user)

        # Try to access admin user's profile
        response = sales_client.get(f'/api/v1/users/{self.admin_user.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)  # Permission denied returns 404


class PerformanceIntegrationTests(CRMIntegrationTestCase):
    """Test performance and pagination integration"""

    def test_pagination_consistency(self):
        """Test consistent pagination across all list endpoints"""
        client = APIClient()
        client.force_authenticate(user=self.admin_user)  # Admin to see all data

        # Create enough data to test pagination
        for i in range(25):
            Contact.objects.create(
                first_name=f'Page {i}',
                last_name=f'Test {i}',
                email=f'page{i}@example.com',
                owner=self.sales_user
            )

        # Test contacts pagination
        response = client.get('/api/v1/contacts/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        contacts_data = response.json()
        self.assertIn('results', contacts_data)
        self.assertIn('count', contacts_data)
        self.assertIn('next', contacts_data)
        self.assertIn('previous', contacts_data)
        self.assertEqual(len(contacts_data['results']), 20)  # Default page size

        # Test deals pagination
        response = client.get('/api/v1/deals/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        deals_data = response.json()
        self.assertIn('results', deals_data)
        self.assertIn('count', deals_data)

        # Test activities pagination
        response = client.get('/api/v1/activities/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        activities_data = response.json()
        self.assertIn('results', activities_data)
        self.assertIn('count', activities_data)

    def test_large_dataset_search_performance(self):
        """Test search performance with large datasets"""
        client = APIClient()
        client.force_authenticate(user=self.admin_user)

        # Create many contacts with searchable content
        for i in range(100):
            Contact.objects.create(
                first_name=f'Search {i}',
                last_name=f'Performance {i}',
                email=f'search{i}@performance.com',
                company=f'Performance Corp {i}',
                owner=self.sales_user
            )

        # Test search with specific term
        response = client.get('/api/v1/contacts/?search=Performance')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        search_results = response.json()
        self.assertGreater(len(search_results['results']), 0)
        # Search should complete in reasonable time

        # Test search pagination
        response = client.get('/api/v1/contacts/?search=Performance&page=1')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class APIResponseFormatTests(CRMIntegrationTestCase):
    """Test API response format consistency"""

    def test_list_response_format_consistency(self):
        """Test consistent list response format"""
        client = APIClient()
        client.force_authenticate(user=self.admin_user)

        # Test contacts list format
        response = client.get('/api/v1/contacts/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        contacts_response = response.json()
        self.assertIn('results', contacts_response)
        self.assertIn('count', contacts_response)
        self.assertIsInstance(contacts_response['results'], list)

        if contacts_response['results']:
            contact = contacts_response['results'][0]
            self.assertIn('id', contact)
            self.assertIn('first_name', contact)
            self.assertIn('last_name', contact)
            self.assertIn('email', contact)

        # Test deals list format
        response = client.get('/api/v1/deals/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        deals_response = response.json()
        self.assertIn('results', deals_response)
        self.assertIn('count', deals_response)
        self.assertIsInstance(deals_response['results'], list)

        if deals_response['results']:
            deal = deals_response['results'][0]
            self.assertIn('id', deal)
            self.assertIn('title', deal)
            self.assertIn('value', deal)
            self.assertIn('stage', deal)

    def test_detail_response_format_consistency(self):
        """Test consistent detail response format"""
        client = APIClient()
        client.force_authenticate(user=self.admin_user)

        # Test contact detail format
        response = client.get(f'/api/v1/contacts/{self.contact1.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        contact = response.json()
        self.assertIn('id', contact)
        self.assertIn('uuid', contact)
        self.assertIn('created_at', contact)
        self.assertIn('updated_at', contact)
        self.assertIn('full_name', contact)

        # Test deal detail format
        response = client.get(f'/api/v1/deals/{self.deal1.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        deal = response.json()
        self.assertIn('id', deal)
        self.assertIn('uuid', deal)
        self.assertIn('created_at', deal)
        self.assertIn('updated_at', deal)
        self.assertIn('formatted_value', deal)
        self.assertIn('pipeline_position', deal)

        # Test activity detail format
        response = client.get(f'/api/v1/activities/{self.activity1.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        activity = response.json()
        self.assertIn('id', activity)
        self.assertIn('uuid', activity)
        self.assertIn('created_at', activity)
        self.assertIn('status', activity)
        self.assertIn('is_overdue', activity)

    def test_error_response_format_consistency(self):
        """Test consistent error response format"""
        client = APIClient()
        client.force_authenticate(user=self.sales_user)

        # Test validation error format
        invalid_data = {
            'first_name': '',
            'email': 'invalid-email'
        }

        response = client.post('/api/v1/contacts/', invalid_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error_response = response.json()
        self.assertIsInstance(error_response, dict)
        # Error responses should be dictionaries with field names as keys

    def test_success_response_format_consistency(self):
        """Test consistent success response format for creation"""
        client = APIClient()
        client.force_authenticate(user=self.sales_user)

        # Test contact creation response
        contact_data = {
            'first_name': 'Response',
            'last_name': 'Test',
            'email': 'response@example.com',
            'owner': self.sales_user.id
        }

        response = client.post('/api/v1/contacts/', contact_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        created_contact = response.json()
        self.assertIn('id', created_contact)
        self.assertIn('uuid', created_contact)
        self.assertIn('created_at', created_contact)
        self.assertIn('updated_at', created_contact)