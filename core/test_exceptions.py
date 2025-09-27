"""
Tests for custom exceptions and error handling.
"""

from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from unittest.mock import patch, MagicMock
import json

from .exceptions import (
    BaseBusinessError, ValidationError, DuplicateRecordError,
    PollinationError, PlantCompatibilityError, InvalidPollinationTypeError,
    GerminationError, SeedSourceCompatibilityError, InvalidSeedlingQuantityError,
    DateError, FutureDateError, InvalidDateRangeError,
    PermissionError, InsufficientPermissionsError,
    AlertError, AlertGenerationError, ReportError, ReportGenerationError,
    ExportError, custom_exception_handler, handle_validation_errors
)
from .middleware import GlobalErrorHandlingMiddleware, RequestLoggingMiddleware

User = get_user_model()


class BaseBusinessErrorTest(TestCase):
    """Test cases for BaseBusinessError."""
    
    def test_base_business_error_creation(self):
        """Test creating a base business error."""
        error = BaseBusinessError("Test error", "test_code", {"key": "value"})
        
        self.assertEqual(error.message, "Test error")
        self.assertEqual(error.code, "test_code")
        self.assertEqual(error.details, {"key": "value"})
        self.assertEqual(str(error), "Test error")
    
    def test_base_business_error_defaults(self):
        """Test default values for base business error."""
        error = BaseBusinessError("Test error")
        
        self.assertEqual(error.code, "business_error")
        self.assertEqual(error.details, {})


class ValidationErrorTest(TestCase):
    """Test cases for ValidationError."""
    
    def test_validation_error_creation(self):
        """Test creating a validation error."""
        error = ValidationError("Invalid data", "invalid_field", "field_name")
        
        self.assertEqual(error.message, "Invalid data")
        self.assertEqual(error.code, "invalid_field")
        self.assertEqual(error.field, "field_name")
    
    def test_validation_error_defaults(self):
        """Test default values for validation error."""
        error = ValidationError("Invalid data")
        
        self.assertEqual(error.code, "validation_error")
        self.assertIsNone(error.field)


class DuplicateRecordErrorTest(TestCase):
    """Test cases for DuplicateRecordError."""
    
    def test_duplicate_record_error_with_details(self):
        """Test creating duplicate record error with details."""
        error = DuplicateRecordError(
            model_name="Plant",
            fields=["genus", "species", "location"]
        )
        
        self.assertIn("Plant", error.message)
        self.assertIn("genus, species, location", error.message)
        self.assertEqual(error.code, "duplicate_record")
        self.assertEqual(error.model_name, "Plant")
        self.assertEqual(error.fields, ["genus", "species", "location"])
    
    def test_duplicate_record_error_default_message(self):
        """Test duplicate record error with default message."""
        error = DuplicateRecordError()
        
        self.assertEqual(error.message, "Ya existe un registro similar")


class PollinationErrorTest(TestCase):
    """Test cases for pollination-related errors."""
    
    def test_plant_compatibility_error(self):
        """Test plant compatibility error."""
        error = PlantCompatibilityError(
            "Plants not compatible",
            pollination_type="Sibling",
            mother_plant="Plant A",
            father_plant="Plant B"
        )
        
        self.assertEqual(error.code, "plant_compatibility_error")
        self.assertEqual(error.pollination_type, "Sibling")
        self.assertEqual(error.mother_plant, "Plant A")
        self.assertEqual(error.father_plant, "Plant B")
    
    def test_invalid_pollination_type_error(self):
        """Test invalid pollination type error."""
        error = InvalidPollinationTypeError("Invalid", ["Self", "Sibling"])
        
        self.assertEqual(error.code, "invalid_pollination_type")
        self.assertEqual(error.pollination_type, "Invalid")
        self.assertEqual(error.valid_types, ["Self", "Sibling"])
        self.assertIn("Invalid", error.message)


class GerminationErrorTest(TestCase):
    """Test cases for germination-related errors."""
    
    def test_seed_source_compatibility_error(self):
        """Test seed source compatibility error."""
        error = SeedSourceCompatibilityError(
            "Incompatible seed source",
            seed_source="Source A",
            plant="Plant B"
        )
        
        self.assertEqual(error.code, "seed_source_compatibility_error")
        self.assertEqual(error.seed_source, "Source A")
        self.assertEqual(error.plant, "Plant B")
    
    def test_invalid_seedling_quantity_error(self):
        """Test invalid seedling quantity error."""
        error = InvalidSeedlingQuantityError(10, 15)
        
        self.assertEqual(error.code, "invalid_seedling_quantity")
        self.assertEqual(error.seeds_planted, 10)
        self.assertEqual(error.seedlings_germinated, 15)
        self.assertIn("10", error.message)
        self.assertIn("15", error.message)


