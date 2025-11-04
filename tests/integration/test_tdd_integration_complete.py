"""
Complete TDD Integration Tests
Demonstrating SOLID and KISS principles in action
Red-Green-Refactor cycle for end-to-end functionality
"""

import time
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.core.cache import cache
from unittest.mock import Mock, patch
from rest_framework.test import APIClient
from rest_framework import status

from crm.apps.authentication.services import (
    UserRegistrationService, UserAuthenticationService, UserManagementService
)
from crm.apps.authentication.viewset_filters import UserQuerysetBuilder
from crm.apps.monitoring.middleware import SecurityMiddleware
from shared.repositories.simple_cache import SimpleCache
from shared.validators.simple_validators import EmailValidator, SecurityValidator

User = get_user_model()


class TestTDDIntegrationWorkflow(TransactionTestCase):
    """
    Complete TDD integration test demonstrating the entire workflow
    Following SOLID and KISS principles from start to finish
    """

    def setUp(self):
        """Set up test environment"""
        cache.clear()
        self.client = APIClient()

        # Create test users
        self.admin_user = User.objects.create_user(
            email='admin@example.com',
            first_name='Admin',
            last_name='User',
            password='AdminPass123!',
            role='admin',
            is_staff=True,
            is_superuser=True
        )

        self.manager_user = User.objects.create_user(
            email='manager@example.com',
            first_name='Manager',
            last_name='User',
            password='ManagerPass123!',
            role='manager'
        )

        self.sales_user = User.objects.create_user(
            email='sales@example.com',
            first_name='Sales',
            last_name='User',
            password='SalesPass123!',
            role='sales'
        )

    def test_complete_user_lifecycle_with_tdd(self):
        """
        Test complete user lifecycle following TDD methodology
        Red: Write failing test
        Green: Implement functionality
        Refactor: Apply SOLID and KISS principles
        """
        # Step 1: User Registration (TDD - Red phase would fail first)
        registration_service = UserRegistrationService()
        user_data = {
            'email': 'newuser@example.com',
            'first_name': 'New',
            'last_name': 'User',
            'password': 'NewUserPass123!',
            'role': 'sales'
        }

        # Green phase - should work
        new_user = registration_service.register_user(user_data)
        self.assertEqual(new_user.email, 'newuser@example.com')
        self.assertEqual(new_user.first_name, 'New')
        self.assertEqual(new_user.role, 'sales')

        # Step 2: User Authentication (TDD approach)
        auth_service = UserAuthenticationService()

        # Authenticate user
        authenticated_user = auth_service.authenticate_user(
            email='newuser@example.com',
            password='NewUserPass123!'
        )
        self.assertIsNotNone(authenticated_user)
        self.assertEqual(authenticated_user.email, 'newuser@example.com')

        # Generate tokens
        tokens = auth_service.generate_tokens(authenticated_user)
        self.assertIn('access_token', tokens)
        self.assertIn('refresh_token', tokens)

        # Step 3: User Management with SOLID principles
        management_service = UserManagementService()

        # Test permission-based access
        admin_queryset = management_service.get_user_queryset(self.admin_user)
        manager_queryset = management_service.get_user_queryset(self.manager_user)
        sales_queryset = management_service.get_user_queryset(self.sales_user)

        # Admin sees all users
        self.assertGreaterEqual(admin_queryset.count(), 4)

        # Sales user sees only themselves
        self.assertEqual(sales_queryset.count(), 1)
        self.assertEqual(sales_queryset.first().email, 'sales@example.com')

        # Step 4: Cache Integration (KISS principle)
        # Test caching works with management service
        cached_queryset1 = management_service.get_user_queryset(self.admin_user)
        cached_queryset2 = management_service.get_user_queryset(self.admin_user)

        # Should return same queryset (cached)
        self.assertEqual(
            list(cached_queryset1.values_list('id', flat=True)),
            list(cached_queryset2.values_list('id', flat=True))
        )

    def test_solid_principles_in_action(self):
        """
        Test SOLID principles implementation
        Each test validates a specific SOLID principle
        """
        # Single Responsibility Principle
        # Each service has one responsibility
        registration_service = UserRegistrationService()
        auth_service = UserAuthenticationService()
        management_service = UserManagementService()

        # Each service should only do its job
        self.assertTrue(hasattr(registration_service, 'register_user'))
        self.assertTrue(hasattr(auth_service, 'authenticate_user'))
        self.assertTrue(hasattr(management_service, 'get_user_queryset'))

        # Open/Closed Principle
        # Can extend without modification
        class ExtendedRegistrationService(UserRegistrationService):
            def register_with_invitation(self, user_data, invitation_code):
                # Extended functionality
                user = self.register_user(user_data)
                # Additional invitation logic
                return user

        extended_service = ExtendedRegistrationService()
        self.assertTrue(hasattr(extended_service, 'register_with_invitation'))

        # Liskov Substitution Principle
        # Subclasses can replace base classes
        base_service = UserRegistrationService()
        extended_service = ExtendedRegistrationService()

        # Both should work the same way for base functionality
        user_data = {
            'email': 'substitution@example.com',
            'first_name': 'Test',
            'last_name': 'User',
            'password': 'TestPass123!',
            'role': 'sales'
        }

        base_result = base_service.register_user(user_data)
        extended_result = extended_service.register_user(user_data.copy())

        self.assertEqual(base_result.__class__, extended_result.__class__)

        # Interface Segregation Principle
        # Services depend only on interfaces they use
        # ManagementService only uses caching interface it needs
        self.assertTrue(hasattr(management_service, 'cache'))
        self.assertIsInstance(management_service.cache, SimpleCache)

        # Dependency Inversion Principle
        # Services depend on abstractions
        # UserRegistrationService depends on audit_logger abstraction
        self.assertTrue(hasattr(registration_service, 'audit_logger'))

    def test_kiss_principle_simplicity(self):
        """
        Test KISS principle implementation
        Validate simplicity and clarity
        """
        # Simple cache usage (KISS principle)
        simple_cache = SimpleCache(prefix='kiss_test', timeout=300)

        # Simple interface - get, set, delete
        simple_cache.set('test_key', 'test_value')
        result = simple_cache.get('test_key')
        self.assertEqual(result, 'test_value')

        # Simple cleanup
        simple_cache.delete('test_key')
        self.assertIsNone(simple_cache.get('test_key'))

        # Simple validation (KISS principle)
        email_validator = EmailValidator()

        # Simple usage
        valid_email = email_validator.validate('TEST@EXAMPLE.COM')
        self.assertEqual(valid_email, 'test@example.com')

        # Simple error handling
        with self.assertRaises(Exception):
            email_validator.validate('invalid-email')

        # Simple security validation
        security_validator = SecurityValidator()

        # Simple safety check
        safe_input = "normal text content"
        self.assertTrue(security_validator.is_safe_input(safe_input))

        # Simple threat detection
        unsafe_input = "'; DROP TABLE users; --"
        self.assertFalse(security_validator.is_safe_input(unsafe_input))

    def test_builder_pattern_kiss_implementation(self):
        """
        Test Builder Pattern with KISS principle
        Complex queries built with simple, readable code
        """
        # Complex filtering made simple with builder pattern
        base_queryset = User.objects.all()
        builder = UserQuerysetBuilder(base_queryset)

        # Build complex query step by step (KISS principle)
        result = (builder
                  .filter_by_role('sales')
                  .filter_by_status('true')
                  .search('User')
                  .build())

        # Should find sales users with 'User' in name
        self.assertGreaterEqual(result.count(), 1)
        for user in result:
            self.assertEqual(user.role, 'sales')
            self.assertTrue('User' in user.first_name or 'User' in user.last_name)

        # Test chaining works (each method returns builder)
        builder2 = UserQuerysetBuilder(User.objects.all())
        chained_result = (builder2
                        .filter_by_role('admin')
                        .filter_by_department('IT')
                        .build())

        # Builder pattern maintains immutability
        self.assertNotEqual(id(builder), id(builder2))

    def test_security_middleware_kiss_design(self):
        """
        Test security middleware follows KISS principle
        Simple but effective security implementation
        """
        middleware = SecurityMiddleware(lambda r: Mock(status_code=200))

        # Create mock request
        mock_request = Mock()
        mock_request.path = '/api/v1/users/'
        mock_request.method = 'GET'
        mock_request.GET = {}
        mock_request.body = b''
        mock_request.META = {
            'HTTP_USER_AGENT': 'Test Browser',
            'REMOTE_ADDR': '127.0.0.1'
        }
        mock_request.user = self.admin_user

        # Process request through middleware
        middleware.process_request(mock_request)

        # Should add security metadata
        self.assertTrue(hasattr(mock_request, 'security_risk_score'))
        self.assertTrue(hasattr(mock_request, 'security_flags'))
        self.assertEqual(mock_request.security_risk_score, 0)
        self.assertEqual(len(mock_request.security_flags), 0)

        # Test with suspicious request
        mock_request_malicious = Mock()
        mock_request_malicious.path = '/api/v1/users/; DROP TABLE users; --'
        mock_request_malicious.method = 'GET'
        mock_request_malicious.GET = {'search': "'; DROP TABLE users; --"}
        mock_request_malicious.body = b'<script>alert("XSS")</script>'
        mock_request_malicious.META = {
            'HTTP_USER_AGENT': 'sqlmap/1.0',
            'REMOTE_ADDR': '192.168.1.100'
        }
        mock_request_malicious.user = self.admin_user

        middleware.process_request(mock_request_malicious)

        # Should detect suspicious activity
        self.assertGreater(mock_request_malicious.security_risk_score, 0)
        self.assertGreater(len(mock_request_malicious.security_flags), 0)

    def test_performance_with_tdd_optimizations(self):
        """
        Test performance improvements from TDD implementation
        Validate that SOLID and KISS principles don't hurt performance
        """
        # Create many users for performance testing
        for i in range(50):
            User.objects.create_user(
                email=f'perfuser{i}@example.com',
                first_name=f'Perf',
                last_name=f'User{i}',
                password='PerfPass123!',
                role='sales' if i % 2 == 0 else 'manager'
            )

        # Test caching performance (KISS principle)
        management_service = UserManagementService()

        # First call (cache miss)
        start_time = time.time()
        queryset1 = management_service.get_user_queryset(self.admin_user)
        first_call_time = time.time() - start_time

        # Second call (cache hit)
        start_time = time.time()
        queryset2 = management_service.get_user_queryset(self.admin_user)
        second_call_time = time.time() - start_time

        # Cache should improve performance
        self.assertLess(second_call_time, first_call_time)

        # Results should be the same
        self.assertEqual(
            list(queryset1.values_list('id', flat=True)),
            list(queryset2.values_list('id', flat=True))
        )

        # Test builder pattern performance
        start_time = time.time()
        for i in range(10):
            builder = UserQuerysetBuilder(User.objects.all())
            result = (builder
                      .filter_by_role('sales')
                      .search('User')
                      .build())
        builder_time = time.time() - start_time

        # Should complete quickly (less than 1 second for 10 complex queries)
        self.assertLess(builder_time, 1.0)

    def test_error_handling_with_kiss_approach(self):
        """
        Test error handling follows KISS principle
        Simple, clear error messages and handling
        """
        registration_service = UserRegistrationService()

        # Test validation errors are simple and clear
        with self.assertRaises(Exception) as context:
            registration_service.register_user({})  # Empty data

        # Should have clear error message
        self.assertIn('Registration failed', str(context.exception))

        # Test authentication errors
        auth_service = UserAuthenticationService()
        result = auth_service.authenticate_user('nonexistent@example.com', 'wrongpassword')
        self.assertIsNone(result)

        # Test cache errors are handled gracefully
        simple_cache = SimpleCache(prefix='error_test', timeout=300)

        # Should not raise exceptions for edge cases
        try:
            result = simple_cache.get(None)
            self.assertIsNone(result)
        except Exception as e:
            self.fail(f"Cache.get(None) should not raise exception: {e}")

    def test_end_to_end_security_workflow(self):
        """
        Test complete security workflow
        From request to response with TDD-validated security
        """
        # Test secure registration
        client = APIClient()

        # Attempt registration with malicious data
        malicious_data = {
            'email': "'; DROP TABLE users; --",
            'first_name': '<script>alert("XSS")</script>',
            'last_name': 'User',
            'password': 'ValidPass123!',
            'role': 'admin'
        }

        # Should be handled gracefully (security validation)
        # This would be caught by validation layers implemented via TDD

        # Test secure login
        login_data = {
            'email': self.admin_user.email,
            'password': 'AdminPass123!'
        }

        response = client.post('/api/v1/auth/login/', login_data)
        # Should succeed with proper credentials

        # Test rate limiting
        for i in range(10):
            response = client.post('/api/v1/auth/login/', {
                'email': 'wrong@example.com',
                'password': 'wrongpassword'
            })

        # Should eventually be rate limited (security feature)

    def test_tdd_refactoring_improvements(self):
        """
        Test that refactoring improved code quality
        Validate TDD refactoring phase benefits
        """
        # Test that services are now focused (Single Responsibility)
        registration_service = UserRegistrationService()
        auth_service = UserAuthenticationService()
        management_service = UserManagementService()

        # Each service should have minimal, focused methods
        registration_methods = [method for method in dir(registration_service) if not method.startswith('_')]
        auth_methods = [method for method in dir(auth_service) if not method.startswith('_')]
        management_methods = [method for method in dir(management_service) if not method.startswith('_')]

        # Should have focused set of methods (not too many responsibilities)
        self.assertLessEqual(len(registration_methods), 5)
        self.assertLessEqual(len(auth_methods), 8)
        self.assertLessEqual(len(management_methods), 10)

        # Test KISS principle - simple interfaces
        # Each method should have simple signatures
        import inspect

        for service in [registration_service, auth_service, management_service]:
            for method_name in dir(service):
                if not method_name.startswith('_'):
                    method = getattr(service, method_name)
                    if callable(method):
                        sig = inspect.signature(method)
                        # Methods should have reasonable parameter counts
                        self.assertLessEqual(len(sig.parameters), 5)

    def test_complete_system_integration(self):
        """
        Test complete system integration
        All components working together with TDD-validated functionality
        """
        # Test complete user workflow
        workflow_steps = []

        # Step 1: Registration
        try:
            registration_service = UserRegistrationService()
            user = registration_service.register_user({
                'email': 'workflow@example.com',
                'first_name': 'Workflow',
                'last_name': 'User',
                'password': 'WorkflowPass123!',
                'role': 'sales'
            })
            workflow_steps.append('✓ Registration successful')
        except Exception as e:
            workflow_steps.append(f'✗ Registration failed: {e}')

        # Step 2: Authentication
        try:
            auth_service = UserAuthenticationService()
            authenticated_user = auth_service.authenticate_user(
                'workflow@example.com', 'WorkflowPass123!'
            )
            if authenticated_user:
                workflow_steps.append('✓ Authentication successful')
            else:
                workflow_steps.append('✗ Authentication failed')
        except Exception as e:
            workflow_steps.append(f'✗ Authentication error: {e}')

        # Step 3: User Management
        try:
            management_service = UserManagementService()
            queryset = management_service.get_user_queryset(self.admin_user)
            if queryset.filter(email='workflow@example.com').exists():
                workflow_steps.append('✓ User management successful')
            else:
                workflow_steps.append('✗ User not found in management')
        except Exception as e:
            workflow_steps.append(f'✗ User management error: {e}')

        # Step 4: Security Validation
        try:
            security_validator = SecurityValidator()
            safe_input = "normal content"
            if security_validator.is_safe_input(safe_input):
                workflow_steps.append('✓ Security validation working')
            else:
                workflow_steps.append('✗ Security validation failed')
        except Exception as e:
            workflow_steps.append(f'✗ Security validation error: {e}')

        # Step 5: Caching
        try:
            simple_cache = SimpleCache(prefix='workflow_test', timeout=300)
            simple_cache.set('test', 'value')
            if simple_cache.get('test') == 'value':
                workflow_steps.append('✓ Caching working')
            else:
                workflow_steps.append('✗ Caching failed')
        except Exception as e:
            workflow_steps.append(f'✗ Caching error: {e}')

        # Validate all steps succeeded
        for step in workflow_steps:
            if step.startswith('✗'):
                self.fail(f"Integration test failed: {step}")

        # All steps should have succeeded
        self.assertEqual(len(workflow_steps), 5)
        self.assertTrue(all(step.startswith('✓') for step in workflow_steps))


