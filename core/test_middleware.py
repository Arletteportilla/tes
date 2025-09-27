"""
Tests for error handling middleware.
"""

import json
from django.test import TestCase, RequestFactory, override_settings
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.core.exceptions import ValidationError as DjangoValidationError
from unittest.mock import patch, MagicMock

from .middleware import GlobalErrorHandlingMiddleware, RequestLoggingMiddleware
from .exceptions import (
    ValidationError, DuplicateRecordError, PollinationError,
    PermissionError, BaseBusinessError
)

User = get_user_model()


class GlobalErrorHandlingMiddlewareTest(TestCase):
    """Test cases for GlobalErrorHandlingMiddleware."""
    
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
    
    def test_process_exception_api_request_business_error(self):
        """Test processing business errors for API requests."""
        request = self.factory.post(
            '/api/test/',
            data=json.dumps({'test': 'data'}),
            content_type='application/json',
            HTTP_ACCEPT='application/json'
        )
        request.user = self.user
        
        error = ValidationError("Test validation error", "test_code")
        
        with patch('core.exceptions.logger') as mock_logger:
            response = self.middleware.process_exception(request, error)
        
        self.assertIsInstance(response, JsonResponse)
        self.assertEqual(response.status_code, 400)
        
        response_data = json.loads(response.content)
        self.assertEqual(response_data['error']['code'], 'test_code')
        self.assertEqual(response_data['error']['message'], 'Test validation error')
        self.assertIn('timestamp', response_data['error'])
        
        # Verify logging was called (the log_business_error function is called)
        mock_logger.warning.assert_called()
    
    def test_process_exception_api_request_django_validation_error(self):
        """Test processing Django validation errors for API requests."""
        request = self.factory.post('/api/test/', HTTP_ACCEPT='application/json')
        request.user = self.user
        
        error = DjangoValidationError({'field1': ['Error message']})
        
        with patch('core.middleware.logger') as mock_logger:
            response = self.middleware.process_exception(request, error)
        
        self.assertIsInstance(response, JsonResponse)
        self.assertEqual(response.status_code, 400)
        
        response_data = json.loads(response.content)
        self.assertEqual(response_data['error']['code'], 'validation_error')
        self.assertEqual(response_data['error']['details'], {'field1': ['Error message']})
    
    def test_process_exception_api_request_permission_error(self):
        """Test processing permission errors for API requests."""
        request = self.factory.post('/api/test/', HTTP_ACCEPT='application/json')
        request.user = self.user
        
        error = PermissionError("Access denied")
        
        with patch('core.middleware.logger') as mock_logger:
            response = self.middleware.process_exception(request, error)
        
        self.assertIsInstance(response, JsonResponse)
        self.assertEqual(response.status_code, 403)
        
        response_data = json.loads(response.content)
        self.assertEqual(response_data['error']['code'], 'permission_denied')
    
    def test_process_exception_api_request_value_error(self):
        """Test processing value errors for API requests."""
        request = self.factory.post('/api/test/', HTTP_ACCEPT='application/json')
        request.user = self.user
        
        error = ValueError("Invalid value")
        
        with patch('core.middleware.logger') as mock_logger:
            response = self.middleware.process_exception(request, error)
        
        self.assertIsInstance(response, JsonResponse)
        self.assertEqual(response.status_code, 400)
        
        response_data = json.loads(response.content)
        self.assertEqual(response_data['error']['code'], 'invalid_value')
    
    def test_process_exception_api_request_key_error(self):
        """Test processing key errors for API requests."""
        request = self.factory.post('/api/test/', HTTP_ACCEPT='application/json')
        request.user = self.user
        
        error = KeyError("missing_field")
        
        with patch('core.middleware.logger') as mock_logger:
            response = self.middleware.process_exception(request, error)
        
        self.assertIsInstance(response, JsonResponse)
        self.assertEqual(response.status_code, 400)
        
        response_data = json.loads(response.content)
        self.assertEqual(response_data['error']['code'], 'missing_field')
        self.assertIn('missing_field', response_data['error']['message'])
    
    @override_settings(DEBUG=True)
    def test_process_exception_api_request_server_error_debug(self):
        """Test processing server errors in debug mode."""
        request = self.factory.post('/api/test/', HTTP_ACCEPT='application/json')
        request.user = self.user
        
        error = Exception("Unexpected error")
        
        with patch('core.middleware.logger') as mock_logger:
            response = self.middleware.process_exception(request, error)
        
        self.assertIsInstance(response, JsonResponse)
        self.assertEqual(response.status_code, 500)
        
        response_data = json.loads(response.content)
        self.assertEqual(response_data['error']['code'], 'internal_server_error')
        self.assertIn('debug', response_data['error'])
        self.assertIn('traceback', response_data['error']['debug'])
    
    @override_settings(DEBUG=False)
    def test_process_exception_api_request_server_error_production(self):
        """Test processing server errors in production mode."""
        request = self.factory.post('/api/test/', HTTP_ACCEPT='application/json')
        request.user = self.user
        
        error = Exception("Unexpected error")
        
        with patch('core.middleware.logger') as mock_logger:
            response = self.middleware.process_exception(request, error)
        
        self.assertIsInstance(response, JsonResponse)
        self.assertEqual(response.status_code, 500)
        
        response_data = json.loads(response.content)
        self.assertEqual(response_data['error']['code'], 'internal_server_error')
        self.assertNotIn('debug', response_data['error'])
        self.assertIn('error_id', response_data['error']['details'])
    
    def test_process_exception_non_api_request(self):
        """Test that non-API requests are not handled."""
        request = self.factory.get('/admin/')
        error = ValidationError("Test error")
        
        response = self.middleware.process_exception(request, error)
        
        self.assertIsNone(response)
    
    def test_is_api_request_json_accept_header(self):
        """Test API request detection with JSON accept header."""
        request = self.factory.get('/test/', HTTP_ACCEPT='application/json')
        
        self.assertTrue(self.middleware._is_api_request(request))
    
    def test_is_api_request_api_path(self):
        """Test API request detection with API path."""
        request = self.factory.get('/api/test/')
        
        self.assertTrue(self.middleware._is_api_request(request))
    
    def test_is_api_request_auth_path(self):
        """Test API request detection with auth path."""
        request = self.factory.get('/auth/login/')
        
        self.assertTrue(self.middleware._is_api_request(request))
    
    def test_is_not_api_request(self):
        """Test non-API request detection."""
        request = self.factory.get('/admin/')
        
        self.assertFalse(self.middleware._is_api_request(request))
    
    def test_get_client_ip_x_forwarded_for(self):
        """Test getting client IP from X-Forwarded-For header."""
        request = self.factory.get(
            '/api/test/',
            HTTP_X_FORWARDED_FOR='192.168.1.1,10.0.0.1'
        )
        
        ip = self.middleware._get_client_ip(request)
        
        self.assertEqual(ip, '192.168.1.1')
    
    def test_get_client_ip_remote_addr(self):
        """Test getting client IP from REMOTE_ADDR."""
        request = self.factory.get('/api/test/', REMOTE_ADDR='192.168.1.1')
        
        ip = self.middleware._get_client_ip(request)
        
        self.assertEqual(ip, '192.168.1.1')
    
    def test_log_exception_with_request_body(self):
        """Test logging exception with request body."""
        request = self.factory.post(
            '/api/test/',
            data=json.dumps({'field': 'value', 'password': 'secret'}),
            content_type='application/json'
        )
        request.user = self.user
        
        error = ValidationError("Test error")
        
        with patch('core.exceptions.logger') as mock_logger:
            self.middleware._log_exception(error, request)
        
        # Verify logging was called (log_business_error uses the exceptions logger)
        mock_logger.warning.assert_called_once()
        
        # Check that sensitive fields are redacted
        call_args = mock_logger.warning.call_args
        if call_args and len(call_args) > 1 and 'extra' in call_args[1]:
            extra_data = call_args[1]['extra']
            self.assertIn('request_body', extra_data)
            self.assertEqual(extra_data['request_body']['password'], '[REDACTED]')
            self.assertEqual(extra_data['request_body']['field'], 'value')
    
    def test_handle_duplicate_record_error_status_code(self):
        """Test that duplicate record errors return 409 status."""
        request = self.factory.post('/api/test/', HTTP_ACCEPT='application/json')
        error = DuplicateRecordError("Duplicate record")
        
        response = self.middleware._handle_business_error(error, request)
        
        self.assertEqual(response.status_code, 409)
    
    def test_handle_permission_error_status_code(self):
        """Test that permission errors return 403 status."""
        request = self.factory.post('/api/test/', HTTP_ACCEPT='application/json')
        error = PermissionError("Access denied", "admin_required")
        
        response = self.middleware._handle_business_error(error, request)
        
        self.assertEqual(response.status_code, 403)


