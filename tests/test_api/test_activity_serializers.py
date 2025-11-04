"""
Activity Serializer Tests - TDD Approach
Testing comprehensive validation and serialization logic
Following SOLID principles and comprehensive test coverage
"""

import pytest
from datetime import datetime, timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers
from rest_framework.test import APITestCase
from rest_framework.exceptions import ValidationError

from crm.apps.activities.models import Activity, ActivityComment
from crm.apps.contacts.models import Contact
from crm.apps.deals.models import Deal
from crm.apps.activities.serializers import (
    ActivitySerializer,
    ActivityDetailSerializer,
    ActivityCreateSerializer,
    ActivityUpdateSerializer,
    ActivitySummarySerializer,
    ActivityCommentSerializer
)

User = get_user_model()


class ActivitySerializerTestCase(TestCase):
    """Base test case for Activity serializers"""

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


class ActivitySerializerTests(ActivitySerializerTestCase):
    """Test ActivitySerializer functionality"""

    def test_valid_activity_serialization(self):
        """Test serialization of valid activity data"""
        activity = Activity.objects.create(**self.activity_data)
        serializer = ActivitySerializer(activity)

        data = serializer.data
        self.assertEqual(data['id'], activity.id)
        self.assertEqual(data['type'], 'call')
        self.assertEqual(data['title'], 'Test Activity')
        self.assertEqual(data['priority'], 'medium')
        self.assertEqual(data['contact'], self.contact.id)
        self.assertEqual(data['deal'], self.deal.id)
        self.assertEqual(data['owner'], self.user.id)
        self.assertIn('uuid', data)
        self.assertIn('created_at', data)
        self.assertIn('updated_at', data)

    def test_activity_validation_missing_required_fields(self):
        """Test validation fails with missing required fields"""
        invalid_data = {
            'title': 'Test Activity',
            # Missing type, scheduled_at, contact/deal, owner
        }
        serializer = ActivitySerializer(data=invalid_data)

        with self.assertRaises(ValidationError) as context:
            serializer.is_valid(raise_exception=True)

        self.assertIn('type', context.exception.detail)
        self.assertIn('scheduled_at', context.exception.detail)
        # At least one of contact or deal should be required
        self.assertIn('non_field_errors', context.exception.detail)

    def test_activity_validation_invalid_type(self):
        """Test validation fails with invalid activity type"""
        data = self.activity_data.copy()
        data['type'] = 'invalid_type'
        serializer = ActivitySerializer(data=data)

        with self.assertRaises(ValidationError) as context:
            serializer.is_valid(raise_exception=True)

        self.assertIn('type', context.exception.detail)

    def test_activity_validation_invalid_priority(self):
        """Test validation fails with invalid priority"""
        data = self.activity_data.copy()
        data['priority'] = 'invalid_priority'
        serializer = ActivitySerializer(data=data)

        with self.assertRaises(ValidationError) as context:
            serializer.is_valid(raise_exception=True)

        self.assertIn('priority', context.exception.detail)

    def test_activity_validation_invalid_duration(self):
        """Test validation fails with invalid duration"""
        data = self.activity_data.copy()
        data['duration_minutes'] = -30  # Negative duration
        serializer = ActivitySerializer(data=data)

        with self.assertRaises(ValidationError) as context:
            serializer.is_valid(raise_exception=True)

        self.assertIn('duration_minutes', context.exception.detail)

    def test_activity_validation_past_scheduled_time(self):
        """Test validation fails with past scheduled time for new activities"""
        data = self.activity_data.copy()
        past_time = (timezone.now() - timedelta(hours=1)).isoformat()
        data['scheduled_at'] = past_time
        data['type'] = 'meeting'  # Not a note
        serializer = ActivitySerializer(data=data)

        with self.assertRaises(ValidationError) as context:
            serializer.is_valid(raise_exception=True)

        self.assertIn('scheduled_at', context.exception.detail)

    def test_activity_validation_past_time_for_note(self):
        """Test validation allows past time for notes"""
        data = self.activity_data.copy()
        past_time = (timezone.now() - timedelta(hours=1)).isoformat()
        data['scheduled_at'] = past_time
        data['type'] = 'note'
        serializer = ActivitySerializer(data=data)

        self.assertTrue(serializer.is_valid())

    def test_activity_validation_neither_contact_nor_deal(self):
        """Test validation fails when neither contact nor deal is specified"""
        data = self.activity_data.copy()
        data.pop('contact', None)
        data.pop('deal', None)
        serializer = ActivitySerializer(data=data)

        with self.assertRaises(ValidationError) as context:
            serializer.is_valid(raise_exception=True)

        self.assertIn('non_field_errors', context.exception.detail)

    def test_optional_fields_handling(self):
        """Test proper handling of optional fields"""
        minimal_data = {
            'type': 'call',
            'title': 'Minimal Activity',
            'scheduled_at': (timezone.now() + timedelta(days=1)).isoformat(),
            'contact': self.contact.id,
            'owner': self.user.id
        }
        serializer = ActivitySerializer(data=minimal_data)
        self.assertTrue(serializer.is_valid())

        activity = serializer.save()
        self.assertEqual(activity.description, '')
        self.assertEqual(activity.duration_minutes, None)
        self.assertEqual(activity.priority, 'medium')  # Default
        self.assertEqual(activity.location, '')
        self.assertEqual(activity.video_conference_url, '')

    def test_computed_fields(self):
        """Test computed fields are properly calculated"""
        # Create activity in different states
        future_activity = Activity.objects.create(
            owner=self.user,
            contact=self.contact,
            type='call',
            title='Future Activity',
            scheduled_at=timezone.now() + timedelta(days=1)
        )

        past_activity = Activity.objects.create(
            owner=self.user,
            contact=self.contact,
            type='call',
            title='Past Activity',
            scheduled_at=timezone.now() - timedelta(days=1)
        )

        completed_activity = Activity.objects.create(
            owner=self.user,
            contact=self.contact,
            type='call',
            title='Completed Activity',
            scheduled_at=timezone.now() - timedelta(days=1),
            is_completed=True,
            completed_at=timezone.now()
        )

        cancelled_activity = Activity.objects.create(
            owner=self.user,
            contact=self.contact,
            type='call',
            title='Cancelled Activity',
            scheduled_at=timezone.now() + timedelta(days=1),
            is_cancelled=True
        )

        # Test future activity
        serializer = ActivitySerializer(future_activity)
        data = serializer.data
        self.assertFalse(data['is_overdue'])
        self.assertFalse(data['is_due_soon'])
        self.assertEqual(data['status'], 'scheduled')

        # Test past activity
        serializer = ActivitySerializer(past_activity)
        data = serializer.data
        self.assertTrue(data['is_overdue'])
        self.assertFalse(data['is_due_soon'])
        self.assertEqual(data['status'], 'overdue')

        # Test completed activity
        serializer = ActivitySerializer(completed_activity)
        data = serializer.data
        self.assertFalse(data['is_overdue'])
        self.assertFalse(data['is_due_soon'])
        self.assertEqual(data['status'], 'completed')

        # Test cancelled activity
        serializer = ActivitySerializer(cancelled_activity)
        data = serializer.data
        self.assertFalse(data['is_overdue'])
        self.assertFalse(data['is_due_soon'])
        self.assertEqual(data['status'], 'cancelled')


