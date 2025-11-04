"""
Django app configuration for monitoring module.
Following Django best practices and SOLID principles.
"""

from django.apps import AppConfig


class MonitoringConfig(AppConfig):
    """
    Configuration class for the monitoring app.

    This configuration follows the Single Responsibility Principle by focusing
    solely on the setup and initialization of monitoring-related functionality.
    """

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'crm.apps.monitoring'
    verbose_name = 'System Monitoring & Health Checks'

    def ready(self) -> None:
        """
        Initialize the monitoring app when Django starts.

        This method sets up necessary signal handlers and background monitoring
        processes. It follows the Open/Closed Principle by being open for
        extension but closed for modification.
        """
        # Import signals to register them
        try:
            from crm.apps.monitoring import signals  # noqa: F401
        except ImportError:
            # Signals module may not exist during initial app creation
            pass

        # Initialize metrics collectors
        self._initialize_metrics()

    def _initialize_metrics(self) -> None:
        """
        Initialize Prometheus metrics collectors.

        This method sets up default metrics that should be available
        for monitoring system performance and business metrics.
        """
        # Import metrics module to initialize collectors
        try:
            from crm.apps.monitoring.metrics import MetricsCollector
            # Initialize metrics collectors on app startup
            MetricsCollector.initialize_default_metrics()
        except ImportError:
            # Metrics module may not exist during initial app creation
            pass