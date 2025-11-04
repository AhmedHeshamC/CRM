"""
Documentation Utilities
Utility functions for OpenAPI schema generation and documentation enhancement
Following SOLID principles and enterprise best practices
"""

from drf_spectacular.utils import OpenApiExample
from drf_spectacular.types import OpenApiTypes
from django.contrib.auth import get_user_model
from rest_framework import status

User = get_user_model()


def user_role_handler(choices):
    """
    Handler for User Role enum choices in OpenAPI documentation
    Following Single Responsibility Principle
    """
    return {
        'enum': [choice[0] for choice in choices],
        'description': 'User role with specific permissions',
        'example': 'sales',
        'x-enum-varnames': [choice[0].upper() for choice in choices],
    }


def deal_stage_handler(choices):
    """
    Handler for Deal Stage enum choices in OpenAPI documentation
    Following Single Responsibility Principle
    """
    return {
        'enum': [choice[0] for choice in choices],
        'description': 'Current stage of the deal in the sales pipeline',
        'example': 'qualified',
        'x-enum-varnames': [choice[0].upper().replace(' ', '_') for choice in choices],
    }


def activity_type_handler(choices):
    """
    Handler for Activity Type enum choices in OpenAPI documentation
    Following Single Responsibility Principle
    """
    return {
        'enum': [choice[0] for choice in choices],
        'description': 'Type of activity or task',
        'example': 'call',
        'x-enum-varnames': [choice[0].upper().replace(' ', '_') for choice in choices],
    }


def activity_priority_handler(choices):
    """
    Handler for Activity Priority enum choices in OpenAPI documentation
    Following Single Responsibility Principle
    """
    return {
        'enum': [choice[0] for choice in choices],
        'description': 'Priority level of the activity',
        'example': 'medium',
        'x-enum-varnames': [choice[0].upper() for choice in choices],
    }


# Common OpenAPI examples for documentation
AUTH_EXAMPLES = [
    OpenApiExample(
        'Valid Login',
        value={
            'email': 'john.doe@company.com',
            'password': 'SecurePass123!'
        },
        request_only=True,
        response_only=False,
    ),
    OpenApiExample(
        'Valid Registration',
        value={
            'email': 'jane.smith@company.com',
            'first_name': 'Jane',
            'last_name': 'Smith',
            'password': 'SecurePass123!',
            'password_confirm': 'SecurePass123!',
            'role': 'sales',
            'phone': '+1-555-123-4567',
            'department': 'Sales'
        },
        request_only=True,
        response_only=False,
    ),
    OpenApiExample(
        'Token Refresh',
        value={
            'refresh_token': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...'
        },
        request_only=True,
        response_only=False,
    ),
]

CONTACT_EXAMPLES = [
    OpenApiExample(
        'Valid Contact',
        value={
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john.doe@company.com',
            'phone': '+1-555-123-4567',
            'company': 'Acme Corp',
            'title': 'CEO',
            'website': 'https://acmecorp.com',
            'address': '123 Main St',
            'city': 'New York',
            'state': 'NY',
            'country': 'USA',
            'postal_code': '10001',
            'linkedin_url': 'https://linkedin.com/in/johndoe',
            'twitter_url': 'https://twitter.com/johndoe',
            'tags': ['important', 'enterprise', 'tech'],
            'lead_source': 'website'
        },
        request_only=True,
        response_only=False,
    ),
]

DEAL_EXAMPLES = [
    OpenApiExample(
        'Valid Deal',
        value={
            'title': 'Enterprise Software License',
            'description': 'Large-scale software licensing agreement for enterprise operations',
            'contact': 1,
            'value': '50000.00',
            'currency': 'USD',
            'stage': 'qualified',
            'probability': 75,
            'expected_close_date': '2024-12-31',
            'custom_fields': {
                'contract_type': 'annual',
                'support_level': 'premium'
            }
        },
        request_only=True,
        response_only=False,
    ),
]

