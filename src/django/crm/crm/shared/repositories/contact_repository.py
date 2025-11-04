"""
Contact Repository - KISS Implementation
Simple, focused data access following SOLID principles
"""

from django.contrib.auth import get_user_model
from django.db.models import Q, Count, Sum
from .base import BaseRepository

User = get_user_model()


class ContactRepository(BaseRepository):
    """
    Simple Contact Repository - Following KISS principle
    Focused only on data access operations
    """

    def __init__(self):
        from crm.apps.contacts.models import Contact
        super().__init__(Contact)

    def get_user_contacts(self, user_id, include_inactive=False):
        """Get contacts for a specific user"""
        queryset = self.model.objects.filter(owner_id=user_id)
        if not include_inactive:
            queryset = queryset.filter(is_active=True)
        return queryset

    def get_by_email(self, email, user_id=None):
        """Get contact by email"""
        queryset = self.model.objects.filter(email__iexact=email)
        if user_id:
            queryset = queryset.filter(owner_id=user_id)
        return queryset.first()

    def search_contacts(self, user_id, query):
        """Simple search functionality"""
        if not query:
            return self.get_user_contacts(user_id)

        return self.model.objects.filter(
            Q(owner_id=user_id) &
            (
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query) |
                Q(email__icontains=query) |
                Q(company__icontains=query)
            )
        )

    def get_by_company(self, user_id, company):
        """Get contacts by company"""
        return self.model.objects.filter(
            owner_id=user_id,
            company__icontains=company
        )

    def get_recent_contacts(self, user_id, days=30):
        """Get recent contacts"""
        from django.utils import timezone
        from datetime import timedelta

        cutoff_date = timezone.now() - timedelta(days=days)
        return self.model.objects.filter(
            owner_id=user_id,
            created_at__gte=cutoff_date
        ).order_by('-created_at')

    def get_statistics(self, user_id=None):
        """Simple contact statistics"""
        queryset = self.model.objects.all()
        if user_id:
            queryset = queryset.filter(owner_id=user_id)

        return {
            'total_contacts': queryset.count(),
            'active_contacts': queryset.filter(is_active=True).count(),
            'inactive_contacts': queryset.filter(is_active=False).count(),
        }