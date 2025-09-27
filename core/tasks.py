"""
Core Celery tasks for Sistema de Polinización y Germinación.

This module contains system-level tasks for monitoring, maintenance, and health checks.
"""

from celery import shared_task
from django.core.management import call_command
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
import logging
import psutil
import os

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def system_health_check(self):
    """
    Perform system health check and send alerts if issues are detected.
    
    Checks:
    - Database connectivity
    - Disk space
    - Memory usage
    - Celery worker status
    """
    try:
        health_status = {
            'timestamp': timezone.now().isoformat(),
            'status': 'healthy',
            'checks': {},
            'warnings': [],
            'errors': []
        }
        
        # Check database connectivity
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                health_status['checks']['database'] = 'healthy'
        except Exception as e:
            health_status['checks']['database'] = 'error'
            health_status['errors'].append(f'Database connectivity error: {str(e)}')
            health_status['status'] = 'unhealthy'
        
        # Check disk space
        try:
            disk_usage = psutil.disk_usage('/')
            disk_percent = (disk_usage.used / disk_usage.total) * 100
            
            if disk_percent > 90:
                health_status['checks']['disk_space'] = 'critical'
                health_status['errors'].append(f'Disk space critical: {disk_percent:.1f}% used')
                health_status['status'] = 'unhealthy'
            elif disk_percent > 80:
                health_status['checks']['disk_space'] = 'warning'
                health_status['warnings'].append(f'Disk space warning: {disk_percent:.1f}% used')
            else:
                health_status['checks']['disk_space'] = 'healthy'
                
            health_status['checks']['disk_usage_percent'] = round(disk_percent, 1)
        except Exception as e:
            health_status['checks']['disk_space'] = 'error'
            health_status['warnings'].append(f'Could not check disk space: {str(e)}')
        
        # Check memory usage
        try:
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            if memory_percent > 90:
                health_status['checks']['memory'] = 'critical'
                health_status['errors'].append(f'Memory usage critical: {memory_percent:.1f}%')
                health_status['status'] = 'unhealthy'
            elif memory_percent > 80:
                health_status['checks']['memory'] = 'warning'
                health_status['warnings'].append(f'Memory usage warning: {memory_percent:.1f}%')
            else:
                health_status['checks']['memory'] = 'healthy'
                
            health_status['checks']['memory_usage_percent'] = round(memory_percent, 1)
        except Exception as e:
            health_status['checks']['memory'] = 'error'
            health_status['warnings'].append(f'Could not check memory usage: {str(e)}')
        
        # Check Celery worker status
        try:
            from celery import current_app
            inspect = current_app.control.inspect()
            active_workers = inspect.active()
            
            if active_workers:
                health_status['checks']['celery_workers'] = 'healthy'
                health_status['checks']['active_workers'] = len(active_workers)
            else:
                health_status['checks']['celery_workers'] = 'warning'
                health_status['warnings'].append('No active Celery workers detected')
        except Exception as e:
            health_status['checks']['celery_workers'] = 'error'
            health_status['warnings'].append(f'Could not check Celery workers: {str(e)}')
        
        # Log health status
        if health_status['status'] == 'unhealthy':
            logger.error(f'System health check failed: {health_status}')
        elif health_status['warnings']:
            logger.warning(f'System health check warnings: {health_status}')
        else:
            logger.info(f'System health check passed: {health_status}')
        
        # Send email alert if critical issues detected
        if health_status['errors'] and hasattr(settings, 'ADMIN_EMAIL'):
            send_health_alert_email(health_status)
        
        return health_status
        
    except Exception as exc:
        logger.error(f'System health check task failed: {str(exc)}')
        raise self.retry(exc=exc, countdown=300, max_retries=3)


@shared_task
def cleanup_old_logs():
    """
    Clean up old log files to prevent disk space issues.
    
    Removes log files older than the configured retention period.
    """
    try:
        log_dir = getattr(settings, 'LOG_DIR', os.path.join(settings.BASE_DIR, 'logs'))
        retention_days = getattr(settings, 'LOG_RETENTION_DAYS', 30)
        
        if not os.path.exists(log_dir):
            logger.warning(f'Log directory does not exist: {log_dir}')
            return {'status': 'skipped', 'reason': 'log directory not found'}
        
        cutoff_time = timezone.now() - timezone.timedelta(days=retention_days)
        cleaned_files = []
        
        for filename in os.listdir(log_dir):
            file_path = os.path.join(log_dir, filename)
            
            if os.path.isfile(file_path) and filename.endswith('.log'):
                file_mtime = timezone.datetime.fromtimestamp(
                    os.path.getmtime(file_path), 
                    tz=timezone.get_current_timezone()
                )
                
                if file_mtime < cutoff_time:
                    try:
                        os.remove(file_path)
                        cleaned_files.append(filename)
                        logger.info(f'Removed old log file: {filename}')
                    except Exception as e:
                        logger.error(f'Failed to remove log file {filename}: {str(e)}')
        
        result = {
            'status': 'completed',
            'cleaned_files': cleaned_files,
            'retention_days': retention_days,
            'timestamp': timezone.now().isoformat()
        }
        
        logger.info(f'Log cleanup completed: {len(cleaned_files)} files removed')
        return result
        
    except Exception as e:
        logger.error(f'Log cleanup task failed: {str(e)}')
        raise