class ActivityCreateSerializerTests(ActivitySerializerTestCase):
    """Test ActivityCreateSerializer functionality"""

    def test_create_serializer_validates_required_fields(self):
        """Test create serializer enforces all required fields"""
        data = self.activity_data.copy()
        serializer = ActivityCreateSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_create_serializer_sets_defaults(self):
        """Test create serializer sets appropriate defaults"""
        data = {
            'type': 'call',
            'title': 'New Activity',
            'scheduled_at': (timezone.now() + timedelta(days=1)).isoformat(),
            'contact': self.contact.id,
            'owner': self.user.id
        }
        serializer = ActivityCreateSerializer(data=data)
        self.assertTrue(serializer.is_valid())

        activity = serializer.save()
        self.assertEqual(activity.priority, 'medium')  # Default
        self.assertFalse(activity.is_completed)
        self.assertFalse(activity.is_cancelled)

    def test_create_sanitizes_data(self):
        """Test create serializer properly sanitizes input data"""
        data = {
            'type': 'call',
            'title': '  Sanitized Activity  ',
            'description': '  This is a sanitized activity  ',
            'location': '  Conference Room A  ',
            'scheduled_at': (timezone.now() + timedelta(days=1)).isoformat(),
            'contact': self.contact.id,
            'owner': self.user.id
        }
        serializer = ActivityCreateSerializer(data=data)
        self.assertTrue(serializer.is_valid())

        activity = serializer.save()
        self.assertEqual(activity.title, 'Sanitized Activity')
        self.assertEqual(activity.description, 'This is a sanitized activity')
        self.assertEqual(activity.location, 'Conference Room A')

    def test_create_automatic_reminder_calculation(self):
        """Test create serializer automatically calculates reminder time"""
        data = {
            'type': 'call',
            'title': 'Activity with Reminder',
            'scheduled_at': (timezone.now() + timedelta(days=1)).isoformat(),
            'reminder_minutes': 30,
            'contact': self.contact.id,
            'owner': self.user.id
        }
        serializer = ActivityCreateSerializer(data=data)
        self.assertTrue(serializer.is_valid())

        activity = serializer.save()
        self.assertEqual(activity.reminder_minutes, 30)
        self.assertIsNotNone(activity.reminder_at)
        self.assertEqual(
            activity.reminder_at,
            activity.scheduled_at - timedelta(minutes=30)
        )

    def test_create_with_contact_only(self):
        """Test creating activity with only contact"""
        data = {
            'type': 'call',
            'title': 'Contact Only Activity',
            'scheduled_at': (timezone.now() + timedelta(days=1)).isoformat(),
            'contact': self.contact.id,
            'owner': self.user.id
        }
        serializer = ActivityCreateSerializer(data=data)
        self.assertTrue(serializer.is_valid())

        activity = serializer.save()
        self.assertEqual(activity.contact, self.contact)
        self.assertIsNone(activity.deal)

    def test_create_with_deal_only(self):
        """Test creating activity with only deal"""
        data = {
            'type': 'call',
            'title': 'Deal Only Activity',
            'scheduled_at': (timezone.now() + timedelta(days=1)).isoformat(),
            'deal': self.deal.id,
            'owner': self.user.id
        }
        serializer = ActivityCreateSerializer(data=data)
        self.assertTrue(serializer.is_valid())

        activity = serializer.save()
        self.assertEqual(activity.deal, self.deal)
        self.assertIsNone(activity.contact)


