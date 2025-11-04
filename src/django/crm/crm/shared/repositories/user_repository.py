"""
User Repository - KISS Implementation
Simple, focused data access following SOLID principles
"""

from django.db.models import Q
from .base import BaseRepository


class UserRepository(BaseRepository):
    """
    Simple User Repository - Following KISS principle
    Focused only on data access operations
    """

    def __init__(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        super().__init__(User)

    def get_by_email(self, email):
        """Get user by email"""
        return self.model.objects.filter(email__iexact=email).first()

    def get_active_users(self):
        """Get active users"""
        return self.model.objects.filter(is_active=True)

    def get_by_role(self, role):
        """Get users by role"""
        return self.model.objects.filter(role=role)

    def search_users(self, query):
        """Simple search functionality"""
        if not query:
            return self.get_active_users()

        return self.model.objects.filter(
            Q(is_active=True) &
            (
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query) |
                Q(email__icontains=query) |
                Q(role__icontains=query)
            )
        )

    def get_user_statistics(self):
        """Simple user statistics"""
        return {
            'total_users': self.model.objects.count(),
            'active_users': self.model.objects.filter(is_active=True).count(),
            'admin_users': self.model.objects.filter(role='admin').count(),
            'sales_users': self.model.objects.filter(role='sales').count(),
            'manager_users': self.model.objects.filter(role='manager').count(),
        }