class RequestLoggingMiddlewareTest(TestCase):
    """Test cases for RequestLoggingMiddleware."""
    
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
    
    def test_should_log_auth_request(self):
        """Test that auth requests should be logged."""
        request = self.factory.get('/auth/login/')
        
        self.assertTrue(self.middleware._should_log_request(request))
    
    def test_should_not_log_health_check(self):
        """Test that health check requests should not be logged."""
        request = self.factory.get('/health/')
        
        self.assertFalse(self.middleware._should_log_request(request))
    
    def test_should_not_log_ping(self):
        """Test that ping requests should not be logged."""
        request = self.factory.get('/ping/')
        
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
        self.assertIn('GET', call_args[0][0])
        self.assertIn('/api/test', call_args[0][0])
        
        # Check extra data
        extra_data = call_args[1]['extra']
        self.assertEqual(extra_data['request_method'], 'GET')
        self.assertEqual(extra_data['request_path'], '/api/test/')
        self.assertEqual(extra_data['request_user'], 'testuser - Test User')
    
    @patch('core.middleware.logger')
    def test_process_request_anonymous_user(self, mock_logger):
        """Test request logging with anonymous user."""
        request = self.factory.get('/api/test/')
        # Don't set user to simulate anonymous request
        
        self.middleware.process_request(request)
        
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        extra_data = call_args[1]['extra']
        self.assertEqual(extra_data['request_user'], 'Anonymous')
    
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
        
        # Check extra data
        extra_data = call_args[1]['extra']
        self.assertEqual(extra_data['response_status'], 200)
    
    @patch('core.middleware.logger')
    def test_process_response_non_api_request(self, mock_logger):
        """Test that non-API responses are not logged."""
        request = self.factory.get('/admin/')
        response = MagicMock()
        response.status_code = 200
        
        result = self.middleware.process_response(request, response)
        
        self.assertEqual(result, response)
        mock_logger.info.assert_not_called()
    
    def test_get_client_ip_x_forwarded_for(self):
        """Test getting client IP from X-Forwarded-For header."""
        request = self.factory.get(
            '/api/test/',
            HTTP_X_FORWARDED_FOR='192.168.1.1,10.0.0.1'
        )
        
        ip = self.middleware._get_client_ip(request)
        
        self.assertEqual(ip, '192.168.1.1')
    
    def test_get_client_ip_remote_addr(self):
        """Test getting client IP from REMOTE_ADDR."""
        request = self.factory.get('/api/test/', REMOTE_ADDR='192.168.1.1')
        
        ip = self.middleware._get_client_ip(request)
        
        self.assertEqual(ip, '192.168.1.1')