class DateErrorTest(TestCase):
    """Test cases for date-related errors."""
    
    def test_future_date_error(self):
        """Test future date error."""
        from datetime import date
        future_date = date(2025, 12, 31)
        
        error = FutureDateError(future_date, "fecha de prueba")
        
        self.assertEqual(error.code, "future_date_not_allowed")
        self.assertEqual(error.date_value, future_date)
        self.assertEqual(error.field_name, "fecha de prueba")
        self.assertIn("fecha de prueba", error.message)
    
    def test_invalid_date_range_error(self):
        """Test invalid date range error."""
        from datetime import date
        start_date = date(2024, 12, 31)
        end_date = date(2024, 1, 1)
        
        error = InvalidDateRangeError(start_date, end_date)
        
        self.assertEqual(error.code, "invalid_date_range")
        self.assertEqual(error.start_date, start_date)
        self.assertEqual(error.end_date, end_date)


class PermissionErrorTest(TestCase):
    """Test cases for permission-related errors."""
    
    def test_insufficient_permissions_error(self):
        """Test insufficient permissions error."""
        error = InsufficientPermissionsError("delete_record", "Admin")
        
        self.assertEqual(error.action, "delete_record")
        self.assertEqual(error.required_role, "Admin")
        self.assertIn("Admin", error.message)
        self.assertIn("delete_record", error.message)


class CustomExceptionHandlerTest(TestCase):
    """Test cases for custom exception handler."""
    
    def setUp(self):
        """Set up test data."""
        self.factory = RequestFactory()
    
    def test_handle_business_error(self):
        """Test handling business errors."""
        from rest_framework.response import Response
        request = self.factory.get('/api/test/')
        error = ValidationError("Test validation error", "test_code")
        
        response = custom_exception_handler(error, {'request': request})
        
        # Our custom handler should return a Response for business errors
        self.assertIsInstance(response, Response)
    
    def test_handle_validation_errors_list(self):
        """Test handling validation errors as list."""
        errors = ["Error 1", "Error 2"]
        result = handle_validation_errors(errors)
        
        self.assertEqual(result, {'non_field_errors': errors})
    
    def test_handle_validation_errors_dict(self):
        """Test handling validation errors as dict."""
        errors = {'field1': ['Error 1'], 'field2': ['Error 2']}
        result = handle_validation_errors(errors)
        
        self.assertEqual(result, errors)
    
    def test_handle_validation_errors_string(self):
        """Test handling validation errors as string."""
        error = "Single error"
        result = handle_validation_errors(error)
        
        self.assertEqual(result, {'non_field_errors': ['Single error']})


