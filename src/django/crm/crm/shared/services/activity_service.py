"""
Activity Service - KISS Implementation
Simple business logic following SOLID principles
"""

from ..repositories.activity_repository import ActivityRepository
from django.core.exceptions import ValidationError


class ActivityService:
    """
    Simple Activity Service - Following KISS principle
    Focused only on activity business logic
    """

    def __init__(self, repository=None):
        """Initialize with repository"""
        self.repository = repository or ActivityRepository()

    def create_activity(self, data, user_id):
        """Create new activity with simple validation"""
        # Set owner
        data['owner_id'] = user_id
        return self.repository.create(**data)

    def update_activity(self, activity_id, data, user_id):
        """Update activity with permission check"""
        activity = self.repository.get_by_id(activity_id)
        if not activity:
            raise ValidationError('Activity not found.')

        # Check permission
        if activity.owner_id != user_id:
            raise ValidationError('Permission denied.')

        return self.repository.update(activity, **data)

    def complete_activity(self, activity_id, user_id, completion_notes=None):
        """Mark activity as completed"""
        activity = self.repository.get_by_id(activity_id)
        if not activity:
            raise ValidationError('Activity not found.')

        if activity.owner_id != user_id:
            raise ValidationError('Permission denied.')

        data = {'is_completed': True}
        if completion_notes:
            data['completion_notes'] = completion_notes

        return self.repository.update(activity, **data)

    def cancel_activity(self, activity_id, user_id):
        """Cancel activity"""
        activity = self.repository.get_by_id(activity_id)
        if not activity:
            raise ValidationError('Activity not found.')

        if activity.owner_id != user_id:
            raise ValidationError('Permission denied.')

        return self.repository.update(activity, is_cancelled=True)

    def get_user_activities(self, user_id, include_completed=False):
        """Get activities for user"""
        return self.repository.get_user_activities(user_id, include_completed)

    def get_upcoming_activities(self, user_id, days=7):
        """Get upcoming activities"""
        return self.repository.get_upcoming_activities(user_id, days)

    def get_overdue_activities(self, user_id):
        """Get overdue activities"""
        return self.repository.get_overdue_activities(user_id)

    def search_user_activities(self, user_id, query):
        """Search activities for user"""
        return self.repository.search_activities(user_id, query)