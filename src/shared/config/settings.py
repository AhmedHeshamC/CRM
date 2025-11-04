"""
Configuration Management for CRM System
Following SOLID principles and enterprise best practices
"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class Environment(Enum):
    """Environment enumeration"""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass
class DatabaseConfig:
    """Database configuration settings"""
    host: str = "localhost"
    port: int = 5432
    name: str = "crm_db"
    user: str = "postgres"
    password: str = ""
    engine: str = "django.db.backends.postgresql"
    options: Dict[str, Any] = field(default_factory=dict)

    def get_django_settings(self) -> Dict[str, Any]:
        """Get Django database settings"""
        return {
            'ENGINE': self.engine,
            'HOST': self.host,
            'PORT': self.port,
            'NAME': self.name,
            'USER': self.user,
            'PASSWORD': self.password,
            'OPTIONS': self.options,
        }


@dataclass
class RedisConfig:
    """Redis configuration settings"""
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    ssl: bool = False
    connection_pool_kwargs: Dict[str, Any] = field(default_factory=dict)

    def get_url(self) -> str:
        """Get Redis connection URL"""
        protocol = "rediss" if self.ssl else "redis"
        auth_part = f":{self.password}@" if self.password else ""
        return f"{protocol}://{auth_part}{self.host}:{self.port}/{self.db}"


@dataclass
class EmailConfig:
    """Email configuration settings"""
    backend: str = "django.core.mail.backends.smtp.EmailBackend"
    host: str = "localhost"
    port: int = 587
    use_tls: bool = True
    use_ssl: bool = False
    timeout: int = 30
    host_user: str = ""
    host_password: str = ""
    default_from_email: str = "noreply@crm.example.com"
    reply_to_email: str = ""

    def get_django_settings(self) -> Dict[str, Any]:
        """Get Django email settings"""
        return {
            'EMAIL_BACKEND': self.backend,
            'EMAIL_HOST': self.host,
            'EMAIL_PORT': self.port,
            'EMAIL_USE_TLS': self.use_tls,
            'EMAIL_USE_SSL': self.use_ssl,
            'EMAIL_TIMEOUT': self.timeout,
            'EMAIL_HOST_USER': self.host_user,
            'EMAIL_HOST_PASSWORD': self.host_password,
            'DEFAULT_FROM_EMAIL': self.default_from_email,
            'REPLY_TO_EMAIL': self.reply_to_email,
        }


@dataclass
class SecurityConfig:
    """Security configuration settings"""
    secret_key: str = ""
    debug: bool = False
    allowed_hosts: list = field(default_factory=lambda: ["localhost", "127.0.0.1"])
    cors_allowed_origins: list = field(default_factory=list)
    cors_allowed_methods: list = field(default_factory=lambda: ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
    cors_allowed_headers: list = field(default_factory=lambda: ["*"])
    csrf_trusted_origins: list = field(default_factory=list)
    session_cookie_secure: bool = False
    session_cookie_httponly: bool = True
    session_cookie_samesite: str = "Lax"
    secure_ssl_redirect: bool = False
    secure_hsts_seconds: int = 0
    secure_hsts_include_subdomains: bool = False
    secure_hsts_preload: bool = False
    secure_content_type_nosniff: bool = True
    secure_browser_xss_filter: bool = True
    secure_referrer_policy: str = "same-origin"

    def get_django_settings(self) -> Dict[str, Any]:
        """Get Django security settings"""
        return {
            'SECRET_KEY': self.secret_key,
            'DEBUG': self.debug,
            'ALLOWED_HOSTS': self.allowed_hosts,
            'CORS_ALLOWED_ORIGINS': self.cors_allowed_origins,
            'CORS_ALLOWED_METHODS': self.cors_allowed_methods,
            'CORS_ALLOWED_HEADERS': self.cors_allowed_headers,
            'CSRF_TRUSTED_ORIGINS': self.csrf_trusted_origins,
            'SESSION_COOKIE_SECURE': self.session_cookie_secure,
            'SESSION_COOKIE_HTTPONLY': self.session_cookie_httponly,
            'SESSION_COOKIE_SAMESITE': self.session_cookie_samesite,
            'SECURE_SSL_REDIRECT': self.secure_ssl_redirect,
            'SECURE_HSTS_SECONDS': self.secure_hsts_seconds,
            'SECURE_HSTS_INCLUDE_SUBDOMAINS': self.secure_hsts_include_subdomains,
            'SECURE_HSTS_PRELOAD': self.secure_hsts_preload,
            'SECURE_CONTENT_TYPE_NOSNIFF': self.secure_content_type_nosniff,
            'SECURE_BROWSER_XSS_FILTER': self.secure_browser_xss_filter,
            'SECURE_REFERRER_POLICY': self.secure_referrer_policy,
        }


@dataclass
class CacheConfig:
    """Cache configuration settings"""
    default_timeout: int = 300
    key_prefix: str = "crm"
    version: int = 1
    backend: str = "django.core.cache.backends.redis.RedisCache"
    redis_url: str = ""

    def get_django_settings(self) -> Dict[str, Any]:
        """Get Django cache settings"""
        return {
            'default': {
                'BACKEND': self.backend,
                'LOCATION': self.redis_url,
                'TIMEOUT': self.default_timeout,
                'KEY_PREFIX': self.key_prefix,
                'VERSION': self.version,
                'OPTIONS': {
                    'CLIENT_CLASS': 'django_redis.client.DefaultClient',
                }
            }
        }


@dataclass
class LoggingConfig:
    """Logging configuration settings"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format: str = "%Y-%m-%d %H:%M:%S"
    file_handler: bool = False
    file_path: str = "logs/crm.log"
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    console_handler: bool = True

    def get_django_settings(self) -> Dict[str, Any]:
        """Get Django logging settings"""
        handlers = {}
        if self.console_handler:
            handlers['console'] = {
                'class': 'logging.StreamHandler',
                'formatter': 'verbose',
            }

        if self.file_handler:
            handlers['file'] = {
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': self.file_path,
                'maxBytes': self.max_file_size,
                'backupCount': self.backup_count,
                'formatter': 'verbose',
            }

        return {
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': {
                'verbose': {
                    'format': self.format,
                    'datefmt': self.date_format,
                },
            },
            'handlers': handlers,
            'root': {
                'handlers': list(handlers.keys()),
                'level': self.level,
            },
            'loggers': {
                'django': {
                    'handlers': list(handlers.keys()),
                    'level': self.level,
                    'propagate': False,
                },
                'crm': {
                    'handlers': list(handlers.keys()),
                    'level': self.level,
                    'propagate': False,
                },
            },
        }


