"""
UserViewSet Filter Classes - SOLID Compliant
Extracting filtering logic to follow Single Responsibility Principle
"""

from django.db.models import Q
from rest_framework import filters


class UserFilterMixin:
    """
    Mixin for user filtering functionality
    Following Single Responsibility Principle
    """

    def apply_role_filter(self, queryset, role):
        """Apply role filtering"""
        if role:
            return queryset.filter(role=role)
        return queryset

    def apply_status_filter(self, queryset, is_active):
        """Apply status filtering"""
        if is_active is not None:
            return queryset.filter(is_active=is_active.lower() == 'true')
        return queryset

    def apply_department_filter(self, queryset, department):
        """Apply department filtering"""
        if department:
            return queryset.filter(department__icontains=department)
        return queryset

    def apply_search_filter(self, queryset, search):
        """Apply search functionality"""
        if search:
            return queryset.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(email__icontains=search) |
                Q(department__icontains=search)
            )
        return queryset


class UserQuerysetBuilder(UserFilterMixin):
    """
    Builder pattern for complex user queries
    Following SOLID principles
    """

    def __init__(self, base_queryset):
        self.queryset = base_queryset

    def filter_by_role(self, role):
        """Chain role filtering"""
        self.queryset = self.apply_role_filter(self.queryset, role)
        return self

    def filter_by_status(self, is_active):
        """Chain status filtering"""
        self.queryset = self.apply_status_filter(self.queryset, is_active)
        return self

    def filter_by_department(self, department):
        """Chain department filtering"""
        self.queryset = self.apply_department_filter(self.queryset, department)
        return self

    def search(self, query):
        """Chain search filtering"""
        self.queryset = self.apply_search_filter(self.queryset, query)
        return self

    def build(self):
        """Return final queryset"""
        return self.queryset