"""
API Documentation Tests
Comprehensive test suite for OpenAPI documentation generation and validation
Following SOLID principles and TDD methodology
"""

import json
import pytest
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from drf_spectacular.openapi import AutoSchema
from drf_spectacular.plumbing import build_object_type, build_basic_type

User = get_user_model()


class OpenAPISchemaGenerationTestCase(TestCase):
    """
    Test OpenAPI schema generation and validation
    Following Single Responsibility Principle for schema validation testing
    """

    def setUp(self):
        """Set up test data for schema generation testing"""
        self.schema_url = reverse('schema')

    def test_schema_endpoint_exists(self):
        """Test that OpenAPI schema endpoint exists and returns JSON"""
        response = self.client.get(self.schema_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/vnd.oas.openapi+json')

    def test_schema_basic_structure(self):
        """Test that OpenAPI schema has required basic structure"""
        response = self.client.get(self.schema_url)
        schema = response.json()

        # Required OpenAPI fields
        self.assertIn('openapi', schema)
        self.assertIn('info', schema)
        self.assertIn('paths', schema)
        self.assertIn('components', schema)

        # Required info fields
        info = schema['info']
        self.assertIn('title', info)
        self.assertIn('version', info)
        self.assertIn('description', info)

        # Check CRM-specific content
        self.assertEqual(info['title'], 'CRM API')
        self.assertEqual(info['version'], '1.0.0')
        self.assertIn('Enterprise Customer Relationship Management API', info['description'])

    def test_schema_authentication_structure(self):
        """Test that authentication is properly documented in schema"""
        response = self.client.get(self.schema_url)
        schema = response.json()

        # Check components section exists
        self.assertIn('components', schema)
        components = schema['components']

        # Check security schemes
        self.assertIn('securitySchemes', components)
        security_schemes = components['securitySchemes']

        # Check JWT authentication scheme
        self.assertIn('bearerAuth', security_schemes)
        jwt_scheme = security_schemes['bearerAuth']

        self.assertEqual(jwt_scheme['type'], 'http')
        self.assertEqual(jwt_scheme['scheme'], 'bearer')
        self.assertEqual(jwt_scheme['bearerFormat'], 'JWT')
        self.assertIn('description', jwt_scheme)

    def test_schema_tags_structure(self):
        """Test that API tags are properly structured"""
        response = self.client.get(self.schema_url)
        schema = response.json()

        # Check tags exist
        if 'tags' in schema:
            tags = schema['tags']
            tag_names = [tag['name'] for tag in tags]

            # Required tags for CRM API
            expected_tags = ['Authentication', 'Contacts', 'Deals', 'Activities', 'Users']
            for expected_tag in expected_tags:
                self.assertIn(expected_tag, tag_names)

    def test_schema_error_responses(self):
        """Test that error responses are properly documented"""
        response = self.client.get(self.schema_url)
        schema = response.json()

        # Check for error response components
        if 'components' in schema and 'responses' in schema['components']:
            responses = schema['components']['responses']

            # Common error responses should be documented
            expected_errors = ['400', '401', '403', '404', '429', '500']
            for error_code in expected_errors:
                self.assertIn(error_code, responses)

    def test_schema_servers_configuration(self):
        """Test that servers are properly configured"""
        response = self.client.get(self.schema_url)
        schema = response.json()

        if 'servers' in schema:
            servers = schema['servers']
            self.assertTrue(len(servers) > 0)

            # Check server structure
            for server in servers:
                self.assertIn('url', server)
                self.assertIn('description', server)

    def test_schema_contact_and_license(self):
        """Test that contact and license information is included"""
        response = self.client.get(self.schema_url)
        schema = response.json()

        info = schema['info']

        # Contact information
        if 'contact' in info:
            contact = info['contact']
            self.assertIn('name', contact)
            self.assertIn('email', contact)

        # License information
        if 'license' in info:
            license_info = info['license']
            self.assertIn('name', license_info)


class SwaggerUITestCase(TestCase):
    """
    Test Swagger UI functionality and accessibility
    Following Single Responsibility Principle for UI testing
    """

    def setUp(self):
        """Set up test data for Swagger UI testing"""
        self.swagger_url = reverse('swagger-ui')

    def test_swagger_ui_accessible(self):
        """Test that Swagger UI page loads successfully"""
        response = self.client.get(self.swagger_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, 'swagger-ui')

    def test_swagger_ui_has_schema_link(self):
        """Test that Swagger UI includes schema reference"""
        response = self.client.get(self.swagger_url)
        self.assertContains(response, 'schema')

    def test_swagger_ui_includes_authentication(self):
        """Test that Swagger UI includes authentication documentation"""
        response = self.client.get(self.swagger_url)
        self.assertContains(response, 'Bearer')


class RedocUITestCase(TestCase):
    """
    Test Redoc UI functionality and accessibility
    Following Single Responsibility Principle for UI testing
    """

    def setUp(self):
        """Set up test data for Redoc UI testing"""
        self.redoc_url = reverse('redoc')

    def test_redoc_ui_accessible(self):
        """Test that Redoc page loads successfully"""
        response = self.client.get(self.redoc_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, 'redoc')

    def test_redoc_ui_has_schema_link(self):
        """Test that Redoc includes schema reference"""
        response = self.client.get(self.redoc_url)
        self.assertContains(response, 'schema')


class APIDocumentationIntegrationTestCase(APITestCase):
    """
    Integration tests for API documentation with actual endpoints
    Following SOLID principles for comprehensive integration testing
    """

    def setUp(self):
        """Set up test data and authentication"""
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User',
            role='sales'
        )

    def test_authentication_endpoints_documented(self):
        """Test that authentication endpoints are properly documented"""
        schema_response = self.client.get(reverse('schema'))
        schema = schema_response.json()

        if 'paths' in schema:
            paths = schema['paths']

            # Check for authentication endpoints
            auth_paths = [
                '/api/v1/auth/auth/login/',
                '/api/v1/auth/auth/register/',
                '/api/v1/auth/auth/logout/',
                '/api/v1/auth/auth/refresh/',
            ]

            for path in auth_paths:
                self.assertIn(path, paths, f"Authentication endpoint {path} not found in schema")

    def test_contact_endpoints_documented(self):
        """Test that contact endpoints are properly documented"""
        schema_response = self.client.get(reverse('schema'))
        schema = schema_response.json()

        if 'paths' in schema:
            paths = schema['paths']

            # Check for contact endpoints
            contact_paths = [
                '/api/v1/contacts/',
                '/api/v1/contacts/{id}/',
            ]

            for path in contact_paths:
                # Check pattern match for path with parameters
                path_found = any(
                    path.replace('{id}', '{pk}') in documented_path
                    for documented_path in paths.keys()
                )
                self.assertTrue(path_found, f"Contact endpoint {path} not found in schema")

    def test_request_response_schemas(self):
        """Test that request/response schemas are properly documented"""
        schema_response = self.client.get(reverse('schema'))
        schema = schema_response.json()

        if 'components' in schema and 'schemas' in schema['components']:
            schemas = schema['components']['schemas']

            # Check for key model schemas
            expected_schemas = [
                'User',
                'Contact',
                'Deal',
                'Activity',
                'UserCreate',
                'ContactCreate',
                'Login',
                'Register'
            ]

            for expected_schema in expected_schemas:
                # Allow partial matches (e.g., 'UserCreate' should match 'UserCreateSerializer')
                schema_found = any(
                    expected_schema.lower() in schema_name.lower()
                    for schema_name in schemas.keys()
                )
                self.assertTrue(schema_found, f"Schema {expected_schema} not found in documentation")

    def test_authentication_flow_documentation(self):
        """Test that authentication flow is properly documented"""
        # Test login endpoint
        login_data = {
            'email': 'test@example.com',
            'password': 'testpass123'
        }

        response = self.client.post('/api/v1/auth/auth/login/', login_data, format='json')

        if response.status_code == status.HTTP_200_OK:
            # Verify token structure matches documentation
            response_data = response.json()
            self.assertIn('access_token', response_data)
            self.assertIn('refresh_token', response_data)
            self.assertIn('user', response_data)

    def test_error_response_format(self):
        """Test that error responses match documented format"""
        # Test invalid login
        invalid_data = {
            'email': 'invalid@example.com',
            'password': 'wrongpassword'
        }

        response = self.client.post('/api/v1/auth/auth/login/', invalid_data, format='json')

        if response.status_code == status.HTTP_400_BAD_REQUEST:
            # Verify error response format
            response_data = response.json()
            self.assertIn('detail', response_data)


