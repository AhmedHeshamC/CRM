"""
PostgreSQL Test Settings for CRM Project
Following TDD approach to test PostgreSQL configuration
"""

import os
from .settings_base import *

# Override database configuration for PostgreSQL testing
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'test_crm_db'),
        'USER': os.environ.get('DB_USER', 'test_crm_user'),
        'PASSWORD': os.environ.get('DB_PASSWORD', 'test_crm_password'),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
        'OPTIONS': {
            'connect_timeout': 60,
        }
    }
}