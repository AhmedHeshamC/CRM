"""
Authentication and Authorization Module
Following SOLID principles for enterprise security
"""

from .middleware import JWTAuthenticationMiddleware, SecurityHeadersMiddleware
from .permissions import (
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
from .exceptions import (
    custom_exception_handler,
    AuthenticationError,
    AuthorizationError,
    TokenError as CustomTokenError,
)

__all__ = [
    # Middleware
    'JWTAuthenticationMiddleware',
    'SecurityHeadersMiddleware',

    # Permission Classes
    'BaseRolePermission',
    'IsAdminUser',
    'IsManagerOrAdminUser',
    'IsSalesOrAboveUser',
    'IsOwnerOrReadOnly',
    'IsSelfOrAdmin',
    'DynamicRolePermission',
    'DepartmentBasedPermission',
    'ContactPermission',
    'DealPermission',
    'ActivityPermission',

    # Exception Handlers
    'custom_exception_handler',
    'AuthenticationError',
    'AuthorizationError',
    'CustomTokenError',
]