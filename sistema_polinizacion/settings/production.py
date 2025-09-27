"""
Production settings for Sistema de Polinización y Germinación project.

This file contains settings specific to the production environment.
Security and performance optimizations are applied here.
"""

from .base import *
from decouple import config
import os

# Security Settings for Production
SECRET_KEY = config('SECRET_KEY')  # Required in production
DEBUG = False
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='').split(',')

# Database Configuration - PostgreSQL for production
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
        'OPTIONS': {
            'sslmode': config('DB_SSLMODE', default='prefer'),
        },
        'CONN_MAX_AGE': config('DB_CONN_MAX_AGE', default=60, cast=int),
    }
}

# CORS Configuration for production (restrictive)
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS', default='').split(',')

# Public API Testing is DISABLED in production
ENABLE_PUBLIC_API_TESTING = False

# Ensure authentication is required in production
REST_FRAMEWORK['DEFAULT_PERMISSION_CLASSES'] = [
    'rest_framework.permissions.IsAuthenticated',
]

# Spectacular settings for production
SPECTACULAR_SETTINGS.update({
    'SERVERS': [
        {
            'url': config('API_BASE_URL', default='https://api.sistema-polinizacion.com'),
            'description': 'Servidor de producción'
        }
    ],
})

# Production-specific middleware (security focused)
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # For static files serving
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # Custom middleware for error handling and logging
    'core.middleware.RequestLoggingMiddleware',
    'core.middleware.GlobalErrorHandlingMiddleware',
]

# Email Configuration for Production
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = config('EMAIL_HOST')
EMAIL_PORT = config('EMAIL_PORT', cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default=EMAIL_HOST_USER)

# Celery Configuration for Production
CELERY_BROKER_URL = config('CELERY_BROKER_URL')
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND')
CELERY_TASK_ALWAYS_EAGER = False
CELERY_TASK_EAGER_PROPAGATES = False
CELERY_WORKER_PREFETCH_MULTIPLIER = config('CELERY_WORKER_PREFETCH_MULTIPLIER', default=1, cast=int)
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_DISABLE_RATE_LIMITS = False

# Production Logging Configuration
LOGGING = BASE_LOGGING.copy()
LOGGING.update({
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': config('LOG_FILE_PATH', default='/var/log/sistema_polinizacion/django.log'),
            'formatter': 'verbose',
            'maxBytes': 1024*1024*10,  # 10MB
            'backupCount': 5,
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': config('ERROR_LOG_FILE_PATH', default='/var/log/sistema_polinizacion/errors.log'),
            'formatter': 'error_detailed',
            'maxBytes': 1024*1024*10,  # 10MB
            'backupCount': 5,
        },
        'business_error_file': {
            'level': 'WARNING',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': config('BUSINESS_ERROR_LOG_FILE_PATH', default='/var/log/sistema_polinizacion/business_errors.log'),
            'formatter': 'json',
            'maxBytes': 1024*1024*10,  # 10MB
            'backupCount': 5,
        },
        'validation_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': config('VALIDATION_LOG_FILE_PATH', default='/var/log/sistema_polinizacion/validation.log'),
            'formatter': 'verbose',
            'maxBytes': 1024*1024*10,  # 10MB
            'backupCount': 5,
        },
        'syslog': {
            'level': 'INFO',
            'class': 'logging.handlers.SysLogHandler',
            'formatter': 'verbose',
            'address': '/dev/log',
        },
    },
    'root': {
        'handlers': ['syslog'],
        'level': 'WARNING',
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'syslog'],
            'level': 'INFO',
            'propagate': False,
        },
        'sistema_polinizacion': {
            'handlers': ['file', 'syslog'],
            'level': 'INFO',
            'propagate': False,
        },
        # Custom loggers for error handling
        'core.middleware': {
            'handlers': ['error_file', 'syslog'],
            'level': 'INFO',
            'propagate': False,
        },
        'core.exceptions': {
            'handlers': ['business_error_file', 'syslog'],
            'level': 'WARNING',
            'propagate': False,
        },
        'core.validators': {
            'handlers': ['validation_file', 'syslog'],
            'level': 'INFO',
            'propagate': False,
        },
        'pollination.services': {
            'handlers': ['business_error_file', 'syslog'],
            'level': 'INFO',
            'propagate': False,
        },
        'germination.services': {
            'handlers': ['business_error_file', 'syslog'],
            'level': 'INFO',
            'propagate': False,
        },
        'alerts.services': {
            'handlers': ['business_error_file', 'syslog'],
            'level': 'INFO',
            'propagate': False,
        },
        'reports.services': {
            'handlers': ['business_error_file', 'syslog'],
            'level': 'INFO',
            'propagate': False,
        },
        # Security-related logging
        'django.security': {
            'handlers': ['error_file', 'syslog'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
})

