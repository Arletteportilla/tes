"""
Development settings for Sistema de Polinización y Germinación project.

This file contains settings specific to the development environment.
"""

from .base import *
from decouple import config

# Security Settings for Development
SECRET_KEY = config('SECRET_KEY', default='django-insecure-development-key-change-in-production')
DEBUG = True
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1,0.0.0.0').split(',')

# Database Configuration - SQLite for development
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# CORS Configuration for development
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

# Public API Testing Configuration (Development Only)
ENABLE_PUBLIC_API_TESTING = config('ENABLE_PUBLIC_API_TESTING', default=True, cast=bool)

if ENABLE_PUBLIC_API_TESTING:
    # Use custom permission that allows public access for testing
    REST_FRAMEWORK['DEFAULT_PERMISSION_CLASSES'] = [
        'core.permissions.PublicAPITestingPermission',
    ]
    
    # Add warning message to API documentation
    SPECTACULAR_SETTINGS['DESCRIPTION'] += '''
    
    ## ⚠️ MODO DE DESARROLLO - APIs PÚBLICAS PARA TESTING
    
    **ATENCIÓN**: Este servidor está configurado en modo de desarrollo con APIs públicas habilitadas.
    
    - **Autenticación deshabilitada**: No se requiere token JWT para la mayoría de endpoints
    - **Solo para testing**: Esta configuración NO debe usarse en producción
    - **Endpoints protegidos**: Solo los endpoints de autenticación requieren credenciales válidas
    
    Para probar con autenticación, use los endpoints:
    - `POST /api/auth/login/` - Obtener token JWT
    - `POST /api/auth/token/` - Obtener token JWT (alternativo)
    
    '''

# Spectacular settings for development
SPECTACULAR_SETTINGS.update({
    'SERVERS': [
        {
            'url': 'http://localhost:8000',
            'description': 'Servidor de desarrollo local'
        },
        {
            'url': 'http://127.0.0.1:8000',
            'description': 'Servidor de desarrollo local (IP)'
        }
    ],
})

# Development-specific middleware
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # Custom middleware for error handling and logging
    'core.middleware.PublicAPITestingMiddleware',
    'core.middleware.RequestLoggingMiddleware',
    'core.middleware.GlobalErrorHandlingMiddleware',
]

# Email backend for development (console)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Celery Configuration for Development
CELERY_TASK_ALWAYS_EAGER = config('CELERY_TASK_ALWAYS_EAGER', default=False, cast=bool)
CELERY_TASK_EAGER_PROPAGATES = True

# Development Logging Configuration
LOGGING = BASE_LOGGING.copy()
LOGGING.update({
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'formatter': 'verbose',
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'errors.log',
            'formatter': 'error_detailed',
        },
        'business_error_file': {
            'level': 'WARNING',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'business_errors.log',
            'formatter': 'json',
        },
        'validation_file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'validation.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'DEBUG',
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'sistema_polinizacion': {
            'handlers': ['file', 'console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        # Custom loggers for error handling
        'core.middleware': {
            'handlers': ['error_file', 'console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'core.exceptions': {
            'handlers': ['business_error_file', 'console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'core.validators': {
            'handlers': ['validation_file', 'console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'pollination.services': {
            'handlers': ['business_error_file', 'console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'germination.services': {
            'handlers': ['business_error_file', 'console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'alerts.services': {
            'handlers': ['business_error_file', 'console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'reports.services': {
            'handlers': ['business_error_file', 'console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        # Django debug toolbar and other dev tools
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
})

# Development-specific security settings (less restrictive)
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
SECURE_CONTENT_TYPE_NOSNIFF = False
SECURE_BROWSER_XSS_FILTER = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Cache configuration for development (dummy cache)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

# Development-specific JWT settings (longer tokens for easier testing)
SIMPLE_JWT.update({
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=config('JWT_ACCESS_TOKEN_LIFETIME_HOURS', default=24, cast=int)),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=config('JWT_REFRESH_TOKEN_LIFETIME_DAYS', default=7, cast=int)),
})

# File upload settings for development
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB

# Development-specific installed apps (add debug tools if needed)
DEVELOPMENT_APPS = [
    # Add development-specific apps here
    # 'debug_toolbar',
    # 'django_extensions',
]

INSTALLED_APPS = INSTALLED_APPS + DEVELOPMENT_APPS

# Internal IPs for debug toolbar (if used)
INTERNAL_IPS = [
    '127.0.0.1',
    'localhost',
]