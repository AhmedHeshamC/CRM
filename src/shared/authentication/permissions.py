"""
Role-Based Permission Classes for API Authorization
Following SOLID principles and enterprise security best practices
"""

from rest_framework import permissions
from rest_framework.request import Request
from rest_framework.views import View
from django.contrib.auth import get_user_model
from typing import List, Optional, Set
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


class BaseRolePermission(permissions.BasePermission):
    """
    Base class for role-based permissions
    Following Single Responsibility Principle and Open/Closed Principle
    """

    # Role hierarchy - higher numbers have more privileges
    ROLE_HIERARCHY = {
        'support': 1,
        'sales': 2,
        'manager': 3,
        'admin': 4,
    }

    def has_permission(self, request: Request, view: View) -> bool:
        """
        Check if user has basic permission for the endpoint
        Following Single Responsibility Principle
        """
        if not request.user or not request.user.is_authenticated:
            logger.warning(f"Unauthenticated access attempt to {view.__class__.__name__}")
            return False

        if not request.user.is_active:
            logger.warning(f"Inactive user {request.user.email} attempted access")
            return False

        return True

    def has_object_permission(self, request: Request, view: View, obj) -> bool:
        """
        Check if user has permission for specific object
        Following Single Responsibility Principle
        """
        return self.has_permission(request, view)

    def _get_user_role_level(self, user: User) -> int:
        """
        Get user's role level in hierarchy
        Following Single Responsibility Principle
        """
        return self.ROLE_HIERARCHY.get(user.role, 0)

    def _has_higher_or_equal_role(self, user: User, target_role: str) -> bool:
        """
        Check if user has higher or equal role than target
        Following Single Responsibility Principle
        """
        user_level = self._get_user_role_level(user)
        target_level = self.ROLE_HIERARCHY.get(target_role, 0)
        return user_level >= target_level


class IsAdminUser(BaseRolePermission):
    """
    Permission class for admin-only access
    Following Single Responsibility Principle
    """

    def has_permission(self, request: Request, view: View) -> bool:
        """Allow access only to admin users"""
        if not super().has_permission(request, view):
            return False

        if not request.user.is_admin():
            logger.warning(f"Non-admin user {request.user.email} attempted admin access")
            return False

        return True


class IsManagerOrAdminUser(BaseRolePermission):
    """
    Permission class for manager or admin access
    Following Single Responsibility Principle
    """

    def has_permission(self, request: Request, view: View) -> bool:
        """Allow access to manager and admin users"""
        if not super().has_permission(request, view):
            return False

        if not (request.user.is_manager() or request.user.is_admin()):
            logger.warning(f"Non-manager/admin user {request.user.email} attempted manager access")
            return False

        return True


class IsSalesOrAboveUser(BaseRolePermission):
    """
    Permission class for sales and above roles
    Following Single Responsibility Principle
    """

    def has_permission(self, request: Request, view: View) -> bool:
        """Allow access to sales, manager, and admin users"""
        if not super().has_permission(request, view):
            return False

        allowed_roles = ['sales', 'manager', 'admin']
        if request.user.role not in allowed_roles:
            logger.warning(f"User {request.user.email} with role {request.user.role} attempted sales access")
            return False

        return True


class IsOwnerOrReadOnly(BaseRolePermission):
    """
    Permission class for object-level permissions
    Following Single Responsibility Principle
    """

    def has_object_permission(self, request: Request, view: View, obj) -> bool:
        """Allow write access only to object owner or admin"""
        # Safe methods (GET, HEAD, OPTIONS) are allowed for authenticated users
        if request.method in permissions.SAFE_METHODS:
            return self.has_permission(request, view)

        # Write permissions require ownership or admin role
        if not self.has_permission(request, view):
            return False

        # Check if user is owner
        if hasattr(obj, 'user') and obj.user == request.user:
            return True

        # Check if user is the object itself (for User model)
        if obj == request.user:
            return True

        # Admin users can modify anything
        if request.user.is_admin():
            return True

        # Managers can modify users with lower role levels
        if request.user.is_manager() and hasattr(obj, 'role'):
            return self._has_higher_or_equal_role(request.user, obj.role)

        logger.warning(f"User {request.user.email} attempted unauthorized access to object")
        return False


class IsSelfOrAdmin(BaseRolePermission):
    """
    Permission class for user profile access
    Following Single Responsibility Principle
    """

    def has_object_permission(self, request: Request, view: View, obj) -> bool:
        """Allow access only to self or admin users"""
        if not self.has_permission(request, view):
            return False

        # Check if accessing own profile
        if hasattr(obj, 'user') and obj.user == request.user:
            return True

        # Check if the object is the user themselves
        if obj == request.user:
            return True

        # Admin users can access any profile
        return request.user.is_admin()