ACTIVITY_EXAMPLES = [
    OpenApiExample(
        'Valid Activity',
        value={
            'title': 'Follow-up Call with Client',
            'description': 'Discuss proposal details and answer questions',
            'type': 'call',
            'priority': 'high',
            'contact': 1,
            'deal': 1,
            'scheduled_at': '2024-11-15T14:30:00Z',
            'duration_minutes': 30,
            'reminder_minutes': 15,
            'location': 'Conference Room A',
            'attendees': [1, 2],
            'custom_fields': {
                'agenda': 'Proposal review',
                'preparation_needed': True
            }
        },
        request_only=True,
        response_only=False,
    ),
]

BULK_OPERATION_EXAMPLES = [
    OpenApiExample(
        'Bulk Deactivate Users',
        value={
            'user_ids': [1, 2, 3],
            'operation': 'deactivate'
        },
        request_only=True,
        response_only=False,
    ),
    OpenApiExample(
        'Bulk Update Contacts',
        value={
            'contact_ids': [1, 2, 3],
            'operation': 'update',
            'data': {
                'tags': ['priority'],
                'lead_source': 'referral'
            }
        },
        request_only=True,
        response_only=False,
    ),
]

SEARCH_EXAMPLES = [
    OpenApiExample(
        'Search Contacts',
        value={
            'query': 'john doe',
            'company': 'acme',
            'tags': ['enterprise'],
            'is_active': True
        },
        request_only=True,
        response_only=False,
    ),
    OpenApiExample(
        'Search Deals',
        value={
            'query': 'enterprise software',
            'stage': 'qualified',
            'min_value': '10000',
            'max_value': '100000'
        },
        request_only=True,
        response_only=False,
    ),
]

PAGINATION_EXAMPLES = [
    OpenApiExample(
        'Pagination Parameters',
        value={
            'page': 1,
            'page_size': 20,
            'ordering': '-created_at'
        },
        request_only=True,
        response_only=False,
    ),
]


def get_auth_error_examples():
    """
    Get authentication error examples for OpenAPI documentation
    Following Single Responsibility Principle
    """
    return [
        {
            '401': {
                'description': 'Invalid credentials',
                'content': {
                    'application/json': {
                        'example': {
                            'detail': 'Invalid email or password.',
                            'code': 'authentication_failed'
                        }
                    }
                }
            }
        },
        {
            '401': {
                'description': 'Token expired',
                'content': {
                    'application/json': {
                        'example': {
                            'detail': 'Given token not valid for any token type',
                            'code': 'token_not_valid'
                        }
                    }
                }
            }
        },
        {
            '403': {
                'description': 'Insufficient permissions',
                'content': {
                    'application/json': {
                        'example': {
                            'detail': 'You do not have permission to perform this action.',
                            'code': 'permission_denied'
                        }
                    }
                }
            }
        },
    ]


def get_validation_error_examples():
    """
    Get validation error examples for OpenAPI documentation
    Following Single Responsibility Principle
    """
    return [
        {
            '400': {
                'description': 'Validation failed',
                'content': {
                    'application/json': {
                        'example': {
                            'error': 'Validation failed',
                            'details': {
                                'email': ['This field is required.'],
                                'password': ['Password must be at least 8 characters long.']
                            }
                        }
                    }
                }
            }
        },
        {
            '400': {
                'description': 'Invalid data format',
                'content': {
                    'application/json': {
                        'example': {
                            'error': 'Invalid data format',
                            'details': {
                                'non_field_errors': ['Invalid JSON format.']
                            }
                        }
                    }
                }
            }
        },
    ]


def get_success_response_examples():
    """
    Get success response examples for OpenAPI documentation
    Following Single Responsibility Principle
    """
    return [
        {
            '201': {
                'description': 'Resource created successfully',
                'content': {
                    'application/json': {
                        'example': {
                            'id': 1,
                            'uuid': '550e8400-e29b-41d4-a716-446655440000',
                            'created_at': '2024-11-03T10:30:00Z',
                            'message': 'Resource created successfully'
                        }
                    }
                }
            }
        },
        {
            '200': {
                'description': 'Operation completed successfully',
                'content': {
                    'application/json': {
                        'example': {
                            'message': 'Operation completed successfully',
                            'updated_count': 5
                        }
                    }
                }
            }
        },
    ]