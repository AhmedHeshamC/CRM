"""
Django Settings for CRM Project
Following SOLID principles and enterprise best practices
"""

import os
import sys
from pathlib import Path
from datetime import timedelta

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Import base settings first
from .settings_base import *

# Try to import environ for environment variable handling
try:
    import environ
    HAS_ENVIRON = True
except ImportError:
    HAS_ENVIRON = False
    print("Warning: python-decouple not available, using default settings")

# Environment variables setup
if HAS_ENVIRON:
    env = environ.Env(
        DEBUG=(bool, False)
    )

    # Take environment variables from .env file (if it exists)
    env_file_path = os.path.join(BASE_DIR, '.env')
    if os.path.exists(env_file_path):
        environ.Env.read_env(env_file_path)

    # Override settings with environment variables
    SECRET_KEY = env('SECRET_KEY', default=SECRET_KEY)
    DEBUG = env('DEBUG', default=DEBUG)
    ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=ALLOWED_HOSTS)

    # Database configuration
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': env('DB_NAME', default=DATABASES['default']['NAME']),
            'USER': env('DB_USER', default=DATABASES['default']['USER']),
            'PASSWORD': env('DB_PASSWORD', default=DATABASES['default']['PASSWORD']),
            'HOST': env('DB_HOST', default=DATABASES['default']['HOST']),
            'PORT': env('DB_PORT', default=DATABASES['default']['PORT']),
            'OPTIONS': {
                'connect_timeout': 60,
            }
        }
    }

    # Redis Configuration
    REDIS_URL = env('REDIS_URL', default=REDIS_URL)

    # Enhanced Cache Configuration
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': REDIS_URL,
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
                'SOCKET_CONNECT_TIMEOUT': 5,
                'SOCKET_TIMEOUT': 5,
                'RETRY_ON_TIMEOUT': True,
                'MAX_CONNECTIONS': 1000,
                'COMPRESS_MIN_LEN': 10,
            }
        },
        'sessions': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': REDIS_URL,
            'TIMEOUT': 3600 * 24 * 7,  # 1 week
        }
    }

    # Session Configuration
    SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
    SESSION_CACHE_ALIAS = 'sessions'

    # Celery Configuration
    CELERY_BROKER_URL = REDIS_URL
    CELERY_RESULT_BACKEND = REDIS_URL

    # CORS Configuration
    CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=CORS_ALLOWED_ORIGINS)

    # Logging Configuration
    LOGGING['root']['level'] = env('LOG_LEVEL', default='INFO')

    # JWT Settings - Enhanced Security Configuration
    SIMPLE_JWT.update({
        'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15 if not env.bool('DEBUG', default=DEBUG) else 60),
        'REFRESH_TOKEN_LIFETIME': timedelta(days=7 if not env.bool('DEBUG', default=DEBUG) else 1),
        'SIGNING_KEY': SECRET_KEY,
        'AUDIENCE': env('JWT_AUDIENCE', default=None),
        'ISSUER': env('JWT_ISSUER', default='crm-api'),
        'JWK_URL': env('JWK_URL', default=None),
        'LEEWAY': timedelta(seconds=10),
        'AUTH_COOKIE': env('AUTH_COOKIE_NAME', default='access_token'),
        'AUTH_COOKIE_DOMAIN': env('AUTH_COOKIE_DOMAIN', default=None),
        'AUTH_COOKIE_SECURE': not env.bool('DEBUG', default=DEBUG),
        'AUTH_COOKIE_HTTP_ONLY': True,
        'AUTH_COOKIE_SAMESITE': 'Lax',
        'AUTH_COOKIE_PATH': '/',
    })

    # Security Settings
    SECURE_HSTS_SECONDS = 31536000 if not env.bool('DEBUG', default=DEBUG) else 0
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True if not env.bool('DEBUG', default=DEBUG) else False
    SECURE_HSTS_PRELOAD = True if not env.bool('DEBUG', default=DEBUG) else False

else:
    # Fallback to basic settings when environ is not available
    print("Warning: Running without environment variable support")

    # Override with basic environment variables if available
    SECRET_KEY = os.environ.get('SECRET_KEY', SECRET_KEY)
    DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'
    ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

    # Database from environment variables
    db_url = os.environ.get('DATABASE_URL')
    if db_url:
        # Parse DATABASE_URL if provided
        import re
        match = re.match(r'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', db_url)
        if match:
            user, password, host, port, name = match.groups()
            DATABASES = {
                'default': {
                    'ENGINE': 'django.db.backends.postgresql',
                    'NAME': name,
                    'USER': user,
                    'PASSWORD': password,
                    'HOST': host,
                    'PORT': port,
                    'OPTIONS': {
                        'connect_timeout': 60,
                    }
                }
            }

# Import additional advanced settings if environment supports them
if HAS_ENVIRON:
    try:
        from .settings_advanced import *
    except ImportError:
        pass