class DynamicRolePermission(BaseRolePermission):
    """
    Dynamic permission class based on request method
    Following Open/Closed Principle for flexible permission handling
    """

    # Method-based role requirements
    METHOD_ROLE_REQUIREMENTS = {
        'GET': ['support', 'sales', 'manager', 'admin'],
        'POST': ['sales', 'manager', 'admin'],
        'PUT': ['sales', 'manager', 'admin'],
        'PATCH': ['sales', 'manager', 'admin'],
        'DELETE': ['manager', 'admin'],
    }

    def __init__(self, custom_requirements: Optional[dict] = None):
        """
        Initialize with custom role requirements if provided
        Following Dependency Inversion Principle
        """
        if custom_requirements:
            self.METHOD_ROLE_REQUIREMENTS.update(custom_requirements)

    def has_permission(self, request: Request, view: View) -> bool:
        """Check permission based on HTTP method and user role"""
        if not super().has_permission(request, view):
            return False

        method = request.method.upper()
        required_roles = self.METHOD_ROLE_REQUIREMENTS.get(method, ['admin'])

        if request.user.role not in required_roles:
            logger.warning(
                f"User {request.user.email} with role {request.user.role} "
                f"attempted {method} access (requires: {required_roles})"
            )
            return False

        return True


class DepartmentBasedPermission(BaseRolePermission):
    """
    Permission class based on department access
    Following Single Responsibility Principle
    """

    def __init__(self, allowed_departments: Optional[Set[str]] = None):
        """
        Initialize with allowed departments
        Following Dependency Inversion Principle
        """
        self.allowed_departments = allowed_departments or set()

    def has_permission(self, request: Request, view: View) -> bool:
        """Check permission based on user's department"""
        if not super().has_permission(request, view):
            return False

        # Admin users can bypass department restrictions
        if request.user.is_admin():
            return True

        # Check if user's department is allowed
        user_department = getattr(request.user, 'department', None)
        if user_department and self.allowed_departments:
            if user_department not in self.allowed_departments:
                logger.warning(
                    f"User {request.user.email} from department {user_department} "
                    f"attempted access to restricted departments: {self.allowed_departments}"
                )
                return False

        return True


class CustomPermissionMixin:
    """
    Mixin for custom permission logic
    Following Interface Segregation Principle
    """

    def has_custom_permission(self, request: Request, view: View, **kwargs) -> bool:
        """
        Override this method in subclasses for custom permission logic
        Following Template Method Pattern
        """
        return True


class ContactPermission(BaseRolePermission, CustomPermissionMixin):
    """
    Custom permission class for contact operations
    Following Single Responsibility Principle
    """

    def has_permission(self, request: Request, view: View) -> bool:
        """Check permission for contact operations"""
        if not super().has_permission(request, view):
            return False

        # All authenticated users can view contacts
        if request.method in permissions.SAFE_METHODS:
            return True

        # Sales, manager, and admin can create/update contacts
        if request.method in ['POST', 'PUT', 'PATCH']:
            return request.user.role in ['sales', 'manager', 'admin']

        # Only manager and admin can delete contacts
        if request.method == 'DELETE':
            return request.user.role in ['manager', 'admin']

        return False

    def has_object_permission(self, request: Request, view: View, obj) -> bool:
        """Check object-level permission for contacts"""
        if not self.has_permission(request, view):
            return False

        # Admin can access any contact
        if request.user.is_admin():
            return True

        # Manager can access contacts owned by their team
        if request.user.is_manager():
            return self.has_custom_permission(request, view, obj=obj)

        # Sales users can only access their own contacts
        if request.user.is_sales_user():
            return hasattr(obj, 'assigned_to') and obj.assigned_to == request.user

        return False


class DealPermission(BaseRolePermission, CustomPermissionMixin):
    """
    Custom permission class for deal operations
    Following Single Responsibility Principle
    """

    def has_permission(self, request: Request, view: View) -> bool:
        """Check permission for deal operations"""
        if not super().has_permission(request, view):
            return False

        # All authenticated users can view deals
        if request.method in permissions.SAFE_METHODS:
            return True

        # Sales, manager, and admin can create/update deals
        if request.method in ['POST', 'PUT', 'PATCH']:
            return request.user.role in ['sales', 'manager', 'admin']

        # Only manager and admin can delete deals
        if request.method == 'DELETE':
            return request.user.role in ['manager', 'admin']

        return False

    def has_object_permission(self, request: Request, view: View, obj) -> bool:
        """Check object-level permission for deals"""
        if not self.has_permission(request, view):
            return False

        # Admin can access any deal
        if request.user.is_admin():
            return True

        # Manager can access deals in their team
        if request.user.is_manager():
            return self.has_custom_permission(request, view, obj=obj)

        # Sales users can only access their own deals
        if request.user.is_sales_user():
            return hasattr(obj, 'assigned_to') and obj.assigned_to == request.user

        return False


class ActivityPermission(BaseRolePermission, CustomPermissionMixin):
    """
    Custom permission class for activity operations
    Following Single Responsibility Principle
    """

    def has_permission(self, request: Request, view: View) -> bool:
        """Check permission for activity operations"""
        if not super().has_permission(request, view):
            return False

        # All authenticated users can view activities
        if request.method in permissions.SAFE_METHODS:
            return True

        # All authenticated users can create activities
        if request.method == 'POST':
            return True

        # Only activity creator or admin/manager can update/delete
        if request.method in ['PUT', 'PATCH', 'DELETE']:
            return request.user.role in ['manager', 'admin']

        return True

    def has_object_permission(self, request: Request, view: View, obj) -> bool:
        """Check object-level permission for activities"""
        if not self.has_permission(request, view):
            return False

        # Admin can access any activity
        if request.user.is_admin():
            return True

        # Manager can access activities in their team
        if request.user.is_manager():
            return self.has_custom_permission(request, view, obj=obj)

        # Users can access their own activities
        return hasattr(obj, 'created_by') and obj.created_by == request.user