"""
Celery configuration for Sistema de Polinización y Germinación project.

This module configures Celery for handling asynchronous tasks including:
- Automatic alert generation
- Periodic task scheduling
- Email notifications
- Report generation
"""

import os
from celery import Celery
from celery.schedules import crontab
from django.conf import settings

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sistema_polinizacion.settings')

app = Celery('sistema_polinizacion')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Celery Beat Schedule for Periodic Tasks
app.conf.beat_schedule = {
    # Process alerts every hour
    'process-alerts-hourly': {
        'task': 'alerts.tasks.process_pending_alerts',
        'schedule': crontab(minute=0),  # Every hour at minute 0
        'options': {
            'expires': 3600,  # Task expires after 1 hour
        }
    },
    
    # Generate weekly alerts every Monday at 8:00 AM
    'generate-weekly-alerts': {
        'task': 'alerts.tasks.generate_weekly_alerts',
        'schedule': crontab(hour=8, minute=0, day_of_week=1),  # Monday 8:00 AM
        'options': {
            'expires': 86400,  # Task expires after 24 hours
        }
    },
    
    # Generate preventive alerts daily at 9:00 AM
    'generate-preventive-alerts': {
        'task': 'alerts.tasks.generate_preventive_alerts',
        'schedule': crontab(hour=9, minute=0),  # Daily 9:00 AM
        'options': {
            'expires': 86400,  # Task expires after 24 hours
        }
    },
    
    # Generate frequent alerts (daily reminders) at 10:00 AM
    'generate-frequent-alerts': {
        'task': 'alerts.tasks.generate_frequent_alerts',
        'schedule': crontab(hour=10, minute=0),  # Daily 10:00 AM
        'options': {
            'expires': 86400,  # Task expires after 24 hours
        }
    },
    
    # Clean up old alerts weekly on Sunday at 2:00 AM
    'cleanup-old-alerts': {
        'task': 'alerts.tasks.cleanup_old_alerts',
        'schedule': crontab(hour=2, minute=0, day_of_week=0),  # Sunday 2:00 AM
        'options': {
            'expires': 86400,  # Task expires after 24 hours
        }
    },
    
    # Generate system health report daily at 6:00 AM
    'system-health-check': {
        'task': 'core.tasks.system_health_check',
        'schedule': crontab(hour=6, minute=0),  # Daily 6:00 AM
        'options': {
            'expires': 3600,  # Task expires after 1 hour
        }
    },
}

# Celery Configuration
app.conf.update(
    # Task routing
    task_routes={
        'alerts.tasks.*': {'queue': 'alerts'},
        'reports.tasks.*': {'queue': 'reports'},
        'core.tasks.*': {'queue': 'system'},
    },
    
    # Task serialization
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    
    # Task execution
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    
    # Worker configuration
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    
    # Result backend
    result_expires=3600,  # 1 hour
    result_backend_transport_options={
        'master_name': 'mymaster',
        'visibility_timeout': 3600,
    },
    
    # Timezone
    timezone=getattr(settings, 'TIME_ZONE', 'America/Bogota'),
    enable_utc=True,
    
    # Monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,
    
    # Error handling
    task_reject_on_worker_lost=True,
    task_acks_late=True,
)

# Task priority configuration
app.conf.task_default_priority = 5
app.conf.worker_disable_rate_limits = False

# Queue configuration
app.conf.task_default_queue = 'default'
app.conf.task_queues = {
    'default': {
        'exchange': 'default',
        'routing_key': 'default',
    },
    'alerts': {
        'exchange': 'alerts',
        'routing_key': 'alerts',
    },
    'reports': {
        'exchange': 'reports',
        'routing_key': 'reports',
    },
    'system': {
        'exchange': 'system',
        'routing_key': 'system',
    },
}

@app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery configuration"""
    print(f'Request: {self.request!r}')
    return f'Debug task executed successfully at {self.request.id}'

@app.task(bind=True, max_retries=3)
def test_task_with_retry(self, fail=False):
    """Test task with retry mechanism"""
    if fail:
        try:
            raise Exception("Intentional failure for testing")
        except Exception as exc:
            # Retry after 60 seconds
            raise self.retry(exc=exc, countdown=60)
    return "Task completed successfully"

# Signal handlers for monitoring
from celery.signals import task_prerun, task_postrun, task_failure

@task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **kwds):
    """Handler called before task execution"""
    print(f'Task {task.name} [{task_id}] is about to run')

@task_postrun.connect
def task_postrun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, retval=None, state=None, **kwds):
    """Handler called after task execution"""
    print(f'Task {task.name} [{task_id}] completed with state: {state}')

@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, traceback=None, einfo=None, **kwds):
    """Handler called when task fails"""
    print(f'Task {sender.name} [{task_id}] failed: {exception}')

# Health check task
@app.task
def celery_health_check():
    """Health check task to verify Celery is working"""
    return {
        'status': 'healthy',
        'timestamp': app.now(),
        'worker_id': app.control.inspect().active(),
    }