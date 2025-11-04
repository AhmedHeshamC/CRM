"""
Celery Configuration for CRM Backend
Following SOLID principles and enterprise best practices
"""

import os
from celery import Celery
from django.conf import settings
from celery.schedules import crontab
import environ

# Set default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')

# Initialize environment
env = environ.Env()

# Create Celery app
app = Celery('crm')

# Load configuration from Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks from all installed apps
app.autodiscover_tasks()

# Configure task routing
app.conf.task_routes = {
    'crm.apps.tasks.email.*': {'queue': 'email'},
    'crm.apps.tasks.exports.*': {'queue': 'exports'},
    'crm.apps.tasks.reports.*': {'queue': 'reports'},
    'crm.apps.tasks.notifications.*': {'queue': 'notifications'},
    'crm.apps.tasks.workflows.*': {'queue': 'workflows'},
}

# Configure task priorities
app.conf.task_default_priority = 5
app.conf.task_priority_max = 10
app.conf.task_priority_min = 1

# Configure worker settings
app.conf.worker_prefetch_multiplier = 1
app.conf.task_acks_late = True
app.conf.worker_disable_rate_limits = False

# Configure result backend
app.conf.result_backend_transport_options = {
    'master_name': 'mymaster',
    'visibility_timeout': 3600,
    'retry_policy': {
        'timeout': 5.0
    }
}

# Configure task serialization with security
app.conf.task_serializer = 'json'
app.conf.result_serializer = 'json'
app.conf.accept_content = ['json']
app.conf.result_expires = 3600  # 1 hour
app.conf.result_compression = 'gzip'

# Configure timezone
app.conf.enable_utc = True
app.conf.timezone = 'UTC'

# Configure beat scheduler
app.conf.beat_scheduler = 'django_celery_beat.schedulers:DatabaseScheduler'

# Configure task tracking
app.conf.task_track_started = True
app.conf.task_send_sent_event = True
app.conf.worker_send_task_events = True
app.conf.task_send_fail_event = True
app.conf.task_send_retry_event = True

# Configure retry policies
app.conf.task_default_retry_delay = 60  # 1 minute
app.conf.task_max_retries = 3
app.conf.task_default_retry_policy = {
    'max_retries': 3,
    'interval_start': 0,
    'interval_step': 0.2,
    'interval_max': 200,
    'jitter': True,
}

# Configure soft and hard time limits
app.conf.task_soft_time_limit = 300  # 5 minutes
app.conf.task_time_limit = 600  # 10 minutes

# Configure specific task time limits
app.conf.task_soft_time_limit = {
    'crm.apps.tasks.exports.data_export': 1800,  # 30 minutes for exports
    'crm.apps.tasks.reports.generate_report': 900,  # 15 minutes for reports
    'crm.apps.tasks.email.send_email_notification': 60,  # 1 minute for emails
}

app.conf.task_time_limit = {
    'crm.apps.tasks.exports.data_export': 3600,  # 1 hour for exports
    'crm.apps.tasks.reports.generate_report': 1800,  # 30 minutes for reports
    'crm.apps.tasks.email.send_email_notification': 120,  # 2 minutes for emails
}

# Configure queues
app.conf.task_routes.update({
    'crm.apps.tasks.exports.data_export': {
        'queue': 'exports',
        'routing_key': 'exports',
        'priority': 2,  # Lower priority for long-running tasks
    },
    'crm.apps.tasks.reports.generate_report': {
        'queue': 'reports',
        'routing_key': 'reports',
        'priority': 3,
    },
    'crm.apps.tasks.email.send_email_notification': {
        'queue': 'email',
        'routing_key': 'email',
        'priority': 8,  # High priority for emails
    },
    'crm.apps.tasks.notifications.send_activity_reminder': {
        'queue': 'notifications',
        'routing_key': 'notifications',
        'priority': 7,
    },
    'crm.apps.tasks.workflows.process_deal_followup': {
        'queue': 'workflows',
        'routing_key': 'workflows',
        'priority': 6,
    },
})

# Configure queue settings
app.conf.task_create_missing_queues = True
app.conf.task_default_queue = 'default'
app.conf.task_queues = {
    'default': {
        'exchange': 'default',
        'routing_key': 'default',
        'durable': True,
    },
    'email': {
        'exchange': 'email',
        'routing_key': 'email',
        'durable': True,
    },
    'exports': {
        'exchange': 'exports',
        'routing_key': 'exports',
        'durable': True,
    },
    'reports': {
        'exchange': 'reports',
        'routing_key': 'reports',
        'durable': True,
    },
    'notifications': {
        'exchange': 'notifications',
        'routing_key': 'notifications',
        'durable': True,
    },
    'workflows': {
        'exchange': 'workflows',
        'routing_key': 'workflows',
        'durable': True,
    },
}

# Configure monitoring and security
app.conf.broker_transport_options = {
    'visibility_timeout': 3600,
    'retry_policy': {
        'timeout': 5.0
    },
    'max_connections': 10,
    'connection_pool_kwargs': {
        'max_connections': 10,
        'retry_on_timeout': True,
    },
}

# Configure flower authentication (if enabled)
if env.bool('ENABLE_FLOWER_AUTH', default=True):
    app.conf.flower_basic_auth = env.list('FLOWER_BASIC_AUTH', default=['admin:admin123'])
    app.conf.flower_port = env.int('FLOWER_PORT', default=5555)
    app.conf.flower_url_prefix = env('FLOWER_URL_PREFIX', default='')

# Configure security settings
app.conf.worker_hijack_root_logger = False
app.conf.worker_log_color = False
app.conf.worker_log_format = '[%(asctime)s: %(levelname)s/%(processName)s] %(message)s'
app.conf.worker_task_log_format = '[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s'

# Configure performance optimizations
app.conf.broker_connection_retry_on_startup = True
app.conf.broker_connection_max_retries = 10
app.conf.broker_connection_retry_delay = 1.0

# Configure events for monitoring
app.conf.worker_send_task_events = True
app.conf.task_send_sent_event = True

# Test task for connectivity
@app.task(bind=True, name='test_connection')
def test_connection(self):
    """Test task to verify Celery connectivity"""
    return f"Celery is working\! Task ID: {self.request.id}"


# Health check task
@app.task(bind=True, name='health_check')
def health_check(self):
    """Health check task for monitoring Celery workers"""
    return {
        'status': 'healthy',
        'worker_id': self.request.id,
        'timestamp': self.request.timestamp,
    }


if __name__ == '__main__':
    app.start()
