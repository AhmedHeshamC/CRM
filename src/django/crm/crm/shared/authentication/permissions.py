"""
Shared Authentication Permissions
Following SOLID and KISS principles for clean, maintainable permissions
"""

from rest_framework import permissions
from django.contrib.auth import get_user_model

User = get_user_model()


class IsAdminUser(permissions.BasePermission):
    """
    Permission check for admin users
    Following Single Responsibility Principle
    """

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            hasattr(request.user, 'role') and
            request.user.role == 'admin'
        )


class IsManagerOrAdminUser(permissions.BasePermission):
    """
    Permission check for manager or admin users
    Following KISS principle - simple business logic
    """

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            hasattr(request.user, 'role') and
            request.user.role in ['manager', 'admin']
        )


class IsSelfOrAdmin(permissions.BasePermission):
    """
    Permission check - user can only access their own data unless admin
    Following SOLID principles
    """

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False

        # Admin can access any object
        if hasattr(request.user, 'role') and request.user.role == 'admin':
            return True

        # User can only access their own objects
        return hasattr(obj, 'id') and obj.id == request.user.id


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Permission check - only owners can write, others can read
    Following KISS principle for clear permissions
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions for any authenticated user
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions only for object owner or admin
        if not request.user or not request.user.is_authenticated:
            return False

        # Admin can edit any object
        if hasattr(request.user, 'role') and request.user.role == 'admin':
            return True

        # Check if user is the owner
        owner_field = getattr(obj, 'owner', None)
        if owner_field and hasattr(owner_field, 'id'):
            return owner_field.id == request.user.id

        # Fallback to direct ID comparison
        return hasattr(obj, 'id') and obj.id == request.user.id


class DynamicRolePermission(permissions.BasePermission):
    """
    Dynamic permission based on user role and action
    Following Open/Closed Principle - extensible for new roles
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        # Admin can do anything
        if hasattr(request.user, 'role') and request.user.role == 'admin':
            return True

        # Manager permissions
        if hasattr(request.user, 'role') and request.user.role == 'manager':
            return self._has_manager_permission(request, view)

        # Regular user permissions
        return self._has_user_permission(request, view)

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False

        # Admin can access any object
        if hasattr(request.user, 'role') and request.user.role == 'admin':
            return True

        # Manager permissions
        if hasattr(request.user, 'role') and request.user.role == 'manager':
            return self._has_manager_object_permission(request, view, obj)

        # User can only access their own objects
        return hasattr(obj, 'id') and obj.id == request.user.id

    def _has_manager_permission(self, request, view):
        """KISS principle - simple manager permissions"""
        # Managers can read most data and create certain resources
        if request.method in permissions.SAFE_METHODS:
            return True

        # Specific creation permissions
        allowed_actions = ['create', 'list']
        return getattr(view, 'action', None) in allowed_actions

    def _has_user_permission(self, request, view):
        """KISS principle - simple user permissions"""
        # Users can only read data and update their own profile
        if request.method in permissions.SAFE_METHODS:
            return True

        # Allow specific actions on user's own data
        allowed_actions = ['retrieve', 'update', 'partial_update']
        return getattr(view, 'action', None) in allowed_actions

    def _has_manager_object_permission(self, request, view, obj):
        """Manager object-level permissions"""
        # Managers can read most objects
        if request.method in permissions.SAFE_METHODS:
            return True

        # Limited write permissions for managers
        return request.method in ['PATCH']  # Only allow partial updates