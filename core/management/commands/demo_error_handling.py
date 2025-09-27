"""
Django management command to demonstrate the global error handling system.
Usage: python manage.py demo_error_handling
"""

from django.core.management.base import BaseCommand
from django.test import RequestFactory
from django.contrib.auth import get_user_model
from core.middleware import GlobalErrorHandlingMiddleware
from core.exceptions import (
    ValidationError, DuplicateRecordError, PollinationError,
    GerminationError, PermissionError, FutureDateError
)
import json

User = get_user_model()


class Command(BaseCommand):
    help = 'Demonstrate the global error handling system'

    def handle(self, *args, **options):
        """Demonstrate the global error handling system."""
        self.stdout.write("=" * 60)
        self.stdout.write("GLOBAL ERROR HANDLING SYSTEM DEMONSTRATION")
        self.stdout.write("=" * 60)
        
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
        
        self.stdout.write(f"\nTesting {len(test_cases)} different error scenarios...\n")
        
        for i, test_case in enumerate(test_cases, 1):
            self.stdout.write(f"{i}. {test_case['name']}")
            self.stdout.write(f"   Description: {test_case['description']}")
            
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
                self.stdout.write(f"   Status Code: {response.status_code}")
                self.stdout.write(f"   Error Code: {response_data['error']['code']}")
                self.stdout.write(f"   Message: {response_data['error']['message']}")
                
                # Show details if available
                if response_data['error']['details']:
                    self.stdout.write(f"   Details: {response_data['error']['details']}")
            else:
                self.stdout.write("   Response: Not handled (non-API request)")
            
            self.stdout.write("")
        
        self.stdout.write("=" * 60)
        self.stdout.write("ERROR RESPONSE FORMAT CONSISTENCY")
        self.stdout.write("=" * 60)
        
        # Show consistent error format
        request = factory.post('/api/test/', HTTP_ACCEPT='application/json')
        request.user = user
        
        error = ValidationError("Ejemplo de error de validación", "validation_example")
        response = middleware.process_exception(request, error)
        response_data = json.loads(response.content)
        
        self.stdout.write("All API errors follow this consistent format:")
        self.stdout.write(json.dumps(response_data, indent=2, ensure_ascii=False))
        
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("LOGGING CONFIGURATION")
        self.stdout.write("=" * 60)
        
        self.stdout.write("Error logs are written to the following files:")
        self.stdout.write("- logs/django.log - General application logs")
        self.stdout.write("- logs/errors.log - System errors and exceptions")
        self.stdout.write("- logs/business_errors.log - Business logic errors (JSON format)")
        self.stdout.write("- logs/validation.log - Validation errors and warnings")
        
        self.stdout.write("\nMiddleware features:")
        self.stdout.write("- Automatic API request detection")
        self.stdout.write("- Consistent error response format")
        self.stdout.write("- Sensitive data redaction in logs")
        self.stdout.write("- Different handling for debug vs production")
        self.stdout.write("- Request/response logging")
        self.stdout.write("- Client IP tracking")
        self.stdout.write("- User context in logs")
        
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("DEMONSTRATION COMPLETE"))
        self.stdout.write("=" * 60)