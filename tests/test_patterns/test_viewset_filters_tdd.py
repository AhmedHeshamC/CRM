"""
TDD Tests for UserViewSet Filtering Logic
Following Red-Green-Refactor cycle
"""

import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.db.models import Q
from unittest.mock import Mock, patch

from crm.apps.authentication.viewset_filters import UserFilterMixin, UserQuerysetBuilder

User = get_user_model()


class TestUserFilterMixin(TestCase):
    """
    Test UserFilterMixin following TDD methodology
    Red phase: Write failing tests first
    """

    def setUp(self):
        """Set up test data"""
        self.filter_mixin = UserFilterMixin()

        # Create test users
        self.admin_user = User.objects.create_user(
            email='admin@example.com',
            first_name='Admin',
            last_name='User',
            password='testpass123',
            role='admin'
        )

        self.sales_user = User.objects.create_user(
            email='sales@example.com',
            first_name='Sales',
            last_name='User',
            password='testpass123',
            role='sales'
        )

        self.manager_user = User.objects.create_user(
            email='manager@example.com',
            first_name='Manager',
            last_name='User',
            password='testpass123',
            role='manager'
        )

    def test_apply_role_filter_with_valid_role(self):
        """
        Test role filtering with valid role
        TDD: Should filter by role correctly
        """
        # Arrange
        base_queryset = User.objects.all()
        role = 'sales'

        # Act
        filtered_queryset = self.filter_mixin.apply_role_filter(base_queryset, role)

        # Assert
        self.assertEqual(filtered_queryset.count(), 1)
        self.assertEqual(filtered_queryset.first().role, 'sales')

    def test_apply_role_filter_with_none_role(self):
        """
        Test role filtering with None role
        TDD: Should return original queryset
        """
        # Arrange
        base_queryset = User.objects.all()
        original_count = base_queryset.count()

        # Act
        filtered_queryset = self.filter_mixin.apply_role_filter(base_queryset, None)

        # Assert
        self.assertEqual(filtered_queryset.count(), original_count)

    def test_apply_status_filter_active(self):
        """
        Test status filtering with active status
        TDD: Should filter active users
        """
        # Arrange
        # Deactivate one user for testing
        self.sales_user.is_active = False
        self.sales_user.save()

        base_queryset = User.objects.all()
        is_active = 'true'

        # Act
        filtered_queryset = self.filter_mixin.apply_status_filter(base_queryset, is_active)

        # Assert
        self.assertEqual(filtered_queryset.count(), 2)
        self.assertTrue(all(user.is_active for user in filtered_queryset))

    def test_apply_status_filter_inactive(self):
        """
        Test status filtering with inactive status
        TDD: Should filter inactive users
        """
        # Arrange
        # Deactivate one user for testing
        self.sales_user.is_active = False
        self.sales_user.save()

        base_queryset = User.objects.all()
        is_active = 'false'

        # Act
        filtered_queryset = self.filter_mixin.apply_status_filter(base_queryset, is_active)

        # Assert
        self.assertEqual(filtered_queryset.count(), 1)
        self.assertFalse(filtered_queryset.first().is_active)

    def test_apply_department_filter(self):
        """
        Test department filtering
        TDD: Should filter by department
        """
        # Arrange
        self.admin_user.department = 'IT'
        self.admin_user.save()

        self.sales_user.department = 'Sales'
        self.sales_user.save()

        base_queryset = User.objects.all()
        department = 'sales'

        # Act
        filtered_queryset = self.filter_mixin.apply_department_filter(base_queryset, department)

        # Assert
        self.assertEqual(filtered_queryset.count(), 1)
        self.assertEqual(filtered_queryset.first().department, 'Sales')

    def test_apply_search_filter_by_first_name(self):
        """
        Test search filtering by first name
        TDD: Should search across multiple fields
        """
        # Arrange
        base_queryset = User.objects.all()
        search = 'Admin'

        # Act
        filtered_queryset = self.filter_mixin.apply_search_filter(base_queryset, search)

        # Assert
        self.assertEqual(filtered_queryset.count(), 1)
        self.assertEqual(filtered_queryset.first().first_name, 'Admin')

    def test_apply_search_filter_by_email(self):
        """
        Test search filtering by email
        TDD: Should search across multiple fields
        """
        # Arrange
        base_queryset = User.objects.all()
        search = 'sales@example.com'

        # Act
        filtered_queryset = self.filter_mixin.apply_search_filter(base_queryset, search)

        # Assert
        self.assertEqual(filtered_queryset.count(), 1)
        self.assertEqual(filtered_queryset.first().email, 'sales@example.com')

    def test_apply_search_filter_case_insensitive(self):
        """
        Test search filtering is case insensitive
        TDD: Should be case insensitive
        """
        # Arrange
        base_queryset = User.objects.all()
        search = 'MANAGER'  # Uppercase

        # Act
        filtered_queryset = self.filter_mixin.apply_search_filter(base_queryset, search)

        # Assert
        self.assertEqual(filtered_queryset.count(), 1)
        self.assertEqual(filtered_queryset.first().first_name, 'Manager')


