"""
Prometheus metrics collection and management.

This module provides metrics collection functionality following SOLID principles:
- Single Responsibility: Each collector focuses on one type of metrics
- Open/Closed: New metric types can be added without modification
- Dependency Inversion: Depends on Prometheus client abstractions
"""

import time
import psutil
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, generate_latest
from prometheus_client.core import REGISTRY

from django.db import connection
from django.core.cache import cache
from django.utils import timezone
from django.conf import settings

import structlog

logger = structlog.get_logger(__name__)


class BaseMetricsCollector(ABC):
    """
    Abstract base class for metrics collectors.

    This class defines the interface that all metrics collectors must implement,
    following the Dependency Inversion Principle.
    """

    @abstractmethod
    def collect(self) -> List[str]:
        """
        Collect metrics in Prometheus format.

        Returns:
            List[str]: List of Prometheus-formatted metric lines
        """
        pass


class SystemMetricsCollector(BaseMetricsCollector):
    """
    Collector for system-level metrics.

    This collector follows the Single Responsibility Principle by focusing
    solely on system resource metrics.
    """

    def __init__(self):
        """Initialize system metrics collector."""
        pass

    def collect(self) -> List[str]:
        """
        Collect system metrics.

        Returns:
            List[str]: Prometheus-formatted system metrics
        """
        try:
            metrics = []

            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()

            metrics.extend([
                '# HELP crm_system_cpu_usage_percent System CPU usage percentage',
                '# TYPE crm_system_cpu_usage_percent gauge',
                f'crm_system_cpu_usage_percent {cpu_percent:.2f}',
                '',
                '# HELP crm_system_cpu_count Number of CPU cores',
                '# TYPE crm_system_cpu_count gauge',
                f'crm_system_cpu_count {cpu_count}',
                ''
            ])

            if cpu_freq:
                metrics.extend([
                    '# HELP crm_system_cpu_frequency_mhz CPU frequency in MHz',
                    '# TYPE crm_system_cpu_frequency_mhz gauge',
                    f'crm_system_cpu_frequency_mhz {cpu_freq.current:.2f}',
                    ''
                ])

            # Memory metrics
            memory = psutil.virtual_memory()
            metrics.extend([
                '# HELP crm_system_memory_bytes System memory information',
                '# TYPE crm_system_memory_bytes gauge',
                f'crm_system_memory_bytes{{type="total"}} {memory.total}',
                f'crm_system_memory_bytes{{type="available"}} {memory.available}',
                f'crm_system_memory_bytes{{type="used"}} {memory.used}',
                f'crm_system_memory_bytes{{type="free"}} {memory.free}',
                '',
                '# HELP crm_system_memory_usage_percent System memory usage percentage',
                '# TYPE crm_system_memory_usage_percent gauge',
                f'crm_system_memory_usage_percent {memory.percent:.2f}',
                ''
            ])

            # Disk metrics
            disk = psutil.disk_usage('/')
            metrics.extend([
                '# HELP crm_system_disk_bytes System disk usage information',
                '# TYPE crm_system_disk_bytes gauge',
                f'crm_system_disk_bytes{{type="total",device="/"}} {disk.total}',
                f'crm_system_disk_bytes{{type="used",device="/"}} {disk.used}',
                f'crm_system_disk_bytes{{type="free",device="/"}} {disk.free}',
                '',
                '# HELP crm_system_disk_usage_percent System disk usage percentage',
                '# TYPE crm_system_disk_usage_percent gauge',
                f'crm_system_disk_usage_percent{{device="/"}} {(disk.used/disk.total)*100:.2f}',
                ''
            ])

            # System load (Unix-like systems only)
            try:
                load_avg = psutil.getloadavg()
                metrics.extend([
                    '# HELP crm_system_load_average System load average',
                    '# TYPE crm_system_load_average gauge',
                    f'crm_system_load_average{{period="1m"}} {load_avg[0]:.2f}',
                    f'crm_system_load_average{{period="5m"}} {load_avg[1]:.2f}',
                    f'crm_system_load_average{{period="15m"}} {load_avg[2]:.2f}',
                    ''
                ])
            except AttributeError:
                # Not available on Windows
                pass

            # Network metrics
            try:
                network = psutil.net_io_counters()
                metrics.extend([
                    '# HELP crm_system_network_bytes Network I/O bytes',
                    '# TYPE crm_system_network_bytes counter',
                    f'crm_system_network_bytes{{direction="sent"}} {network.bytes_sent}',
                    f'crm_system_network_bytes{{direction="recv"}} {network.bytes_recv}',
                    '',
                    '# HELP crm_system_network_packets Network I/O packets',
                    '# TYPE crm_system_network_packets counter',
                    f'crm_system_network_packets{{direction="sent"}} {network.packets_sent}',
                    f'crm_system_network_packets{{direction="recv"}} {network.packets_recv}',
                    ''
                ])
            except Exception as e:
                logger.warning(f"Failed to collect network metrics: {e}")

            return metrics

        except Exception as e:
            logger.error(f"System metrics collection failed: {e}")
            return [f"# System metrics collection error: {e}"]


