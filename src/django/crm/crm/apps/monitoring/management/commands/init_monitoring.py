"""
Django management command to initialize monitoring system.

This command sets up the monitoring system, including alert handlers
and background monitoring processes following SOLID principles.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone

import structlog

from ..alerts import get_alert_manager, log_alert_handler
from ..metrics import MetricsCollector

logger = structlog.get_logger(__name__)


class Command(BaseCommand):
    """
    Management command to initialize the monitoring system.

    This command follows the Single Responsibility Principle by focusing
    solely on initializing monitoring components.
    """

    help = 'Initialize the monitoring system and start background monitoring'

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            '--no-background',
            action='store_true',
            help='Do not start background monitoring thread',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be initialized without actually doing it',
        )

    def handle(self, *args, **options):
        """
        Handle the command execution.

        Args:
            *args: Command arguments
            **options: Command options
        """
        self.stdout.write(self.style.SUCCESS('Initializing CRM Monitoring System...'))

        if options['dry_run']:
            self.stdout.write('DRY RUN - No changes will be made')

        try:
            # Initialize alert manager
            self._initialize_alert_manager(options['dry_run'])

            # Initialize metrics collector
            self._initialize_metrics_collector(options['dry_run'])

            # Start background monitoring if requested
            if not options['no_background'] and not options['dry_run']:
                self._start_background_monitoring()

            self.stdout.write(self.style.SUCCESS('Monitoring system initialized successfully!'))

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Failed to initialize monitoring system: {e}')
            )
            logger.error(f"Monitoring initialization failed: {e}")

    def _initialize_alert_manager(self, dry_run: bool):
        """
        Initialize the alert manager with handlers.

        Args:
            dry_run: Whether this is a dry run
        """
        if dry_run:
            self.stdout.write('  Would initialize alert manager')
            return

        try:
            alert_manager = get_alert_manager()

            # Add default alert handler
            alert_manager.add_alert_handler(log_alert_handler)

            # Add custom alert handlers here if needed
            # alert_manager.add_alert_handler(custom_slack_handler)
            # alert_manager.add_alert_handler(custom_email_handler)

            self.stdout.write(self.style.SUCCESS('   Alert manager initialized'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'   Failed to initialize alert manager: {e}'))
            raise

    def _initialize_metrics_collector(self, dry_run: bool):
        """
        Initialize the metrics collector.

        Args:
            dry_run: Whether this is a dry run
        """
        if dry_run:
            self.stdout.write('  Would initialize metrics collector')
            return

        try:
            # Initialize metrics collector (this also sets up Prometheus metrics)
            MetricsCollector.initialize_default_metrics()

            self.stdout.write(self.style.SUCCESS('   Metrics collector initialized'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'   Failed to initialize metrics collector: {e}'))
            raise

    def _start_background_monitoring(self):
        """Start background monitoring processes."""
        try:
            alert_manager = get_alert_manager()
            alert_manager.start_monitoring()

            self.stdout.write(self.style.SUCCESS('   Background monitoring started'))
            self.stdout.write('  (Monitoring runs in background thread)')

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'   Failed to start background monitoring: {e}'))
            raise