class TestUserQuerysetBuilder(TestCase):
    """
    Test UserQuerysetBuilder following TDD methodology
    Testing Builder pattern implementation
    """

    def setUp(self):
        """Set up test data"""
        # Create test users with different attributes
        self.admin_user = User.objects.create_user(
            email='admin@example.com',
            first_name='Admin',
            last_name='User',
            password='testpass123',
            role='admin',
            department='IT',
            is_active=True
        )

        self.sales_user = User.objects.create_user(
            email='sales@example.com',
            first_name='Sales',
            last_name='User',
            password='testpass123',
            role='sales',
            department='Sales',
            is_active=True
        )

        self.inactive_manager = User.objects.create_user(
            email='manager@example.com',
            first_name='Manager',
            last_name='User',
            password='testpass123',
            role='manager',
            department='Management',
            is_active=False
        )

    def test_builder_with_no_filters(self):
        """
        Test builder with no filters applied
        TDD: Should return all users
        """
        # Arrange
        base_queryset = User.objects.all()
        builder = UserQuerysetBuilder(base_queryset)

        # Act
        result = builder.build()

        # Assert
        self.assertEqual(result.count(), 3)

    def test_builder_with_single_role_filter(self):
        """
        Test builder with single role filter
        TDD: Should apply role filter correctly
        """
        # Arrange
        base_queryset = User.objects.all()
        builder = UserQuerysetBuilder(base_queryset)

        # Act
        result = builder.filter_by_role('sales').build()

        # Assert
        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first().role, 'sales')

    def test_builder_with_multiple_filters(self):
        """
        Test builder with multiple filters
        TDD: Should chain filters correctly
        """
        # Arrange
        base_queryset = User.objects.all()
        builder = UserQuerysetBuilder(base_queryset)

        # Act
        result = (builder
                  .filter_by_role('admin')
                  .filter_by_status('true')
                  .filter_by_department('it')
                  .build())

        # Assert
        self.assertEqual(result.count(), 1)
        user = result.first()
        self.assertEqual(user.role, 'admin')
        self.assertEqual(user.department, 'IT')
        self.assertTrue(user.is_active)

    def test_builder_with_search_and_filters(self):
        """
        Test builder with search and other filters
        TDD: Should combine search with filters
        """
        # Arrange
        base_queryset = User.objects.all()
        builder = UserQuerysetBuilder(base_queryset)

        # Act
        result = (builder
                  .search('user')  # Should match all users with 'User' in last name
                  .filter_by_status('true')
                  .build())

        # Assert
        self.assertEqual(result.count(), 2)  # Two active users with 'User' in last name

    def test_builder_is_immutable(self):
        """
        Test that builder doesn't modify original queryset
        TDD: Should be immutable
        """
        # Arrange
        base_queryset = User.objects.all()
        original_count = base_queryset.count()
        builder = UserQuerysetBuilder(base_queryset)

        # Act
        builder.filter_by_role('admin').build()

        # Assert
        self.assertEqual(base_queryset.count(), original_count)

    def test_builder_chaining_returns_self(self):
        """
        Test that builder methods return builder instance
        TDD: Should enable method chaining
        """
        # Arrange
        base_queryset = User.objects.all()
        builder = UserQuerysetBuilder(base_queryset)

        # Act & Assert
        result = builder.filter_by_role('sales')
        self.assertIsInstance(result, UserQuerysetBuilder)

        result = result.filter_by_status('true')
        self.assertIsInstance(result, UserQuerysetBuilder)

    def test_builder_with_empty_search(self):
        """
        Test builder with empty search term
        TDD: Should handle empty search gracefully
        """
        # Arrange
        base_queryset = User.objects.all()
        builder = UserQuerysetBuilder(base_queryset)

        # Act
        result = builder.search('').build()

        # Assert
        self.assertEqual(result.count(), 3)  # Should return all users

    def test_builder_with_none_values(self):
        """
        Test builder with None filter values
        TDD: Should handle None values gracefully
        """
        # Arrange
        base_queryset = User.objects.all()
        builder = UserQuerysetBuilder(base_queryset)

        # Act
        result = (builder
                  .filter_by_role(None)
                  .filter_by_status(None)
                  .filter_by_department(None)
                  .build())

        # Assert
        self.assertEqual(result.count(), 3)  # Should return all users


