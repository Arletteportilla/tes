#!/usr/bin/env python
"""
Demonstration script for the global error handling system.
This script shows how different types of errors are handled and logged.
"""

import os
import sys
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sistema_polinizacion.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth import get_user_model
from core.middleware import GlobalErrorHandlingMiddleware
from core.exceptions import (
    ValidationError, DuplicateRecordError, PollinationError,
    GerminationError, PermissionError, FutureDateError
)
import json

User = get_user_model()


def demo_error_handling():
    """Demonstrate the global error handling system."""
    print("=" * 60)
    print("GLOBAL ERROR HANDLING SYSTEM DEMONSTRATION")
    print("=" * 60)
    
    # Create test user
    try:
        user = User.objects.get(username='demo_user')
    except User.DoesNotExist:
        user = User.objects.create_user(
            username='demo_user',
            email='demo@example.com',
            password='demo123',
            first_name='Demo',
            last_name='User'
        )
    
    # Setup middleware and request factory
    factory = RequestFactory()
    middleware = GlobalErrorHandlingMiddleware(get_response=lambda r: None)
    
    # Test cases
    test_cases = [
        {
            'name': 'Validation Error',
            'error': ValidationError("Campo 'fecha' es requerido", "missing_field"),
            'description': "Business validation error with custom code"
        },
        {
            'name': 'Duplicate Record Error',
            'error': DuplicateRecordError(
                model_name="Plant",
                fields=["genus", "species", "location"]
            ),
            'description': "Duplicate record error with model details"
        },
        {
            'name': 'Future Date Error',
            'error': FutureDateError("2025-12-31", "fecha_polinizacion"),
            'description': "Date validation error for future dates"
        },
        {
            'name': 'Permission Error',
            'error': PermissionError("Acceso denegado", "admin_required", user),
            'description': "Permission denied error with user context"
        },
        {
            'name': 'Pollination Error',
            'error': PollinationError(
                "Plantas incompatibles para polinización tipo Sibling",
                "plant_compatibility_error",
                "Sibling"
            ),
            'description': "Business logic error specific to pollination"
        },
        {
            'name': 'Server Error',
            'error': Exception("Unexpected database connection error"),
            'description': "Unhandled server error"
        },
        {
            'name': 'Value Error',
            'error': ValueError("Invalid numeric value: 'abc'"),
            'description': "Python built-in error"
        },
        {
            'name': 'Key Error',
            'error': KeyError("required_field"),
            'description': "Missing required field error"
        }
    ]
    
    print(f"\nTesting {len(test_cases)} different error scenarios...\n")
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"{i}. {test_case['name']}")
        print(f"   Description: {test_case['description']}")
        
        # Create API request
        request = factory.post(
            '/api/test/',
            data=json.dumps({'test': 'data'}),
            content_type='application/json',
            HTTP_ACCEPT='application/json'
        )
        request.user = user
        
        # Process error through middleware
        response = middleware.process_exception(request, test_case['error'])
        
        if response:
            response_data = json.loads(response.content)
            print(f"   Status Code: {response.status_code}")
            print(f"   Error Code: {response_data['error']['code']}")
            print(f"   Message: {response_data['error']['message']}")
            
            # Show details if available
            if response_data['error']['details']:
                print(f"   Details: {response_data['error']['details']}")
        else:
            print("   Response: Not handled (non-API request)")
        
        print()
    
    print("=" * 60)
    print("ERROR RESPONSE FORMAT CONSISTENCY")
    print("=" * 60)
    
    # Show consistent error format
    request = factory.post('/api/test/', HTTP_ACCEPT='application/json')
    request.user = user
    
    error = ValidationError("Ejemplo de error de validación", "validation_example")
    response = middleware.process_exception(request, error)
    response_data = json.loads(response.content)
    
    print("All API errors follow this consistent format:")
    print(json.dumps(response_data, indent=2, ensure_ascii=False))
    
    print("\n" + "=" * 60)
    print("LOGGING CONFIGURATION")
    print("=" * 60)
    
    print("Error logs are written to the following files:")
    print("- logs/django.log - General application logs")
    print("- logs/errors.log - System errors and exceptions")
    print("- logs/business_errors.log - Business logic errors (JSON format)")
    print("- logs/validation.log - Validation errors and warnings")
    
    print("\nMiddleware features:")
    print("- Automatic API request detection")
    print("- Consistent error response format")
    print("- Sensitive data redaction in logs")
    print("- Different handling for debug vs production")
    print("- Request/response logging")
    print("- Client IP tracking")
    print("- User context in logs")
    
    print("\n" + "=" * 60)
    print("DEMONSTRATION COMPLETE")
    print("=" * 60)


if __name__ == '__main__':
    demo_error_handling()