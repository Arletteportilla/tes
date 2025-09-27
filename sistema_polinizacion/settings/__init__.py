"""
Settings package for Sistema de Polinización y Germinación

This package contains environment-specific settings configurations:
- base.py: Common settings shared across all environments
- development.py: Development-specific settings
- production.py: Production-specific settings

The appropriate settings module is loaded based on the DJANGO_SETTINGS_MODULE
environment variable or defaults to development settings.
"""

import os
from decouple import config

# Determine which settings to use based on environment
ENVIRONMENT = config('DJANGO_ENVIRONMENT', default='development')

if ENVIRONMENT == 'production':
    from .production import *
elif ENVIRONMENT == 'development':
    from .development import *
else:
    # Default to development
    from .development import *