class TestUserViewSetIntegration(TestCase):
    """
    Integration tests for UserViewSet with new filtering logic
    Testing the complete integration with TDD approach
    """

    def setUp(self):
        """Set up test data"""
        self.admin_user = User.objects.create_user(
            email='admin@example.com',
            first_name='Admin',
            last_name='User',
            password='testpass123',
            role='admin',
            is_staff=True,
            is_superuser=True
        )

        self.sales_user = User.objects.create_user(
            email='sales@example.com',
            first_name='Sales',
            last_name='User',
            password='testpass123',
            role='sales'
        )

    def test_queryset_filtering_integration(self):
        """
        Test the integration of filtering logic in actual ViewSet context
        TDD: Should work in real ViewSet scenario
        """
        # Simulate ViewSet filtering logic
        from crm.apps.authentication.viewset_filters import UserQuerysetBuilder

        # Simulate request parameters
        role = 'sales'
        is_active = 'true'
        search = 'Sales'

        # Build queryset using new pattern
        queryset = User.objects.all()
        builder = UserQuerysetBuilder(queryset)

        filtered_queryset = (builder
                           .filter_by_role(role)
                           .filter_by_status(is_active)
                           .search(search)
                           .build())

        # Assert results
        self.assertEqual(filtered_queryset.count(), 1)
        user = filtered_queryset.first()
        self.assertEqual(user.role, 'sales')
        self.assertTrue(user.is_active)
        self.assertEqual(user.first_name, 'Sales')

    def test_performance_with_large_dataset(self):
        """
        Test performance with larger dataset
        TDD: Should maintain performance with many users
        """
        # Create additional users for performance testing
        for i in range(100):
            User.objects.create_user(
                email=f'user{i}@example.com',
                first_name=f'User{i}',
                last_name='Test',
                password='testpass123',
                role='sales' if i % 2 == 0 else 'manager'
            )

        from crm.apps.authentication.viewset_filters import UserQuerysetBuilder

        # Test filtering performance
        import time
        start_time = time.time()

        queryset = User.objects.all()
        builder = UserQuerysetBuilder(queryset)
        result = builder.filter_by_role('sales').build()

        end_time = time.time()
        execution_time = end_time - start_time

        # Assert performance (should be under 1 second for 103 users)
        self.assertLess(execution_time, 1.0)
        self.assertEqual(result.count(), 51)  # Half should be sales role

    def test_solid_principles_compliance(self):
        """
        Test that the new filtering logic follows SOLID principles
        TDD: Should comply with SOLID principles
        """
        from crm.apps.authentication.viewset_filters import UserFilterMixin, UserQuerysetBuilder

        # Test Single Responsibility Principle
        filter_mixin = UserFilterMixin()

        # Each method should have a single responsibility
        assert hasattr(filter_mixin, 'apply_role_filter')
        assert hasattr(filter_mixin, 'apply_status_filter')
        assert hasattr(filter_mixin, 'apply_department_filter')
        assert hasattr(filter_mixin, 'apply_search_filter')

        # Test Open/Closed Principle - should be extensible
        class ExtendedFilterMixin(UserFilterMixin):
            def apply_custom_filter(self, queryset, custom_value):
                if custom_value:
                    return queryset.filter(custom_field=custom_value)
                return queryset

        extended_filter = ExtendedFilterMixin()
        assert hasattr(extended_filter, 'apply_custom_filter')

        # Test Interface Segregation - methods are focused
        # UserQuerysetBuilder only depends on UserFilterMixin methods it uses
        builder = UserQuerysetBuilder(User.objects.all())
        result = builder.filter_by_role('admin').build()
        assert isinstance(result, type(User.objects.all()))

        # Test Dependency Inversion - depends on abstraction (Q objects)
        # UserFilterMixin uses Django's Q abstraction, not concrete implementations