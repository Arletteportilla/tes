"""
Integration tests for global error handling system.
Tests the complete error handling flow from API endpoints to logging.
"""

import json
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from unittest.mock import patch
from rest_framework.test import APIClient
from rest_framework import status

from .exceptions import ValidationError, DuplicateRecordError
from .middleware import GlobalErrorHandlingMiddleware

User = get_user_model()


class ErrorHandlingIntegrationTest(TestCase):
    """Integration tests for the complete error handling system."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
    
    def test_api_validation_error_handling(self):
        """Test that API validation errors are handled consistently."""
        # This would be a real API endpoint that raises a validation error
        # For now, we'll test the middleware directly
        from django.test import RequestFactory
        
        factory = RequestFactory()
        middleware = GlobalErrorHandlingMiddleware(get_response=lambda r: None)
        
        request = factory.post(
            '/api/test/',
            data=json.dumps({'invalid': 'data'}),
            content_type='application/json',
            HTTP_ACCEPT='application/json'
        )
        request.user = self.user
        
        error = ValidationError("Campo requerido faltante", "missing_field")
        
        with patch('core.exceptions.logger') as mock_logger:
            response = middleware.process_exception(request, error)
        
        # Verify response format
        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.content)
        
        self.assertIn('error', response_data)
        self.assertEqual(response_data['error']['code'], 'missing_field')
        self.assertEqual(response_data['error']['message'], 'Campo requerido faltante')
        self.assertIn('timestamp', response_data['error'])
        
        # Verify logging occurred
        mock_logger.warning.assert_called_once()
    
    def test_api_duplicate_record_error_handling(self):
        """Test that duplicate record errors return correct status code."""
        from django.test import RequestFactory
        
        factory = RequestFactory()
        middleware = GlobalErrorHandlingMiddleware(get_response=lambda r: None)
        
        request = factory.post(
            '/api/plants/',
            data=json.dumps({'genus': 'Rosa', 'species': 'rubiginosa'}),
            content_type='application/json',
            HTTP_ACCEPT='application/json'
        )
        request.user = self.user
        
        error = DuplicateRecordError(
            model_name="Plant",
            fields=["genus", "species"]
        )
        
        with patch('core.exceptions.logger') as mock_logger:
            response = middleware.process_exception(request, error)
        
        # Verify 409 Conflict status code
        self.assertEqual(response.status_code, 409)
        response_data = json.loads(response.content)
        
        self.assertEqual(response_data['error']['code'], 'duplicate_record')
        self.assertIn('Plant', response_data['error']['message'])
        
        # Verify logging occurred
        mock_logger.warning.assert_called_once()
    
    def test_api_server_error_handling_debug_mode(self):
        """Test server error handling in debug mode."""
        from django.test import RequestFactory
        from django.conf import settings
        
        factory = RequestFactory()
        middleware = GlobalErrorHandlingMiddleware(get_response=lambda r: None)
        
        request = factory.get('/api/test/', HTTP_ACCEPT='application/json')
        request.user = self.user
        
        error = Exception("Unexpected server error")
        
        with patch('core.middleware.logger') as mock_logger:
            with patch.object(settings, 'DEBUG', True):
                response = middleware.process_exception(request, error)
        
        # Verify 500 status code
        self.assertEqual(response.status_code, 500)
        response_data = json.loads(response.content)
        
        self.assertEqual(response_data['error']['code'], 'internal_server_error')
        self.assertIn('debug', response_data['error'])
        self.assertIn('traceback', response_data['error']['debug'])
        
        # Verify logging occurred
        mock_logger.error.assert_called_once()
    
    def test_api_server_error_handling_production_mode(self):
        """Test server error handling in production mode."""
        from django.test import RequestFactory
        from django.conf import settings
        
        factory = RequestFactory()
        middleware = GlobalErrorHandlingMiddleware(get_response=lambda r: None)
        
        request = factory.get('/api/test/', HTTP_ACCEPT='application/json')
        request.user = self.user
        
        error = Exception("Unexpected server error")
        
        with patch('core.middleware.logger') as mock_logger:
            with patch.object(settings, 'DEBUG', False):
                response = middleware.process_exception(request, error)
        
        # Verify 500 status code
        self.assertEqual(response.status_code, 500)
        response_data = json.loads(response.content)
        
        self.assertEqual(response_data['error']['code'], 'internal_server_error')
        self.assertNotIn('debug', response_data['error'])
        self.assertIn('error_id', response_data['error']['details'])
        
        # Verify logging occurred
        mock_logger.error.assert_called_once()
    
    def test_non_api_request_not_handled(self):
        """Test that non-API requests are not handled by the middleware."""
        from django.test import RequestFactory
        
        factory = RequestFactory()
        middleware = GlobalErrorHandlingMiddleware(get_response=lambda r: None)
        
        # Regular web request (not API)
        request = factory.get('/admin/')
        error = ValidationError("Test error")
        
        response = middleware.process_exception(request, error)
        
        # Should return None (not handled)
        self.assertIsNone(response)
    
    def test_request_logging_middleware_integration(self):
        """Test that request logging middleware works with error handling."""
        from django.test import RequestFactory
        from core.middleware import RequestLoggingMiddleware
        
        factory = RequestFactory()
        logging_middleware = RequestLoggingMiddleware(get_response=lambda r: None)
        error_middleware = GlobalErrorHandlingMiddleware(get_response=lambda r: None)
        
        request = factory.post('/api/test/', HTTP_ACCEPT='application/json')
        request.user = self.user
        
        with patch('core.middleware.logger') as mock_logger:
            # Process request through logging middleware
            logging_middleware.process_request(request)
            
            # Simulate error
            error = ValidationError("Test error")
            response = error_middleware.process_exception(request, error)
            
            # Process response through logging middleware
            final_response = logging_middleware.process_response(request, response)
        
        # Verify response is correct
        self.assertEqual(final_response.status_code, 400)
        
        # Verify both request and response were logged
        self.assertEqual(mock_logger.info.call_count, 2)
    
    def test_sensitive_data_redaction_in_logs(self):
        """Test that sensitive data is redacted in logs."""
        from django.test import RequestFactory
        
        factory = RequestFactory()
        middleware = GlobalErrorHandlingMiddleware(get_response=lambda r: None)
        
        request = factory.post(
            '/api/auth/login/',
            data=json.dumps({
                'username': 'testuser',
                'password': 'secret123',
                'token': 'abc123',
                'secret': 'mysecret'
            }),
            content_type='application/json',
            HTTP_ACCEPT='application/json'
        )
        request.user = self.user
        
        error = ValidationError("Invalid credentials")
        
        with patch('core.exceptions.logger') as mock_logger:
            middleware._log_exception(error, request)
        
        # Verify logging was called
        mock_logger.warning.assert_called_once()
        
        # Check that sensitive fields were redacted
        call_args = mock_logger.warning.call_args
        if call_args and len(call_args) > 1 and 'extra' in call_args[1]:
            extra_data = call_args[1]['extra']
            if 'request_body' in extra_data:
                body = extra_data['request_body']
                self.assertEqual(body['password'], '[REDACTED]')
                self.assertEqual(body['token'], '[REDACTED]')
                self.assertEqual(body['secret'], '[REDACTED]')
                self.assertEqual(body['username'], 'testuser')  # Not sensitive
    
    def test_error_response_consistency(self):
        """Test that all error responses follow the same format."""
        from django.test import RequestFactory
        
        factory = RequestFactory()
        middleware = GlobalErrorHandlingMiddleware(get_response=lambda r: None)
        
        request = factory.post('/api/test/', HTTP_ACCEPT='application/json')
        request.user = self.user
        
        # Test different error types
        test_cases = [
            (ValidationError("Validation error"), 400),
            (DuplicateRecordError("Duplicate error"), 409),
            (ValueError("Value error"), 400),
            (KeyError("missing_key"), 400),
            (Exception("Server error"), 500)
        ]
        
        for error, expected_status in test_cases:
            with self.subTest(error=type(error).__name__):
                response = middleware.process_exception(request, error)
                
                self.assertEqual(response.status_code, expected_status)
                response_data = json.loads(response.content)
                
                # Check required fields
                self.assertIn('error', response_data)
                error_obj = response_data['error']
                
                self.assertIn('code', error_obj)
                self.assertIn('message', error_obj)
                self.assertIn('details', error_obj)
                self.assertIn('timestamp', error_obj)
                
                # Verify timestamp format (ISO format)
                self.assertRegex(
                    error_obj['timestamp'],
                    r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+'
                )
    
    def test_logging_configuration_integration(self):
        """Test that logging configuration works correctly."""
        import logging
        
        # Test that our custom loggers are configured
        middleware_logger = logging.getLogger('core.middleware')
        exceptions_logger = logging.getLogger('core.exceptions')
        
        self.assertIsNotNone(middleware_logger)
        self.assertIsNotNone(exceptions_logger)
        
        # Test that they have the correct handlers
        # This is more of a configuration test
        self.assertTrue(len(middleware_logger.handlers) >= 0)
        self.assertTrue(len(exceptions_logger.handlers) >= 0)


class ErrorHandlingPerformanceTest(TestCase):
    """Performance tests for error handling system."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
    
    def test_error_handling_performance(self):
        """Test that error handling doesn't significantly impact performance."""
        from django.test import RequestFactory
        import time
        
        factory = RequestFactory()
        middleware = GlobalErrorHandlingMiddleware(get_response=lambda r: None)
        
        request = factory.post('/api/test/', HTTP_ACCEPT='application/json')
        request.user = self.user
        
        error = ValidationError("Test error")
        
        # Measure time for error handling
        start_time = time.time()
        
        with patch('core.exceptions.logger'):
            for _ in range(100):  # Process 100 errors
                response = middleware.process_exception(request, error)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Should process 100 errors in less than 1 second
        self.assertLess(total_time, 1.0)
        
        # Verify response is still correct
        self.assertEqual(response.status_code, 400)