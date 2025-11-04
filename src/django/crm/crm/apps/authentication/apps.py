"""
Authentication App Configuration
"""

from django.apps import AppConfig


class AuthenticationConfig(AppConfig):
    """Authentication app configuration with enterprise features"""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'crm.apps.authentication'
    verbose_name = 'Authentication & Authorization'

    def ready(self):
        """Initialize app with signal handlers and other setup"""
        try:
            import crm.apps.authentication.signals  # noqa
        except ImportError:
            # Signals module not available, continuing without it
            pass