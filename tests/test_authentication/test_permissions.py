"""
Test Suite for Role-Based Permission Classes
Following TDD approach and SOLID principles
"""

import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView
from rest_framework.request import Request
from unittest.mock import MagicMock
from shared.authentication.permissions import (
    BaseRolePermission,
    IsAdminUser,
    IsManagerOrAdminUser,
    IsSalesOrAboveUser,
    IsOwnerOrReadOnly,
    IsSelfOrAdmin,
    DynamicRolePermission,
    DepartmentBasedPermission,
    ContactPermission,
    DealPermission,
    ActivityPermission,
)

User = get_user_model()


class BaseRolePermissionTest(TestCase):
    """Test cases for BaseRolePermission"""

    def setUp(self):
        """Set up test environment"""
        self.factory = APIRequestFactory()
        self.permission = BaseRolePermission()
        self.view = APIView()

        # Create test users
        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            role='admin'
        )
        self.manager_user = User.objects.create_user(
            email='manager@test.com',
            password='testpass123',
            role='manager'
        )
        self.sales_user = User.objects.create_user(
            email='sales@test.com',
            password='testpass123',
            role='sales'
        )
        self.support_user = User.objects.create_user(
            email='support@test.com',
            password='testpass123',
            role='support'
        )
        self.inactive_user = User.objects.create_user(
            email='inactive@test.com',
            password='testpass123',
            role='sales',
            is_active=False
        )

    def test_role_hierarchy(self):
        """Test role hierarchy levels"""
        hierarchy = self.permission.ROLE_HIERARCHY
        self.assertEqual(hierarchy['admin'], 4)
        self.assertEqual(hierarchy['manager'], 3)
        self.assertEqual(hierarchy['sales'], 2)
        self.assertEqual(hierarchy['support'], 1)

    def test_get_user_role_level(self):
        """Test getting user role level"""
        self.assertEqual(self.permission._get_user_role_level(self.admin_user), 4)
        self.assertEqual(self.permission._get_user_role_level(self.manager_user), 3)
        self.assertEqual(self.permission._get_user_role_level(self.sales_user), 2)
        self.assertEqual(self.permission._get_user_role_level(self.support_user), 1)

    def test_has_higher_or_equal_role(self):
        """Test role comparison"""
        # Admin can access all roles
        self.assertTrue(self.permission._has_higher_or_equal_role(self.admin_user, 'admin'))
        self.assertTrue(self.permission._has_higher_or_equal_role(self.admin_user, 'manager'))
        self.assertTrue(self.permission._has_higher_or_equal_role(self.admin_user, 'sales'))
        self.assertTrue(self.permission._has_higher_or_equal_role(self.admin_user, 'support'))

        # Manager can access manager and below
        self.assertFalse(self.permission._has_higher_or_equal_role(self.manager_user, 'admin'))
        self.assertTrue(self.permission._has_higher_or_equal_role(self.manager_user, 'manager'))
        self.assertTrue(self.permission._has_higher_or_equal_role(self.manager_user, 'sales'))
        self.assertTrue(self.permission._has_higher_or_equal_role(self.manager_user, 'support'))

        # Sales can access sales and support
        self.assertFalse(self.permission._has_higher_or_equal_role(self.sales_user, 'admin'))
        self.assertFalse(self.permission._has_higher_or_equal_role(self.sales_user, 'manager'))
        self.assertTrue(self.permission._has_higher_or_equal_role(self.sales_user, 'sales'))
        self.assertTrue(self.permission._has_higher_or_equal_role(self.sales_user, 'support'))

    def test_unauthenticated_access_denied(self):
        """Test that unauthenticated users are denied"""
        request = self.factory.get('/api/v1/contacts/')
        request.user = MagicMock()
        request.user.is_authenticated = False

        self.assertFalse(self.permission.has_permission(request, self.view))

    def test_inactive_user_denied(self):
        """Test that inactive users are denied"""
        request = self.factory.get('/api/v1/contacts/')
        request.user = self.inactive_user

        self.assertFalse(self.permission.has_permission(request, self.view))

    def test_authenticated_user_allowed(self):
        """Test that authenticated active users are allowed"""
        request = self.factory.get('/api/v1/contacts/')
        request.user = self.sales_user

        self.assertTrue(self.permission.has_permission(request, self.view))