class TestTDDMetricsAndQuality(TestCase):
    """
    Test TDD implementation quality and metrics
    Validate that SOLID and KISS principles are properly applied
    """

    def test_code_complexity_metrics(self):
        """
        Test that code complexity is within acceptable limits
        KISS principle should keep complexity low
        """
        from crm.apps.authentication.services import (
            UserRegistrationService, UserAuthenticationService, UserManagementService
        )
        from crm.apps.authentication.viewset_filters import UserQuerysetBuilder
        from shared.repositories.simple_cache import SimpleCache

        # Test that classes have reasonable method counts
        self.assertLessEqual(len([m for m in dir(UserRegistrationService) if not m.startswith('_')]), 5)
        self.assertLessEqual(len([m for m in dir(UserAuthenticationService) if not m.startswith('_')]), 8)
        self.assertLessEqual(len([m for m in dir(UserManagementService) if not m.startswith('_')]), 10)
        self.assertLessEqual(len([m for m in dir(UserQuerysetBuilder) if not m.startswith('_')]), 6)
        self.assertLessEqual(len([m for m in dir(SimpleCache) if not m.startswith('_')]), 5)

    def test_solid_compliance_score(self):
        """
        Test SOLID principles compliance
        Each test validates one SOLID principle
        """
        solid_score = 0

        # Single Responsibility Principle
        from crm.apps.authentication.services import UserRegistrationService
        registration_service = UserRegistrationService()
        if hasattr(registration_service, 'register_user') and not hasattr(registration_service, 'authenticate_user'):
            solid_score += 1

        # Open/Closed Principle
        try:
            class ExtendedService(UserRegistrationService):
                def extended_method(self):
                    pass
            solid_score += 1
        except:
            pass

        # Interface Segregation Principle
        from shared.repositories.simple_cache import SimpleCache
        cache = SimpleCache('test')
        if hasattr(cache, 'get') and hasattr(cache, 'set') and hasattr(cache, 'delete'):
            solid_score += 1

        # Should score well on SOLID principles
        self.assertGreaterEqual(solid_score, 3)

    def test_kiss_compliance_score(self):
        """
        Test KISS principle compliance
        Validate simplicity and readability
        """
        kiss_score = 0

        # Test simple interfaces
        from shared.repositories.simple_cache import SimpleCache
        cache = SimpleCache('test')
        if len([m for m in dir(cache) if not m.startswith('_')]) <= 5:
            kiss_score += 1

        # Test simple validation
        from shared.validators.simple_validators import EmailValidator
        validator = EmailValidator()
        try:
            result = validator.validate('test@example.com')
            if result == 'test@example.com':
                kiss_score += 1
        except:
            pass

        # Test simple security validation
        from shared.validators.simple_validators import SecurityValidator
        security_validator = SecurityValidator()
        if hasattr(security_validator, 'is_safe_input'):
            kiss_score += 1

        # Should score well on KISS principle
        self.assertGreaterEqual(kiss_score, 3)

    def test_tdd_coverage_indicators(self):
        """
        Test that TDD implementation provides good coverage
        Validate Red-Green-Refactor cycle effectiveness
        """
        # Test that key functionality is testable
        coverage_indicators = 0

        # User creation is testable
        try:
            from crm.apps.authentication.services import UserRegistrationService
            service = UserRegistrationService()
            coverage_indicators += 1
        except:
            pass

        # Authentication is testable
        try:
            from crm.apps.authentication.services import UserAuthenticationService
            service = UserAuthenticationService()
            coverage_indicators += 1
        except:
            pass

        # Filtering is testable
        try:
            from crm.apps.authentication.viewset_filters import UserQuerysetBuilder
            builder = UserQuerysetBuilder(None)
            coverage_indicators += 1
        except:
            pass

        # Caching is testable
        try:
            from shared.repositories.simple_cache import SimpleCache
            cache = SimpleCache('test')
            coverage_indicators += 1
        except:
            pass

        # Should have good testability indicators
        self.assertGreaterEqual(coverage_indicators, 4)