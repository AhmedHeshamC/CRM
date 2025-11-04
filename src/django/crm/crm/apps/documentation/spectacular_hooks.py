"""
drf-spectacular Hooks
Custom hooks for OpenAPI schema generation and enhancement
Following SOLID principles and enterprise best practices
"""

from drf_spectacular.plumbing import build_object_type, build_basic_type
from drf_spectacular.drainage import add_warning
from drf_spectacular.extensions import OpenApiAuthenticationExtension
from drf_spectacular.openapi import AutoSchema
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework import status


def remove_response_headers(result, generator, request, public):
    """
    Remove unnecessary response headers from OpenAPI schema
    Following Single Responsibility Principle for clean schema generation
    """
    # Remove unnecessary headers from all responses
    if 'paths' in result:
        for path_item in result['paths'].values():
            for operation in path_item.values():
                if 'responses' in operation:
                    for response in operation['responses'].values():
                        if 'headers' in response:
                            # Keep only important headers
                            important_headers = ['Authorization', 'Content-Type', 'X-Rate-Limit']
                            response['headers'] = {
                                k: v for k, v in response['headers'].items()
                                if k in important_headers
                            }

    return result


def add_security_schemes(result, generator, request, public):
    """
    Add comprehensive security schemes to OpenAPI schema
    Following Single Responsibility Principle for security documentation
    """
    # Add JWT Bearer authentication scheme
    result['components']['securitySchemes'] = {
        'bearerAuth': {
            'type': 'http',
            'scheme': 'bearer',
            'bearerFormat': 'JWT',
            'description': """
                JWT Authentication token required for all API endpoints.

                **How to obtain token:**
                1. POST /api/v1/auth/auth/login/ with email and password
                2. Receive access_token and refresh_token in response
                3. Include access_token in Authorization header

                **Token format:**
                ```
                Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
                ```

                **Token expiration:**
                - Access tokens: 15 minutes (production), 60 minutes (development)
                - Refresh tokens: 7 days (production), 1 day (development)

                **Token refresh:**
                POST /api/v1/auth/auth/refresh/ with refresh_token to get new access_token
            """,
        }
    }

    return result


def add_examples(result, generator, request, public):
    """
    Add comprehensive examples to OpenAPI schema
    Following Single Responsibility Principle for better developer experience
    """
    # Add examples to common operations
    if 'paths' in result:
        for path, path_item in result['paths'].items():
            for method, operation in path_item.items():
                if 'operationId' in operation:
                    # Add examples based on operation type
                    if 'login' in operation.get('operationId', ''):
                        add_login_examples(operation)
                    elif 'register' in operation.get('operationId', ''):
                        add_register_examples(operation)
                    elif 'create' in operation.get('operationId', ''):
                        add_create_examples(operation)
                    elif 'list' in operation.get('operationId', ''):
                        add_list_examples(operation)

    return result


def add_error_responses(result, generator, request, public):
    """
    Add comprehensive error responses to OpenAPI schema
    Following Single Responsibility Principle for better error documentation
    """
    # Define common error responses
    error_responses = {
        '400': {
            'description': 'Bad Request - Invalid input data',
            'content': {
                'application/json': {
                    'schema': build_object_type(
                        properties={
                            'error': build_basic_type('string'),
                            'details': build_object_type(
                                additional_properties=build_basic_type('string')
                            )
                        }
                    ),
                    'examples': {
                        'validation_error': {
                            'summary': 'Validation error',
                            'value': {
                                'error': 'Validation failed',
                                'details': {
                                    'email': ['This field is required.'],
                                    'password': ['Password must be at least 8 characters long.']
                                }
                            }
                        }
                    }
                }
            }
        },
        '401': {
            'description': 'Unauthorized - Authentication required',
            'content': {
                'application/json': {
                    'schema': build_object_type(
                        properties={
                            'detail': build_basic_type('string'),
                            'code': build_basic_type('string')
                        }
                    ),
                    'examples': {
                        'not_authenticated': {
                            'summary': 'Not authenticated',
                            'value': {
                                'detail': 'Authentication credentials were not provided.',
                                'code': 'not_authenticated'
                            }
                        },
                        'invalid_token': {
                            'summary': 'Invalid token',
                            'value': {
                                'detail': 'Given token not valid for any token type',
                                'code': 'token_not_valid'
                            }
                        }
                    }
                }
            }
        },
        '403': {
            'description': 'Forbidden - Permission denied',
            'content': {
                'application/json': {
                    'schema': build_object_type(
                        properties={
                            'detail': build_basic_type('string'),
                            'code': build_basic_type('string')
                        }
                    ),
                    'example': {
                        'detail': 'You do not have permission to perform this action.',
                        'code': 'permission_denied'
                    }
                }
            }
        },
        '404': {
            'description': 'Not Found - Resource does not exist',
            'content': {
                'application/json': {
                    'schema': build_object_type(
                        properties={
                            'detail': build_basic_type('string'),
                            'code': build_basic_type('string')
                        }
                    ),
                    'example': {
                        'detail': 'Not found.',
                        'code': 'not_found'
                    }
                }
            }
        },
        '429': {
            'description': 'Too Many Requests - Rate limit exceeded',
            'content': {
                'application/json': {
                    'schema': build_object_type(
                        properties={
                            'detail': build_basic_type('string'),
                            'code': build_basic_type('string')
                        }
                    ),
                    'example': {
                        'detail': 'Request was throttled. Expected available in 60 seconds.',
                        'code': 'throttled'
                    }
                }
            }
        },
        '500': {
            'description': 'Internal Server Error',
            'content': {
                'application/json': {
                    'schema': build_object_type(
                        properties={
                            'detail': build_basic_type('string'),
                            'code': build_basic_type('string')
                        }
                    ),
                    'example': {
                        'detail': 'A server error occurred.',
                        'code': 'server_error'
                    }
                }
            }
        },
    }

    # Add error responses to all operations
    if 'paths' in result:
        for path_item in result['paths'].values():
            for operation in path_item.values():
                if 'responses' in operation:
                    # Merge error responses with existing responses
                    operation['responses'].update(error_responses)

    return result