class IsAdminUserTest(TestCase):
    """Test cases for IsAdminUser"""

    def setUp(self):
        """Set up test environment"""
        self.factory = APIRequestFactory()
        self.permission = IsAdminUser()
        self.view = APIView()

        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            role='admin'
        )
        self.sales_user = User.objects.create_user(
            email='sales@test.com',
            password='testpass123',
            role='sales'
        )

    def test_admin_user_allowed(self):
        """Test that admin users are allowed"""
        request = self.factory.get('/api/v1/admin/')
        request.user = self.admin_user

        self.assertTrue(self.permission.has_permission(request, self.view))

    def test_non_admin_user_denied(self):
        """Test that non-admin users are denied"""
        request = self.factory.get('/api/v1/admin/')
        request.user = self.sales_user

        self.assertFalse(self.permission.has_permission(request, self.view))


class IsManagerOrAdminUserTest(TestCase):
    """Test cases for IsManagerOrAdminUser"""

    def setUp(self):
        """Set up test environment"""
        self.factory = APIRequestFactory()
        self.permission = IsManagerOrAdminUser()
        self.view = APIView()

        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            role='admin'
        )
        self.manager_user = User.objects.create_user(
            email='manager@test.com',
            password='testpass123',
            role='manager'
        )
        self.sales_user = User.objects.create_user(
            email='sales@test.com',
            password='testpass123',
            role='sales'
        )

    def test_admin_user_allowed(self):
        """Test that admin users are allowed"""
        request = self.factory.get('/api/v1/manager/')
        request.user = self.admin_user

        self.assertTrue(self.permission.has_permission(request, self.view))

    def test_manager_user_allowed(self):
        """Test that manager users are allowed"""
        request = self.factory.get('/api/v1/manager/')
        request.user = self.manager_user

        self.assertTrue(self.permission.has_permission(request, self.view))

    def test_sales_user_denied(self):
        """Test that sales users are denied"""
        request = self.factory.get('/api/v1/manager/')
        request.user = self.sales_user

        self.assertFalse(self.permission.has_permission(request, self.view))


class IsSalesOrAboveUserTest(TestCase):
    """Test cases for IsSalesOrAboveUser"""

    def setUp(self):
        """Set up test environment"""
        self.factory = APIRequestFactory()
        self.permission = IsSalesOrAboveUser()
        self.view = APIView()

        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            role='admin'
        )
        self.manager_user = User.objects.create_user(
            email='manager@test.com',
            password='testpass123',
            role='manager'
        )
        self.sales_user = User.objects.create_user(
            email='sales@test.com',
            password='testpass123',
            role='sales'
        )
        self.support_user = User.objects.create_user(
            email='support@test.com',
            password='testpass123',
            role='support'
        )

    def test_admin_user_allowed(self):
        """Test that admin users are allowed"""
        request = self.factory.get('/api/v1/sales/')
        request.user = self.admin_user

        self.assertTrue(self.permission.has_permission(request, self.view))

    def test_manager_user_allowed(self):
        """Test that manager users are allowed"""
        request = self.factory.get('/api/v1/sales/')
        request.user = self.manager_user

        self.assertTrue(self.permission.has_permission(request, self.view))

    def test_sales_user_allowed(self):
        """Test that sales users are allowed"""
        request = self.factory.get('/api/v1/sales/')
        request.user = self.sales_user

        self.assertTrue(self.permission.has_permission(request, self.view))

    def test_support_user_denied(self):
        """Test that support users are denied"""
        request = self.factory.get('/api/v1/sales/')
        request.user = self.support_user

        self.assertFalse(self.permission.has_permission(request, self.view))


class IsOwnerOrReadOnlyTest(TestCase):
    """Test cases for IsOwnerOrReadOnly"""

    def setUp(self):
        """Set up test environment"""
        self.factory = APIRequestFactory()
        self.permission = IsOwnerOrReadOnly()
        self.view = APIView()

        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            role='admin'
        )
        self.sales_user = User.objects.create_user(
            email='sales@test.com',
            password='testpass123',
            role='sales'
        )

        # Mock objects
        self.owned_object = MagicMock()
        self.owned_object.user = self.sales_user

        self.other_object = MagicMock()
        self.other_object.user = self.admin_user

    def test_safe_methods_allowed_for_authenticated(self):
        """Test that safe methods are allowed for authenticated users"""
        for method in ['GET', 'HEAD', 'OPTIONS']:
            with self.subTest(method=method):
                request = getattr(self.factory, method.lower())('/api/v1/contacts/')
                request.user = self.sales_user

                self.assertTrue(self.permission.has_permission(request, self.view))

    def test_owner_can_modify_own_object(self):
        """Test that owners can modify their own objects"""
        request = self.factory.put('/api/v1/contacts/1/')
        request.user = self.sales_user

        self.assertTrue(self.permission.has_object_permission(request, self.view, self.owned_object))

    def test_owner_cannot_modify_other_object(self):
        """Test that owners cannot modify other objects"""
        request = self.factory.put('/api/v1/contacts/1/')
        request.user = self.sales_user

        self.assertFalse(self.permission.has_object_permission(request, self.view, self.other_object))

    def test_admin_can_modify_any_object(self):
        """Test that admin can modify any object"""
        request = self.factory.put('/api/v1/contacts/1/')
        request.user = self.admin_user

        self.assertTrue(self.permission.has_object_permission(request, self.view, self.other_object))

    def test_user_can_modify_self(self):
        """Test that user can modify themselves"""
        request = self.factory.put('/api/v1/users/1/')
        request.user = self.sales_user

        self.assertTrue(self.permission.has_object_permission(request, self.view, self.sales_user))


