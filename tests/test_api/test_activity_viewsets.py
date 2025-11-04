"""
Activity ViewSet Tests - TDD Approach
Testing comprehensive CRUD operations and business logic
Following SOLID principles and comprehensive test coverage
"""

import pytest
from datetime import datetime, timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from rest_framework.exceptions import NotAuthenticated, PermissionDenied

from crm.apps.activities.models import Activity, ActivityComment
from crm.apps.contacts.models import Contact
from crm.apps.deals.models import Deal
from crm.apps.activities.serializers import ActivitySerializer, ActivityDetailSerializer
from crm.apps.activities.viewsets import ActivityViewSet

User = get_user_model()


class ActivityViewSetTestCase(APITestCase):
    """Base test case for Activity ViewSet tests"""

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

        self.deal = Deal.objects.create(
            title='Test Deal',
            value='10000.00',
            stage='qualified',
            contact=self.contact,
            owner=self.user,
            expected_close_date=timezone.now().date() + timedelta(days=30)
        )

        tomorrow = timezone.now() + timedelta(days=1)
        self.activity_data = {
            'type': 'call',
            'title': 'Test Activity',
            'description': 'This is a test activity',
            'scheduled_at': tomorrow.isoformat(),
            'duration_minutes': 60,
            'priority': 'medium',
            'contact': self.contact.id,
            'deal': self.deal.id,
            'owner': self.user.id,
            'location': 'Conference Room A',
            'video_conference_url': 'https://zoom.us/j/123456789'
        }

        self.activity = Activity.objects.create(**self.activity_data)

        # URL patterns
        self.list_url = reverse('activity-list')
        self.detail_url = reverse('activity-detail', kwargs={'pk': self.activity.id})


