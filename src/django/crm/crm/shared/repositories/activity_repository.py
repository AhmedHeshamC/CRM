"""
Activity Repository - KISS Implementation
Simple, focused data access following SOLID principles
"""

from django.contrib.auth import get_user_model
from django.db.models import Q
from .base import BaseRepository

User = get_user_model()


class ActivityRepository(BaseRepository):
    """
    Simple Activity Repository - Following KISS principle
    Focused only on data access operations
    """

    def __init__(self):
        from crm.apps.activities.models import Activity
        super().__init__(Activity)

    def get_user_activities(self, user_id, include_completed=False):
        """Get activities for a specific user"""
        queryset = self.model.objects.filter(owner_id=user_id)
        if not include_completed:
            queryset = queryset.filter(is_completed=False)
        return queryset

    def get_contact_activities(self, contact_id, user_id=None):
        """Get activities for a specific contact"""
        queryset = self.model.objects.filter(contact_id=contact_id)
        if user_id:
            queryset = queryset.filter(owner_id=user_id)
        return queryset

    def get_deal_activities(self, deal_id, user_id=None):
        """Get activities for a specific deal"""
        queryset = self.model.objects.filter(deal_id=deal_id)
        if user_id:
            queryset = queryset.filter(owner_id=user_id)
        return queryset

    def get_upcoming_activities(self, user_id, days=7):
        """Get upcoming activities"""
        from django.utils import timezone
        from datetime import timedelta

        cutoff_date = timezone.now() + timedelta(days=days)
        return self.model.objects.filter(
            owner_id=user_id,
            scheduled_at__lte=cutoff_date,
            is_completed=False,
            is_cancelled=False
        ).order_by('scheduled_at')

    def get_overdue_activities(self, user_id):
        """Get overdue activities"""
        from django.utils import timezone

        return self.model.objects.filter(
            owner_id=user_id,
            scheduled_at__lt=timezone.now(),
            is_completed=False,
            is_cancelled=False
        ).order_by('scheduled_at')

    def search_activities(self, user_id, query):
        """Simple search functionality"""
        if not query:
            return self.get_user_activities(user_id)

        return self.model.objects.filter(
            Q(owner_id=user_id) &
            (
                Q(title__icontains=query) |
                Q(description__icontains=query) |
                Q(contact__first_name__icontains=query) |
                Q(contact__last_name__icontains=query) |
                Q(deal__title__icontains=query)
            )
        )