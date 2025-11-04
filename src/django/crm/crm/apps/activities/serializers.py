"""
Activity Serializers - API Data Transformation Layer
Following SOLID principles and enterprise best practices
"""

from datetime import datetime, timedelta
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .models import Activity, ActivityComment
from crm.apps.contacts.serializers import ContactSummarySerializer
from crm.apps.deals.serializers import DealSummarySerializer

User = get_user_model()


class BaseActivitySerializer(serializers.ModelSerializer):
    """
    Base Activity Serializer with common validation logic
    Following Single Responsibility Principle
    """

    # Computed fields
    status = serializers.CharField(read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    is_due_soon = serializers.BooleanField(read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    duration_display = serializers.SerializerMethodField()
    priority_display_with_color = serializers.SerializerMethodField()

    # Custom field validation
    scheduled_at = serializers.DateTimeField(
        error_messages={
            'invalid': _('Enter a valid date and time.'),
            'null': _('Scheduled time is required.')
        }
    )

    duration_minutes = serializers.IntegerField(
        min_value=1,
        required=False,
        allow_null=True,
        error_messages={
            'min_value': _('Duration must be at least 1 minute.'),
            'invalid': _('Enter a valid number.')
        }
    )

    reminder_minutes = serializers.IntegerField(
        min_value=0,
        required=False,
        allow_null=True,
        error_messages={
            'min_value': _('Reminder time cannot be negative.'),
            'invalid': _('Enter a valid number.')
        }
    )

    # Relationship serializers
    contact_details = ContactSummarySerializer(source='contact', read_only=True)
    deal_details = DealSummarySerializer(source='deal', read_only=True)
    owner_details = serializers.SerializerMethodField()

    class Meta:
        model = Activity
        fields = [
            'id', 'uuid', 'type', 'type_display', 'title', 'description',
            'scheduled_at', 'duration_minutes', 'duration_display',
            'priority', 'priority_display', 'priority_display_with_color',
            'is_completed', 'is_cancelled', 'completed_at', 'completion_notes',
            'contact', 'contact_details', 'deal', 'deal_details', 'owner',
            'owner_details', 'reminder_minutes', 'reminder_sent', 'reminder_at',
            'location', 'video_conference_url', 'status', 'is_overdue',
            'is_due_soon', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'uuid', 'created_at', 'updated_at', 'completed_at',
            'reminder_sent', 'reminder_at', 'status', 'is_overdue', 'is_due_soon'
        ]

    def get_duration_display(self, obj):
        """Get formatted duration display"""
        return obj.get_duration_display()

    def get_priority_display_with_color(self, obj):
        """Get priority display with color information"""
        return obj.get_priority_display_with_color()

    def get_owner_details(self, obj):
        """Get simplified owner information"""
        return {
            'id': obj.owner.id,
            'name': obj.owner.get_full_name(),
            'email': obj.owner.email,
            'role': obj.owner.role
        }

    def validate_type(self, value):
        """Validate activity type"""
        valid_types = [choice[0] for choice in Activity.ACTIVITY_TYPES]
        if value not in valid_types:
            raise serializers.ValidationError(
                _('Invalid activity type. Must be one of: {}').format(', '.join(valid_types))
            )
        return value

    def validate_priority(self, value):
        """Validate priority"""
        valid_priorities = [choice[0] for choice in Activity.PRIORITY_CHOICES]
        if value not in valid_priorities:
            raise serializers.ValidationError(
                _('Invalid priority. Must be one of: {}').format(', '.join(valid_priorities))
            )
        return value

    def validate_scheduled_at(self, value):
        """Validate scheduled time"""
        # Notes can be scheduled in the past
        if self.instance and self.instance.type == 'note':
            return value

        # For new activities (not notes), check if scheduled time is in the future
        if not self.instance and value < timezone.now() - timedelta(minutes=5):
            activity_type = self.initial_data.get('type', '')
            if activity_type != 'note':
                raise serializers.ValidationError(
                    _('Scheduled time cannot be in the past for new activities (except notes).')
                )

        return value

    def validate(self, attrs):
        """
        Cross-field validation
        Following SOLID principles for comprehensive validation
        """
        # At least one of contact or deal must be specified
        contact = attrs.get('contact')
        deal = attrs.get('deal')

        if not contact and not deal:
            raise serializers.ValidationError(
                _('Activity must be associated with either a contact or a deal.')
            )

        # Validate completion logic
        is_completed = attrs.get('is_completed', False) if 'is_completed' in attrs else (
            self.instance.is_completed if self.instance else False
        )

        if is_completed:
            # Completed activities should have completed_at
            if 'completed_at' not in attrs and (not self.instance or not self.instance.completed_at):
                attrs['completed_at'] = timezone.now()

            # Reset cancellation if completing
            if 'is_cancelled' in attrs:
                attrs['is_cancelled'] = False
        elif 'is_cancelled' in attrs and attrs['is_cancelled']:
            # Cancelled activities should not be completed
            attrs['is_completed'] = False
            attrs['completed_at'] = None
            attrs['completion_notes'] = None

        # Auto-calculate reminder_at based on reminder_minutes
        reminder_minutes = attrs.get('reminder_minutes')
        scheduled_at = attrs.get('scheduled_at')

        if reminder_minutes is not None and scheduled_at:
            attrs['reminder_at'] = scheduled_at - timedelta(minutes=reminder_minutes)
        elif reminder_minutes is None:
            attrs['reminder_at'] = None

        return attrs

    def validate_title(self, value):
        """Validate and sanitize title"""
        if not value or not value.strip():
            raise serializers.ValidationError(_('Activity title is required.'))
        return value.strip()

    def validate_description(self, value):
        """Validate and sanitize description"""
        if value:
            return value.strip()
        return ''

    def validate_location(self, value):
        """Validate and sanitize location"""
        if value:
            return value.strip()
        return ''


class ActivitySerializer(BaseActivitySerializer):
    """
    Standard Activity Serializer for general use
    Following Open/Closed Principle for extensibility
    """

    class Meta(BaseActivitySerializer.Meta):
        pass


class ActivityCreateSerializer(BaseActivitySerializer):
    """
    Activity Create Serializer with creation-specific validation
    Following Single Responsibility Principle
    """

    owner = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        write_only=True
    )

    class Meta(BaseActivitySerializer.Meta):
        fields = [
            'type', 'title', 'description', 'scheduled_at', 'duration_minutes',
            'priority', 'contact', 'deal', 'owner', 'reminder_minutes',
            'location', 'video_conference_url'
        ]

    def create(self, validated_data):
        """
        Create activity with business logic
        Following KISS principle for clean, readable creation logic
        """
        # Set default values
        validated_data.setdefault('priority', 'medium')
        validated_data.setdefault('is_completed', False)
        validated_data.setdefault('is_cancelled', False)

        return super().create(validated_data)


class ActivityUpdateSerializer(BaseActivitySerializer):
    """
    Activity Update Serializer with update-specific validation
    Following Single Responsibility Principle
    """

    class Meta(BaseActivitySerializer.Meta):
        fields = [
            'type', 'title', 'description', 'scheduled_at', 'duration_minutes',
            'priority', 'is_completed', 'is_cancelled', 'completion_notes',
            'contact', 'deal', 'reminder_minutes', 'location',
            'video_conference_url'
        ]

    def update(self, instance, validated_data):
        """
        Update activity with business logic
        Following SOLID principles for clean business logic
        """
        # Handle completion status changes
        if 'is_completed' in validated_data:
            is_completed = validated_data['is_completed']

            if is_completed and not instance.is_completed:
                # Activity is being marked as completed
                validated_data['completed_at'] = timezone.now()
            elif not is_completed and instance.is_completed:
                # Activity is being un-completed
                validated_data['completed_at'] = None
                validated_data['completion_notes'] = None

        # Handle cancellation status changes
        if 'is_cancelled' in validated_data:
            is_cancelled = validated_data['is_cancelled']

            if is_cancelled:
                # Activity is being cancelled
                validated_data['is_completed'] = False
                validated_data['completed_at'] = None
                validated_data['completion_notes'] = None

        # Update reminder_sent if reminder time changed
        if 'reminder_at' in validated_data:
            new_reminder_at = validated_data['reminder_at']
            if new_reminder_at != instance.reminder_at:
                validated_data['reminder_sent'] = False

        return super().update(instance, validated_data)


class ActivityDetailSerializer(BaseActivitySerializer):
    """
    Detailed Activity Serializer with comprehensive information
    Following Single Responsibility Principle for detailed views
    """

    comments = serializers.SerializerMethodField()

    class Meta(BaseActivitySerializer.Meta):
        fields = BaseActivitySerializer.Meta.fields + ['comments']

    def get_comments(self, obj):
        """Get activity comments"""
        comments = obj.comments.order_by('created_at')
        return ActivityCommentSerializer(comments, many=True).data


class ActivitySummarySerializer(serializers.ModelSerializer):
    """
    Summary Activity Serializer for list views and dropdowns
    Following KISS principle for lightweight data transfer
    """

    status = serializers.CharField(read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    is_due_soon = serializers.BooleanField(read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    contact = ContactSummarySerializer(read_only=True)

    class Meta:
        model = Activity
        fields = [
            'id', 'uuid', 'type', 'type_display', 'title', 'scheduled_at',
            'priority', 'priority_display', 'status', 'is_overdue',
            'is_due_soon', 'is_completed', 'is_cancelled', 'contact'
        ]


class ActivityCommentSerializer(serializers.ModelSerializer):
    """
    Activity Comment Serializer for activity updates
    Following SOLID principles for clean data transformation
    """

    author_name = serializers.CharField(source='author.get_full_name', read_only=True)

    class Meta:
        model = ActivityComment
        fields = [
            'id', 'activity', 'comment', 'author', 'author_name', 'created_at'
        ]
        read_only_fields = ['id', 'author', 'created_at']

    def validate_comment(self, value):
        """Validate and sanitize comment"""
        if not value or not value.strip():
            raise serializers.ValidationError(_('Comment cannot be empty.'))
        return value.strip()

    def create(self, validated_data):
        """Create comment with proper user assignment"""
        # Set author from request context if not provided
        request = self.context.get('request')
        if request and request.user and not validated_data.get('author'):
            validated_data['author'] = request.user

        return super().create(validated_data)


class ActivityBulkOperationSerializer(serializers.Serializer):
    """
    Bulk operation serializer for activity management
    Following KISS principle for simple bulk operations
    """

    activity_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
        error_messages={
            'min_length': _('At least one activity ID must be provided.')
        }
    )

    operation = serializers.ChoiceField(
        choices=[
            ('complete', _('Complete')),
            ('cancel', _('Cancel')),
            ('reschedule', _('Reschedule')),
            ('delete', _('Delete')),
        ]
    )

    new_scheduled_time = serializers.DateTimeField(
        required=False,
        allow_null=True,
        error_messages={
            'invalid': _('Enter a valid date and time.')
        }
    )

    completion_notes = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True
    )

    def validate_activity_ids(self, value):
        """Validate activity IDs exist"""
        existing_ids = Activity.objects.filter(id__in=value).values_list('id', flat=True)
        missing_ids = set(value) - set(existing_ids)

        if missing_ids:
            raise serializers.ValidationError(
                _('The following activity IDs do not exist: {}').format(list(missing_ids))
            )

        return value

    def validate(self, attrs):
        """Cross-field validation"""
        operation = attrs.get('operation')
        new_scheduled_time = attrs.get('new_scheduled_time')

        if operation == 'reschedule' and not new_scheduled_time:
            raise serializers.ValidationError(
                _('New scheduled time is required for reschedule operation.')
            )

        return attrs


class ActivityStatisticsSerializer(serializers.Serializer):
    """
    Activity Statistics Serializer for analytics
    Following Single Responsibility Principle for analytics
    """

    total_activities = serializers.IntegerField(read_only=True)
    completed_activities = serializers.IntegerField(read_only=True)
    pending_activities = serializers.IntegerField(read_only=True)
    overdue_activities = serializers.IntegerField(read_only=True)
    completion_rate = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    activities_by_type = serializers.DictField(read_only=True)
    activities_by_priority = serializers.DictField(read_only=True)
    activities_this_week = serializers.IntegerField(read_only=True)
    activities_this_month = serializers.IntegerField(read_only=True)


class ActivityCalendarSerializer(serializers.Serializer):
    """
    Activity Calendar Serializer for calendar views
    Following Single Responsibility Principle for calendar functionality
    """

    start_date = serializers.DateField()
    end_date = serializers.DateField()
    activities = serializers.ListField(read_only=True)

    def validate(self, attrs):
        """Validate date range"""
        start_date = attrs.get('start_date')
        end_date = attrs.get('end_date')

        if start_date >= end_date:
            raise serializers.ValidationError(_('End date must be after start date.'))

        # Limit date range to 1 year
        if (end_date - start_date).days > 365:
            raise serializers.ValidationError(_('Date range cannot exceed 1 year.'))

        return attrs


class ActivityReminderSerializer(serializers.Serializer):
    """
    Activity Reminder Serializer for reminder management
    Following Single Responsibility Principle for reminder functionality
    """

    activity_id = serializers.IntegerField()
    reminder_minutes = serializers.IntegerField(min_value=0)
    send_now = serializers.BooleanField(default=False)

    def validate_activity_id(self, value):
        """Validate activity exists"""
        if not Activity.objects.filter(id=value).exists():
            raise serializers.ValidationError(_('Activity not found.'))
        return value

    def validate(self, attrs):
        """Cross-field validation"""
        send_now = attrs.get('send_now', False)
        reminder_minutes = attrs.get('reminder_minutes')

        if send_now and reminder_minutes:
            raise serializers.ValidationError(
                _('Cannot set reminder time and send now simultaneously.')
            )


# Simple TDD Serializers - Following KISS principle
class SimpleActivitySerializer(serializers.ModelSerializer):
    """
    Simple Activity Serializer for TDD API development
    Following KISS principle - minimal functionality
    """
    owner = serializers.PrimaryKeyRelatedField(read_only=True)
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    contact_name = serializers.SerializerMethodField()
    deal_title = serializers.SerializerMethodField()

    class Meta:
        model = Activity
        fields = [
            'id', 'type', 'type_display', 'title', 'description',
            'contact', 'contact_name', 'deal', 'deal_title',
            'scheduled_at', 'duration_minutes', 'priority',
            'owner', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'owner']

    def get_contact_name(self, obj):
        """Get contact name for display"""
        return str(obj.contact) if obj.contact else None

    def get_deal_title(self, obj):
        """Get deal title for display"""
        return obj.deal.title if obj.deal else None

    def create(self, validated_data):
        """Set owner from request context"""
        request = self.context.get('request')
        if request and request.user:
            validated_data['owner'] = request.user
        return super().create(validated_data)

        return attrs