class ActivityViewSetAuthenticationTests(ActivityViewSetTestCase):
    """Test authentication requirements for Activity ViewSet"""

    def test_unauthenticated_access_denied(self):
        """Test that unauthenticated users cannot access activity endpoints"""
        client = APIClient()

        # Test list access
        response = client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Test detail access
        response = client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Test create access
        response = client.post(self.list_url, self.activity_data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_access_allowed(self):
        """Test that authenticated users can access activity endpoints"""
        client = APIClient()
        client.force_authenticate(user=self.user)

        # Test list access
        response = client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Test detail access
        response = client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class ActivityViewSetListTests(ActivityViewSetTestCase):
    """Test Activity ViewSet list operations"""

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(user=self.user)

    def test_list_activities_returns_user_activities_only(self):
        """Test list endpoint returns only activities owned by the user"""
        # Create activities for different users
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

        Activity.objects.create(
            owner=other_user,
            contact=other_contact,
            title='Other Activity',
            type='call',
            scheduled_at=timezone.now() + timedelta(days=1)
        )

        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(len(data['results']), 1)
        self.assertEqual(data['results'][0]['id'], self.activity.id)

    def test_list_activities_with_pagination(self):
        """Test list endpoint respects pagination"""
        # Create additional activities
        for i in range(25):
            Activity.objects.create(
                owner=self.user,
                contact=self.contact,
                title=f'Activity {i}',
                type='call',
                scheduled_at=timezone.now() + timedelta(days=i+1)
            )

        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertIn('results', data)
        self.assertIn('count', data)
        self.assertIn('next', data)
        self.assertIn('previous', data)
        self.assertEqual(len(data['results']), 20)  # Default page size

    def test_list_activities_with_search(self):
        """Test list endpoint with search functionality"""
        # Create additional activities
        Activity.objects.create(
            owner=self.user,
            contact=self.contact,
            title='Important Meeting',
            type='meeting',
            scheduled_at=timezone.now() + timedelta(days=2)
        )

        # Search by title
        response = self.client.get(f'{self.list_url}?search=important')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(len(data['results']), 1)
        self.assertEqual(data['results'][0]['title'], 'Important Meeting')

        # Search by type
        response = self.client.get(f'{self.list_url}?search=meeting')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(len(data['results']), 1)

    def test_list_activities_with_filtering(self):
        """Test list endpoint with filtering"""
        # Create activities with different types and priorities
        urgent_activity = Activity.objects.create(
            owner=self.user,
            contact=self.contact,
            title='Urgent Activity',
            type='call',
            priority='urgent',
            scheduled_at=timezone.now() + timedelta(days=3)
        )

        # Filter by type
        response = self.client.get(f'{self.list_url}?type=call')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        activity_ids = [activity['id'] for activity in data['results']]
        self.assertIn(self.activity.id, activity_ids)
        self.assertIn(urgent_activity.id, activity_ids)

        # Filter by priority
        response = self.client.get(f'{self.list_url}?priority=urgent')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        activity_ids = [activity['id'] for activity in data['results']]
        self.assertNotIn(self.activity.id, activity_ids)
        self.assertIn(urgent_activity.id, activity_ids)

    def test_list_activities_with_ordering(self):
        """Test list endpoint with ordering"""
        # Create activities with different scheduled times
        early_activity = Activity.objects.create(
            owner=self.user,
            contact=self.contact,
            title='Early Activity',
            type='call',
            scheduled_at=timezone.now() + timedelta(hours=1)
        )

        late_activity = Activity.objects.create(
            owner=self.user,
            contact=self.contact,
            title='Late Activity',
            type='call',
            scheduled_at=timezone.now() + timedelta(days=5)
        )

        # Order by scheduled_at ascending
        response = self.client.get(f'{self.list_url}?ordering=scheduled_at')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        scheduled_times = [activity['scheduled_at'] for activity in data['results']]
        self.assertEqual(scheduled_times, sorted(scheduled_times))

        # Order by priority
        response = self.client.get(f'{self.list_url}?ordering=priority')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        # Note: Priority ordering depends on your implementation

    def test_list_activities_serializer_selection(self):
        """Test appropriate serializer is used for list view"""
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        activity = data['results'][0]

        # Should include basic fields
        self.assertIn('id', activity)
        self.assertIn('title', activity)
        self.assertIn('type', activity)
        self.assertIn('status', activity)

        # Should include summary-specific fields
        self.assertIn('is_overdue', activity)
        self.assertIn('is_due_soon', activity)
        self.assertIn('contact', activity)

        # Should not include verbose fields for list view
        self.assertNotIn('description', activity)
        self.assertNotIn('completion_notes', activity)
        self.assertNotIn('comments', activity)


class ActivityViewSetCreateTests(ActivityViewSetTestCase):
    """Test Activity ViewSet create operations"""

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(user=self.user)

    def test_create_activity_valid_data(self):
        """Test creating activity with valid data"""
        new_activity_data = {
            'type': 'meeting',
            'title': 'New Activity',
            'description': 'This is a new activity',
            'scheduled_at': (timezone.now() + timedelta(days=2)).isoformat(),
            'duration_minutes': 90,
            'priority': 'high',
            'contact': self.contact.id,
            'deal': self.deal.id,
            'owner': self.user.id,
            'location': 'Main Office',
            'reminder_minutes': 30
        }

        response = self.client.post(self.list_url, new_activity_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        data = response.json()
        self.assertEqual(data['title'], 'New Activity')
        self.assertEqual(data['type'], 'meeting')
        self.assertEqual(data['priority'], 'high')
        self.assertEqual(data['duration_minutes'], 90)

        # Verify activity was created in database
        activity = Activity.objects.get(id=data['id'])
        self.assertEqual(activity.owner, self.user)
        self.assertEqual(activity.contact, self.contact)
        self.assertEqual(activity.deal, self.deal)
        self.assertEqual(activity.reminder_minutes, 30)
        self.assertIsNotNone(activity.reminder_at)

    def test_create_activity_invalid_data(self):
        """Test creating activity with invalid data"""
        invalid_data = {
            'title': 'Invalid Activity',
            'type': 'invalid_type',  # Invalid type
            'priority': 'invalid_priority',  # Invalid priority
            'duration_minutes': -30,  # Negative duration
            'scheduled_at': '2020-01-01',  # Past time (for non-note)
            'contact': self.contact.id,
            'owner': self.user.id
        }

        response = self.client.post(self.list_url, invalid_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        data = response.json()
        self.assertIn('type', data)
        self.assertIn('priority', data)
        self.assertIn('duration_minutes', data)
        self.assertIn('scheduled_at', data)

    def test_create_activity_with_contact_only(self):
        """Test creating activity with only contact"""
        new_activity_data = {
            'type': 'call',
            'title': 'Contact Only Activity',
            'scheduled_at': (timezone.now() + timedelta(days=3)).isoformat(),
            'contact': self.contact.id,
            'owner': self.user.id
        }

        response = self.client.post(self.list_url, new_activity_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        data = response.json()
        self.assertEqual(data['contact'], self.contact.id)
        self.assertIsNone(data.get('deal'))

    def test_create_activity_with_deal_only(self):
        """Test creating activity with only deal"""
        new_activity_data = {
            'type': 'email',
            'title': 'Deal Only Activity',
            'scheduled_at': (timezone.now() + timedelta(days=4)).isoformat(),
            'deal': self.deal.id,
            'owner': self.user.id
        }

        response = self.client.post(self.list_url, new_activity_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        data = response.json()
        self.assertEqual(data['deal'], self.deal.id)
        self.assertIsNone(data.get('contact'))

    def test_create_activity_without_contact_or_deal(self):
        """Test creating activity without contact or deal fails"""
        invalid_data = {
            'type': 'call',
            'title': 'Orphaned Activity',
            'scheduled_at': (timezone.now() + timedelta(days=5)).isoformat(),
            'owner': self.user.id
            # Missing both contact and deal
        }

        response = self.client.post(self.list_url, invalid_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        data = response.json()
        self.assertIn('non_field_errors', data)

    def test_create_note_with_past_time(self):
        """Test creating note with past time is allowed"""
        note_data = {
            'type': 'note',
            'title': 'Past Note',
            'scheduled_at': (timezone.now() - timedelta(hours=1)).isoformat(),
            'contact': self.contact.id,
            'owner': self.user.id
        }

        response = self.client.post(self.list_url, note_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_activity_sanitizes_data(self):
        """Test create endpoint sanitizes input data"""
        new_activity_data = {
            'type': 'call',
            'title': '  Sanitized Activity  ',
            'description': '  This is a sanitized activity  ',
            'location': '  Sanitized Location  ',
            'scheduled_at': (timezone.now() + timedelta(days=6)).isoformat(),
            'contact': self.contact.id,
            'owner': self.user.id
        }

        response = self.client.post(self.list_url, new_activity_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        data = response.json()
        self.assertEqual(data['title'], 'Sanitized Activity')
        self.assertEqual(data['description'], 'This is a sanitized activity')
        self.assertEqual(data['location'], 'Sanitized Location')

    def test_create_activity_owner_assignment(self):
        """Test activity owner is automatically set to current user"""
        new_activity_data = {
            'type': 'call',
            'title': 'Owner Test Activity',
            'scheduled_at': (timezone.now() + timedelta(days=7)).isoformat(),
            'contact': self.contact.id
        }

        response = self.client.post(self.list_url, new_activity_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        data = response.json()
        activity = Activity.objects.get(id=data['id'])
        self.assertEqual(activity.owner, self.user)


class ActivityViewSetRetrieveTests(ActivityViewSetTestCase):
    """Test Activity ViewSet retrieve operations"""

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(user=self.user)

    def test_retrieve_own_activity(self):
        """Test retrieving own activity"""
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(data['id'], self.activity.id)
        self.assertEqual(data['title'], 'Test Activity')
        self.assertEqual(data['type'], 'call')

    def test_retrieve_other_user_activity_denied(self):
        """Test retrieving other user's activity is denied"""
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

        other_activity = Activity.objects.create(
            owner=other_user,
            contact=other_contact,
            title='Other Activity',
            type='call',
            scheduled_at=timezone.now() + timedelta(days=1)
        )

        other_detail_url = reverse('activity-detail', kwargs={'pk': other_activity.id})
        response = self.client.get(other_detail_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_admin_can_access_any_activity(self):
        """Test admin can access any activity"""
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

        other_activity = Activity.objects.create(
            owner=other_user,
            contact=other_contact,
            title='Other Activity',
            type='call',
            scheduled_at=timezone.now() + timedelta(days=1)
        )

        admin_client = APIClient()
        admin_client.force_authenticate(user=self.admin_user)

        other_detail_url = reverse('activity-detail', kwargs={'pk': other_activity.id})
        response = admin_client.get(other_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(data['id'], other_activity.id)

    def test_retrieve_nonexistent_activity(self):
        """Test retrieving non-existent activity returns 404"""
        fake_url = reverse('activity-detail', kwargs={'pk': 99999})
        response = self.client.get(fake_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_uses_detail_serializer(self):
        """Test retrieve endpoint uses detail serializer"""
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        # Should include detail-specific fields
        self.assertIn('contact_details', data)
        self.assertIn('deal_details', data)
        self.assertIn('owner_details', data)
        self.assertIn('comments', data)
        self.assertIn('duration_display', data)
        self.assertIn('priority_display_with_color', data)


class ActivityViewSetUpdateTests(ActivityViewSetTestCase):
    """Test Activity ViewSet update operations"""

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(user=self.user)

    def test_update_own_activity(self):
        """Test updating own activity"""
        update_data = {
            'title': 'Updated Activity Title',
            'priority': 'high',
            'duration_minutes': 120
        }

        response = self.client.patch(self.detail_url, update_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(data['title'], 'Updated Activity Title')
        self.assertEqual(data['priority'], 'high')
        self.assertEqual(data['duration_minutes'], 120)

    def test_update_activity_completion_status(self):
        """Test updating activity completion status"""
        update_data = {
            'is_completed': True,
            'completion_notes': 'Activity completed successfully'
        }

        response = self.client.patch(self.detail_url, update_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertTrue(data['is_completed'])
        self.assertIsNotNone(data['completed_at'])
        self.assertEqual(data['completion_notes'], 'Activity completed successfully')
        self.assertEqual(data['status'], 'completed')

    def test_update_activity_cancellation_status(self):
        """Test updating activity cancellation status"""
        update_data = {'is_cancelled': True}

        response = self.client.patch(self.detail_url, update_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertTrue(data['is_cancelled'])
        self.assertFalse(data['is_completed'])  # Should be false when cancelled
        self.assertEqual(data['status'], 'cancelled')

    def test_update_activity_reschedule(self):
        """Test updating activity scheduled time"""
        new_time = timezone.now() + timedelta(days=5)
        update_data = {
            'scheduled_at': new_time.isoformat(),
            'reminder_minutes': 60
        }

        response = self.client.patch(self.detail_url, update_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertIsNotNone(data['reminder_at'])
        # Verify reminder was recalculated
        expected_reminder = new_time - timedelta(minutes=60)
        actual_reminder = datetime.fromisoformat(data['reminder_at'].replace('Z', '+00:00'))
        self.assertAlmostEqual(
            actual_reminder.timestamp(),
            expected_reminder.timestamp(),
            delta=60  # Allow 1 minute tolerance
        )

    def test_update_other_user_activity_denied(self):
        """Test updating other user's activity is denied"""
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

        other_activity = Activity.objects.create(
            owner=other_user,
            contact=other_contact,
            title='Other Activity',
            type='call',
            scheduled_at=timezone.now() + timedelta(days=1)
        )

        other_detail_url = reverse('activity-detail', kwargs={'pk': other_activity.id})
        update_data = {'title': 'Updated'}

        response = self.client.patch(other_detail_url, update_data)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_activity_invalid_data(self):
        """Test updating activity with invalid data"""
        update_data = {
            'type': 'invalid_type',
            'priority': 'invalid_priority',
            'duration_minutes': -30
        }

        response = self.client.patch(self.detail_url, update_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        data = response.json()
        self.assertIn('type', data)
        self.assertIn('priority', data)
        self.assertIn('duration_minutes', data)

    def test_admin_can_update_any_activity(self):
        """Test admin can update any activity"""
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

        other_activity = Activity.objects.create(
            owner=other_user,
            contact=other_contact,
            title='Other Activity',
            type='call',
            scheduled_at=timezone.now() + timedelta(days=1)
        )

        admin_client = APIClient()
        admin_client.force_authenticate(user=self.admin_user)

        other_detail_url = reverse('activity-detail', kwargs={'pk': other_activity.id})
        update_data = {'title': 'Admin Updated'}

        response = admin_client.patch(other_detail_url, update_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(data['title'], 'Admin Updated')


class ActivityViewSetDeleteTests(ActivityViewSetTestCase):
    """Test Activity ViewSet delete operations"""

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(user=self.user)

    def test_delete_own_activity(self):
        """Test deleting own activity"""
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Activity should be deleted (hard delete)
        with self.assertRaises(Activity.DoesNotExist):
            Activity.objects.get(id=self.activity.id)

    def test_delete_other_user_activity_denied(self):
        """Test deleting other user's activity is denied"""
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

        other_activity = Activity.objects.create(
            owner=other_user,
            contact=other_contact,
            title='Other Activity',
            type='call',
            scheduled_at=timezone.now() + timedelta(days=1)
        )

        other_detail_url = reverse('activity-detail', kwargs={'pk': other_activity.id})
        response = self.client.delete(other_detail_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Activity should still exist
        self.assertTrue(Activity.objects.filter(id=other_activity.id).exists())

    def test_admin_can_delete_any_activity(self):
        """Test admin can delete any activity"""
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

        other_activity = Activity.objects.create(
            owner=other_user,
            contact=other_contact,
            title='Other Activity',
            type='call',
            scheduled_at=timezone.now() + timedelta(days=1)
        )

        admin_client = APIClient()
        admin_client.force_authenticate(user=self.admin_user)

        other_detail_url = reverse('activity-detail', kwargs={'pk': other_activity.id})
        response = admin_client.delete(other_detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Activity should be deleted
        with self.assertRaises(Activity.DoesNotExist):
            Activity.objects.get(id=other_activity.id)


class ActivityViewSetCustomActionsTests(ActivityViewSetTestCase):
    """Test Activity ViewSet custom actions"""

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(user=self.user)

    def test_complete_activity_action(self):
        """Test complete activity action"""
        complete_url = reverse('activity-complete', kwargs={'pk': self.activity.id})
        complete_data = {
            'completion_notes': 'Activity completed via action'
        }

        response = self.client.post(complete_url, complete_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertIn('message', data)
        self.assertEqual(data['status'], 'completed')

        # Verify activity was completed
        self.activity.refresh_from_db()
        self.assertTrue(self.activity.is_completed)
        self.assertIsNotNone(self.activity.completed_at)
        self.assertEqual(self.activity.completion_notes, 'Activity completed via action')

    def test_cancel_activity_action(self):
        """Test cancel activity action"""
        cancel_url = reverse('activity-cancel', kwargs={'pk': self.activity.id})

        response = self.client.post(cancel_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertIn('message', data)
        self.assertEqual(data['status'], 'cancelled')

        # Verify activity was cancelled
        self.activity.refresh_from_db()
        self.assertTrue(self.activity.is_cancelled)

    def test_reschedule_activity_action(self):
        """Test reschedule activity action"""
        new_time = timezone.now() + timedelta(days=3)
        reschedule_url = reverse('activity-reschedule', kwargs={'pk': self.activity.id})
        reschedule_data = {
            'new_scheduled_time': new_time.isoformat(),
            'reason': 'Client requested reschedule'
        }

        response = self.client.post(reschedule_url, reschedule_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertIn('message', data)
        self.assertIn('new_scheduled_time', data)

        # Verify activity was rescheduled
        self.activity.refresh_from_db()
        self.assertAlmostEqual(
            self.activity.scheduled_at.timestamp(),
            new_time.timestamp(),
            delta=60  # Allow 1 minute tolerance
        )

    def test_add_comment_action(self):
        """Test add comment action"""
        comment_url = reverse('activity-add-comment', kwargs={'pk': self.activity.id})
        comment_data = {
            'comment': 'This is a test comment'
        }

        response = self.client.post(comment_url, comment_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        data = response.json()
        self.assertEqual(data['comment'], 'This is a test comment')
        self.assertEqual(data['author'], self.user.id)

        # Verify comment was created
        comment = ActivityComment.objects.get(id=data['id'])
        self.assertEqual(comment.activity, self.activity)
        self.assertEqual(comment.author, self.user)

    def test_bulk_operations_action(self):
        """Test bulk operations action"""
        # Create additional activities
        activity2 = Activity.objects.create(
            owner=self.user,
            contact=self.contact,
            title='Second Activity',
            type='call',
            scheduled_at=timezone.now() + timedelta(days=2)
        )

        bulk_url = reverse('activity-bulk-operations')
        bulk_data = {
            'activity_ids': [self.activity.id, activity2.id],
            'operation': 'complete',
            'completion_notes': 'Bulk completed'
        }

        response = self.client.post(bulk_url, bulk_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertIn('message', data)
        self.assertEqual(data['updated_count'], 2)

        # Verify activities were completed
        self.activity.refresh_from_db()
        activity2.refresh_from_db()
        self.assertTrue(self.activity.is_completed)
        self.assertTrue(activity2.is_completed)

    def test_upcoming_activities_action(self):
        """Test upcoming activities action"""
        upcoming_url = reverse('activity-upcoming')
        response = self.client.get(upcoming_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertIsInstance(data, list)
        # Should include activities scheduled for the future

    def test_overdue_activities_action(self):
        """Test overdue activities action"""
        # Create an overdue activity
        overdue_activity = Activity.objects.create(
            owner=self.user,
            contact=self.contact,
            title='Overdue Activity',
            type='call',
            scheduled_at=timezone.now() - timedelta(days=1)
        )

        overdue_url = reverse('activity-overdue')
        response = self.client.get(overdue_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertIsInstance(data, list)
        activity_ids = [activity['id'] for activity in data]
        self.assertIn(overdue_activity.id, activity_ids)

    def test_activity_statistics_action(self):
        """Test activity statistics action"""
        stats_url = reverse('activity-statistics')
        response = self.client.get(stats_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertIn('total_activities', data)
        self.assertIn('completed_activities', data)
        self.assertIn('pending_activities', data)
        self.assertIn('completion_rate', data)
        self.assertIn('activities_by_type', data)


class ActivityViewSetIntegrationTests(ActivityViewSetTestCase):
    """Integration tests for Activity ViewSet"""

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(user=self.user)

    def test_full_crud_workflow(self):
        """Test complete CRUD workflow"""
        # Create
        create_data = {
            'type': 'meeting',
            'title': 'Workflow Activity',
            'scheduled_at': (timezone.now() + timedelta(days=2)).isoformat(),
            'contact': self.contact.id
        }

        response = self.client.post(self.list_url, create_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        activity_data = response.json()
        activity_id = activity_data['id']

        # Retrieve
        detail_url = reverse('activity-detail', kwargs={'pk': activity_id})
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Update
        update_data = {'priority': 'high'}
        response = self.client.patch(detail_url, update_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Complete
        complete_url = reverse('activity-complete', kwargs={'pk': activity_id})
        complete_data = {'completion_notes': 'Workflow completed'}
        response = self.client.post(complete_url, complete_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Delete
        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Verify deletion
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_activity_lifecycle_workflow(self):
        """Test activity lifecycle from creation to completion"""
        # Create activity
        create_data = {
            'type': 'call',
            'title': 'Lifecycle Test Activity',
            'scheduled_at': (timezone.now() + timedelta(hours=2)).isoformat(),
            'contact': self.contact.id,
            'reminder_minutes': 30
        }

        response = self.client.post(self.list_url, create_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        activity_data = response.json()
        activity_id = activity_data['id']
        detail_url = reverse('activity-detail', kwargs={'pk': activity_id})

        # Verify initial state
        activity = Activity.objects.get(id=activity_id)
        self.assertFalse(activity.is_completed)
        self.assertFalse(activity.is_cancelled)
        self.assertIsNotNone(activity.reminder_at)

        # Reschedule
        new_time = timezone.now() + timedelta(hours=4)
        reschedule_url = reverse('activity-reschedule', kwargs={'pk': activity_id})
        reschedule_data = {
            'new_scheduled_time': new_time.isoformat(),
            'reason': 'Rescheduled for availability'
        }

        response = self.client.post(reschedule_url, reschedule_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Add comment
        comment_url = reverse('activity-add-comment', kwargs={'pk': activity_id})
        comment_data = {'comment': 'Preparation notes for the call'}

        response = self.client.post(comment_url, comment_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Complete activity
        complete_url = reverse('activity-complete', kwargs={'pk': activity_id})
        complete_data = {
            'completion_notes': 'Successful call with client'
        }

        response = self.client.post(complete_url, complete_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify final state
        activity.refresh_from_db()
        self.assertTrue(activity.is_completed)
        self.assertIsNotNone(activity.completed_at)
        self.assertEqual(activity.completion_notes, 'Successful call with client')

        # Verify comment exists
        self.assertEqual(activity.comments.count(), 1)

    def test_error_handling_consistency(self):
        """Test consistent error handling across endpoints"""
        # Test with invalid data
        invalid_data = {
            'type': 'invalid_type',
            'priority': 'invalid_priority'
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