class ActivityUpdateSerializerTests(ActivitySerializerTestCase):
    """Test ActivityUpdateSerializer functionality"""

    def setUp(self):
        super().setUp()
        self.activity = Activity.objects.create(**self.activity_data)

    def test_update_serializer_accepts_partial_data(self):
        """Test update serializer allows partial updates"""
        update_data = {
            'title': 'Updated Activity Title',
            'priority': 'high'
        }
        serializer = ActivityUpdateSerializer(
            self.activity,
            data=update_data,
            partial=True
        )
        self.assertTrue(serializer.is_valid())

    def test_update_sanitizes_provided_fields(self):
        """Test update serializer sanitizes only provided fields"""
        update_data = {
            'title': '  Updated Activity Title  ',
            'description': '  Updated description  ',
            'location': '  Updated Location  '
        }
        serializer = ActivityUpdateSerializer(
            self.activity,
            data=update_data,
            partial=True
        )
        self.assertTrue(serializer.is_valid())

        updated_activity = serializer.save()
        self.assertEqual(updated_activity.title, 'Updated Activity Title')
        self.assertEqual(updated_activity.description, 'Updated description')
        self.assertEqual(updated_activity.location, 'Updated Location')

    def test_update_preserves_unchanged_fields(self):
        """Test update preserves fields that weren't updated"""
        update_data = {'title': 'Updated Activity Title'}
        serializer = ActivityUpdateSerializer(
            self.activity,
            data=update_data,
            partial=True
        )
        self.assertTrue(serializer.is_valid())

        updated_activity = serializer.save()
        self.assertEqual(updated_activity.title, 'Updated Activity Title')
        self.assertEqual(updated_activity.type, 'call')  # Unchanged
        self.assertEqual(updated_activity.priority, 'medium')  # Unchanged

    def test_update_completion_status(self):
        """Test updating activity completion status"""
        update_data = {
            'is_completed': True,
            'completion_notes': 'Activity completed successfully'
        }
        serializer = ActivityUpdateSerializer(
            self.activity,
            data=update_data,
            partial=True
        )
        self.assertTrue(serializer.is_valid())

        updated_activity = serializer.save()
        self.assertTrue(updated_activity.is_completed)
        self.assertIsNotNone(updated_activity.completed_at)
        self.assertEqual(updated_activity.completion_notes, 'Activity completed successfully')

    def test_update_cancellation_status(self):
        """Test updating activity cancellation status"""
        update_data = {'is_cancelled': True}
        serializer = ActivityUpdateSerializer(
            self.activity,
            data=update_data,
            partial=True
        )
        self.assertTrue(serializer.is_valid())

        updated_activity = serializer.save()
        self.assertTrue(updated_activity.is_cancelled)

    def test_update_reminder_calculation(self):
        """Test updating activity recalculates reminder time"""
        update_data = {'reminder_minutes': 60}
        serializer = ActivityUpdateSerializer(
            self.activity,
            data=update_data,
            partial=True
        )
        self.assertTrue(serializer.is_valid())

        updated_activity = serializer.save()
        self.assertEqual(updated_activity.reminder_minutes, 60)
        self.assertEqual(
            updated_activity.reminder_at,
            updated_activity.scheduled_at - timedelta(minutes=60)
        )


