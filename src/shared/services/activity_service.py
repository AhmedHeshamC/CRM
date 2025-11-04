"""
Activity Service Implementation
Following SOLID principles and enterprise best practices
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from django.contrib.auth import get_user_model
from django.utils import timezone

from .base_service import BaseService, ValidationError, NotFoundError, PermissionError, ConflictError
from ..repositories.activity_repository import ActivityRepository
from ..repositories.contact_repository import ContactRepository
from ..repositories.deal_repository import DealRepository
from crm.apps.activities.models import Activity

User = get_user_model()


class ActivityService(BaseService[Activity]):
    """
    Service for Activity business operations
    Following SOLID principles and clean architecture
    """

    def __init__(self,
                 activity_repository: Optional[ActivityRepository] = None,
                 contact_repository: Optional[ContactRepository] = None,
                 deal_repository: Optional[DealRepository] = None):
        """Initialize activity service with repositories"""
        super().__init__(activity_repository or ActivityRepository())
        self.contact_repository = contact_repository or ContactRepository()
        self.deal_repository = deal_repository or DealRepository()

    def validate_create_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate activity data for creation

        Args:
            data: Activity data

        Returns:
            Validated data

        Raises:
            ValidationError: If data is invalid
        """
        validated_data = {}

        # Validate required fields
        required_fields = ['type', 'title', 'scheduled_at', 'owner']
        for field in required_fields:
            if field not in data or data[field] is None:
                raise ValidationError(f"{field} is required")

        # Validate type
        valid_types = [choice[0] for choice in Activity.ACTIVITY_TYPES]
        if data['type'] not in valid_types:
            raise ValidationError(f"Invalid activity type. Must be one of: {valid_types}")
        validated_data['type'] = data['type']

        # Validate title
        validated_data['title'] = data['title'].strip()
        if len(validated_data['title']) < 3:
            raise ValidationError("Title must be at least 3 characters long")

        # Validate scheduled_at
        scheduled_at = data['scheduled_at']
        if isinstance(scheduled_at, str):
            try:
                # Handle ISO format datetime strings
                scheduled_at = datetime.fromisoformat(scheduled_at.replace('Z', '+00:00'))
                if scheduled_at.tzinfo is None:
                    scheduled_at = timezone.make_aware(scheduled_at)
            except (ValueError, AttributeError):
                raise ValidationError("Invalid scheduled_at format. Use ISO datetime format.")

        # For new activities (except notes), scheduled time should not be too far in the past
        if scheduled_at < timezone.now() - timedelta(minutes=5) and data['type'] != 'note':
            raise ValidationError("Scheduled time cannot be more than 5 minutes in the past for new activities")

        validated_data['scheduled_at'] = scheduled_at

        # Validate owner
        owner = data['owner']
        if isinstance(owner, int):
            owner_obj = User.objects.get(id=owner)
            validated_data['owner'] = owner_obj
        else:
            validated_data['owner'] = owner

        # Validate that at least one of contact or deal is specified
        contact = data.get('contact')
        deal = data.get('deal')

        if not contact and not deal:
            raise ValidationError("Activity must be associated with either a contact or a deal")

        # Validate contact if provided
        if contact:
            if isinstance(contact, int):
                contact_obj = self.contact_repository.get_by_id(contact)
                if not contact_obj:
                    raise ValidationError("Contact not found")
                validated_data['contact'] = contact_obj
            else:
                validated_data['contact'] = contact

        # Validate deal if provided
        if deal:
            if isinstance(deal, int):
                deal_obj = self.deal_repository.get_by_id(deal)
                if not deal_obj:
                    raise ValidationError("Deal not found")
                validated_data['deal'] = deal_obj
            else:
                validated_data['deal'] = deal

        # Validate optional fields
        if 'description' in data and data['description']:
            validated_data['description'] = data['description'].strip()

        # Validate duration
        if 'duration_minutes' in data and data['duration_minutes']:
            duration = data['duration_minutes']
            if not isinstance(duration, int) or duration <= 0:
                raise ValidationError("Duration must be a positive integer in minutes")
            validated_data['duration_minutes'] = duration

        # Validate priority
        if 'priority' in data:
            valid_priorities = [choice[0] for choice in Activity.PRIORITY_CHOICES]
            if data['priority'] not in valid_priorities:
                raise ValidationError(f"Invalid priority. Must be one of: {valid_priorities}")
            validated_data['priority'] = data['priority']
        else:
            validated_data['priority'] = 'medium'

        # Validate reminder
        if 'reminder_minutes' in data and data['reminder_minutes']:
            reminder = data['reminder_minutes']
            if not isinstance(reminder, int) or reminder <= 0:
                raise ValidationError("Reminder minutes must be a positive integer")
            validated_data['reminder_minutes'] = reminder

        # Validate location for meetings
        if 'location' in data and data['location']:
            validated_data['location'] = data['location'].strip()

        # Validate video conference URL
        if 'video_conference_url' in data and data['video_conference_url']:
            validated_data['video_conference_url'] = data['video_conference_url'].strip()

        # Set defaults
        validated_data.setdefault('is_completed', False)
        validated_data.setdefault('is_cancelled', False)

        return validated_data

    def validate_update_data(self, entity_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate activity data for update

        Args:
            entity_id: Activity ID
            data: Update data

        Returns:
            Validated data

        Raises:
            ValidationError: If data is invalid
            NotFoundError: If activity doesn't exist
        """
        # Check if activity exists
        activity = self.repository.get_by_id(entity_id)
        if not activity:
            raise NotFoundError(f"Activity with ID {entity_id} not found")

        validated_data = {}

        # Can't update completed or cancelled activities (except to uncomplete)
        if activity.is_completed and 'is_completed' in data and data['is_completed']:
            raise ValidationError("Activity is already completed")
        if activity.is_cancelled and 'is_cancelled' in data and data['is_cancelled']:
            raise ValidationError("Activity is already cancelled")

        # Validate and clean fields
        if 'title' in data:
            if not data['title'].strip():
                raise ValidationError("Title cannot be empty")
            if len(data['title'].strip()) < 3:
                raise ValidationError("Title must be at least 3 characters long")
            validated_data['title'] = data['title'].strip()

        if 'scheduled_at' in data:
            scheduled_at = data['scheduled_at']
            if isinstance(scheduled_at, str):
                try:
                    scheduled_at = datetime.fromisoformat(scheduled_at.replace('Z', '+00:00'))
                    if scheduled_at.tzinfo is None:
                        scheduled_at = timezone.make_aware(scheduled_at)
                except (ValueError, AttributeError):
                    raise ValidationError("Invalid scheduled_at format")

            # Allow rescheduling past activities but not too far in the past
            if (scheduled_at < timezone.now() - timedelta(minutes=5) and
                activity.type != 'note' and
                not activity.is_completed):
                raise ValidationError("Cannot reschedule to more than 5 minutes in the past")

            validated_data['scheduled_at'] = scheduled_at

        if 'duration_minutes' in data:
            duration = data['duration_minutes']
            if duration and (not isinstance(duration, int) or duration <= 0):
                raise ValidationError("Duration must be a positive integer in minutes")
            validated_data['duration_minutes'] = duration

        if 'priority' in data:
            valid_priorities = [choice[0] for choice in Activity.PRIORITY_CHOICES]
            if data['priority'] not in valid_priorities:
                raise ValidationError(f"Invalid priority. Must be one of: {valid_priorities}")
            validated_data['priority'] = data['priority']

        if 'reminder_minutes' in data:
            reminder = data['reminder_minutes']
            if reminder and (not isinstance(reminder, int) or reminder <= 0):
                raise ValidationError("Reminder minutes must be a positive integer")
            validated_data['reminder_minutes'] = reminder

        if 'description' in data:
            validated_data['description'] = data['description'].strip() if data['description'] else None

        if 'location' in data:
            validated_data['location'] = data['location'].strip() if data['location'] else None

        if 'video_conference_url' in data:
            validated_data['video_conference_url'] = data['video_conference_url'].strip() if data['video_conference_url'] else None

        return validated_data

    def create_activity(self, data: Dict[str, Any], user_id: int) -> Activity:
        """
        Create a new activity with business logic

        Args:
            data: Activity data
            user_id: ID of user creating the activity

        Returns:
            Created activity

        Raises:
            ValidationError: If data is invalid
            PermissionError: If user doesn't have permission
        """
        # Validate owner permissions
        if 'owner' in data:
            owner_id = data['owner'].id if hasattr(data['owner'], 'id') else data['owner']
            if owner_id != user_id:
                user = User.objects.get(id=user_id)
                if not user.is_admin() and not user.is_manager():
                    raise PermissionError("You can only create activities for yourself")

        # Validate contact access if contact is specified
        if 'contact' in data and data['contact']:
            contact_id = data['contact'].id if hasattr(data['contact'], 'id') else data['contact']
            contact = self.contact_repository.get_by_id(contact_id)
            if not contact:
                raise NotFoundError(f"Contact with ID {contact_id} not found")

            user = User.objects.get(id=user_id)
            if contact.owner_id != user_id and not user.is_admin():
                raise PermissionError("You can only create activities for your own contacts")

        # Validate deal access if deal is specified
        if 'deal' in data and data['deal']:
            deal_id = data['deal'].id if hasattr(data['deal'], 'id') else data['deal']
            deal = self.deal_repository.get_by_id(deal_id)
            if not deal:
                raise NotFoundError(f"Deal with ID {deal_id} not found")

            user = User.objects.get(id=user_id)
            if deal.owner_id != user_id and not user.is_admin():
                raise PermissionError("You can only create activities for your own deals")

        return self.create(data)

    def update_activity(self, activity_id: int, data: Dict[str, Any], user_id: int) -> Activity:
        """
        Update an activity with business logic

        Args:
            activity_id: Activity ID
            data: Update data
            user_id: ID of user updating the activity

        Returns:
            Updated activity

        Raises:
            ValidationError: If data is invalid
            NotFoundError: If activity doesn't exist
            PermissionError: If user doesn't have permission
        """
        # Get activity to check permissions
        activity = self.repository.get_by_id(activity_id)
        if not activity:
            raise NotFoundError(f"Activity with ID {activity_id} not found")

        # Check permissions
        user = User.objects.get(id=user_id)
        if activity.owner_id != user_id and not user.is_admin():
            raise PermissionError("You can only update your own activities")

        return self.update(activity_id, data)

    def complete_activity(self, activity_id: int, notes: Optional[str] = None, user_id: int = None) -> Activity:
        """
        Complete an activity with business logic

        Args:
            activity_id: Activity ID
            notes: Optional completion notes
            user_id: ID of user completing the activity

        Returns:
            Updated activity

        Raises:
            ValidationError: If activity cannot be completed
            NotFoundError: If activity doesn't exist
            PermissionError: If user doesn't have permission
        """
        # Get activity to check permissions
        activity = self.repository.get_by_id(activity_id)
        if not activity:
            raise NotFoundError(f"Activity with ID {activity_id} not found")

        # Check permissions
        if user_id:
            user = User.objects.get(id=user_id)
            if activity.owner_id != user_id and not user.is_admin():
                raise PermissionError("You can only complete your own activities")

        # Validate that activity can be completed
        if activity.is_completed:
            raise ValidationError("Activity is already completed")
        elif activity.is_cancelled:
            raise ValidationError("Cannot complete a cancelled activity")

        success = self.repository.complete_activity(activity_id, notes)
        if not success:
            raise ValidationError("Failed to complete activity")

        return self.repository.get_by_id(activity_id)

    def cancel_activity(self, activity_id: int, user_id: int = None) -> Activity:
        """
        Cancel an activity with business logic

        Args:
            activity_id: Activity ID
            user_id: ID of user cancelling the activity

        Returns:
            Updated activity

        Raises:
            ValidationError: If activity cannot be cancelled
            NotFoundError: If activity doesn't exist
            PermissionError: If user doesn't have permission
        """
        # Get activity to check permissions
        activity = self.repository.get_by_id(activity_id)
        if not activity:
            raise NotFoundError(f"Activity with ID {activity_id} not found")

        # Check permissions
        if user_id:
            user = User.objects.get(id=user_id)
            if activity.owner_id != user_id and not user.is_admin():
                raise PermissionError("You can only cancel your own activities")

        # Validate that activity can be cancelled
        if activity.is_cancelled:
            raise ValidationError("Activity is already cancelled")
        elif activity.is_completed:
            raise ValidationError("Cannot cancel a completed activity")

        success = self.repository.cancel_activity(activity_id)
        if not success:
            raise ValidationError("Failed to cancel activity")

        return self.repository.get_by_id(activity_id)

    def reschedule_activity(self, activity_id: int, new_time: datetime, user_id: int = None) -> Activity:
        """
        Reschedule an activity with business logic

        Args:
            activity_id: Activity ID
            new_time: New scheduled time
            user_id: ID of user rescheduling the activity

        Returns:
            Updated activity

        Raises:
            ValidationError: If activity cannot be rescheduled
            NotFoundError: If activity doesn't exist
            PermissionError: If user doesn't have permission
        """
        # Get activity to check permissions
        activity = self.repository.get_by_id(activity_id)
        if not activity:
            raise NotFoundError(f"Activity with ID {activity_id} not found")

        # Check permissions
        if user_id:
            user = User.objects.get(id=user_id)
            if activity.owner_id != user_id and not user.is_admin():
                raise PermissionError("You can only reschedule your own activities")

        # Validate that activity can be rescheduled
        if activity.is_completed:
            raise ValidationError("Cannot reschedule a completed activity")
        elif activity.is_cancelled:
            raise ValidationError("Cannot reschedule a cancelled activity")

        # Validate new time
        if isinstance(new_time, str):
            try:
                new_time = datetime.fromisoformat(new_time.replace('Z', '+00:00'))
                if new_time.tzinfo is None:
                    new_time = timezone.make_aware(new_time)
            except (ValueError, AttributeError):
                raise ValidationError("Invalid new_time format")

        success = self.repository.reschedule_activity(activity_id, new_time)
        if not success:
            raise ValidationError("Failed to reschedule activity")

        return self.repository.get_by_id(activity_id)

    def get_user_activities(self, user_id: int, **filters) -> List[Activity]:
        """
        Get all activities for a user

        Args:
            user_id: User ID
            **filters: Additional filters

        Returns:
            List of activities
        """
        filters['owner_id'] = user_id
        return self.repository.filter(**filters)

    def get_user_upcoming_activities(self, user_id: int, days: int = 7) -> List[Activity]:
        """
        Get upcoming activities for a user

        Args:
            user_id: User ID
            days: Number of days ahead

        Returns:
            List of upcoming activities
        """
        return self.repository.get_upcoming_activities(user_id, days)

    def get_user_overdue_activities(self, user_id: int) -> List[Activity]:
        """
        Get overdue activities for a user

        Args:
            user_id: User ID

        Returns:
            List of overdue activities
        """
        return self.repository.get_overdue_activities(user_id)

    def get_activities_by_type(self, user_id: int, activity_type: str) -> List[Activity]:
        """
        Get activities by type for a user

        Args:
            user_id: User ID
            activity_type: Activity type

        Returns:
            List of activities
        """
        return self.repository.get_by_type(activity_type, user_id)

    def get_activities_by_priority(self, user_id: int, priority: str) -> List[Activity]:
        """
        Get activities by priority for a user

        Args:
            user_id: User ID
            priority: Priority level

        Returns:
            List of activities
        """
        return self.repository.get_activities_by_priority(priority, user_id)

    def search_user_activities(self, user_id: int, query: str) -> List[Activity]:
        """
        Search activities for a specific user

        Args:
            user_id: User ID
            query: Search query

        Returns:
            List of matching activities
        """
        return self.repository.search_activities(query, user_id)

    def get_activities_for_date_range(self, user_id: int, start_date: datetime, end_date: datetime) -> List[Activity]:
        """
        Get activities for a user within date range

        Args:
            user_id: User ID
            start_date: Start date
            end_date: End date

        Returns:
            List of activities
        """
        return self.repository.get_activities_for_date_range(start_date, end_date, user_id)

    def get_activity_statistics(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get activity statistics

        Args:
            user_id: Optional user ID to filter by

        Returns:
            Statistics dictionary
        """
        return self.repository.get_activity_statistics(user_id)

    def get_due_soon_activities(self, user_id: int, hours: int = 24) -> List[Activity]:
        """
        Get activities due soon for a user

        Args:
            user_id: User ID
            hours: Number of hours ahead

        Returns:
            List of activities due soon
        """
        return self.repository.get_due_soon_activities(hours, user_id)

    def get_completed_activities(self, user_id: int, days: int = 7) -> List[Activity]:
        """
        Get completed activities for a user

        Args:
            user_id: User ID
            days: Number of days to look back

        Returns:
            List of completed activities
        """
        return self.repository.get_completed_activities(user_id, days)

    def bulk_complete_activities(self, activity_ids: List[int], user_id: int) -> Dict[str, Any]:
        """
        Bulk complete activities for a user

        Args:
            activity_ids: List of activity IDs
            user_id: User ID

        Returns:
            Dictionary with completion results
        """
        results = {
            'completed': [],
            'failed': [],
            'errors': []
        }

        for activity_id in activity_ids:
            try:
                completed_activity = self.complete_activity(activity_id, user_id=user_id)
                results['completed'].append(completed_activity.id)
            except Exception as e:
                results['failed'].append(activity_id)
                results['errors'].append(str(e))

        return results

    def get_activities_needing_reminders(self) -> List[Activity]:
        """
        Get activities that need reminders sent

        Returns:
            List of activities needing reminders
        """
        return self.repository.get_activities_needing_reminders()

    def send_reminders(self, activity_ids: List[int]) -> Dict[str, Any]:
        """
        Send reminders for activities

        Args:
            activity_ids: List of activity IDs

        Returns:
            Dictionary with reminder results
        """
        results = {
            'sent': [],
            'failed': [],
            'errors': []
        }

        for activity_id in activity_ids:
            try:
                success = self.repository.send_reminder(activity_id)
                if success:
                    results['sent'].append(activity_id)
                else:
                    results['failed'].append(activity_id)
            except Exception as e:
                results['failed'].append(activity_id)
                results['errors'].append(str(e))

        return results