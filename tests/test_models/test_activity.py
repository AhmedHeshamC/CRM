"""
Activity Model Tests - Test-Driven Development Approach
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
from datetime import timedelta

from crm.apps.contacts.models import Contact
from crm.apps.deals.models import Deal
from crm.apps.activities.models import Activity, ActivityComment

User = get_user_model()


class ActivityModelTest(TestCase):
    """Test Activity model following TDD methodology"""

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

        self.activity_data = {
            'type': 'call',
            'title': 'Initial Sales Call',
            'description': 'Discovery call to understand client needs',
            'scheduled_at': timezone.now() + timezone.timedelta(hours=1),
            'duration_minutes': 30,
            'priority': 'high',
            'contact': self.contact,
            'owner': self.user
        }

    def test_activity_creation_with_minimum_fields(self):
        """Test creating activity with minimum required fields"""
        # Arrange & Act
        activity = Activity.objects.create(
            type='call',
            title='Test Call',
            scheduled_at=timezone.now() + timezone.timedelta(hours=1),
            contact=self.contact,
            owner=self.user
        )

        # Assert
        self.assertEqual(activity.type, 'call')
        self.assertEqual(activity.title, 'Test Call')
        self.assertEqual(activity.contact, self.contact)
        self.assertEqual(activity.owner, self.user)
        self.assertEqual(activity.priority, 'medium')  # Default priority
        self.assertFalse(activity.is_completed)
        self.assertFalse(activity.is_cancelled)
        self.assertIsNotNone(activity.uuid)
        self.assertIsInstance(activity.uuid, uuid.UUID)

    def test_activity_creation_with_all_fields(self):
        """Test creating activity with all fields"""
        # Arrange & Act
        activity = Activity.objects.create(**self.activity_data)

        # Assert
        self.assertEqual(activity.description, 'Discovery call to understand client needs')
        self.assertEqual(activity.duration_minutes, 30)
        self.assertEqual(activity.priority, 'high')

    def test_activity_str_representation(self):
        """Test string representation of activity"""
        # Arrange & Act
        activity = Activity.objects.create(**self.activity_data)

        # Assert
        self.assertEqual(str(activity), 'Phone Call - Initial Sales Call')

    def test_activity_type_choices(self):
        """Test valid activity types"""
        valid_types = ['call', 'email', 'meeting', 'demo', 'followup', 'task', 'note', 'lunch', 'webinar']

        for activity_type in valid_types:
            # Arrange & Act
            activity_data = self.activity_data.copy()
            activity_data['type'] = activity_type
            activity_data['title'] = f'Test {activity_type}'
            activity = Activity.objects.create(**activity_data)

            # Assert
            self.assertEqual(activity.type, activity_type)

    def test_activity_priority_choices(self):
        """Test valid priority choices"""
        valid_priorities = ['low', 'medium', 'high', 'urgent']

        for priority in valid_priorities:
            # Arrange & Act
            activity_data = self.activity_data.copy()
            activity_data['priority'] = priority
            activity_data['title'] = f'Test {priority} priority'
            activity = Activity.objects.create(**activity_data)

            # Assert
            self.assertEqual(activity.priority, priority)

    def test_activity_validation_contact_or_deal_required(self):
        """Test that activity must have either contact or deal"""
        # Arrange
        activity = Activity(
            type='call',
            title='Test Call',
            scheduled_at=timezone.now() + timezone.timedelta(hours=1),
            owner=self.user
        )

        # Act & Assert
        with self.assertRaises(ValidationError) as context:
            activity.full_clean()
        self.assertIn('Activity must be associated with either a contact or a deal', str(context.exception))

    def test_activity_duration_validation(self):
        """Test duration validation"""
        # Arrange
        activity = Activity(**self.activity_data)

        # Act & Assert
        activity.duration_minutes = 0
        with self.assertRaises(ValidationError) as context:
            activity.full_clean()
        self.assertIn('Duration must be positive if specified', str(context.exception))

        activity.duration_minutes = -10
        with self.assertRaises(ValidationError):
            activity.full_clean()

        # Valid duration
        activity.duration_minutes = 60
        try:
            activity.full_clean()
        except ValidationError:
            self.fail('Duration of 60 minutes should be valid')

    def test_activity_scheduled_in_past_validation(self):
        """Test validation for activities scheduled in the past"""
        # Arrange
        activity = Activity(**self.activity_data)
        activity.scheduled_at = timezone.now() - timezone.timedelta(hours=1)

        # Act & Assert
        with self.assertRaises(ValidationError) as context:
            activity.full_clean()
        self.assertIn('Scheduled time cannot be in the past', str(context.exception))

    def test_activity_scheduled_in_past_for_note_type(self):
        """Test that note type can be scheduled in the past"""
        # Arrange
        activity = Activity(**self.activity_data)
        activity.type = 'note'
        activity.scheduled_at = timezone.now() - timezone.timedelta(hours=1)

        # Act & Assert - Should not raise exception
        try:
            activity.full_clean()
        except ValidationError:
            self.fail('Note type should allow past scheduling')

    def test_activity_properties(self):
        """Test activity property methods"""
        # Arrange
        past_activity_data = self.activity_data.copy()
        past_activity_data['scheduled_at'] = timezone.now() - timezone.timedelta(hours=1)
        past_activity_data['type'] = 'call'
        past_activity = Activity.objects.create(**past_activity_data)

        future_activity = Activity.objects.create(**self.activity_data)

        completed_activity_data = self.activity_data.copy()
        completed_activity_data['is_completed'] = True
        completed_activity_data['completed_at'] = timezone.now()
        completed_activity = Activity.objects.create(**completed_activity_data)

        cancelled_activity_data = self.activity_data.copy()
        cancelled_activity_data['is_cancelled'] = True
        cancelled_activity = Activity.objects.create(**cancelled_activity_data)

        # Assert
        self.assertTrue(past_activity.is_overdue)
        self.assertFalse(past_activity.is_due_soon())

        self.assertFalse(future_activity.is_overdue)
        self.assertTrue(future_activity.is_due_soon(hours=2))  # Within 2 hours

        self.assertEqual(completed_activity.status, 'completed')
        self.assertEqual(cancelled_activity.status, 'cancelled')
        self.assertEqual(past_activity.status, 'overdue')
        self.assertEqual(future_activity.status, 'due_soon')

    def test_activity_mark_completed(self):
        """Test marking activity as completed"""
        # Arrange & Act
        activity = Activity.objects.create(**self.activity_data)
        completion_notes = 'Had a great call, client is interested'
        activity.mark_completed(completion_notes)

        # Assert
        activity.refresh_from_db()
        self.assertTrue(activity.is_completed)
        self.assertIsNotNone(activity.completed_at)
        self.assertEqual(activity.completion_notes, completion_notes)

    def test_activity_mark_cancelled(self):
        """Test marking activity as cancelled"""
        # Arrange & Act
        activity = Activity.objects.create(**self.activity_data)
        activity.mark_cancelled()

        # Assert
        activity.refresh_from_db()
        self.assertTrue(activity.is_cancelled)

    def test_activity_snooze(self):
        """Test snoozing activity"""
        # Arrange
        original_time = timezone.now() + timezone.timedelta(hours=1)
        activity = Activity.objects.create(**self.activity_data)
        activity.scheduled_at = original_time
        activity.save()

        # Act
        activity.snooze(minutes=30)

        # Assert
        activity.refresh_from_db()
        expected_time = original_time + timezone.timedelta(minutes=30)
        self.assertEqual(activity.scheduled_at, expected_time)

    def test_activity_reschedule(self):
        """Test rescheduling activity"""
        # Arrange
        activity = Activity.objects.create(**self.activity_data)
        new_time = timezone.now() + timezone.timedelta(days=1)

        # Act
        activity.reschedule(new_time)

        # Assert
        activity.refresh_from_db()
        self.assertEqual(activity.scheduled_at, new_time)

    def test_activity_auto_reminder_calculation(self):
        """Test automatic reminder time calculation"""
        # Arrange & Act
        activity_data = self.activity_data.copy()
        activity_data['reminder_minutes'] = 15
        activity = Activity.objects.create(**activity_data)

        # Assert
        expected_reminder = activity.scheduled_at - timedelta(minutes=15)
        self.assertEqual(activity.reminder_at, expected_reminder)

    def test_activity_reset_completion_tracking(self):
        """Test resetting completion tracking when un-completing"""
        # Arrange
        activity = Activity.objects.create(**self.activity_data)
        activity.mark_completed('Test completion')

        # Act
        activity.is_completed = False
        activity.save()

        # Assert
        activity.refresh_from_db()
        self.assertIsNone(activity.completed_at)
        self.assertIsNone(activity.completion_notes)

    def test_activity_manager_methods(self):
        """Test custom manager methods"""
        # Arrange
        past_activity_data = self.activity_data.copy()
        past_activity_data['scheduled_at'] = timezone.now() - timezone.timedelta(hours=1)
        past_activity = Activity.objects.create(**past_activity_data)

        future_activity = Activity.objects.create(**self.activity_data)

        completed_activity_data = self.activity_data.copy()
        completed_activity_data['scheduled_at'] = timezone.now() - timezone.timedelta(minutes=30)
        completed_activity_data['is_completed'] = True
        completed_activity_data['completed_at'] = timezone.now()
        completed_activity = Activity.objects.create(**completed_activity_data)

        cancelled_activity_data = self.activity_data.copy()
        cancelled_activity_data['is_cancelled'] = True
        cancelled_activity = Activity.objects.create(**cancelled_activity_data)

        # Test by_owner()
        owner_activities = Activity.objects.by_owner(self.user)
        self.assertIn(future_activity, owner_activities)
        self.assertIn(completed_activity, owner_activities)
        self.assertNotIn(cancelled_activity, owner_activities)  # Cancelled excluded

        # Test upcoming()
        upcoming_activities = Activity.objects.upcoming()
        self.assertIn(future_activity, upcoming_activities)
        self.assertNotIn(past_activity, upcoming_activities)
        self.assertNotIn(completed_activity, upcoming_activities)

        # Test overdue()
        overdue_activities = Activity.objects.overdue()
        self.assertIn(past_activity, overdue_activities)
        self.assertNotIn(future_activity, overdue_activities)

        # Test completed_today()
        today_activities = Activity.objects.completed_today()
        self.assertIn(completed_activity, today_activities)

        # Test by_type()
        call_activities = Activity.objects.by_type('call')
        self.assertIn(future_activity, call_activities)

        # Test all_objects()
        all_activities = Activity.objects.all_objects()
        self.assertIn(cancelled_activity, all_activities)  # Now included

    def test_activity_due_soon(self):
        """Test activities due soon method"""
        # Arrange
        due_soon_data = self.activity_data.copy()
        due_soon_data['scheduled_at'] = timezone.now() + timedelta(hours=2)
        due_soon_activity = Activity.objects.create(**due_soon_data)

        far_activity_data = self.activity_data.copy()
        far_activity_data['scheduled_at'] = timezone.now() + timedelta(hours=25)
        far_activity = Activity.objects.create(**far_activity_data)

        # Act
        due_soon_activities = Activity.objects.due_soon(hours=24)

        # Assert
        self.assertIn(due_soon_activity, due_soon_activities)
        self.assertNotIn(far_activity, due_soon_activities)

    def test_activity_for_date_range(self):
        """Test activities within date range"""
        # Arrange
        start_date = timezone.now()
        end_date = timezone.now() + timedelta(days=7)

        within_range_data = self.activity_data.copy()
        within_range_data['scheduled_at'] = timezone.now() + timedelta(days=3)
        within_range_activity = Activity.objects.create(**within_range_data)

        outside_range_data = self.activity_data.copy()
        outside_range_data['scheduled_at'] = timezone.now() + timedelta(days=10)
        outside_range_activity = Activity.objects.create(**outside_range_data)

        # Act
        range_activities = Activity.objects.for_date_range(start_date, end_date)

        # Assert
        self.assertIn(within_range_activity, range_activities)
        self.assertNotIn(outside_range_activity, range_activities)

    def test_activity_get_duration_display(self):
        """Test duration display formatting"""
        # Arrange & Act
        minutes_activity_data = self.activity_data.copy()
        minutes_activity_data['duration_minutes'] = 30
        minutes_activity = Activity.objects.create(**minutes_activity_data)

        hours_activity_data = self.activity_data.copy()
        hours_activity_data['duration_minutes'] = 120
        hours_activity = Activity.objects.create(**hours_activity_data)

        mixed_activity_data = self.activity_data.copy()
        mixed_activity_data['duration_minutes'] = 90
        mixed_activity = Activity.objects.create(**mixed_activity_data)

        # Assert
        self.assertEqual(minutes_activity.get_duration_display(), '30 min')
        self.assertEqual(hours_activity.get_duration_display(), '2 hr')
        self.assertEqual(mixed_activity.get_duration_display(), '1 hr 30 min')

        # Test without duration
        no_duration_activity = Activity.objects.create(
            type='note',
            title='Test Note',
            scheduled_at=timezone.now(),
            contact=self.contact,
            owner=self.user
        )
        self.assertIsNone(no_duration_activity.get_duration_display())

    def test_activity_get_priority_display_with_color(self):
        """Test priority display with color classes"""
        # Arrange
        urgent_activity_data = self.activity_data.copy()
        urgent_activity_data['priority'] = 'urgent'
        urgent_activity = Activity.objects.create(**urgent_activity_data)

        # Act & Assert
        priority_info = urgent_activity.get_priority_display_with_color()
        self.assertEqual(priority_info['label'], 'Urgent')
        self.assertEqual(priority_info['color'], 'danger')

    def test_activity_model_indexes(self):
        """Test that model has proper indexes"""
        meta = Activity._meta
        index_fields = [index.fields for index in meta.indexes]

        expected_indexes = [
            ['type'],
            ['scheduled_at'],
            ['owner'],
            ['contact'],
            ['deal'],
            ['is_completed'],
            ['priority'],
            ['created_at'],
        ]

        for expected in expected_indexes:
            self.assertIn(expected, index_fields)


class ActivityCommentModelTest(TestCase):
    """Test ActivityComment model"""

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

        self.activity = Activity.objects.create(
            type='call',
            title='Test Call',
            scheduled_at=timezone.now() + timezone.timedelta(hours=1),
            contact=self.contact,
            owner=self.user
        )

        self.comment_data = {
            'activity': self.activity,
            'author': self.user,
            'comment': 'Had a great conversation about their requirements'
        }

    def test_comment_creation(self):
        """Test creating activity comment"""
        # Arrange & Act
        comment = ActivityComment.objects.create(**self.comment_data)

        # Assert
        self.assertEqual(comment.activity, self.activity)
        self.assertEqual(comment.author, self.user)
        self.assertEqual(comment.comment, 'Had a great conversation about their requirements')

    def test_comment_str_representation(self):
        """Test string representation of comment"""
        # Arrange & Act
        comment = ActivityComment.objects.create(**self.comment_data)

        # Assert
        self.assertEqual(str(comment), 'Comment by Sales User on Test Call')

    def test_comment_ordering(self):
        """Test that comments are ordered by created_at descending"""
        # Arrange & Act
        with freeze_time('2024-01-01 12:00:00'):
            comment1 = ActivityComment.objects.create(**self.comment_data)

        with freeze_time('2024-01-01 13:00:00'):
            comment_data = self.comment_data.copy()
            comment_data['comment'] = 'Second comment'
            comment2 = ActivityComment.objects.create(**comment_data)

        # Assert
        comments = list(ActivityComment.objects.all())
        self.assertEqual(comments[0], comment2)
        self.assertEqual(comments[1], comment1)