class ActivityDetailSerializerTests(ActivitySerializerTestCase):
    """Test ActivityDetailSerializer functionality"""

    def setUp(self):
        super().setUp()
        self.activity = Activity.objects.create(**self.activity_data)

    def test_detail_serializer_includes_additional_fields(self):
        """Test detail serializer includes comprehensive activity information"""
        serializer = ActivityDetailSerializer(self.activity)
        data = serializer.data

        # Should include basic fields
        self.assertEqual(data['id'], self.activity.id)
        self.assertEqual(data['title'], 'Test Activity')

        # Should include computed fields
        self.assertEqual(data['status'], 'scheduled')
        self.assertFalse(data['is_overdue'])
        self.assertFalse(data['is_due_soon'])

        # Should include relationship data
        self.assertIn('contact_details', data)
        self.assertIn('deal_details', data)
        self.assertIn('owner_details', data)
        self.assertEqual(data['contact_details']['id'], self.contact.id)
        self.assertEqual(data['deal_details']['id'], self.deal.id)
        self.assertEqual(data['owner_details']['id'], self.user.id)

        # Should include timestamps
        self.assertIn('created_at', data)
        self.assertIn('updated_at', data)
        self.assertIn('scheduled_at', data)

    def test_detail_serializer_includes_comments(self):
        """Test detail serializer includes activity comments"""
        # Create some comments
        ActivityComment.objects.create(
            activity=self.activity,
            author=self.user,
            comment='First comment'
        )
        ActivityComment.objects.create(
            activity=self.activity,
            author=self.user,
            comment='Second comment'
        )

        serializer = ActivityDetailSerializer(self.activity)
        data = serializer.data

        self.assertIn('comments', data)
        self.assertEqual(len(data['comments']), 2)
        self.assertEqual(data['comments'][0]['comment'], 'First comment')
        self.assertEqual(data['comments'][1]['comment'], 'Second comment')