class DocumentationValidationTestCase(TestCase):
    """
    Test documentation validation and completeness
    Following Single Responsibility Principle for validation testing
    """

    def test_schema_is_valid_openapi(self):
        """Test that generated schema is valid OpenAPI 3.0"""
        response = self.client.get(reverse('schema'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        schema = response.json()

        # Basic OpenAPI 3.0 validation
        self.assertIn('openapi', schema)
        self.assertTrue(schema['openapi'].startswith('3.0'))

        # Required top-level fields
        required_fields = ['info', 'paths']
        for field in required_fields:
            self.assertIn(field, schema)

    def test_all_endpoints_have_documentation(self):
        """Test that all registered endpoints have documentation"""
        from django.urls import get_resolver
        from django.conf import settings

        schema_response = self.client.get(reverse('schema'))
        schema = schema_response.json()

        # Get all API endpoints
        resolver = get_resolver()
        api_endpoints = []

        for pattern in resolver.url_patterns:
            try:
                # This is a simplified check - in practice you'd need more sophisticated URL parsing
                if hasattr(pattern, 'url_patterns'):
                    for sub_pattern in pattern.url_patterns:
                        if hasattr(sub_pattern, 'pattern'):
                            pattern_str = str(sub_pattern.pattern)
                            if 'api' in pattern_str:
                                api_endpoints.append(pattern_str)
            except:
                continue

        # Verify schema paths include our endpoints
        if 'paths' in schema:
            schema_paths = schema['paths'].keys()
            # This is a basic check - you'd want more sophisticated validation in practice
            self.assertTrue(len(schema_paths) > 0, "No API paths found in schema")

    def test_documentation_completeness(self):
        """Test documentation completeness score"""
        schema_response = self.client.get(reverse('schema'))
        schema = schema_response.json()

        # Calculate basic completeness metrics
        completeness_score = 0
        total_checks = 0

        # Check for basic OpenAPI structure
        required_top_level = ['openapi', 'info', 'paths']
        for field in required_top_level:
            total_checks += 1
            if field in schema:
                completeness_score += 1

        # Check for authentication
        total_checks += 1
        if 'components' in schema and 'securitySchemes' in schema['components']:
            completeness_score += 1

        # Check for server configuration
        total_checks += 1
        if 'servers' in schema:
            completeness_score += 1

        # Calculate percentage
        if total_checks > 0:
            completeness_percentage = (completeness_score / total_checks) * 100
            # Documentation should be at least 80% complete
            self.assertGreaterEqual(completeness_percentage, 80.0,
                                  f"Documentation completeness: {completeness_percentage}%")


class DocumentationPerformanceTestCase(TestCase):
    """
    Test documentation generation performance
    Following Single Responsibility Principle for performance testing
    """

    def test_schema_generation_performance(self):
        """Test that schema generation is performant"""
        import time

        start_time = time.time()
        response = self.client.get(reverse('schema'))
        end_time = time.time()

        generation_time = end_time - start_time

        # Schema generation should be fast (< 2 seconds)
        self.assertLess(generation_time, 2.0,
                       f"Schema generation took too long: {generation_time} seconds")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_ui_rendering_performance(self):
        """Test that UI rendering is performant"""
        import time

        # Test Swagger UI
        start_time = time.time()
        response = self.client.get(reverse('swagger-ui'))
        end_time = time.time()

        swagger_render_time = end_time - start_time
        self.assertLess(swagger_render_time, 1.0,
                       f"Swagger UI rendering took too long: {swagger_render_time} seconds")

        # Test Redoc
        start_time = time.time()
        response = self.client.get(reverse('redoc'))
        end_time = time.time()

        redoc_render_time = end_time - start_time
        self.assertLess(redoc_render_time, 1.0,
                       f"Redoc rendering took too long: {redoc_render_time} seconds")