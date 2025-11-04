"""
Documentation App Configuration
Following SOLID principles and Django best practices
"""

from django.apps import AppConfig


class DocumentationConfig(AppConfig):
    """Documentation app configuration with SOLID principles"""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'crm.apps.documentation'
    verbose_name = 'API Documentation'

    def ready(self):
        """Initialize app-specific configurations"""
        # Import signals or other app-specific initialization
        pass