class ActivitySummarySerializerTests(ActivitySerializerTestCase):
    """Test ActivitySummarySerializer functionality"""

    def setUp(self):
        super().setUp()
        self.activity = Activity.objects.create(**self.activity_data)

    def test_summary_serializer_includes_essential_fields(self):
        """Test summary serializer includes only essential fields"""
        serializer = ActivitySummarySerializer(self.activity)
        data = serializer.data

        # Should include essential identification fields
        self.assertIn('id', data)
        self.assertIn('uuid', data)
        self.assertEqual(data['title'], 'Test Activity')
        self.assertEqual(data['type'], 'call')
        self.assertEqual(data['priority'], 'medium')
        self.assertEqual(data['scheduled_at'], data['scheduled_at'])

        # Should include computed summary fields
        self.assertIn('status', data)
        self.assertIn('is_overdue', data)
        self.assertIn('is_due_soon', data)

        # Should not include verbose fields
        self.assertNotIn('description', data)
        self.assertNotIn('completion_notes', data)
        self.assertNotIn('created_at', data)
        self.assertNotIn('updated_at', data)
        self.assertNotIn('comments', data)

    def test_summary_serializer_includes_contact_summary(self):
        """Test summary serializer includes brief contact information"""
        serializer = ActivitySummarySerializer(self.activity)
        data = serializer.data

        self.assertIn('contact', data)
        self.assertEqual(data['contact']['id'], self.contact.id)
        self.assertEqual(data['contact']['full_name'], 'John Doe')


class ActivityCommentSerializerTests(ActivitySerializerTestCase):
    """Test ActivityCommentSerializer functionality"""

    def setUp(self):
        super().setUp()
        self.activity = Activity.objects.create(**self.activity_data)
        self.comment_data = {
            'activity': self.activity.id,
            'comment': 'This is a test comment',
            'author': self.user.id
        }

    def test_comment_serialization(self):
        """Test comment serialization"""
        comment = ActivityComment.objects.create(
            activity=self.activity,
            author=self.user,
            comment='Test comment'
        )
        serializer = ActivityCommentSerializer(comment)
        data = serializer.data

        self.assertEqual(data['id'], comment.id)
        self.assertEqual(data['comment'], 'Test comment')
        self.assertEqual(data['activity'], self.activity.id)
        self.assertEqual(data['author'], self.user.id)
        self.assertIn('created_at', data)

    def test_comment_validation(self):
        """Test comment validation"""
        invalid_data = {
            'activity': self.activity.id,
            # Missing comment
        }
        serializer = ActivityCommentSerializer(data=invalid_data)

        with self.assertRaises(ValidationError) as context:
            serializer.is_valid(raise_exception=True)

        self.assertIn('comment', context.exception.detail)

    def test_comment_creation(self):
        """Test comment creation"""
        serializer = ActivityCommentSerializer(data=self.comment_data)
        self.assertTrue(serializer.is_valid())

        comment = serializer.save()
        self.assertEqual(comment.activity, self.activity)
        self.assertEqual(comment.comment, 'This is a test comment')
        self.assertEqual(comment.author, self.user)

    def test_comment_sanitization(self):
        """Test comment sanitization"""
        data = self.comment_data.copy()
        data['comment'] = '  This is a sanitized comment  '

        serializer = ActivityCommentSerializer(data=data)
        self.assertTrue(serializer.is_valid())

        comment = serializer.save()
        self.assertEqual(comment.comment, 'This is a sanitized comment')


