"""
Production Security Settings for CRM Project
This file contains enhanced security settings for production deployment
"""

from django.conf import settings

# Enhanced Security Settings for Production
if not settings.DEBUG:
    # HTTPS/SSL Settings
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

    # HSTS Settings
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

    # Cookie Settings
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    CSRF_COOKIE_SECURE = True
    CSRF_COOKIE_HTTPONLY = True
    CSRF_COOKIE_SAMESITE = 'Lax'

    # Additional Security Headers
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

    # Frame Protection
    X_FRAME_OPTIONS = 'DENY'

# Rate Limiting Configuration
RATELIMIT_ENABLE = True
RATELIMIT_USE_CACHE = 'default'

# Rate limiting by view
RATELIMIT_VIEW = {
    'auth.*': ['100/h', '20/m'],
    'contacts.*': ['1000/h', '100/m'],
    'deals.*': ['1000/h', '100/m'],
    'activities.*': ['500/h', '50/m'],
}

# File Upload Security
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
FILE_UPLOAD_PERMISSIONS = 0o644
FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o755

# Allowed File Types
ALLOWED_UPLOAD_MIME_TYPES = [
    'text/plain',
    'text/csv',
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'image/jpeg',
    'image/png',
    'image/gif',
    'image/webp',
]

# Content Security Policy
CSP_DEFAULT_SRC = "'self'"
CSP_SCRIPT_SRC = "'self' 'unsafe-inline'"
CSP_STYLE_SRC = "'self' 'unsafe-inline'"
CSP_IMG_SRC = "'self' data: https:"
CSP_FONT_SRC = "'self'"
CSP_CONNECT_SRC = "'self'"
CSP_FRAME_ANCESTORS = "'none'"
CSP_FORM_ACTION = "'self'"

# Session Security
SESSION_SAVE_EVERY_REQUEST = True
SESSION_COOKIE_AGE = 3600 * 8  # 8 hours
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# Password Security
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 12,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Login Security
LOGIN_URL = '/api/v1/auth/login/'
LOGIN_REDIRECT_URL = '/admin/'
LOGOUT_REDIRECT_URL = '/api/v1/auth/login/'

# Failed Login Attempts
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 0.33  # 20 minutes
AXES_LOCK_OUT_AT_FAILURE = True
AXES_LOCK_OUT_BY_COMBINATION_USER_AND_IP = True
AXES_ONLY_USER_FAILURES = False
AXES_ENABLE_ACCESS_FAILURE_LOG = True

# IP Whitelist for Admin (if needed)
# ADMIN_IP_WHITELIST = ['192.168.1.0/24', '10.0.0.0/8']

# Security Monitoring
SECURITY_LOGGING_ENABLED = True
SECURITY_LOG_LEVEL = 'INFO'
SECURITY_SENSITIVE_PARAMETERS = ['password', 'token', 'secret', 'key']

# API Security
API_THROTTLE_RATES = {
    'user': '1000/hour',
    'anon': '100/hour',
    'upload': '50/hour',
    'export': '20/hour',
}

# CORS Security (Production)
CORS_ALLOWED_ORIGINS = [
    "https://yourdomain.com",
    "https://www.yourdomain.com",
    "https://app.yourdomain.com",
]

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

# Email Security
EMAIL_USE_TLS = True
EMAIL_PORT = 587
EMAIL_HOST_USER = 'noreply@yourdomain.com'
DEFAULT_FROM_EMAIL = 'CRM System <noreply@yourdomain.com>'

# Monitoring and Alerting
SECURITY_MONITORING_ENABLED = True
SECURITY_ALERT_EMAIL = 'security@yourdomain.com'

# Database Security
DATABASE_SSL_MODE = 'require'  # For PostgreSQL

# Backup Security
BACKUP_ENCRYPTION_ENABLED = True
BACKUP_RETENTION_DAYS = 30