class GlobalErrorHandlingMiddlewareTest(TestCase):
    """Test cases for global error handling middleware."""
    
    def setUp(self):
        """Set up test data."""
        self.factory = RequestFactory()
        self.middleware = GlobalErrorHandlingMiddleware(get_response=lambda r: None)
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
    
    def test_is_api_request_json_accept(self):
        """Test API request detection with JSON accept header."""
        request = self.factory.get('/test/', HTTP_ACCEPT='application/json')
        
        self.assertTrue(self.middleware._is_api_request(request))
    
    def test_is_api_request_api_path(self):
        """Test API request detection with API path."""
        request = self.factory.get('/api/test/')
        
        self.assertTrue(self.middleware._is_api_request(request))
    
    def test_is_not_api_request(self):
        """Test non-API request detection."""
        request = self.factory.get('/admin/')
        
        self.assertFalse(self.middleware._is_api_request(request))
    
    def test_get_client_ip_forwarded(self):
        """Test getting client IP with X-Forwarded-For header."""
        request = self.factory.get('/api/test/', HTTP_X_FORWARDED_FOR='192.168.1.1,10.0.0.1')
        
        ip = self.middleware._get_client_ip(request)
        
        self.assertEqual(ip, '192.168.1.1')
    
    def test_get_client_ip_remote_addr(self):
        """Test getting client IP with REMOTE_ADDR."""
        request = self.factory.get('/api/test/', REMOTE_ADDR='192.168.1.1')
        
        ip = self.middleware._get_client_ip(request)
        
        self.assertEqual(ip, '192.168.1.1')
    
    @patch('core.middleware.logger')
    def test_handle_business_error(self, mock_logger):
        """Test handling business errors."""
        request = self.factory.post('/api/test/', HTTP_ACCEPT='application/json')
        request.user = self.user
        error = ValidationError("Test error", "test_code")
        
        response = self.middleware._handle_business_error(error, request)
        
        self.assertIsInstance(response, JsonResponse)
        self.assertEqual(response.status_code, 400)
        
        response_data = json.loads(response.content)
        self.assertEqual(response_data['error']['code'], 'test_code')
        self.assertEqual(response_data['error']['message'], 'Test error')
    
    @patch('core.middleware.logger')
    def test_handle_django_validation_error(self, mock_logger):
        """Test handling Django validation errors."""
        from django.core.exceptions import ValidationError as DjangoValidationError
        
        request = self.factory.post('/api/test/', HTTP_ACCEPT='application/json')
        error = DjangoValidationError({'field1': ['Error message']})
        
        response = self.middleware._handle_django_validation_error(error, request)
        
        self.assertIsInstance(response, JsonResponse)
        self.assertEqual(response.status_code, 400)
        
        response_data = json.loads(response.content)
        self.assertEqual(response_data['error']['code'], 'validation_error')
        self.assertEqual(response_data['error']['details'], {'field1': ['Error message']})
    
    @patch('core.middleware.logger')
    def test_handle_permission_error(self, mock_logger):
        """Test handling permission errors."""
        request = self.factory.post('/api/test/', HTTP_ACCEPT='application/json')
        error = PermissionError("Access denied")
        
        response = self.middleware._handle_permission_error(error, request)
        
        self.assertIsInstance(response, JsonResponse)
        self.assertEqual(response.status_code, 403)
        
        response_data = json.loads(response.content)
        self.assertEqual(response_data['error']['code'], 'permission_denied')
    
    @patch('core.middleware.logger')
    def test_handle_server_error(self, mock_logger):
        """Test handling server errors."""
        request = self.factory.post('/api/test/', HTTP_ACCEPT='application/json')
        error = Exception("Unexpected error")
        
        response = self.middleware._handle_server_error(error, request)
        
        self.assertIsInstance(response, JsonResponse)
        self.assertEqual(response.status_code, 500)
        
        response_data = json.loads(response.content)
        self.assertEqual(response_data['error']['code'], 'internal_server_error')
    
    @patch('core.middleware.logger')
    def test_process_exception_non_api_request(self, mock_logger):
        """Test that non-API requests are not handled."""
        request = self.factory.get('/admin/')
        error = ValidationError("Test error")
        
        response = self.middleware.process_exception(request, error)
        
        self.assertIsNone(response)


class RequestLoggingMiddlewareTest(TestCase):
    """Test cases for request logging middleware."""
    
    def setUp(self):
        """Set up test data."""
        self.factory = RequestFactory()
        self.middleware = RequestLoggingMiddleware(get_response=lambda r: None)
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
    
    def test_should_log_api_request(self):
        """Test that API requests should be logged."""
        request = self.factory.get('/api/test/')
        
        self.assertTrue(self.middleware._should_log_request(request))
    
    def test_should_not_log_health_check(self):
        """Test that health check requests should not be logged."""
        request = self.factory.get('/health/')
        
        self.assertFalse(self.middleware._should_log_request(request))
    
    def test_should_not_log_non_api_request(self):
        """Test that non-API requests should not be logged."""
        request = self.factory.get('/admin/')
        
        self.assertFalse(self.middleware._should_log_request(request))
    
    @patch('core.middleware.logger')
    def test_process_request_logging(self, mock_logger):
        """Test request logging."""
        request = self.factory.get('/api/test/')
        request.user = self.user
        
        self.middleware.process_request(request)
        
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        self.assertIn('API Request', call_args[0][0])
    
    @patch('core.middleware.logger')
    def test_process_response_logging(self, mock_logger):
        """Test response logging."""
        request = self.factory.get('/api/test/')
        request.user = self.user
        
        response = MagicMock()
        response.status_code = 200
        
        result = self.middleware.process_response(request, response)
        
        self.assertEqual(result, response)
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        self.assertIn('API Response', call_args[0][0])
        self.assertIn('200', call_args[0][0])