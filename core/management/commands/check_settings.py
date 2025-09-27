"""
Management command to check and validate settings configuration.

This command helps verify that the environment-specific settings are properly configured.
"""

from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
import os


class Command(BaseCommand):
    help = 'Check and validate settings configuration for different environments'

    def add_arguments(self, parser):
        parser.add_argument(
            '--environment',
            type=str,
            choices=['development', 'production', 'test'],
            help='Check settings for specific environment',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed configuration information',
        )

    def handle(self, *args, **options):
        environment = options.get('environment')
        verbose = options.get('verbose', False)
        
        self.stdout.write(
            self.style.SUCCESS('=== Settings Configuration Check ===')
        )
        
        # Check current environment
        current_env = getattr(settings, 'DJANGO_ENVIRONMENT', 'unknown')
        if hasattr(settings, 'DEBUG'):
            if settings.DEBUG:
                detected_env = 'development'
            else:
                detected_env = 'production'
        else:
            detected_env = 'unknown'
        
        self.stdout.write(f'Current environment: {detected_env}')
        self.stdout.write(f'DEBUG mode: {getattr(settings, "DEBUG", "Not set")}')
        
        # Check database configuration
        self.stdout.write('\n=== Database Configuration ===')
        db_config = settings.DATABASES.get('default', {})
        db_engine = db_config.get('ENGINE', 'Not configured')
        
        if 'sqlite3' in db_engine:
            self.stdout.write(self.style.WARNING('Using SQLite database (development)'))
            if verbose:
                self.stdout.write(f'Database file: {db_config.get("NAME", "Not set")}')
        elif 'postgresql' in db_engine:
            self.stdout.write(self.style.SUCCESS('Using PostgreSQL database (production)'))
            if verbose:
                self.stdout.write(f'Database name: {db_config.get("NAME", "Not set")}')
                self.stdout.write(f'Database host: {db_config.get("HOST", "Not set")}')
                self.stdout.write(f'Database port: {db_config.get("PORT", "Not set")}')
        else:
            self.stdout.write(self.style.ERROR(f'Unknown database engine: {db_engine}'))
        
        # Check security settings
        self.stdout.write('\n=== Security Configuration ===')
        secret_key = getattr(settings, 'SECRET_KEY', '')
        if secret_key == 'django-insecure-development-key-change-in-production':
            self.stdout.write(self.style.ERROR('Using default development SECRET_KEY!'))
        elif 'django-insecure' in secret_key:
            self.stdout.write(self.style.WARNING('Using insecure SECRET_KEY'))
        else:
            self.stdout.write(self.style.SUCCESS('SECRET_KEY is properly configured'))
        
        allowed_hosts = getattr(settings, 'ALLOWED_HOSTS', [])
        if not allowed_hosts or allowed_hosts == ['*']:
            self.stdout.write(self.style.WARNING('ALLOWED_HOSTS not properly configured'))
        else:
            self.stdout.write(self.style.SUCCESS(f'ALLOWED_HOSTS: {allowed_hosts}'))
        
        # Check HTTPS settings
        if getattr(settings, 'SECURE_SSL_REDIRECT', False):
            self.stdout.write(self.style.SUCCESS('HTTPS redirect enabled'))
        else:
            self.stdout.write(self.style.WARNING('HTTPS redirect disabled'))
        
        # Check Celery configuration
        self.stdout.write('\n=== Celery Configuration ===')
        celery_broker = getattr(settings, 'CELERY_BROKER_URL', 'Not configured')
        if 'redis' in celery_broker:
            self.stdout.write(self.style.SUCCESS('Celery broker: Redis'))
        elif 'rabbitmq' in celery_broker:
            self.stdout.write(self.style.SUCCESS('Celery broker: RabbitMQ'))
        else:
            self.stdout.write(self.style.WARNING(f'Celery broker: {celery_broker}'))
        
        celery_eager = getattr(settings, 'CELERY_TASK_ALWAYS_EAGER', False)
        if celery_eager:
            self.stdout.write(self.style.WARNING('Celery tasks running synchronously (development)'))
        else:
            self.stdout.write(self.style.SUCCESS('Celery tasks running asynchronously'))
        
        # Check logging configuration
        self.stdout.write('\n=== Logging Configuration ===')
        logging_config = getattr(settings, 'LOGGING', {})
        if logging_config:
            handlers = logging_config.get('handlers', {})
            if 'file' in handlers:
                self.stdout.write(self.style.SUCCESS('File logging enabled'))
            if 'console' in handlers:
                self.stdout.write(self.style.SUCCESS('Console logging enabled'))
            if 'syslog' in handlers:
                self.stdout.write(self.style.SUCCESS('Syslog logging enabled'))
        else:
            self.stdout.write(self.style.WARNING('No logging configuration found'))
        
        # Check email configuration
        self.stdout.write('\n=== Email Configuration ===')
        email_backend = getattr(settings, 'EMAIL_BACKEND', 'Not configured')
        if 'console' in email_backend:
            self.stdout.write(self.style.WARNING('Using console email backend (development)'))
        elif 'smtp' in email_backend:
            self.stdout.write(self.style.SUCCESS('Using SMTP email backend'))
            if verbose:
                self.stdout.write(f'Email host: {getattr(settings, "EMAIL_HOST", "Not set")}')
                self.stdout.write(f'Email port: {getattr(settings, "EMAIL_PORT", "Not set")}')
        else:
            self.stdout.write(self.style.WARNING(f'Email backend: {email_backend}'))
        
        # Check cache configuration
        self.stdout.write('\n=== Cache Configuration ===')
        cache_config = settings.CACHES.get('default', {})
        cache_backend = cache_config.get('BACKEND', 'Not configured')
        if 'redis' in cache_backend:
            self.stdout.write(self.style.SUCCESS('Using Redis cache'))
        elif 'dummy' in cache_backend:
            self.stdout.write(self.style.WARNING('Using dummy cache (development)'))
        else:
            self.stdout.write(self.style.WARNING(f'Cache backend: {cache_backend}'))
        
        # Check API testing configuration
        self.stdout.write('\n=== API Testing Configuration ===')
        public_api_testing = getattr(settings, 'ENABLE_PUBLIC_API_TESTING', False)
        if public_api_testing:
            self.stdout.write(self.style.WARNING('Public API testing is ENABLED (development only)'))
        else:
            self.stdout.write(self.style.SUCCESS('Public API testing is disabled'))
        
        # Environment-specific checks
        if environment:
            self.stdout.write(f'\n=== {environment.upper()} Environment Specific Checks ===')
            
            if environment == 'production':
                self._check_production_settings()
            elif environment == 'development':
                self._check_development_settings()
            elif environment == 'test':
                self._check_test_settings()
        
        self.stdout.write('\n=== Configuration Check Complete ===')

    def _check_production_settings(self):
        """Check production-specific settings"""
        issues = []
        
        if getattr(settings, 'DEBUG', True):
            issues.append('DEBUG should be False in production')
        
        if getattr(settings, 'ENABLE_PUBLIC_API_TESTING', False):
            issues.append('ENABLE_PUBLIC_API_TESTING should be False in production')
        
        if not getattr(settings, 'SECURE_SSL_REDIRECT', False):
            issues.append('SECURE_SSL_REDIRECT should be True in production')
        
        secret_key = getattr(settings, 'SECRET_KEY', '')
        if 'django-insecure' in secret_key:
            issues.append('SECRET_KEY should not contain "django-insecure" in production')
        
        if issues:
            self.stdout.write(self.style.ERROR('Production configuration issues found:'))
            for issue in issues:
                self.stdout.write(f'  - {issue}')
        else:
            self.stdout.write(self.style.SUCCESS('Production configuration looks good'))

    def _check_development_settings(self):
        """Check development-specific settings"""
        issues = []
        
        if not getattr(settings, 'DEBUG', False):
            issues.append('DEBUG should be True in development')
        
        db_config = settings.DATABASES.get('default', {})
        if 'postgresql' in db_config.get('ENGINE', ''):
            self.stdout.write(self.style.WARNING('Using PostgreSQL in development (consider SQLite for faster development)'))
        
        if issues:
            self.stdout.write(self.style.WARNING('Development configuration notes:'))
            for issue in issues:
                self.stdout.write(f'  - {issue}')
        else:
            self.stdout.write(self.style.SUCCESS('Development configuration looks good'))

    def _check_test_settings(self):
        """Check test-specific settings"""
        issues = []
        
        db_config = settings.DATABASES.get('default', {})
        if ':memory:' not in db_config.get('NAME', ''):
            issues.append('Consider using in-memory SQLite for faster tests')
        
        if not getattr(settings, 'CELERY_TASK_ALWAYS_EAGER', False):
            issues.append('CELERY_TASK_ALWAYS_EAGER should be True for tests')
        
        if issues:
            self.stdout.write(self.style.WARNING('Test configuration suggestions:'))
            for issue in issues:
                self.stdout.write(f'  - {issue}')
        else:
            self.stdout.write(self.style.SUCCESS('Test configuration looks good'))