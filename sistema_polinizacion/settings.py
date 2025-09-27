"""
Django settings for sistema_polinizacion project.

Sistema de Polinización y Germinación
Configuración principal del proyecto Django
"""

from pathlib import Path
from decouple import config
from datetime import timedelta

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Security Settings
SECRET_KEY = config('SECRET_KEY', default='django-insecure-development-key')
DEBUG = config('DEBUG', default=True, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1').split(',')

# Application definition
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'drf_spectacular',
    'corsheaders',
    'django_filters',
]

LOCAL_APPS = [
    'core',
    'authentication',
    'pollination',
    'germination',
    'alerts',
    'reports',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

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

ROOT_URLCONF = 'sistema_polinizacion.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'sistema_polinizacion.wsgi.application'

# Database Configuration
# Use SQLite for development by default
if DEBUG:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    # Production PostgreSQL configuration
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': config('DB_NAME', default='sistema_polinizacion'),
            'USER': config('DB_USER', default='postgres'),
            'PASSWORD': config('DB_PASSWORD', default='postgres'),
            'HOST': config('DB_HOST', default='localhost'),
            'PORT': config('DB_PORT', default='5432'),
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'es-es'
TIME_ZONE = 'America/Bogota'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Django REST Framework Configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    # Custom exception handler for consistent error responses
    'EXCEPTION_HANDLER': 'core.exceptions.custom_exception_handler',
}

# JWT Configuration
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=config('JWT_ACCESS_TOKEN_LIFETIME', default=60, cast=int)),
    'REFRESH_TOKEN_LIFETIME': timedelta(minutes=config('JWT_REFRESH_TOKEN_LIFETIME', default=1440, cast=int)),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': config('JWT_SECRET_KEY', default=SECRET_KEY),
    'VERIFYING_KEY': None,
    'AUDIENCE': None,
    'ISSUER': None,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
}

# Spectacular (Swagger) Configuration
SPECTACULAR_SETTINGS = {
    'TITLE': 'Sistema de Polinización y Germinación API',
    'DESCRIPTION': '''
    API REST para la gestión integral de procesos de polinización y germinación de plantas.
    
    ## Características principales:
    - **Autenticación JWT**: Sistema seguro de autenticación basado en tokens
    - **Control de roles**: Acceso diferenciado según roles de usuario
    - **Gestión de polinización**: Registro y seguimiento de procesos de polinización
    - **Gestión de germinación**: Control de procesos de germinación y trasplante
    - **Sistema de alertas**: Notificaciones automáticas para fechas importantes
    - **Reportes**: Generación de reportes estadísticos y exportación
    
    ## Roles de usuario:
    - **Administrador**: Acceso completo al sistema
    - **Polinizador**: Acceso al módulo de polinización
    - **Germinador**: Acceso al módulo de germinación
    - **Secretaria**: Soporte administrativo y gestión de registros
    
    ## Autenticación:
    Para acceder a los endpoints protegidos, incluya el token JWT en el header:
    ```
    Authorization: Bearer <token>
    ```
    
    Obtenga el token usando el endpoint `/api/auth/login/`
    ''',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    'SCHEMA_PATH_PREFIX': '/api/',
    'CONTACT': {
        'name': 'Sistema de Polinización y Germinación',
        'email': 'admin@sistema-polinizacion.com',
    },
    'LICENSE': {
        'name': 'Proprietary License',
    },
    'TAGS': [
        {
            'name': 'Authentication',
            'description': 'Endpoints para autenticación y gestión de usuarios'
        },
        {
            'name': 'Pollination',
            'description': 'Gestión de registros de polinización'
        },
        {
            'name': 'Germination', 
            'description': 'Gestión de registros de germinación'
        },
        {
            'name': 'Alerts',
            'description': 'Sistema de alertas y notificaciones'
        },
        {
            'name': 'Reports',
            'description': 'Generación y gestión de reportes'
        },
        {
            'name': 'Plants',
            'description': 'Gestión del catálogo de plantas'
        },
    ],
    'EXTERNAL_DOCS': {
        'description': 'Documentación completa del sistema',
        'url': 'https://docs.sistema-polinizacion.com',
    },
    'SERVERS': [
        {
            'url': 'http://localhost:8000',
            'description': 'Servidor de desarrollo'
        },
        {
            'url': 'https://api.sistema-polinizacion.com',
            'description': 'Servidor de producción'
        }
    ],
    'SECURITY': [
        {
            'jwtAuth': []
        }
    ],
    'COMPONENTS': {
        'securitySchemes': {
            'jwtAuth': {
                'type': 'http',
                'scheme': 'bearer',
                'bearerFormat': 'JWT',
                'description': 'Token JWT obtenido del endpoint de login'
            }
        }
    },
    # Removed incompatible camel case hooks
    'ENUM_NAME_OVERRIDES': {
        'ValidationErrorEnum': 'core.exceptions.ValidationErrorEnum',
    },
    'SWAGGER_UI_SETTINGS': {
        'deepLinking': True,
        'persistAuthorization': True,
        'displayOperationId': False,
        'defaultModelsExpandDepth': 2,
        'defaultModelExpandDepth': 2,
        'displayRequestDuration': True,
        'docExpansion': 'none',
        'filter': True,
        'showExtensions': True,
        'showCommonExtensions': True,
    },
    'REDOC_UI_SETTINGS': {
        'hideDownloadButton': False,
        'expandResponses': '200,201',
        'pathInMiddlePanel': True,
        'theme': {
            'colors': {
                'primary': {
                    'main': '#2e7d32'
                }
            }
        }
    }
}

# Public API Testing Configuration (Development Only)
ENABLE_PUBLIC_API_TESTING = config('ENABLE_PUBLIC_API_TESTING', default=True, cast=bool) if DEBUG else False

# CORS Configuration (for development)
if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True
    CORS_ALLOW_CREDENTIALS = True
    
    # Configure public API testing
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
    else:
        # Standard authentication required
        REST_FRAMEWORK['DEFAULT_PERMISSION_CLASSES'] = [
            'rest_framework.permissions.IsAuthenticated',
        ]

# Celery Configuration
CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', default='redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

# Email Configuration
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')

# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
        'json': {
            'format': '{{"level": "{levelname}", "time": "{asctime}", "module": "{module}", "message": "{message}"}}',
            'style': '{',
        },
        'error_detailed': {
            'format': '{levelname} {asctime} {module} {funcName} {lineno} - {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
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
            'level': 'INFO',
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
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
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
            'level': 'INFO',
            'propagate': False,
        },
        'core.exceptions': {
            'handlers': ['business_error_file', 'console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'core.validators': {
            'handlers': ['validation_file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'pollination.services': {
            'handlers': ['business_error_file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'germination.services': {
            'handlers': ['business_error_file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'alerts.services': {
            'handlers': ['business_error_file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'reports.services': {
            'handlers': ['business_error_file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Custom User Model
AUTH_USER_MODEL = 'authentication.CustomUser'