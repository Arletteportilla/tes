"""
Tests for Celery configuration and tasks.

This module tests the Celery setup, task execution, and periodic task scheduling.
"""

import pytest
from django.test import TestCase, override_settings
from django.utils import timezone
from celery import current_app
from unittest.mock import patch, MagicMock
import tempfile
import os

from core.tasks import (
    system_health_check,
    cleanup_old_logs,
    backup_database,
    test_email_configuration
)


class CeleryConfigurationTest(TestCase):
    """Test Celery configuration and basic functionality"""
    
    def test_celery_app_configuration(self):
        """Test that Celery app is properly configured"""
        # Check that Celery app exists
        self.assertIsNotNone(current_app)
        self.assertEqual(current_app.main, 'sistema_polinizacion')
        
        # Check basic configuration
        self.assertEqual(current_app.conf.task_serializer, 'json')
        self.assertEqual(current_app.conf.accept_content, ['json'])
        self.assertEqual(current_app.conf.result_serializer, 'json')
    
    def test_celery_beat_schedule(self):
        """Test that beat schedule is properly configured"""
        beat_schedule = current_app.conf.beat_schedule
        
        # Check that scheduled tasks exist
        expected_tasks = [
            'process-alerts-hourly',
            'generate-weekly-alerts',
            'generate-preventive-alerts',
            'generate-frequent-alerts',
            'cleanup-old-alerts',
            'system-health-check'
        ]
        
        for task_name in expected_tasks:
            self.assertIn(task_name, beat_schedule)
            self.assertIn('task', beat_schedule[task_name])
            self.assertIn('schedule', beat_schedule[task_name])
    
    def test_celery_queues_configuration(self):
        """Test that queues are properly configured"""
        task_routes = current_app.conf.task_routes
        
        # Check task routing
        self.assertIn('alerts.tasks.*', task_routes)
        self.assertIn('reports.tasks.*', task_routes)
        self.assertIn('core.tasks.*', task_routes)
        
        # Check queue configuration
        self.assertEqual(task_routes['alerts.tasks.*']['queue'], 'alerts')
        self.assertEqual(task_routes['reports.tasks.*']['queue'], 'reports')
        self.assertEqual(task_routes['core.tasks.*']['queue'], 'system')


class CeleryTasksTest(TestCase):
    """Test Celery tasks execution"""
    
    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_debug_task(self):
        """Test debug task execution"""
        from sistema_polinizacion.celery import debug_task
        
        result = debug_task.delay()
        self.assertTrue(result.successful())
        self.assertIn('Debug task executed successfully', result.result)
    
    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_test_task_with_retry_success(self):
        """Test retry task with successful execution"""
        from sistema_polinizacion.celery import test_task_with_retry
        
        result = test_task_with_retry.delay(fail=False)
        self.assertTrue(result.successful())
        self.assertEqual(result.result, "Task completed successfully")
    
    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_celery_health_check(self):
        """Test Celery health check task"""
        from sistema_polinizacion.celery import celery_health_check
        
        result = celery_health_check.delay()
        self.assertTrue(result.successful())
        
        health_data = result.result
        self.assertIn('status', health_data)
        self.assertIn('timestamp', health_data)
        self.assertEqual(health_data['status'], 'healthy')


class SystemHealthCheckTest(TestCase):
    """Test system health check task"""
    
    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @patch('core.tasks.psutil')
    @patch('django.db.connection')
    def test_system_health_check_healthy(self, mock_connection, mock_psutil):
        """Test system health check with healthy system"""
        # Mock database connection
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        
        # Mock system resources
        mock_disk = MagicMock()
        mock_disk.total = 1000000000  # 1GB
        mock_disk.used = 500000000    # 500MB (50%)
        mock_psutil.disk_usage.return_value = mock_disk
        
        mock_memory = MagicMock()
        mock_memory.percent = 60.0
        mock_psutil.virtual_memory.return_value = mock_memory
        
        result = system_health_check.delay()
        self.assertTrue(result.successful())
        
        health_status = result.result
        self.assertEqual(health_status['status'], 'healthy')
        self.assertEqual(health_status['checks']['database'], 'healthy')
        self.assertEqual(health_status['checks']['disk_space'], 'healthy')
        self.assertEqual(health_status['checks']['memory'], 'healthy')
    
    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @patch('core.tasks.psutil')
    @patch('django.db.connection')
    def test_system_health_check_critical(self, mock_connection, mock_psutil):
        """Test system health check with critical issues"""
        # Mock database connection failure
        mock_connection.cursor.side_effect = Exception("Database connection failed")
        
        # Mock critical disk usage
        mock_disk = MagicMock()
        mock_disk.total = 1000000000  # 1GB
        mock_disk.used = 950000000    # 950MB (95%)
        mock_psutil.disk_usage.return_value = mock_disk
        
        # Mock critical memory usage
        mock_memory = MagicMock()
        mock_memory.percent = 95.0
        mock_psutil.virtual_memory.return_value = mock_memory
        
        result = system_health_check.delay()
        self.assertTrue(result.successful())
        
        health_status = result.result
        self.assertEqual(health_status['status'], 'unhealthy')
        self.assertEqual(health_status['checks']['database'], 'error')
        self.assertEqual(health_status['checks']['disk_space'], 'critical')
        self.assertEqual(health_status['checks']['memory'], 'critical')
        self.assertTrue(len(health_status['errors']) > 0)