class ActivitySerializerIntegrationTests(ActivitySerializerTestCase):
    """Integration tests for Activity serializers"""

    def test_serializer_with_contact_object(self):
        """Test serializer works with Contact object instead of ID"""
        data = self.activity_data.copy()
        data['contact'] = self.contact
        data['deal'] = self.deal
        data['owner'] = self.user
        serializer = ActivitySerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_serializer_field_validation_order(self):
        """Test field validation happens in correct order"""
        data = self.activity_data.copy()
        data['type'] = 'invalid_type'
        data['priority'] = 'invalid_priority'
        data['duration_minutes'] = -30

        serializer = ActivitySerializer(data=data)
        with self.assertRaises(ValidationError) as context:
            serializer.is_valid(raise_exception=True)

        # Should catch all validation errors
        self.assertIn('type', context.exception.detail)
        self.assertIn('priority', context.exception.detail)
        self.assertIn('duration_minutes', context.exception.detail)

    def test_serializer_error_messages_are_user_friendly(self):
        """Test serializer provides user-friendly error messages"""
        data = self.activity_data.copy()
        data['scheduled_at'] = 'invalid-date'

        serializer = ActivitySerializer(data=data)
        with self.assertRaises(ValidationError) as context:
            serializer.is_valid(raise_exception=True)

        scheduled_at_error = context.exception.detail['scheduled_at'][0]
        self.assertIsInstance(scheduled_at_error, str)
        self.assertTrue(len(scheduled_at_error) > 0)

    def test_activity_type_validation(self):
        """Test activity type field validation"""
        valid_types = [choice[0] for choice in Activity.ACTIVITY_TYPES]

        for activity_type in valid_types:
            data = self.activity_data.copy()
            data['type'] = activity_type
            serializer = ActivitySerializer(data=data)
            self.assertTrue(serializer.is_valid(), f"Failed for activity type: {activity_type}")

        invalid_types = ['invalid_type', 'meeting_type', '']

        for activity_type in invalid_types:
            data = self.activity_data.copy()
            data['type'] = activity_type
            serializer = ActivitySerializer(data=data)
            self.assertFalse(serializer.is_valid(), f"Should have failed for activity type: {activity_type}")

    def test_priority_validation(self):
        """Test priority field validation"""
        valid_priorities = [choice[0] for choice in Activity.PRIORITY_CHOICES]

        for priority in valid_priorities:
            data = self.activity_data.copy()
            data['priority'] = priority
            serializer = ActivitySerializer(data=data)
            self.assertTrue(serializer.is_valid(), f"Failed for priority: {priority}")

        invalid_priorities = ['invalid_priority', 'high_priority', '']

        for priority in invalid_priorities:
            data = self.activity_data.copy()
            data['priority'] = priority
            serializer = ActivitySerializer(data=data)
            self.assertFalse(serializer.is_valid(), f"Should have failed for priority: {priority}")

    def test_activity_status_consistency(self):
        """Test activity status calculation consistency"""
        # Test scheduled activity
        future_time = timezone.now() + timedelta(days=1)
        data = self.activity_data.copy()
        data['scheduled_at'] = future_time
        serializer = ActivitySerializer(data=data)
        self.assertTrue(serializer.is_valid())

        activity = serializer.save()
        serializer = ActivitySerializer(activity)
        data = serializer.data
        self.assertEqual(data['status'], 'scheduled')

        # Test completed activity
        activity.is_completed = True
        activity.completed_at = timezone.now()
        activity.save()
        serializer = ActivitySerializer(activity)
        data = serializer.data
        self.assertEqual(data['status'], 'completed')

    def test_activity_datetime_precision(self):
        """Test activity datetime maintains precision"""
        specific_time = timezone.now() + timedelta(hours=2, minutes=30)
        data = self.activity_data.copy()
        data['scheduled_at'] = specific_time.isoformat()

        serializer = ActivitySerializer(data=data)
        self.assertTrue(serializer.is_valid())

        activity = serializer.save()
        # Should be very close to the original time (within seconds)
        time_diff = abs(activity.scheduled_at - specific_time)
        self.assertLess(time_diff, timedelta(seconds=1))