@dataclass
class CeleryConfig:
    """Celery configuration settings"""
    broker_url: str = "redis://localhost:6379/1"
    result_backend: str = "redis://localhost:6379/2"
    task_serializer: str = "json"
    result_serializer: str = "json"
    accept_content: list = field(default_factory=lambda: ["json"])
    timezone: str = "UTC"
    enable_utc: bool = True
    task_track_started: bool = True
    task_time_limit: int = 300  # 5 minutes
    task_soft_time_limit: int = 240  # 4 minutes
    worker_prefetch_multiplier: int = 1
    worker_max_tasks_per_child: int = 1000

    def get_django_settings(self) -> Dict[str, Any]:
        """Get Django Celery settings"""
        return {
            'broker_url': self.broker_url,
            'result_backend': self.result_backend,
            'task_serializer': self.task_serializer,
            'result_serializer': self.result_serializer,
            'accept_content': self.accept_content,
            'timezone': self.timezone,
            'enable_utc': self.enable_utc,
            'task_track_started': self.task_track_started,
            'task_time_limit': self.task_time_limit,
            'task_soft_time_limit': self.task_soft_time_limit,
            'worker_prefetch_multiplier': self.worker_prefetch_multiplier,
            'worker_max_tasks_per_child': self.worker_max_tasks_per_child,
        }


@dataclass
class APIConfig:
    """API configuration settings"""
    pagination_page_size: int = 20
    pagination_max_page_size: int = 100
    throttle_anon_rate: str = "100/hour"
    throttle_user_rate: str = "1000/hour"
    default_renderer_classes: list = field(default_factory=lambda: ["rest_framework.renderers.JSONRenderer"])
    default_parser_classes: list = field(default_factory=lambda: ["rest_framework.parsers.JSONParser"])
    default_authentication_classes: list = field(default_factory=list)
    default_permission_classes: list = field(default_factory=lambda: ["rest_framework.permissions.IsAuthenticated"])
    swagger_enabled: bool = True
    swagger_title: str = "CRM API"
    swagger_description: str = "Customer Relationship Management API"
    swagger_version: str = "1.0.0"

    def get_django_settings(self) -> Dict[str, Any]:
        """Get Django REST Framework settings"""
        return {
            'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
            'PAGE_SIZE': self.pagination_page_size,
            'PAGE_SIZE_MAX': self.pagination_max_page_size,
            'DEFAULT_THROTTLE_RATES': {
                'anon': self.throttle_anon_rate,
                'user': self.throttle_user_rate,
            },
            'DEFAULT_RENDERER_CLASSES': self.default_renderer_classes,
            'DEFAULT_PARSER_CLASSES': self.default_parser_classes,
            'DEFAULT_AUTHENTICATION_CLASSES': self.default_authentication_classes,
            'DEFAULT_PERMISSION_CLASSES': self.default_permission_classes,
        }


