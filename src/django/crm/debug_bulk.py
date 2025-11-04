#!/usr/bin/env python3

import os
import sys
import django

# Add current directory to Python path
sys.path.insert(0, '/Users/m/Desktop/crm/src')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings_test')
django.setup()

from django.test import TestCase
from rest_framework.test import APIClient
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

# Test bulk user creation with small sample
bulk_data = {
    'users': [
        {
            'email': f'user{i}@company.com',
            'first_name': f'User{i}',
            'last_name': 'Test',
            'password': 'TestPass123!',
            'role': 'sales'
        }
        for i in range(2)  # Start with just 2 users for debugging
    ]
}

print("Testing bulk user creation with data:", bulk_data)
response = client.post('/api/v1/auth/users/bulk-create/', bulk_data)
print(f"Status Code: {response.status_code}")
print(f"Response Data: {response.content.decode()}")

if hasattr(response, 'json'):
    print(f"Response JSON: {response.json()}")