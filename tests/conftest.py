"""
Pytest Configuration and Fixtures
Following TDD methodology with comprehensive test setup
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from typing import Generator, AsyncGenerator
from pathlib import Path
import sys
import os

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import django
from django.test.client import Client
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.conf import settings

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from rest_framework.test import APIClient
try:
    from factory.django import DjangoModelFactory
    from faker import Faker
    FACTORY_AVAILABLE = True
except ImportError:
    FACTORY_AVAILABLE = False

User = get_user_model()

if FACTORY_AVAILABLE:
    fake = Faker()

    class UserFactory(DjangoModelFactory):
        """Factory for creating User instances in tests"""

        class Meta:
            model = User

        email = fake.email()
        first_name = fake.first_name()
        last_name = fake.last_name()
        is_active = True
        is_staff = False
        is_superuser = False
        role = 'sales'

    class AdminUserFactory(DjangoModelFactory):
        """Factory for creating admin User instances"""

        class Meta:
            model = User

        email = fake.email()
        first_name = fake.first_name()
        last_name = fake.last_name()
        is_active = True
        is_staff = True
        is_superuser = True
        role = 'admin'
else:
    # Fallback if factory-boy or faker is not available
    def UserFactory():
        return User.objects.create_user(
            email='test@example.com',
            first_name='Test',
            last_name='User',
            password='testpass123'
        )

    def AdminUserFactory():
        return User.objects.create_superuser(
            email='admin@example.com',
            first_name='Admin',
            last_name='User',
            password='adminpass123'
        )


@pytest.fixture
def db() -> Generator:
    """Database fixture for tests"""
    # Django handles database setup automatically when using pytest-django
    yield


@pytest.fixture
def client() -> Generator[Client, None, None]:
    """Django test client fixture"""
    yield Client()


@pytest.fixture
def api_client() -> Generator[APIClient, None, None]:
    """Django REST API client fixture"""
    yield APIClient()


@pytest.fixture
def user(db) -> Generator[User, None, None]:
    """Create a regular user for testing"""
    yield UserFactory()


@pytest.fixture
def admin_user(db) -> Generator[User, None, None]:
    """Create an admin user for testing"""
    yield AdminUserFactory()


@pytest.fixture
def authenticated_client(client, user) -> Generator[Client, None, None]:
    """Authenticated Django client fixture"""
    client.force_login(user)
    yield client


@pytest.fixture
def authenticated_api_client(api_client, user) -> Generator[APIClient, None, None]:
    """Authenticated API client fixture"""
    api_client.force_authenticate(user=user)
    yield api_client


@pytest.fixture
def admin_api_client(api_client, admin_user) -> Generator[APIClient, None, None]:
    """Admin authenticated API client fixture"""
    api_client.force_authenticate(user=admin_user)
    yield api_client


@pytest.fixture
def sample_user_data() -> dict:
    """Sample user data for testing"""
    return {
        'email': 'test@example.com',
        'first_name': 'John',
        'last_name': 'Doe',
        'password': 'testpass123',
        'role': 'sales'
    }


@pytest.fixture
def sample_contact_data() -> dict:
    """Sample contact data for testing"""
    return {
        'first_name': 'Jane',
        'last_name': 'Smith',
        'email': 'jane.smith@example.com',
        'phone': '+1234567890',
        'company': 'Tech Corp',
        'title': 'Software Engineer',
        'tags': ['vip', 'prospect']
    }


@pytest.fixture
def sample_deal_data() -> dict:
    """Sample deal data for testing"""
    return {
        'title': 'Enterprise Software License',
        'description': 'Large enterprise software licensing deal',
        'value': 100000.00,
        'currency': 'USD',
        'stage': 'qualified',
        'probability': 75,
        'expected_close_date': timezone.now() + timedelta(days=90)
    }


@pytest.fixture
def sample_activity_data() -> dict:
    """Sample activity data for testing"""
    return {
        'type': 'call',
        'title': 'Initial Discovery Call',
        'description': 'Discussed client requirements and budget',
        'scheduled_at': timezone.now() + timedelta(hours=2),
        'duration_minutes': 60,
        'reminder_minutes': 30
    }


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_redis(monkeypatch):
    """Mock Redis for testing"""
    class MockRedis:
        def __init__(self):
            self.data = {}

        def get(self, key):
            return self.data.get(key)

        def set(self, key, value, ex=None):
            self.data[key] = value

        def delete(self, key):
            return self.data.pop(key, None) is not None

        def exists(self, key):
            return key in self.data

    mock_redis_instance = MockRedis()
    monkeypatch.setattr('redis.Redis', lambda **kwargs: mock_redis_instance)
    return mock_redis_instance


@pytest.fixture
def mock_email(monkeypatch):
    """Mock email sending for testing"""
    class MockEmail:
        def __init__(self):
            self.sent_emails = []

        def send_mail(self, subject, message, from_email, recipient_list):
            self.sent_emails.append({
                'subject': subject,
                'message': message,
                'from_email': from_email,
                'recipient_list': recipient_list
            })

    mock_email_instance = MockEmail()
    monkeypatch.setattr('django.core.mail.send_mail', mock_email_instance.send_mail)
    return mock_email_instance