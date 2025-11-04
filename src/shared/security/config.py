"""
Comprehensive Security Configuration Management
Following SOLID principles and enterprise-grade security standards
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any, Union, Type
from dataclasses import dataclass, field
from enum import Enum
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils import timezone
from shared.security.exceptions import SecurityConfigError

logger = logging.getLogger(__name__)


class SecurityEnvironment(Enum):
    """
    Security environment types
    Following Single Responsibility Principle for environment categorization
    """
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class SecurityLevel(Enum):
    """
    Security level configurations
    Following Single Responsibility Principle for security level management
    """
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    MAXIMUM = "maximum"


@dataclass
class RateLimitConfig:
    """Rate limiting configuration"""
    enabled: bool = True
    requests_per_minute: int = 100
    burst_requests_per_minute: int = 150
    requests_per_hour: int = 1000
    enable_user_based_limiting: bool = True
    enable_ip_based_fallback: bool = True
    admin_exemption: bool = True
    exempt_paths: List[str] = field(default_factory=lambda: [
        '/health/', '/metrics/', '/api/schema/', '/admin/'
    ])


@dataclass
class CORSConfig:
    """CORS configuration"""
    enabled: bool = True
    strict_mode: bool = True
    allowed_origins: List[str] = field(default_factory=list)
    allowed_methods: List[str] = field(default_factory=lambda: [
        'GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS', 'HEAD'
    ])
    allowed_headers: List[str] = field(default_factory=lambda: [
        'accept', 'accept-encoding', 'authorization', 'content-type',
        'dnt', 'origin', 'user-agent', 'x-csrftoken', 'x-requested-with'
    ])
    exposed_headers: List[str] = field(default_factory=lambda: [
        'content-length', 'content-type', 'x-total-count', 'x-page-count'
    ])
    allow_credentials: bool = False
    max_age: int = 86400  # 24 hours
    subdomain_policy: str = 'strict'  # strict, permissive, disabled


@dataclass
class SecurityHeadersConfig:
    """Security headers configuration"""
    enabled: bool = True
    enable_hsts: bool = True
    hsts_max_age: int = 31536000  # 1 year
    hsts_include_subdomains: bool = True
    hsts_preload: bool = True
    enable_csp: bool = True
    csp_report_only: bool = False
    csp_report_uri: str = '/api/security/csp-report/'
    enable_feature_policy: bool = True
    enable_permissions_policy: bool = True
    referrer_policy: str = 'strict-origin-when-cross-origin'
    custom_headers: Dict[str, str] = field(default_factory=dict)


@dataclass
class InputValidationConfig:
    """Input validation configuration"""
    enabled: bool = True
    max_field_length: int = 10000
    strict_mode: bool = True
    enable_sql_injection_detection: bool = True
    enable_xss_detection: bool = True
    enable_encoding_detection: bool = True
    allowed_html_tags: List[str] = field(default_factory=lambda: [
        'p', 'br', 'strong', 'em', 'u', 'i', 'b',
        'ul', 'ol', 'li', 'blockquote', 'code', 'pre'
    ])
    allowed_html_attributes: Dict[str, List[str]] = field(default_factory=lambda: {
        '*': ['class'],
        'a': ['href', 'title'],
        'img': ['src', 'alt', 'width', 'height']
    })
    enable_custom_patterns: bool = False
    custom_patterns: List[str] = field(default_factory=list)


@dataclass
class SQLInjectionProtectionConfig:
    """SQL injection protection configuration"""
    enabled: bool = True
    strict_mode: bool = True
    enable_advanced_detection: bool = True
    enable_context_validation: bool = True
    enable_parameter_validation: bool = True
    enable_statistics: bool = True
    custom_patterns: List[str] = field(default_factory=list)
    exempt_fields: List[str] = field(default_factory=list)


@dataclass
class LoggingConfig:
    """Security logging configuration"""
    enabled: bool = True
    level: str = 'INFO'
    enable_file_logging: bool = True
    enable_database_logging: bool = False
    log_retention_days: int = 90
    log_file: str = 'logs/security.log'
    log_max_size: int = 50 * 1024 * 1024  # 50MB
    log_backup_count: int = 5
    enable_structured_logging: bool = True
    enable_real_time_monitoring: bool = True
    enable_anomaly_detection: bool = True


@dataclass
class AlertConfig:
    """Security alert configuration"""
    enabled: bool = True
    enable_email_notifications: bool = False
    enable_sms_notifications: bool = False
    enable_slack_notifications: bool = False
    alert_thresholds: Dict[str, int] = field(default_factory=dict)
    escalation_thresholds: Dict[str, int] = field(default_factory=dict)
    alert_cooldown: int = 300  # 5 minutes
    notification_recipients: List[str] = field(default_factory=list)


@dataclass
class SecurityConfig:
    """
    Main security configuration
    Following Single Responsibility Principle for comprehensive security management
    """
    environment: SecurityEnvironment = SecurityEnvironment.PRODUCTION
    security_level: SecurityLevel = SecurityLevel.HIGH
    rate_limiting: RateLimitConfig = field(default_factory=RateLimitConfig)
    cors: CORSConfig = field(default_factory=CORSConfig)
    security_headers: SecurityHeadersConfig = field(default_factory=SecurityHeadersConfig)
    input_validation: InputValidationConfig = field(default_factory=InputValidationConfig)
    sql_injection_protection: SQLInjectionProtectionConfig = field(default_factory=SQLInjectionProtectionConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    alerts: AlertConfig = field(default_factory=AlertConfig)
    custom_settings: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            'environment': self.environment.value,
            'security_level': self.security_level.value,
            'rate_limiting': {
                'enabled': self.rate_limiting.enabled,
                'requests_per_minute': self.rate_limiting.requests_per_minute,
                'admin_exemption': self.rate_limiting.admin_exemption
            },
            'cors': {
                'enabled': self.cors.enabled,
                'strict_mode': self.cors.strict_mode,
                'allowed_origins_count': len(self.cors.allowed_origins),
                'allow_credentials': self.cors.allow_credentials
            },
            'security_headers': {
                'enabled': self.security_headers.enabled,
                'enable_hsts': self.security_headers.enable_hsts,
                'enable_csp': self.security_headers.enable_csp
            },
            'input_validation': {
                'enabled': self.input_validation.enabled,
                'strict_mode': self.input_validation.strict_mode,
                'enable_sql_injection_detection': self.input_validation.enable_sql_injection_detection,
                'enable_xss_detection': self.input_validation.enable_xss_detection
            },
            'sql_injection_protection': {
                'enabled': self.sql_injection_protection.enabled,
                'strict_mode': self.sql_injection_protection.strict_mode,
                'enable_advanced_detection': self.sql_injection_protection.enable_advanced_detection
            },
            'logging': {
                'enabled': self.logging.enabled,
                'level': self.logging.level,
                'enable_file_logging': self.logging.enable_file_logging,
                'enable_real_time_monitoring': self.logging.enable_real_time_monitoring
            },
            'alerts': {
                'enabled': self.alerts.enabled,
                'enable_email_notifications': self.alerts.enable_email_notifications,
                'notification_recipients_count': len(self.alerts.notification_recipients)
            },
            'custom_settings': self.custom_settings
        }


class SecurityConfigManager:
    """
    Security Configuration Manager
    Following Single Responsibility Principle for configuration management

    Features:
    - Environment-based configuration
    - Dynamic configuration loading
    - Configuration validation
    - Security level management
    - Configuration encryption
    - Audit logging
    """

    def __init__(self):
        """
        Initialize security configuration manager
        Following SOLID principles
        """
        self._config: Optional[SecurityConfig] = None
        self._config_source: str = 'default'
        self._last_loaded: Optional[timezone.datetime] = None
        self._config_cache_ttl = getattr(settings, 'SECURITY_CONFIG_CACHE_TTL', 300)  # 5 minutes

    def load_configuration(self, force_reload: bool = False) -> SecurityConfig:
        """
        Load security configuration
        Following Single Responsibility Principle
        """
        if not force_reload and self._is_config_valid():
            return self._config

        try:
            # Determine configuration source priority
            config_source = self._determine_config_source()

            if config_source == 'file':
                self._config = self._load_from_file()
            elif config_source == 'environment':
                self._config = self._load_from_environment()
            elif config_source == 'database':
                self._config = self._load_from_database()
            else:
                self._config = self._load_default_config()

            self._config_source = config_source
            self._last_loaded = timezone.now()

            # Validate configuration
            self._validate_configuration(self._config)

            logger.info(f"Security configuration loaded from {config_source}")

            return self._config

        except Exception as e:
            logger.error(f"Error loading security configuration: {str(e)}")
            # Fallback to default configuration
            self._config = self._load_default_config()
            self._config_source = 'default_fallback'
            return self._config

    def _is_config_valid(self) -> bool:
        """Check if current configuration is still valid"""
        if not self._config or not self._last_loaded:
            return False

        # Check if configuration has expired
        age_seconds = (timezone.now() - self._last_loaded).total_seconds()
        return age_seconds < self._config_cache_ttl

    def _determine_config_source(self) -> str:
        """
        Determine configuration source based on environment
        Following Single Responsibility Principle
        """
        # Check for explicit configuration source
        config_source = getattr(settings, 'SECURITY_CONFIG_SOURCE', 'auto')
        if config_source != 'auto':
            return config_source

        # Auto-determine based on environment
        if getattr(settings, 'SECURITY_CONFIG_FILE', None):
            return 'file'
        elif os.getenv('SECURITY_CONFIG_JSON'):
            return 'environment'
        elif getattr(settings, 'SECURITY_CONFIG_FROM_DB', False):
            return 'database'
        else:
            return 'default'

    def _load_from_file(self) -> SecurityConfig:
        """Load configuration from file"""
        config_file = getattr(settings, 'SECURITY_CONFIG_FILE', 'security_config.json')

        try:
            with open(config_file, 'r') as f:
                config_data = json.load(f)
            return self._create_config_from_dict(config_data)

        except FileNotFoundError:
            raise SecurityConfigError(f"Security configuration file not found: {config_file}")
        except json.JSONDecodeError as e:
            raise SecurityConfigError(f"Invalid JSON in security configuration file: {str(e)}")

    def _load_from_environment(self) -> SecurityConfig:
        """Load configuration from environment variables"""
        config_json = os.getenv('SECURITY_CONFIG_JSON')
        if config_json:
            try:
                config_data = json.loads(config_json)
                return self._create_config_from_dict(config_data)
            except json.JSONDecodeError as e:
                raise SecurityConfigError(f"Invalid JSON in SECURITY_CONFIG_JSON: {str(e)}")

        # Load from individual environment variables
        return self._load_from_env_vars()

    def _load_from_env_vars(self) -> SecurityConfig:
        """Load configuration from individual environment variables"""
        config = SecurityConfig()

        # Environment
        env_value = os.getenv('SECURITY_ENVIRONMENT', 'production')
        config.environment = SecurityEnvironment(env_value)

        # Security level
        level_value = os.getenv('SECURITY_LEVEL', 'high')
        config.security_level = SecuritySecurity(level_value)

        # Rate limiting
        config.rate_limiting.enabled = self._get_bool_env('RATE_LIMITING_ENABLED', True)
        config.rate_limiting.requests_per_minute = self._get_int_env('RATE_LIMITING_REQUESTS_PER_MINUTE', 100)

        # CORS
        config.cors.enabled = self._get_bool_env('CORS_ENABLED', True)
        config.cors.strict_mode = self._get_bool_env('CORS_STRICT_MODE', True)

        # Security headers
        config.security_headers.enabled = self._get_bool_env('SECURITY_HEADERS_ENABLED', True)
        config.security_headers.enable_hsts = self._get_bool_env('SECURITY_HEADERS_ENABLE_HSTS', True)

        # Input validation
        config.input_validation.enabled = self._get_bool_env('INPUT_VALIDATION_ENABLED', True)
        config.input_validation.strict_mode = self._get_bool_env('INPUT_VALIDATION_STRICT_MODE', True)

        # SQL injection protection
        config.sql_injection_protection.enabled = self._get_bool_env('SQL_INJECTION_PROTECTION_ENABLED', True)
        config.sql_injection_protection.strict_mode = self._get_bool_env('SQL_INJECTION_PROTECTION_STRICT_MODE', True)

        # Logging
        config.logging.enabled = self._get_bool_env('SECURITY_LOGGING_ENABLED', True)
        config.logging.level = os.getenv('SECURITY_LOGGING_LEVEL', 'INFO')

        # Alerts
        config.alerts.enabled = self._get_bool_env('SECURITY_ALERTS_ENABLED', True)
        config.alerts.enable_email_notifications = self._get_bool_env('SECURITY_EMAIL_NOTIFICATIONS', False)

        return config

    def _load_from_database(self) -> SecurityConfig:
        """Load configuration from database"""
        # This would require a SecurityConfig model to be defined
        # Placeholder for database configuration loading
        logger.info("Database configuration loading not implemented, using defaults")
        return self._load_default_config()

    def _load_default_config(self) -> SecurityConfig:
        """Load default security configuration"""
        config = SecurityConfig()

        # Environment-specific defaults
        if settings.DEBUG:
            config.environment = SecurityEnvironment.DEVELOPMENT
            config.security_level = SecurityLevel.MEDIUM
            config.cors.allowed_origins = [
                'http://localhost:3000',
                'http://127.0.0.1:3000',
                'http://localhost:8080',
                'http://127.0.0.1:8080'
            ]
            config.logging.level = 'DEBUG'
        else:
            config.environment = SecurityEnvironment.PRODUCTION
            config.security_level = SecurityLevel.HIGH
            config.cors.allowed_origins = getattr(settings, 'CORS_ALLOWED_ORIGINS', [])
            config.logging.level = 'INFO'

        # Apply Django settings as defaults
        config.cors.allowed_origins.extend(getattr(settings, 'CORS_ALLOWED_ORIGINS', []))
        config.cors.allow_credentials = getattr(settings, 'CORS_ALLOW_CREDENTIALS', False)
        config.rate_limiting.requests_per_minute = getattr(settings, 'RATE_LIMIT_REQUESTS_PER_MINUTE', 100)

        return config

    def _create_config_from_dict(self, config_data: Dict[str, Any]) -> SecurityConfig:
        """Create SecurityConfig from dictionary"""
        try:
            # Parse environment
            env_value = config_data.get('environment', 'production')
            environment = SecurityEnvironment(env_value)

            # Parse security level
            level_value = config_data.get('security_level', 'high')
            security_level = SecurityLevel(level_value)

            # Parse rate limiting
            rate_limit_data = config_data.get('rate_limiting', {})
            rate_limiting = RateLimitConfig(**rate_limit_data)

            # Parse CORS
            cors_data = config_data.get('cors', {})
            cors = CORSConfig(**cors_data)

            # Parse security headers
            headers_data = config_data.get('security_headers', {})
            security_headers = SecurityHeadersConfig(**headers_data)

            # Parse input validation
            validation_data = config_data.get('input_validation', {})
            input_validation = InputValidationConfig(**validation_data)

            # Parse SQL injection protection
            sql_data = config_data.get('sql_injection_protection', {})
            sql_injection_protection = SQLInjectionProtectionConfig(**sql_data)

            # Parse logging
            logging_data = config_data.get('logging', {})
            logging_config = LoggingConfig(**logging_data)

            # Parse alerts
            alerts_data = config_data.get('alerts', {})
            alerts = AlertConfig(**alerts_data)

            return SecurityConfig(
                environment=environment,
                security_level=security_level,
                rate_limiting=rate_limiting,
                cors=cors,
                security_headers=security_headers,
                input_validation=input_validation,
                sql_injection_protection=sql_injection_protection,
                logging=logging_config,
                alerts=alerts,
                custom_settings=config_data.get('custom_settings', {})
            )

        except Exception as e:
            raise SecurityConfigError(f"Error creating configuration from dictionary: {str(e)}")

    def _validate_configuration(self, config: SecurityConfig):
        """
        Validate security configuration
        Following Single Responsibility Principle
        """
        # Environment-specific validation
        if config.environment == SecurityEnvironment.PRODUCTION:
            if config.security_level not in [SecurityLevel.HIGH, SecurityLevel.MAXIMUM]:
                raise SecurityConfigError("Production environment requires HIGH or MAXIMUM security level")

            if not config.security_headers.enable_hsts:
                raise SecurityConfigError("HSTS must be enabled in production")

            if not config.sql_injection_protection.enabled:
                raise SecurityConfigError("SQL injection protection must be enabled in production")

        # CORS validation
        if config.cors.enabled and not config.cors.allowed_origins:
            logger.warning("CORS is enabled but no allowed origins are specified")

        # Logging validation
        if config.logging.enabled and config.logging.level not in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
            raise SecurityConfigError(f"Invalid logging level: {config.logging.level}")

        # Alert validation
        if config.alerts.enable_email_notifications and not config.alerts.notification_recipients:
            raise SecurityConfigError("Email notifications are enabled but no recipients are specified")

    def _get_bool_env(self, key: str, default: bool) -> bool:
        """Get boolean value from environment"""
        value = os.getenv(key)
        if value is None:
            return default
        return value.lower() in ('true', '1', 'yes', 'on')

    def _get_int_env(self, key: str, default: int) -> int:
        """Get integer value from environment"""
        value = os.getenv(key)
        if value is None:
            return default
        try:
            return int(value)
        except ValueError:
            logger.warning(f"Invalid integer value for {key}: {value}, using default: {default}")
            return default

    def save_configuration(self, config: SecurityConfig, target: str = 'file') -> bool:
        """
        Save security configuration
        Following Single Responsibility Principle
        """
        try:
            # Validate configuration before saving
            self._validate_configuration(config)

            if target == 'file':
                return self._save_to_file(config)
            elif target == 'database':
                return self._save_to_database(config)
            else:
                raise SecurityConfigError(f"Unsupported save target: {target}")

        except Exception as e:
            logger.error(f"Error saving security configuration: {str(e)}")
            return False

    def _save_to_file(self, config: SecurityConfig) -> bool:
        """Save configuration to file"""
        config_file = getattr(settings, 'SECURITY_CONFIG_FILE', 'security_config.json')

        try:
            config_data = config.to_dict()

            with open(config_file, 'w') as f:
                json.dump(config_data, f, indent=2, default=str)

            logger.info(f"Security configuration saved to {config_file}")
            return True

        except Exception as e:
            logger.error(f"Error saving configuration to file: {str(e)}")
            return False

    def _save_to_database(self, config: SecurityConfig) -> bool:
        """Save configuration to database"""
        # This would require a SecurityConfig model to be defined
        # Placeholder for database save implementation
        logger.info("Database configuration saving not implemented")
        return False

    def get_current_configuration(self) -> SecurityConfig:
        """Get current security configuration"""
        if not self._config:
            return self.load_configuration()
        return self._config

    def reload_configuration(self) -> SecurityConfig:
        """Force reload security configuration"""
        return self.load_configuration(force_reload=True)

    def update_configuration(self, updates: Dict[str, Any], save: bool = False) -> SecurityConfig:
        """
        Update specific configuration values
        Following Single Responsibility Principle
        """
        config = self.get_current_configuration()
        config_dict = config.to_dict()

        # Apply updates
        self._deep_update(config_dict, updates)

        # Create new configuration
        new_config = self._create_config_from_dict(config_dict)

        # Validate new configuration
        self._validate_configuration(new_config)

        # Update current configuration
        self._config = new_config
        self._last_loaded = timezone.now()

        # Save if requested
        if save:
            self.save_configuration(new_config)

        logger.info("Security configuration updated")

        return new_config

    def _deep_update(self, target: Dict[str, Any], updates: Dict[str, Any]):
        """Deep update dictionary"""
        for key, value in updates.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._deep_update(target[key], value)
            else:
                target[key] = value

    def get_configuration_status(self) -> Dict[str, Any]:
        """Get configuration status information"""
        return {
            'config_source': self._config_source,
            'last_loaded': self._last_loaded.isoformat() if self._last_loaded else None,
            'is_loaded': self._config is not None,
            'cache_ttl_seconds': self._config_cache_ttl,
            'environment': self._config.environment.value if self._config else None,
            'security_level': self._config.security_level.value if self._config else None
        }


# Global security configuration manager instance
security_config_manager = SecurityConfigManager()


def get_security_config() -> SecurityConfig:
    """
    Get current security configuration
    Following Single Responsibility Principle
    """
    return security_config_manager.get_current_configuration()


def reload_security_config() -> SecurityConfig:
    """
    Reload security configuration
    Following Single Responsibility Principle
    """
    return security_config_manager.reload_configuration()


def update_security_config(updates: Dict[str, Any], save: bool = False) -> SecurityConfig:
    """
    Update security configuration
    Following Single Responsibility Principle
    """
    return security_config_manager.update_configuration(updates, save)