@shared_task
def backup_database():
    """
    Create a database backup using Django's dumpdata command.
    
    This task creates a JSON backup of the database for disaster recovery.
    """
    try:
        backup_dir = getattr(settings, 'BACKUP_DIR', os.path.join(settings.BASE_DIR, 'backups'))
        
        # Create backup directory if it doesn't exist
        os.makedirs(backup_dir, exist_ok=True)
        
        # Generate backup filename with timestamp
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f'database_backup_{timestamp}.json'
        backup_path = os.path.join(backup_dir, backup_filename)
        
        # Create database backup
        with open(backup_path, 'w') as backup_file:
            call_command('dumpdata', 
                        '--natural-foreign', 
                        '--natural-primary',
                        '--exclude=contenttypes',
                        '--exclude=auth.permission',
                        '--exclude=sessions.session',
                        '--exclude=admin.logentry',
                        stdout=backup_file)
        
        # Get backup file size
        backup_size = os.path.getsize(backup_path)
        
        result = {
            'status': 'completed',
            'backup_file': backup_filename,
            'backup_path': backup_path,
            'backup_size_bytes': backup_size,
            'backup_size_mb': round(backup_size / (1024 * 1024), 2),
            'timestamp': timezone.now().isoformat()
        }
        
        logger.info(f'Database backup created: {backup_filename} ({result["backup_size_mb"]} MB)')
        
        # Clean up old backups
        cleanup_old_backups(backup_dir)
        
        return result
        
    except Exception as e:
        logger.error(f'Database backup task failed: {str(e)}')
        raise


def cleanup_old_backups(backup_dir, retention_days=7):
    """
    Clean up old backup files to save disk space.
    
    Args:
        backup_dir (str): Directory containing backup files
        retention_days (int): Number of days to retain backups
    """
    try:
        cutoff_time = timezone.now() - timezone.timedelta(days=retention_days)
        cleaned_backups = []
        
        for filename in os.listdir(backup_dir):
            if filename.startswith('database_backup_') and filename.endswith('.json'):
                file_path = os.path.join(backup_dir, filename)
                file_mtime = timezone.datetime.fromtimestamp(
                    os.path.getmtime(file_path),
                    tz=timezone.get_current_timezone()
                )
                
                if file_mtime < cutoff_time:
                    try:
                        os.remove(file_path)
                        cleaned_backups.append(filename)
                        logger.info(f'Removed old backup: {filename}')
                    except Exception as e:
                        logger.error(f'Failed to remove backup {filename}: {str(e)}')
        
        if cleaned_backups:
            logger.info(f'Cleaned up {len(cleaned_backups)} old backup files')
            
    except Exception as e:
        logger.error(f'Backup cleanup failed: {str(e)}')


def send_health_alert_email(health_status):
    """
    Send email alert when system health issues are detected.
    
    Args:
        health_status (dict): Health check results
    """
    try:
        subject = f'[ALERT] Sistema Polinización - Health Check Failed'
        
        message = f"""
Sistema de Polinización y Germinación - Health Check Alert

Status: {health_status['status'].upper()}
Timestamp: {health_status['timestamp']}

ERRORS:
{chr(10).join(f'- {error}' for error in health_status['errors'])}

WARNINGS:
{chr(10).join(f'- {warning}' for warning in health_status['warnings'])}

SYSTEM CHECKS:
{chr(10).join(f'- {check}: {status}' for check, status in health_status['checks'].items())}

Please investigate and resolve these issues immediately.
        """
        
        admin_email = getattr(settings, 'ADMIN_EMAIL', None)
        if admin_email:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[admin_email],
                fail_silently=False
            )
            logger.info(f'Health alert email sent to {admin_email}')
        
    except Exception as e:
        logger.error(f'Failed to send health alert email: {str(e)}')


@shared_task
def test_email_configuration():
    """
    Test email configuration by sending a test email.
    
    This task helps verify that email settings are properly configured.
    """
    try:
        admin_email = getattr(settings, 'ADMIN_EMAIL', None)
        if not admin_email:
            return {'status': 'skipped', 'reason': 'ADMIN_EMAIL not configured'}
        
        subject = 'Test Email - Sistema Polinización'
        message = f"""
This is a test email from Sistema de Polinización y Germinación.

If you receive this email, the email configuration is working correctly.

Timestamp: {timezone.now().isoformat()}
Environment: {getattr(settings, 'DJANGO_ENVIRONMENT', 'unknown')}
        """
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[admin_email],
            fail_silently=False
        )
        
        result = {
            'status': 'success',
            'recipient': admin_email,
            'timestamp': timezone.now().isoformat()
        }
        
        logger.info(f'Test email sent successfully to {admin_email}')
        return result
        
    except Exception as e:
        logger.error(f'Test email failed: {str(e)}')
        raise