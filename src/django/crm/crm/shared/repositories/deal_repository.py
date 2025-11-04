"""
Deal Repository - KISS Implementation
Simple, focused data access following SOLID principles
"""

from django.contrib.auth import get_user_model
from django.db.models import Q, Sum, Count, Avg
from .base import BaseRepository

User = get_user_model()


class DealRepository(BaseRepository):
    """
    Simple Deal Repository - Following KISS principle
    Focused only on data access operations
    """

    def __init__(self):
        from crm.apps.deals.models import Deal
        super().__init__(Deal)

    def get_user_deals(self, user_id, include_closed=False):
        """Get deals for a specific user"""
        queryset = self.model.objects.filter(owner_id=user_id)
        if not include_closed:
            queryset = queryset.filter(is_won=False, is_lost=False)
        return queryset

    def get_contact_deals(self, contact_id, user_id=None):
        """Get deals for a specific contact"""
        queryset = self.model.objects.filter(contact_id=contact_id)
        if user_id:
            queryset = queryset.filter(owner_id=user_id)
        return queryset

    def get_by_stage(self, stage, user_id=None):
        """Get deals by stage"""
        queryset = self.model.objects.filter(stage=stage)
        if user_id:
            queryset = queryset.filter(owner_id=user_id)
        return queryset

    def get_won_deals(self, user_id=None):
        """Get won deals"""
        queryset = self.model.objects.filter(is_won=True)
        if user_id:
            queryset = queryset.filter(owner_id=user_id)
        return queryset

    def get_lost_deals(self, user_id=None):
        """Get lost deals"""
        queryset = self.model.objects.filter(is_lost=True)
        if user_id:
            queryset = queryset.filter(owner_id=user_id)
        return queryset

    def get_open_deals(self, user_id=None):
        """Get open deals (not won or lost)"""
        queryset = self.model.objects.filter(is_won=False, is_lost=False)
        if user_id:
            queryset = queryset.filter(owner_id=user_id)
        return queryset

    def get_pipeline_value(self, user_id=None):
        """Get total value of open deals"""
        queryset = self.get_open_deals(user_id)
        result = queryset.aggregate(total=Sum('value'))
        return result['total'] or 0

    def get_statistics(self, user_id=None):
        """Simple deal statistics"""
        queryset = self.model.objects.all()
        if user_id:
            queryset = queryset.filter(owner_id=user_id)

        return {
            'total_deals': queryset.count(),
            'won_deals': queryset.filter(is_won=True).count(),
            'lost_deals': queryset.filter(is_lost=True).count(),
            'open_deals': queryset.filter(is_won=False, is_lost=False).count(),
            'total_value': queryset.aggregate(Sum('value'))['value__sum'] or 0,
            'won_value': queryset.filter(is_won=True).aggregate(Sum('value'))['value__sum'] or 0,
            'average_value': queryset.aggregate(Avg('value'))['value__avg'] or 0,
        }

    def search_deals(self, user_id, query):
        """Simple search functionality"""
        if not query:
            return self.get_user_deals(user_id)

        return self.model.objects.filter(
            Q(owner_id=user_id) &
            (
                Q(title__icontains=query) |
                Q(description__icontains=query) |
                Q(contact__first_name__icontains=query) |
                Q(contact__last_name__icontains=query) |
                Q(contact__company__icontains=query)
            )
        )