class DynamicRolePermissionTest(TestCase):
    """Test cases for DynamicRolePermission"""

    def setUp(self):
        """Set up test environment"""
        self.factory = APIRequestFactory()
        self.permission = DynamicRolePermission()
        self.view = APIView()

        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            role='admin'
        )
        self.manager_user = User.objects.create_user(
            email='manager@test.com',
            password='testpass123',
            role='manager'
        )
        self.sales_user = User.objects.create_user(
            email='sales@test.com',
            password='testpass123',
            role='sales'
        )
        self.support_user = User.objects.create_user(
            email='support@test.com',
            password='testpass123',
            role='support'
        )

    def test_get_permissions_by_method(self):
        """Test permissions by HTTP method"""
        # GET requests - all roles allowed
        request = self.factory.get('/api/v1/contacts/')
        request.user = self.support_user

        self.assertTrue(self.permission.has_permission(request, self.view))

        # POST requests - sales and above allowed
        request = self.factory.post('/api/v1/contacts/')
        request.user = self.support_user
        self.assertFalse(self.permission.has_permission(request, self.view))

        request.user = self.sales_user
        self.assertTrue(self.permission.has_permission(request, self.view))

        # DELETE requests - manager and admin only
        request = self.factory.delete('/api/v1/contacts/1/')
        request.user = self.sales_user
        self.assertFalse(self.permission.has_permission(request, self.view))

        request.user = self.manager_user
        self.assertTrue(self.permission.has_permission(request, self.view))

    def test_custom_requirements(self):
        """Test custom role requirements"""
        custom_permissions = {
            'POST': ['admin', 'manager'],
            'GET': ['admin', 'manager', 'sales']
        }
        permission = DynamicRolePermission(custom_requirements)

        # Test POST with custom requirements
        request = self.factory.post('/api/v1/special/')
        request.user = self.sales_user

        self.assertFalse(permission.has_permission(request, self.view))

        request.user = self.manager_user
        self.assertTrue(permission.has_permission(request, self.view))


class DepartmentBasedPermissionTest(TestCase):
    """Test cases for DepartmentBasedPermission"""

    def setUp(self):
        """Set up test environment"""
        self.factory = APIRequestFactory()
        self.allowed_departments = {'Sales', 'Marketing'}
        self.permission = DepartmentBasedPermission(self.allowed_departments)
        self.view = APIView()

        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            role='admin'
        )
        self.sales_user = User.objects.create_user(
            email='sales@test.com',
            password='testpass123',
            role='sales',
            department='Sales'
        )
        self.other_user = User.objects.create_user(
            email='other@test.com',
            password='testpass123',
            role='sales',
            department='IT'
        )

    def test_admin_bypasses_department_restriction(self):
        """Test that admin users bypass department restrictions"""
        request = self.factory.get('/api/v1/restricted/')
        request.user = self.admin_user

        self.assertTrue(self.permission.has_permission(request, self.view))

    def test_allowed_department_access(self):
        """Test that users from allowed departments have access"""
        request = self.factory.get('/api/v1/restricted/')
        request.user = self.sales_user

        self.assertTrue(self.permission.has_permission(request, self.view))

    def test_restricted_department_denied(self):
        """Test that users from restricted departments are denied"""
        request = self.factory.get('/api/v1/restricted/')
        request.user = self.other_user

        self.assertFalse(self.permission.has_permission(request, self.view))

    def test_no_department_restriction(self):
        """Test when no department restrictions are set"""
        permission = DepartmentBasedPermission()
        request = self.factory.get('/api/v1/open/')
        request.user = self.other_user

        self.assertTrue(permission.has_permission(request, self.view))


