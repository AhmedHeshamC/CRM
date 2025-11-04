"""
Activity Repository Tests - Test-Driven Development Approach
Following enterprise-grade testing standards with comprehensive coverage
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta

from crm.shared.repositories.activity_repository import ActivityRepository
from crm.apps.activities.models import Activity
from crm.apps.contacts.models import Contact
from crm.apps.deals.models import Deal

User = get_user_model()


class ActivityRepositoryTest(TestCase):
    """Test ActivityRepository following TDD methodology"""

    def setUp(self):
        """Set up test data"""
        self.repository = ActivityRepository()
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
        self.activity_data = {
            'type': 'call',
            'title': 'Test Call',
            'description': 'Test Description',
            'scheduled_at': timezone.now() + timedelta(hours=1),
            'duration_minutes': 30,
            'priority': 'medium',
            'contact': self.contact,
            'owner': self.user
        }

    def tearDown(self):
        """Clean up after tests"""
        cache.clear()

    def test_repository_initialization(self):
        """Test repository initialization"""
        # Assert
        self.assertEqual(self.repository.model, Activity)
        self.assertEqual(self.repository.cache_timeout, 300)
        self.assertEqual(self.repository.cache_prefix, 'activity_')

    def test_get_by_owner(self):
        """Test getting activities by owner"""
        # Arrange
        mock_activities = [Mock(spec=Activity), Mock(spec=Activity)]
        with patch('crm.shared.repositories.activity_repository.cache') as mock_cache:
            mock_cache.get.return_value = mock_activities

            # Act
            result = self.repository.get_by_owner(self.user.id)

            # Assert
            self.assertEqual(result, mock_activities)

    def test_get_by_contact(self):
        """Test getting activities by contact"""
        # Arrange
        mock_activities = [Mock(spec=Activity)]
        with patch('crm.shared.repositories.activity_repository.cache') as mock_cache:
            mock_cache.get.return_value = mock_activities

            # Act
            result = self.repository.get_by_contact(self.contact.id)

            # Assert
            self.assertEqual(result, mock_activities)

    def test_get_by_type(self):
        """Test getting activities by type"""
        # Arrange
        mock_activities = [Mock(spec=Activity)]
        with patch('crm.shared.repositories.activity_repository.cache') as mock_cache:
            mock_cache.get.return_value = mock_activities

            # Act
            result = self.repository.get_by_type('call', self.user.id)

            # Assert
            self.assertEqual(result, mock_activities)
            mock_cache.get.assert_called_once_with('activity_type_call_' + str(self.user.id))

    def test_get_upcoming_activities(self):
        """Test getting upcoming activities"""
        # Arrange
        mock_activities = [Mock(spec=Activity)]
        with patch('crm.shared.repositories.activity_repository.cache') as mock_cache:
            mock_cache.get.return_value = mock_activities

            # Act
            result = self.repository.get_upcoming_activities(self.user.id, 7)

            # Assert
            self.assertEqual(result, mock_activities)

    def test_get_overdue_activities(self):
        """Test getting overdue activities"""
        # Arrange
        mock_activities = [Mock(spec=Activity)]
        with patch('crm.shared.repositories.activity_repository.cache') as mock_cache:
            mock_cache.get.return_value = mock_activities

            # Act
            result = self.repository.get_overdue_activities(self.user.id)

            # Assert
            self.assertEqual(result, mock_activities)

    def test_get_due_soon_activities(self):
        """Test getting activities due soon"""
        # Arrange
        mock_activities = [Mock(spec=Activity)]
        with patch('crm.shared.repositories.activity_repository.cache') as mock_cache:
            mock_cache.get.return_value = mock_activities

            # Act
            result = self.repository.get_due_soon_activities(24, self.user.id)

            # Assert
            self.assertEqual(result, mock_activities)

    def test_get_completed_activities(self):
        """Test getting completed activities"""
        # Arrange
        mock_activities = [Mock(spec=Activity)]
        with patch('crm.shared.repositories.activity_repository.cache') as mock_cache:
            mock_cache.get.return_value = mock_activities

            # Act
            result = self.repository.get_completed_activities(self.user.id, 7)

            # Assert
            self.assertEqual(result, mock_activities)

    def test_get_activities_by_priority(self):
        """Test getting activities by priority"""
        # Arrange
        mock_activities = [Mock(spec=Activity)]
        with patch('crm.shared.repositories.activity_repository.cache') as mock_cache:
            mock_cache.get.return_value = mock_activities

            # Act
            result = self.repository.get_activities_by_priority('high', self.user.id)

            # Assert
            self.assertEqual(result, mock_activities)

    def test_get_activities_for_date_range(self):
        """Test getting activities for date range"""
        # Arrange
        start_date = timezone.now()
        end_date = timezone.now() + timedelta(days=7)
        mock_activities = [Mock(spec=Activity)]
        with patch('crm.shared.repositories.activity_repository.cache') as mock_cache:
            mock_cache.get.return_value = mock_activities

            # Act
            result = self.repository.get_activities_for_date_range(start_date, end_date, self.user.id)

            # Assert
            self.assertEqual(result, mock_activities)

    def test_search_activities(self):
        """Test searching activities"""
        # Arrange
        mock_activities = [Mock(spec=Activity)]
        with patch('crm.shared.repositories.activity_repository.cache') as mock_cache:
            mock_cache.get.return_value = mock_activities

            # Act
            result = self.repository.search_activities('important', self.user.id)

            # Assert
            self.assertEqual(result, mock_activities)
            mock_cache.get.assert_called_once_with('activity_search_important_' + str(self.user.id))

    def test_get_activities_needing_reminders(self):
        """Test getting activities needing reminders"""
        # Arrange
        mock_activities = [Mock(spec=Activity)]
        with patch('crm.shared.repositories.activity_repository.cache') as mock_cache:
            mock_cache.get.return_value = mock_activities

            # Act
            result = self.repository.get_activities_needing_reminders()

            # Assert
            self.assertEqual(result, mock_activities)
            mock_cache.get.assert_called_once_with('activity_need_reminders')

    def test_get_activity_statistics_with_cache(self):
        """Test getting activity statistics with cache"""
        # Arrange
        mock_stats = {
            'total_activities': 100,
            'completed_activities': 60,
            'upcoming_activities': 25,
            'overdue_activities': 5,
            'completion_rate': 60.0,
        }
        with patch('crm.shared.repositories.activity_repository.cache') as mock_cache:
            mock_cache.get.return_value = mock_stats

            # Act
            result = self.repository.get_activity_statistics(self.user.id)

            # Assert
            self.assertEqual(result, mock_stats)
            mock_cache.get.assert_called_once_with('activity_statistics_' + str(self.user.id))

    def test_get_activity_statistics_without_cache(self):
        """Test getting activity statistics without cache"""
        # Arrange
        with patch('crm.shared.repositories.activity_repository.cache') as mock_cache:
            mock_cache.get.return_value = None
            with patch.object(Activity.objects, 'count') as mock_count:
                mock_count.return_value = 100
                with patch.object(Activity.objects, 'filter') as mock_filter:
                    mock_queryset = Mock()
                    mock_queryset.count.return_value = 60
                    mock_filter.return_value = mock_queryset

                    # Act
                    result = self.repository.get_activity_statistics(self.user.id)

                    # Assert
                    self.assertIn('total_activities', result)
                    self.assertIn('completed_activities', result)
                    self.assertEqual(result['total_activities'], 100)

    def test_complete_activity_success(self):
        """Test completing activity successfully"""
        # Arrange
        mock_activity = Mock(spec=Activity)
        mock_activity.id = 1
        mock_activity.uuid = 'test-uuid'

        with patch.object(Activity.objects, 'get') as mock_get:
            mock_get.return_value = mock_activity
            with patch.object(ActivityRepository, '_invalidate_cache_pattern') as mock_invalidate:

                # Act
                result = self.repository.complete_activity(1, 'Completed successfully')

                # Assert
                self.assertTrue(result)
                mock_activity.mark_completed.assert_called_once_with('Completed successfully')

    def test_complete_activity_not_found(self):
        """Test completing activity that doesn't exist"""
        # Arrange
        with patch.object(Activity.objects, 'get') as mock_get:
            mock_get.side_effect = Activity.DoesNotExist()

            # Act
            result = self.repository.complete_activity(999, 'Notes')

            # Assert
            self.assertFalse(result)

    def test_cancel_activity_success(self):
        """Test cancelling activity successfully"""
        # Arrange
        mock_activity = Mock(spec=Activity)
        mock_activity.id = 1
        mock_activity.uuid = 'test-uuid'

        with patch.object(Activity.objects, 'get') as mock_get:
            mock_get.return_value = mock_activity
            with patch.object(ActivityRepository, '_invalidate_cache_pattern') as mock_invalidate:

                # Act
                result = self.repository.cancel_activity(1)

                # Assert
                self.assertTrue(result)
                mock_activity.mark_cancelled.assert_called_once()

    def test_reschedule_activity_success(self):
        """Test rescheduling activity successfully"""
        # Arrange
        new_time = timezone.now() + timedelta(hours=2)
        mock_activity = Mock(spec=Activity)
        mock_activity.id = 1
        mock_activity.uuid = 'test-uuid'

        with patch.object(Activity.objects, 'get') as mock_get:
            mock_get.return_value = mock_activity
            with patch.object(ActivityRepository, '_invalidate_cache_pattern') as mock_invalidate:

                # Act
                result = self.repository.reschedule_activity(1, new_time)

                # Assert
                self.assertTrue(result)
                mock_activity.reschedule.assert_called_once_with(new_time)

    def test_send_reminder_success(self):
        """Test sending reminder successfully"""
        # Arrange
        mock_activity = Mock(spec=Activity)
        mock_activity.id = 1

        with patch.object(Activity.objects, 'get') as mock_get:
            mock_get.return_value = mock_activity
            with patch.object(ActivityRepository, '_invalidate_cache_pattern') as mock_invalidate:

                # Act
                result = self.repository.send_reminder(1)

                # Assert
                self.assertTrue(result)
                mock_activity.send_reminder.assert_called_once()

    def test_clear_activity_cache(self):
        """Test clearing activity-specific cache"""
        # Arrange
        mock_activity = Mock(spec=Activity)
        mock_activity.id = 1
        mock_activity.owner_id = self.user.id
        mock_activity.type = 'call'
        mock_activity.priority = 'high'
        mock_activity.uuid = 'test-uuid'
        mock_activity.contact_id = self.contact.id

        with patch('crm.shared.repositories.activity_repository.cache') as mock_cache:

            # Act
            self.repository.clear_activity_cache(mock_activity)

            # Assert
            expected_cache_keys = [
                'activity_id_1',
                f'activity_owner_{self.user.id}',
                'activity_type_call',
                'activity_priority_high',
                'activity_statistics',
                'activity_need_reminders',
                f'activity_contact_{self.contact.id}',
                'activity_uuid_test-uuid',
            ]

            # Check that delete was called for each expected cache key
            delete_calls = [call[0][0] for call in mock_cache.delete.call_args_list]
            for expected_key in expected_cache_keys:
                self.assertIn(expected_key, delete_calls)


