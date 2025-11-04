"""
Django App Configuration for Background Tasks
Following SOLID principles and Django best practices
"""

from django.apps import AppConfig


class TasksConfig(AppConfig):
    """
    Configuration for the Background Tasks application.

    This app handles all asynchronous background processing including:
    - Email notifications
    - Data exports
    - Report generation
    - Scheduled tasks
    - Activity reminders
    - Deal workflow automation
    """

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'crm.apps.tasks'
    verbose_name = 'Background Tasks'

    def ready(self):
        """
        Initialize app when Django starts.
        Sets up signal handlers and task configurations.
        """
        # Import tasks to ensure they are registered with Celery
        try:
            from . import email_tasks
            from . import export_tasks
            from . import report_tasks
            from . import notification_tasks
            from . import workflow_tasks
            from . import base_tasks
        except ImportError:
            # Tasks modules may not exist during initial migration
            pass

        # Import signal handlers
        try:
            from . import signals
        except ImportError:
            # Signals module may not exist initially
            pass