class DatabaseMetricsCollector(BaseMetricsCollector):
    """
    Collector for database performance metrics.

    This collector follows the Single Responsibility Principle by focusing
    solely on database-related metrics.
    """

    def __init__(self):
        """Initialize database metrics collector."""
        pass

    def collect(self) -> List[str]:
        """
        Collect database metrics.

        Returns:
            List[str]: Prometheus-formatted database metrics
        """
        try:
            metrics = []

            # Test database connectivity and performance
            start_time = time.time()
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            query_time = (time.time() - start_time) * 1000

            metrics.extend([
                '# HELP crm_database_query_latency_ms Database query latency in milliseconds',
                '# TYPE crm_database_query_latency_ms gauge',
                f'crm_database_query_latency_ms {query_time:.4f}',
                ''
            ])

            # Connection pool metrics (if available)
            if hasattr(connection, 'pool') and connection.pool:
                pool = connection.pool
                metrics.extend([
                    '# HELP crm_database_connections Database connection pool status',
                    '# TYPE crm_database_connections gauge',
                    f'crm_database_connections{{state="active"}} {getattr(pool, "checkedout", 0)}',
                    f'crm_database_connections{{state="idle"}} {getattr(pool, "checkedin", 0)}',
                    f'crm_database_connections{{state="overflow"}} {getattr(pool, "num_overflow", 0)}',
                    ''
                ])

            # Database size metrics
            try:
                with connection.cursor() as cursor:
                    # Get database size (PostgreSQL specific)
                    cursor.execute("""
                        SELECT pg_database_size(current_database())
                    """)
                    db_size = cursor.fetchone()[0]

                    metrics.extend([
                        '# HELP crm_database_size_bytes Database size in bytes',
                        '# TYPE crm_database_size_bytes gauge',
                        f'crm_database_size_bytes {db_size}',
                        ''
                    ])

                    # Get table sizes
                    cursor.execute("""
                        SELECT schemaname, tablename,
                               pg_total_relation_size(schemaname||'.'||tablename) as size
                        FROM pg_tables
                        WHERE schemaname = 'public'
                        ORDER BY size DESC
                        LIMIT 10
                    """)
                    table_sizes = cursor.fetchall()

                    for schema, table, size in table_sizes:
                        metrics.append(
                            f'crm_database_table_size_bytes{{table="{table}"}} {size}'
                        )

                    metrics.append('')

            except Exception as e:
                logger.warning(f"Failed to collect database size metrics: {e}")

            # Query performance metrics (if debug mode enabled)
            if settings.DEBUG:
                try:
                    from django.db import connection
                    queries = getattr(connection, 'queries', [])
                    if queries:
                        total_time = sum(float(q['time']) for q in queries)
                        query_count = len(queries)

                        metrics.extend([
                            '# HELP crm_database_query_count_total Total number of database queries',
                            '# TYPE crm_database_query_count_total counter',
                            f'crm_database_query_count_total {query_count}',
                            '',
                            '# HELP crm_database_query_time_total Total query time in milliseconds',
                            '# TYPE crm_database_query_time_total counter',
                            f'crm_database_query_time_total {total_time * 1000:.4f}',
                            ''
                        ])

                except Exception as e:
                    logger.warning(f"Failed to collect query performance metrics: {e}")

            return metrics

        except Exception as e:
            logger.error(f"Database metrics collection failed: {e}")
            return [f"# Database metrics collection error: {e}"]