class Settings:
    """
    Main settings manager following Single Responsibility Principle
    Handles all configuration loading and validation
    """

    def __init__(self):
        """Initialize settings manager"""
        self.environment = self._get_environment()
        self.base_dir = self._get_base_dir()
        self.database = self._load_database_config()
        self.redis = self._load_redis_config()
        self.email = self._load_email_config()
        self.security = self._load_security_config()
        self.cache = self._load_cache_config()
        self.logging = self._load_logging_config()
        self.celery = self._load_celery_config()
        self.api = self._load_api_config()

    def _get_environment(self) -> Environment:
        """Get current environment"""
        env = os.getenv('CRM_ENV', 'development').lower()
        try:
            return Environment(env)
        except ValueError:
            logger.warning(f"Invalid environment '{env}', defaulting to development")
            return Environment.DEVELOPMENT

    def _get_base_dir(self) -> Path:
        """Get base directory of the project"""
        return Path(__file__).parent.parent.parent.parent

    def _load_database_config(self) -> DatabaseConfig:
        """Load database configuration"""
        return DatabaseConfig(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', '5432')),
            name=os.getenv('DB_NAME', 'crm_db'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', ''),
            options={
                'connect_timeout': 10,
            }
        )

    def _load_redis_config(self) -> RedisConfig:
        """Load Redis configuration"""
        return RedisConfig(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', '6379')),
            db=int(os.getenv('REDIS_DB', '0')),
            password=os.getenv('REDIS_PASSWORD'),
            ssl=self.environment == Environment.PRODUCTION
        )

    def _load_email_config(self) -> EmailConfig:
        """Load email configuration"""
        if self.environment == Environment.PRODUCTION:
            return EmailConfig(
                host=os.getenv('EMAIL_HOST'),
                port=int(os.getenv('EMAIL_PORT', '587')),
                use_tls=os.getenv('EMAIL_USE_TLS', 'true').lower() == 'true',
                host_user=os.getenv('EMAIL_HOST_USER'),
                host_password=os.getenv('EMAIL_HOST_PASSWORD'),
                default_from_email=os.getenv('DEFAULT_FROM_EMAIL', 'noreply@crm.example.com'),
            )
        else:
            # Use console backend for development/testing
            return EmailConfig(
                backend='django.core.mail.backends.console.EmailBackend'
            )

    def _load_security_config(self) -> SecurityConfig:
        """Load security configuration"""
        secret_key = os.getenv('SECRET_KEY')
        if not secret_key:
            if self.environment == Environment.PRODUCTION:
                raise ValueError("SECRET_KEY environment variable is required in production")
            else:
                secret_key = 'django-insecure-development-key-change-in-production'

        allowed_hosts = os.getenv('ALLOWED_HOSTS', '').split(',')
        allowed_hosts = [host.strip() for host in allowed_hosts if host.strip()]
        if not allowed_hosts and self.environment != Environment.DEVELOPMENT:
            allowed_hosts = ['*']

        return SecurityConfig(
            secret_key=secret_key,
            debug=self.environment == Environment.DEVELOPMENT,
            allowed_hosts=allowed_hosts or ['localhost', '127.0.0.1'],
            cors_allowed_origins=os.getenv('CORS_ALLOWED_ORIGINS', '').split(','),
            session_cookie_secure=self.environment == Environment.PRODUCTION,
            secure_ssl_redirect=self.environment == Environment.PRODUCTION,
            secure_hsts_seconds=31536000 if self.environment == Environment.PRODUCTION else 0,
        )

    def _load_cache_config(self) -> CacheConfig:
        """Load cache configuration"""
        return CacheConfig(
            redis_url=self.redis.get_url(),
            key_prefix=f"crm_{self.environment.value}",
        )

    def _load_logging_config(self) -> LoggingConfig:
        """Load logging configuration"""
        if self.environment == Environment.PRODUCTION:
            return LoggingConfig(
                level='INFO',
                file_handler=True,
                file_path=str(self.base_dir / 'logs' / 'crm.log'),
                console_handler=False,
            )
        else:
            return LoggingConfig(
                level='DEBUG',
                console_handler=True,
                file_handler=False,
            )

    def _load_celery_config(self) -> CeleryConfig:
        """Load Celery configuration"""
        return CeleryConfig(
            broker_url=f"{self.redis.get_url()}/1",
            result_backend=f"{self.redis.get_url()}/2",
        )

    def _load_api_config(self) -> APIConfig:
        """Load API configuration"""
        return APIConfig(
            swagger_enabled=self.environment != Environment.PRODUCTION,
        )

    def get_django_settings(self) -> Dict[str, Any]:
        """Get complete Django settings dictionary"""
        settings = {
            # Environment settings
            'ENVIRONMENT': self.environment.value,
            'BASE_DIR': self.base_dir,

            # Database
            'DATABASES': {
                'default': self.database.get_django_settings()
            },

            # Cache
            'CACHES': self.cache.get_django_settings(),

            # Email
            **self.email.get_django_settings(),

            # Security
            **self.security.get_django_settings(),

            # Logging
            'LOGGING': self.logging.get_django_settings(),

            # Celery
            **self.celery.get_django_settings(),

            # REST Framework
            'REST_FRAMEWORK': self.api.get_django_settings(),

            # Internationalization
            'LANGUAGE_CODE': 'en-us',
            'TIME_ZONE': 'UTC',
            'USE_I18N': True,
            'USE_TZ': True,

            # Static files
            'STATIC_URL': '/static/',
            'STATIC_ROOT': self.base_dir / 'staticfiles',
            'MEDIA_URL': '/media/',
            'MEDIA_ROOT': self.base_dir / 'media',

            # Apps
            'INSTALLED_APPS': [
                'django.contrib.admin',
                'django.contrib.auth',
                'django.contrib.contenttypes',
                'django.contrib.sessions',
                'django.contrib.messages',
                'django.contrib.staticfiles',

                # Third party apps
                'rest_framework',
                'corsheaders',
                'django_filters',

                # Local apps
                'crm.apps.authentication',
                'crm.apps.contacts',
                'crm.apps.deals',
                'crm.apps.activities',
            ],

            # Middleware
            'MIDDLEWARE': [
                'corsheaders.middleware.CorsMiddleware',
                'django.middleware.security.SecurityMiddleware',
                'django.contrib.sessions.middleware.SessionMiddleware',
                'django.middleware.common.CommonMiddleware',
                'django.middleware.csrf.CsrfViewMiddleware',
                'django.contrib.auth.middleware.AuthenticationMiddleware',
                'django.contrib.messages.middleware.MessageMiddleware',
                'django.middleware.clickjacking.XFrameOptionsMiddleware',
            ],

            # Root URL configuration
            'ROOT_URLCONF': 'crm.urls',

            # Templates
            'TEMPLATES': [
                {
                    'BACKEND': 'django.template.backends.django.DjangoTemplates',
                    'DIRS': [self.base_dir / 'templates'],
                    'APP_DIRS': True,
                    'OPTIONS': {
                        'context_processors': [
                            'django.template.context_processors.debug',
                            'django.template.context_processors.request',
                            'django.contrib.auth.context_processors.auth',
                            'django.contrib.messages.context_processors.messages',
                        ],
                    },
                },
            ],

            # WSGI
            'WSGI_APPLICATION': 'crm.wsgi.application',

            # Auth user model
            'AUTH_USER_MODEL': 'authentication.User',

            # Password validation
            'AUTH_PASSWORD_VALIDATORS': [
                {
                    'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
                },
                {
                    'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
                },
                {
                    'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
                },
                {
                    'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
                },
            ],
        }

        # Add Swagger settings if enabled
        if self.api.swagger_enabled:
            settings.update({
                'DRF_SPECTACULAR': {
                    'TITLE': self.api.swagger_title,
                    'DESCRIPTION': self.api.swagger_description,
                    'VERSION': self.api.swagger_version,
                    'SERVE_INCLUDE_SCHEMA': False,
                },
                'REST_FRAMEWORK']['DEFAULT_SCHEMA_CLASS'] = 'drf_spectacular.openapi.AutoSchema'

        return settings


# Global settings instance
settings = Settings()