# Production Security Settings
SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=True, cast=bool)
SECURE_HSTS_SECONDS = config('SECURE_HSTS_SECONDS', default=31536000, cast=int)  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = config('SECURE_HSTS_INCLUDE_SUBDOMAINS', default=True, cast=bool)
SECURE_HSTS_PRELOAD = config('SECURE_HSTS_PRELOAD', default=True, cast=bool)
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'

# Content Security Policy (if django-csp is installed)
CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC = ("'self'", "'unsafe-inline'")
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'")
CSP_IMG_SRC = ("'self'", "data:", "https:")
CSP_FONT_SRC = ("'self'", "https:")

# Cache configuration for production (Redis)
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': config('REDIS_CACHE_URL', default='redis://localhost:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'SERIALIZER': 'django_redis.serializers.json.JSONSerializer',
            'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
        },
        'KEY_PREFIX': 'sistema_polinizacion',
        'TIMEOUT': 300,  # 5 minutes default
    }
}

# Session configuration for production
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'
SESSION_COOKIE_AGE = config('SESSION_COOKIE_AGE', default=3600, cast=int)  # 1 hour

# Production-specific JWT settings (shorter tokens for security)
SIMPLE_JWT.update({
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=config('JWT_ACCESS_TOKEN_LIFETIME_MINUTES', default=15, cast=int)),
    'REFRESH_TOKEN_LIFETIME': timedelta(hours=config('JWT_REFRESH_TOKEN_LIFETIME_HOURS', default=24, cast=int)),
})

# File upload settings for production
FILE_UPLOAD_MAX_MEMORY_SIZE = config('FILE_UPLOAD_MAX_MEMORY_SIZE', default=2621440, cast=int)  # 2.5MB
DATA_UPLOAD_MAX_MEMORY_SIZE = config('DATA_UPLOAD_MAX_MEMORY_SIZE', default=2621440, cast=int)  # 2.5MB
FILE_UPLOAD_PERMISSIONS = 0o644

# Static files configuration for production (WhiteNoise)
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
WHITENOISE_USE_FINDERS = True
WHITENOISE_AUTOREFRESH = False

# Media files configuration for production
DEFAULT_FILE_STORAGE = config('DEFAULT_FILE_STORAGE', default='django.core.files.storage.FileSystemStorage')

# Database connection pooling (if using django-db-pool)
if config('USE_DB_POOL', default=False, cast=bool):
    DATABASES['default']['ENGINE'] = 'django_db_pool.backends.postgresql'
    DATABASES['default']['POOL_OPTIONS'] = {
        'POOL_SIZE': config('DB_POOL_SIZE', default=10, cast=int),
        'MAX_OVERFLOW': config('DB_MAX_OVERFLOW', default=20, cast=int),
    }

# Monitoring and Performance
if config('USE_SENTRY', default=False, cast=bool):
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.redis import RedisIntegration
    
    sentry_sdk.init(
        dsn=config('SENTRY_DSN'),
        integrations=[
            DjangoIntegration(
                transaction_style='url',
                middleware_spans=True,
                signals_spans=True,
            ),
            CeleryIntegration(
                monitor_beat_tasks=True,
                propagate_traces=True,
            ),
            RedisIntegration(),
        ],
        traces_sample_rate=config('SENTRY_TRACES_SAMPLE_RATE', default=0.1, cast=float),
        send_default_pii=False,
        environment=config('SENTRY_ENVIRONMENT', default='production'),
        release=config('APP_VERSION', default='1.0.0'),
    )

# Health check configuration
HEALTH_CHECK = {
    'DISK_USAGE_MAX': config('HEALTH_CHECK_DISK_USAGE_MAX', default=90, cast=int),  # 90%
    'MEMORY_MIN': config('HEALTH_CHECK_MEMORY_MIN', default=100, cast=int),  # 100MB
}

# Rate limiting (if django-ratelimit is used)
RATELIMIT_ENABLE = config('RATELIMIT_ENABLE', default=True, cast=bool)
RATELIMIT_USE_CACHE = 'default'

# Backup configuration
BACKUP_ENABLED = config('BACKUP_ENABLED', default=True, cast=bool)
BACKUP_STORAGE = config('BACKUP_STORAGE', default='local')
BACKUP_RETENTION_DAYS = config('BACKUP_RETENTION_DAYS', default=30, cast=int)