class BusinessMetricsCollector(BaseMetricsCollector):
    """
    Collector for business and application metrics.

    This collector follows the Single Responsibility Principle by focusing
    solely on business-level metrics.
    """

    def __init__(self):
        """Initialize business metrics collector."""
        pass

    def collect(self) -> List[str]:
        """
        Collect business metrics.

        Returns:
            List[str]: Prometheus-formatted business metrics
        """
        try:
            metrics = []

            # User metrics
            try:
                from crm.apps.authentication.models import User

                total_users = User.objects.count()
                active_users_24h = User.objects.filter(
                    last_login__gte=timezone.now() - timedelta(hours=24)
                ).count()
                new_users_24h = User.objects.filter(
                    date_joined__gte=timezone.now() - timedelta(hours=24)
                ).count()

                # User counts by role
                from django.db import models
                user_roles = User.objects.values('role').annotate(count=models.Count('id'))

                metrics.extend([
                    '# HELP crm_business_users_total Total number of users',
                    '# TYPE crm_business_users_total gauge',
                    f'crm_business_users_total {total_users}',
                    '',
                    '# HELP crm_business_users_active_24h Users active in last 24 hours',
                    '# TYPE crm_business_users_active_24h gauge',
                    f'crm_business_users_active_24h {active_users_24h}',
                    '',
                    '# HELP crm_business_users_new_24h New users in last 24 hours',
                    '# TYPE crm_business_users_new_24h gauge',
                    f'crm_business_users_new_24h {new_users_24h}',
                    '',
                    '# HELP crm_business_users_by_role Number of users by role',
                    '# TYPE crm_business_users_by_role gauge',
                ])

                for role_data in user_roles:
                    metrics.append(
                        f'crm_business_users_by_role{{role="{role_data["role"]}"}} {role_data["count"]}'
                    )

                metrics.append('')

            except Exception as e:
                logger.warning(f"Failed to collect user metrics: {e}")

            # Contact metrics
            try:
                from crm.apps.contacts.models import Contact

                total_contacts = Contact.objects.count()
                new_contacts_24h = Contact.objects.filter(
                    created_at__gte=timezone.now() - timedelta(hours=24)
                ).count()

                metrics.extend([
                    '# HELP crm_business_contacts_total Total number of contacts',
                    '# TYPE crm_business_contacts_total gauge',
                    f'crm_business_contacts_total {total_contacts}',
                    '',
                    '# HELP crm_business_contacts_new_24h New contacts in last 24 hours',
                    '# TYPE crm_business_contacts_new_24h gauge',
                    f'crm_business_contacts_new_24h {new_contacts_24h}',
                    ''
                ])

            except Exception as e:
                logger.warning(f"Failed to collect contact metrics: {e}")

            # Deal metrics
            try:
                from crm.apps.contacts.models import Deal

                total_deals = Deal.objects.count()
                new_deals_24h = Deal.objects.filter(
                    created_at__gte=timezone.now() - timedelta(hours=24)
                ).count()
                won_deals_24h = Deal.objects.filter(
                    stage='closed_won',
                    updated_at__gte=timezone.now() - timedelta(hours=24)
                ).count()

                # Deal counts by stage
                from django.db import models
                deals_by_stage = Deal.objects.values('stage').annotate(count=models.Count('id'))

                metrics.extend([
                    '# HELP crm_business_deals_total Total number of deals',
                    '# TYPE crm_business_deals_total gauge',
                    f'crm_business_deals_total {total_deals}',
                    '',
                    '# HELP crm_business_deals_new_24h New deals in last 24 hours',
                    '# TYPE crm_business_deals_new_24h gauge',
                    f'crm_business_deals_new_24h {new_deals_24h}',
                    '',
                    '# HELP crm_business_deals_won_24h Deals won in last 24 hours',
                    '# TYPE crm_business_deals_won_24h gauge',
                    f'crm_business_deals_won_24h {won_deals_24h}',
                    '',
                    '# HELP crm_business_deals_by_stage Number of deals by stage',
                    '# TYPE crm_business_deals_by_stage gauge',
                ])

                for stage_data in deals_by_stage:
                    metrics.append(
                        f'crm_business_deals_by_stage{{stage="{stage_data["stage"]}"}} {stage_data["count"]}'
                    )

                metrics.append('')

            except Exception as e:
                logger.warning(f"Failed to collect deal metrics: {e}")

            # Activity metrics
            try:
                from crm.apps.activities.models import Activity

                total_activities = Activity.objects.count()
                completed_activities_24h = Activity.objects.filter(
                    status='completed',
                    completed_at__gte=timezone.now() - timedelta(hours=24)
                ).count()

                metrics.extend([
                    '# HELP crm_business_activities_total Total number of activities',
                    '# TYPE crm_business_activities_total gauge',
                    f'crm_business_activities_total {total_activities}',
                    '',
                    '# HELP crm_business_activities_completed_24h Activities completed in last 24 hours',
                    '# TYPE crm_business_activities_completed_24h gauge',
                    f'crm_business_activities_completed_24h {completed_activities_24h}',
                    ''
                ])

            except Exception as e:
                logger.warning(f"Failed to collect activity metrics: {e}")

            return metrics

        except Exception as e:
            logger.error(f"Business metrics collection failed: {e}")
            return [f"# Business metrics collection error: {e}"]


