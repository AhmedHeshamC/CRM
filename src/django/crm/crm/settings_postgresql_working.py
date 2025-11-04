"""
Working PostgreSQL Test Settings for CRM Project
Following TDD approach with minimal configuration
"""

import os
from .settings_base import *

# Simple working database configuration for PostgreSQL testing
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'crm_working_db'),
        'USER': os.environ.get('DB_USER', 'm'),
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
        'OPTIONS': {
            'connect_timeout': 60,
        }
    }
}

# Override apps to include all CRM apps
LOCAL_APPS = [
    'crm.apps.authentication',
    'crm.apps.contacts',
    'crm.apps.activities',
    'crm.apps.deals',
    'crm.apps.monitoring',
    'crm.apps.tasks',
    'crm.apps.documentation',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# Disable migrations for faster testing
class DisableMigrations:
    def __contains__(self, item):
        return True

    def __getitem__(self, item):
        return None

MIGRATION_MODULES = DisableMigrations()

# Simple cache configuration
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

# Simple logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}