class LogCleanupTest(TestCase):
    """Test log cleanup task"""
    
    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_cleanup_old_logs(self):
        """Test log cleanup functionality"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test log files
            old_log = os.path.join(temp_dir, 'old.log')
            new_log = os.path.join(temp_dir, 'new.log')
            
            # Create old log file (modify timestamp)
            with open(old_log, 'w') as f:
                f.write('old log content')
            
            # Create new log file
            with open(new_log, 'w') as f:
                f.write('new log content')
            
            # Set old timestamp for old log
            old_time = timezone.now() - timezone.timedelta(days=35)
            old_timestamp = old_time.timestamp()
            os.utime(old_log, (old_timestamp, old_timestamp))
            
            # Override settings to use temp directory
            with override_settings(LOG_DIR=temp_dir, LOG_RETENTION_DAYS=30):
                result = cleanup_old_logs.delay()
                self.assertTrue(result.successful())
                
                cleanup_result = result.result
                self.assertEqual(cleanup_result['status'], 'completed')
                self.assertIn('old.log', cleanup_result['cleaned_files'])
                
                # Check that old file was removed and new file remains
                self.assertFalse(os.path.exists(old_log))
                self.assertTrue(os.path.exists(new_log))


class DatabaseBackupTest(TestCase):
    """Test database backup task"""
    
    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @patch('core.tasks.call_command')
    def test_backup_database(self, mock_call_command):
        """Test database backup functionality"""
        with tempfile.TemporaryDirectory() as temp_dir:
            with override_settings(BACKUP_DIR=temp_dir):
                result = backup_database.delay()
                self.assertTrue(result.successful())
                
                backup_result = result.result
                self.assertEqual(backup_result['status'], 'completed')
                self.assertIn('backup_file', backup_result)
                self.assertIn('backup_size_bytes', backup_result)
                
                # Check that call_command was called with correct arguments
                mock_call_command.assert_called_once()
                args, kwargs = mock_call_command.call_args
                self.assertEqual(args[0], 'dumpdata')


class EmailConfigurationTest(TestCase):
    """Test email configuration task"""
    
    @override_settings(
        CELERY_TASK_ALWAYS_EAGER=True,
        ADMIN_EMAIL='admin@test.com',
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'
    )
    def test_email_configuration_test(self):
        """Test email configuration test task"""
        result = test_email_configuration.delay()
        self.assertTrue(result.successful())
        
        email_result = result.result
        self.assertEqual(email_result['status'], 'success')
        self.assertEqual(email_result['recipient'], 'admin@test.com')
    
    @override_settings(
        CELERY_TASK_ALWAYS_EAGER=True,
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'
    )
    def test_email_configuration_test_no_admin(self):
        """Test email configuration test task without admin email"""
        # Remove ADMIN_EMAIL setting
        if hasattr(self.settings, 'ADMIN_EMAIL'):
            delattr(self.settings, 'ADMIN_EMAIL')
        
        result = test_email_configuration.delay()
        self.assertTrue(result.successful())
        
        email_result = result.result
        self.assertEqual(email_result['status'], 'skipped')
        self.assertEqual(email_result['reason'], 'ADMIN_EMAIL not configured')


@pytest.mark.integration
class CeleryIntegrationTest(TestCase):
    """Integration tests for Celery with other system components"""
    
    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_alert_task_integration(self):
        """Test integration between Celery and alert system"""
        # This test would require the alerts app to be fully implemented
        # For now, we'll just test that the task can be imported
        try:
            from alerts.tasks import process_pending_alerts
            self.assertTrue(callable(process_pending_alerts))
        except ImportError:
            self.skipTest("Alerts tasks not yet implemented")
    
    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_report_task_integration(self):
        """Test integration between Celery and report system"""
        # This test would require the reports app to be fully implemented
        # For now, we'll just test that the task can be imported
        try:
            from reports.tasks import generate_report
            self.assertTrue(callable(generate_report))
        except ImportError:
            self.skipTest("Report tasks not yet implemented")