class MetricsCollector:
    """
    Main metrics collector that coordinates all metric collection.

    This class follows the Single Responsibility Principle by focusing
    on coordinating metric collection and providing a unified interface.
    """

    def __init__(self):
        """Initialize metrics collector with all sub-collectors."""
        self.collectors = {
            'system': SystemMetricsCollector(),
            'database': DatabaseMetricsCollector(),
            'business': BusinessMetricsCollector(),
        }

        # Initialize Prometheus metrics
        self._initialize_prometheus_metrics()

    def _initialize_prometheus_metrics(self):
        """Initialize Prometheus metrics for runtime collection."""
        # Create a custom registry to avoid conflicts
        self.registry = CollectorRegistry()

        # Request metrics
        self.request_count = Counter(
            'crm_http_requests_total',
            'Total number of HTTP requests',
            ['method', 'endpoint', 'status_code'],
            registry=self.registry
        )

        self.request_duration = Histogram(
            'crm_http_request_duration_seconds',
            'HTTP request duration in seconds',
            ['method', 'endpoint', 'status_code'],
            registry=self.registry
        )

        self.error_count = Counter(
            'crm_http_errors_total',
            'Total number of HTTP errors',
            ['method', 'endpoint', 'status_code'],
            registry=self.registry
        )

        self.exception_count = Counter(
            'crm_exceptions_total',
            'Total number of exceptions',
            ['method', 'endpoint', 'exception_type'],
            registry=self.registry
        )

        # Authentication metrics
        self.auth_attempts = Counter(
            'crm_auth_attempts_total',
            'Total authentication attempts',
            ['result'],  # success, failure
            registry=self.registry
        )

        self.active_users = Gauge(
            'crm_active_users_current',
            'Current number of active users',
            ['role'],
            registry=self.registry
        )

        # Cache metrics
        self.cache_hits = Counter(
            'crm_cache_hits_total',
            'Total cache hits',
            ['cache_alias'],
            registry=self.registry
        )

        self.cache_misses = Counter(
            'crm_cache_misses_total',
            'Total cache misses',
            ['cache_alias'],
            registry=self.registry
        )

    def collect_all(self) -> str:
        """
        Collect all metrics and return Prometheus-formatted output.

        Returns:
            str: Prometheus-formatted metrics
        """
        try:
            # Collect static metrics
            static_metrics = []
            for collector_name, collector in self.collectors.items():
                try:
                    metrics = collector.collect()
                    static_metrics.extend(metrics)
                    static_metrics.append('')  # Add blank line between sections
                except Exception as e:
                    logger.error(f"Failed to collect {collector_name} metrics: {e}")
                    static_metrics.append(f"# {collector_name} metrics collection failed: {e}")

            # Generate runtime metrics
            runtime_metrics = generate_latest(self.registry).decode('utf-8')

            # Combine all metrics
            all_metrics = '\n'.join(static_metrics) + '\n' + runtime_metrics

            return all_metrics

        except Exception as e:
            logger.error(f"Failed to generate metrics: {e}")
            return f"# Metrics generation failed: {e}"

    # Runtime metric update methods

    def record_request_duration(self, method: str, endpoint: str, status_code: int, duration_ms: float):
        """Record HTTP request duration."""
        try:
            duration_seconds = duration_ms / 1000.0
            self.request_duration.labels(
                method=method,
                endpoint=endpoint,
                status_code=str(status_code)
            ).observe(duration_seconds)
        except Exception as e:
            logger.error(f"Failed to record request duration: {e}")

    def increment_request_count(self, method: str, endpoint: str, status_code: int):
        """Increment HTTP request count."""
        try:
            self.request_count.labels(
                method=method,
                endpoint=endpoint,
                status_code=str(status_code)
            ).inc()
        except Exception as e:
            logger.error(f"Failed to increment request count: {e}")

    def increment_error_count(self, method: str, endpoint: str, status_code: int):
        """Increment HTTP error count."""
        try:
            self.error_count.labels(
                method=method,
                endpoint=endpoint,
                status_code=str(status_code)
            ).inc()
        except Exception as e:
            logger.error(f"Failed to increment error count: {e}")

    def increment_slow_request_count(self, method: str, endpoint: str):
        """Increment slow request count."""
        try:
            self.error_count.labels(
                method=method,
                endpoint=endpoint,
                status_code='slow'
            ).inc()
        except Exception as e:
            logger.error(f"Failed to increment slow request count: {e}")

    def record_exception(self, method: str, endpoint: str, exception_type: str, duration_ms: float):
        """Record exception occurrence."""
        try:
            self.exception_count.labels(
                method=method,
                endpoint=endpoint,
                exception_type=exception_type
            ).inc()
        except Exception as e:
            logger.error(f"Failed to record exception: {e}")

    def record_auth_attempt(self, result: str):
        """Record authentication attempt."""
        try:
            self.auth_attempts.labels(result=result).inc()
        except Exception as e:
            logger.error(f"Failed to record auth attempt: {e}")

    def update_active_users(self, role: str, count: int):
        """Update active users count."""
        try:
            self.active_users.labels(role=role).set(count)
        except Exception as e:
            logger.error(f"Failed to update active users: {e}")

    @classmethod
    def initialize_default_metrics(cls):
        """Initialize default metrics on application startup."""
        # This class method can be called from app configuration
        pass