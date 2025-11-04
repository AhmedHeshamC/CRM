"""
Authentication and Authorization Test Suite
Following SOLID principles and TDD approach
"""

# Test modules
from . import test_middleware
from . import test_permissions
from . import test_integration

__all__ = [
    'test_middleware',
    'test_permissions',
    'test_integration',
]