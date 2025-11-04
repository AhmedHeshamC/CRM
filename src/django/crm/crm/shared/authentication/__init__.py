"""
Shared Authentication Package
Following KISS principle for simple, reusable authentication components
"""

from .permissions import (
    IsAdminUser, IsManagerOrAdminUser, IsSelfOrAdmin,
    IsOwnerOrReadOnly, DynamicRolePermission
)

__all__ = [
    'IsAdminUser', 'IsManagerOrAdminUser', 'IsSelfOrAdmin',
    'IsOwnerOrReadOnly', 'DynamicRolePermission'
]