def add_login_examples(operation):
    """Add examples to login operations"""
    if 'requestBody' in operation:
        operation['requestBody']['content']['application/json']['examples'] = {
            'valid_login': {
                'summary': 'Valid login request',
                'value': {
                    'email': 'john.doe@company.com',
                    'password': 'SecurePass123!'
                }
            }
        }

    if 'responses' in operation and '200' in operation['responses']:
        operation['responses']['200']['content']['application/json']['examples'] = {
            'successful_login': {
                'summary': 'Successful login',
                'value': {
                    'access_token': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...',
                    'refresh_token': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...',
                    'user': {
                        'id': 1,
                        'email': 'john.doe@company.com',
                        'first_name': 'John',
                        'last_name': 'Doe',
                        'role': 'sales'
                    }
                }
            }
        }


def add_register_examples(operation):
    """Add examples to registration operations"""
    if 'requestBody' in operation:
        operation['requestBody']['content']['application/json']['examples'] = {
            'valid_registration': {
                'summary': 'Valid registration request',
                'value': {
                    'email': 'jane.smith@company.com',
                    'first_name': 'Jane',
                    'last_name': 'Smith',
                    'password': 'SecurePass123!',
                    'password_confirm': 'SecurePass123!',
                    'role': 'sales',
                    'phone': '+1-555-123-4567',
                    'department': 'Sales'
                }
            }
        }


def add_create_examples(operation):
    """Add examples to create operations"""
    # Generic create examples would be added based on the resource type
    pass


def add_list_examples(operation):
    """Add examples to list operations"""
    # Add pagination parameters
    if 'parameters' not in operation:
        operation['parameters'] = []

    pagination_params = [
        {
            'name': 'page',
            'in': 'query',
            'description': 'Page number for pagination',
            'required': False,
            'schema': {'type': 'integer', 'minimum': 1, 'default': 1},
            'example': 1
        },
        {
            'name': 'page_size',
            'in': 'query',
            'description': 'Number of items per page',
            'required': False,
            'schema': {'type': 'integer', 'minimum': 1, 'maximum': 100, 'default': 20},
            'example': 20
        },
        {
            'name': 'ordering',
            'in': 'query',
            'description': 'Field to order results by',
            'required': False,
            'schema': {'type': 'string'},
            'example': '-created_at'
        }
    ]

    # Add pagination parameters if they don't exist
    existing_param_names = [p.get('name') for p in operation.get('parameters', [])]
    for param in pagination_params:
        if param['name'] not in existing_param_names:
            operation['parameters'].append(param)


class JWTAuthenticationExtension(OpenApiAuthenticationExtension):
    """
    Custom JWT authentication extension for drf-spectacular
    Following Single Responsibility Principle for authentication documentation
    """

    target_class = JWTAuthentication
    name = 'JWT Authentication'

    def get_security_definition(self, auto_schema):
        """
        Get JWT security definition for OpenAPI schema
        Following SOLID principles for clear security documentation
        """
        return {
            'type': 'http',
            'scheme': 'bearer',
            'bearerFormat': 'JWT',
            'description': """
                JWT Authentication required.
                Use the access token returned from the login endpoint.

                Format: Authorization: Bearer <access_token>
            """,
        }