class ActivityRepositoryIntegrationTest(TestCase):
    """Integration tests for ActivityRepository with actual database"""

    def setUp(self):
        """Set up test data"""
        self.repository = ActivityRepository()
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

    def test_create_and_retrieve_activity(self):
        """Test creating and retrieving an activity"""
        # Arrange & Act
        activity = Activity.objects.create(
            type='call',
            title='Test Call',
            scheduled_at=timezone.now() + timedelta(hours=1),
            contact=self.contact,
            owner=self.user
        )

        # Retrieve through repository
        retrieved = self.repository.get_by_id(activity.id)

        # Assert
        self.assertEqual(retrieved.type, 'call')
        self.assertEqual(retrieved.title, 'Test Call')
        self.assertEqual(retrieved.contact.id, self.contact.id)

    def test_get_activities_by_type_integration(self):
        """Test getting activities by type with actual database"""
        # Arrange
        Activity.objects.create(
            type='call',
            title='Call 1',
            scheduled_at=timezone.now() + timedelta(hours=1),
            contact=self.contact,
            owner=self.user
        )
        Activity.objects.create(
            type='call',
            title='Call 2',
            scheduled_at=timezone.now() + timedelta(hours=2),
            contact=self.contact,
            owner=self.user
        )
        Activity.objects.create(
            type='meeting',
            title='Meeting 1',
            scheduled_at=timezone.now() + timedelta(days=1),
            contact=self.contact,
            owner=self.user
        )

        # Act
        call_activities = self.repository.get_by_type('call', self.user.id)
        meeting_activities = self.repository.get_by_type('meeting', self.user.id)

        # Assert
        self.assertEqual(len(call_activities), 2)
        self.assertEqual(len(meeting_activities), 1)

    def test_get_upcoming_activities_integration(self):
        """Test getting upcoming activities with actual database"""
        # Arrange
        Activity.objects.create(
            type='call',
            title='Future Call',
            scheduled_at=timezone.now() + timedelta(hours=1),
            contact=self.contact,
            owner=self.user
        )
        Activity.objects.create(
            type='meeting',
            title='Past Meeting',
            scheduled_at=timezone.now() - timedelta(hours=1),
            is_completed=True,
            contact=self.contact,
            owner=self.user
        )

        # Act
        upcoming = self.repository.get_upcoming_activities(self.user.id)

        # Assert
        self.assertEqual(len(upcoming), 1)
        self.assertEqual(upcoming[0].title, 'Future Call')

    def test_search_activities_integration(self):
        """Test searching activities with actual database"""
        # Arrange
        Activity.objects.create(
            type='call',
            title='Important Call',
            scheduled_at=timezone.now() + timedelta(hours=1),
            contact=self.contact,
            owner=self.user
        )
        Activity.objects.create(
            type='meeting',
            title='Regular Meeting',
            scheduled_at=timezone.now() + timedelta(days=1),
            contact=self.contact,
            owner=self.user
        )

        # Act
        results = self.repository.search_activities('important', self.user.id)

        # Assert
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].title, 'Important Call')

    def test_complete_activity_integration(self):
        """Test completing activity with actual database"""
        # Arrange
        activity = Activity.objects.create(
            type='call',
            title='Test Call',
            scheduled_at=timezone.now() + timedelta(hours=1),
            contact=self.contact,
            owner=self.user
        )

        # Act
        success = self.repository.complete_activity(activity.id, 'Call completed successfully')

        # Retrieve updated activity
        updated_activity = Activity.objects.get(id=activity.id)

        # Assert
        self.assertTrue(success)
        self.assertTrue(updated_activity.is_completed)
        self.assertEqual(updated_activity.completion_notes, 'Call completed successfully')
        self.assertIsNotNone(updated_activity.completed_at)

    def test_cancel_activity_integration(self):
        """Test cancelling activity with actual database"""
        # Arrange
        activity = Activity.objects.create(
            type='meeting',
            title='Test Meeting',
            scheduled_at=timezone.now() + timedelta(hours=1),
            contact=self.contact,
            owner=self.user
        )

        # Act
        success = self.repository.cancel_activity(activity.id)

        # Retrieve updated activity
        updated_activity = Activity.objects.get(id=activity.id)

        # Assert
        self.assertTrue(success)
        self.assertTrue(updated_activity.is_cancelled)

    def test_get_activity_statistics_integration(self):
        """Test getting activity statistics with actual database"""
        # Arrange
        # Create activities with different statuses
        Activity.objects.create(
            type='call',
            title='Completed Call',
            scheduled_at=timezone.now() - timedelta(hours=1),
            is_completed=True,
            completed_at=timezone.now() - timedelta(minutes=30),
            contact=self.contact,
            owner=self.user
        )
        Activity.objects.create(
            type='meeting',
            title='Upcoming Meeting',
            scheduled_at=timezone.now() + timedelta(hours=1),
            contact=self.contact,
            owner=self.user
        )
        Activity.objects.create(
            type='task',
            title='Cancelled Task',
            scheduled_at=timezone.now() + timedelta(hours=2),
            is_cancelled=True,
            contact=self.contact,
            owner=self.user
        )

        # Act
        stats = self.repository.get_activity_statistics(self.user.id)

        # Assert
        self.assertEqual(stats['total_activities'], 3)
        self.assertEqual(stats['completed_activities'], 1)
        self.assertEqual(stats['cancelled_activities'], 1)
        self.assertEqual(stats['upcoming_activities'], 1)  # Only non-cancelled, non-completed
        self.assertAlmostEqual(stats['completion_rate'], 33.33, places=1)

    def test_get_activities_needing_reminders_integration(self):
        """Test getting activities needing reminders with actual database"""
        # Arrange
        past_time = timezone.now() - timedelta(minutes=5)
        future_time = timezone.now() + timedelta(minutes=5)

        # Activity that needs reminder
        activity_needs_reminder = Activity.objects.create(
            type='call',
            title='Call with Reminder',
            scheduled_at=future_time + timedelta(minutes=10),
            reminder_at=past_time,
            reminder_sent=False,
            contact=self.contact,
            owner=self.user
        )

        # Activity that doesn't need reminder (already sent)
        Activity.objects.create(
            type='meeting',
            title='Meeting - Reminder Sent',
            scheduled_at=future_time + timedelta(minutes=20),
            reminder_at=past_time,
            reminder_sent=True,
            contact=self.contact,
            owner=self.user
        )

        # Activity that doesn't need reminder (no reminder set)
        Activity.objects.create(
            type='task',
            title='Task - No Reminder',
            scheduled_at=future_time + timedelta(minutes=30),
            contact=self.contact,
            owner=self.user
        )

        # Act
        activities_needing_reminders = self.repository.get_activities_needing_reminders()

        # Assert
        self.assertEqual(len(activities_needing_reminders), 1)
        self.assertEqual(activities_needing_reminders[0].id, activity_needs_reminder.id)