class ContactPermissionTest(TestCase):
    """Test cases for ContactPermission"""

    def setUp(self):
        """Set up test environment"""
        self.factory = APIRequestFactory()
        self.permission = ContactPermission()
        self.view = APIView()

        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            role='admin'
        )
        self.manager_user = User.objects.create_user(
            email='manager@test.com',
            password='testpass123',
            role='manager'
        )
        self.sales_user = User.objects.create_user(
            email='sales@test.com',
            password='testpass123',
            role='sales'
        )
        self.support_user = User.objects.create_user(
            email='support@test.com',
            password='testpass123',
            role='support'
        )

        # Mock contact object
        self.contact = MagicMock()
        self.contact.assigned_to = self.sales_user

    def test_all_users_can_view_contacts(self):
        """Test that all authenticated users can view contacts"""
        request = self.factory.get('/api/v1/contacts/')
        request.user = self.support_user

        self.assertTrue(self.permission.has_permission(request, self.view))

    def test_sales_manager_admin_can_create_contacts(self):
        """Test that sales, manager, and admin can create contacts"""
        for user in [self.sales_user, self.manager_user, self.admin_user]:
            with self.subTest(user=user.role):
                request = self.factory.post('/api/v1/contacts/')
                request.user = user

                self.assertTrue(self.permission.has_permission(request, self.view))

    def test_support_cannot_create_contacts(self):
        """Test that support users cannot create contacts"""
        request = self.factory.post('/api/v1/contacts/')
        request.user = self.support_user

        self.assertFalse(self.permission.has_permission(request, self.view))

    def test_manager_admin_can_delete_contacts(self):
        """Test that manager and admin can delete contacts"""
        for user in [self.manager_user, self.admin_user]:
            with self.subTest(user=user.role):
                request = self.factory.delete('/api/v1/contacts/1/')
                request.user = user

                self.assertTrue(self.permission.has_permission(request, self.view))

    def test_sales_cannot_delete_contacts(self):
        """Test that sales users cannot delete contacts"""
        request = self.factory.delete('/api/v1/contacts/1/')
        request.user = self.sales_user

        self.assertFalse(self.permission.has_permission(request, self.view))

    def test_sales_user_can_access_own_contact(self):
        """Test that sales user can access their own contact"""
        request = self.factory.get('/api/v1/contacts/1/')
        request.user = self.sales_user

        self.assertTrue(self.permission.has_object_permission(request, self.view, self.contact))

    def test_sales_user_cannot_access_other_contact(self):
        """Test that sales user cannot access other's contact"""
        self.contact.assigned_to = self.manager_user
        request = self.factory.get('/api/v1/contacts/1/')
        request.user = self.sales_user

        self.assertFalse(self.permission.has_object_permission(request, self.view, self.contact))

    def test_admin_can_access_any_contact(self):
        """Test that admin can access any contact"""
        self.contact.assigned_to = self.manager_user
        request = self.factory.get('/api/v1/contacts/1/')
        request.user = self.admin_user

        self.assertTrue(self.permission.has_object_permission(request, self.view, self.contact))


class DealPermissionTest(TestCase):
    """Test cases for DealPermission"""

    def setUp(self):
        """Set up test environment"""
        self.factory = APIRequestFactory()
        self.permission = DealPermission()
        self.view = APIView()

        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            role='admin'
        )
        self.sales_user = User.objects.create_user(
            email='sales@test.com',
            password='testpass123',
            role='sales'
        )

        # Mock deal object
        self.deal = MagicMock()
        self.deal.assigned_to = self.sales_user

    def test_sales_user_can_access_own_deal(self):
        """Test that sales user can access their own deal"""
        request = self.factory.get('/api/v1/deals/1/')
        request.user = self.sales_user

        self.assertTrue(self.permission.has_object_permission(request, self.view, self.deal))

    def test_admin_can_access_any_deal(self):
        """Test that admin can access any deal"""
        request = self.factory.get('/api/v1/deals/1/')
        request.user = self.admin_user

        self.assertTrue(self.permission.has_object_permission(request, self.view, self.deal))


class ActivityPermissionTest(TestCase):
    """Test cases for ActivityPermission"""

    def setUp(self):
        """Set up test environment"""
        self.factory = APIRequestFactory()
        self.permission = ActivityPermission()
        self.view = APIView()

        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            role='admin'
        )
        self.sales_user = User.objects.create_user(
            email='sales@test.com',
            password='testpass123',
            role='sales'
        )

        # Mock activity object
        self.activity = MagicMock()
        self.activity.created_by = self.sales_user

    def test_user_can_access_own_activity(self):
        """Test that user can access their own activity"""
        request = self.factory.get('/api/v1/activities/1/')
        request.user = self.sales_user

        self.assertTrue(self.permission.has_object_permission(request, self.view, self.activity))

    def test_admin_can_access_any_activity(self):
        """Test that admin can access any activity"""
        request = self.factory.get('/api/v1/activities/1/')
        request.user = self.admin_user

        self.assertTrue(self.permission.has_object_permission(request, self.view, self.activity))