class MiddlewareIntegrationTest(TestCase):
    """Integration tests for middleware components."""
    
    def setUp(self):
        """Set up test data."""
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
    
    @patch('core.middleware.logger')
    def test_middleware_chain_with_business_error(self, mock_logger):
        """Test middleware chain handling business errors."""
        # Create middleware instances
        logging_middleware = RequestLoggingMiddleware(get_response=lambda r: None)
        error_middleware = GlobalErrorHandlingMiddleware(get_response=lambda r: None)
        
        request = self.factory.post('/api/test/', HTTP_ACCEPT='application/json')
        request.user = self.user
        
        # Process request through logging middleware
        logging_middleware.process_request(request)
        
        # Simulate business error
        error = ValidationError("Test validation error", "test_code")
        response = error_middleware.process_exception(request, error)
        
        # Process response through logging middleware
        final_response = logging_middleware.process_response(request, response)
        
        # Verify response
        self.assertIsInstance(final_response, JsonResponse)
        self.assertEqual(final_response.status_code, 400)
        
        # Verify logging was called for both request and response
        self.assertEqual(mock_logger.info.call_count, 2)  # Request and response
        
        # Verify business error was logged separately
        with patch('core.exceptions.logger') as mock_exceptions_logger:
            error_middleware.process_exception(request, error)
            mock_exceptions_logger.warning.assert_called()
    
    def test_error_response_format_consistency(self):
        """Test that all error responses follow the same format."""
        middleware = GlobalErrorHandlingMiddleware(get_response=lambda r: None)
        request = self.factory.post('/api/test/', HTTP_ACCEPT='application/json')
        
        # Test different error types
        errors = [
            ValidationError("Validation error", "validation_code"),
            DuplicateRecordError("Duplicate error"),
            PermissionError("Permission error", "admin_required"),
            ValueError("Value error"),
            KeyError("missing_key"),
            Exception("Server error")
        ]
        
        for error in errors:
            with self.subTest(error=type(error).__name__):
                response = middleware.process_exception(request, error)
                
                self.assertIsInstance(response, JsonResponse)
                response_data = json.loads(response.content)
                
                # Check required fields
                self.assertIn('error', response_data)
                self.assertIn('code', response_data['error'])
                self.assertIn('message', response_data['error'])
                self.assertIn('details', response_data['error'])
                self.assertIn('timestamp', response_data['error'])
                
                # Check timestamp format
                self.assertIsInstance(response_data['error']['timestamp'], str)
                self.assertRegex(
                    response_data['error']['timestamp'],
                    r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+'
                )