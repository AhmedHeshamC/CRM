#!/usr/bin/env python3

import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings_test')
django.setup()

from django.test import TestCase, APIClient
from rest_framework import status
from django.contrib.auth import get_user_model

User = get_user_model()

# Create admin user
admin_user = User.objects.create_user(
    email='admin@company.com',
    password='AdminPass123!',
    first_name='Admin',
    last_name='User',
    role='admin',
    is_staff=True,
    is_superuser=True
)

# Set up client
client = APIClient()
client.force_authenticate(user=admin_user)

# Test user creation
create_data = {
    'email': 'newuser@company.com',
    'first_name': 'New',
    'last_name': 'User',
    'password': 'SecurePass123!',
    'password_confirm': 'SecurePass123!',
    'role': 'sales'
}

print("Creating user with data:", create_data)
response = client.post('/api/v1/auth/users/', create_data)
print(f"Status Code: {response.status_code}")
print(f"Response Data: {response.content.decode()}")
print(f"Headers: {dict(response.headers)}")