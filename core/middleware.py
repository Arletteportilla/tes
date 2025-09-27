"""
Middleware for global error handling and logging.
"""

import json
import logging
import traceback
from datetime import datetime
from django.http import JsonResponse
from django.core.exceptions import ValidationError as DjangoValidationError
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin

from .exceptions import BaseBusinessError, ValidationError, log_business_error

logger = logging.getLogger(__name__)


class PublicAPITestingMiddleware(MiddlewareMixin):
    """
    Middleware to add headers indicating public API testing mode.
    """
    
    def process_response(self, request, response):
        """Add headers to indicate testing mode."""
        if settings.DEBUG and getattr(settings, 'ENABLE_PUBLIC_API_TESTING', False):
            response['X-API-Testing-Mode'] = 'public'
            response['X-Authentication-Required'] = 'false'
            response['X-Warning'] = 'Development mode - APIs publicly accessible'
        else:
            response['X-API-Testing-Mode'] = 'protected'
            response['X-Authentication-Required'] = 'true'
        
        return response


class GlobalErrorHandlingMiddleware(MiddlewareMixin):
    """
    Middleware to handle exceptions globally and provide consistent error responses.
    """
    
    def process_exception(self, request, exception):
        """
        Process exceptions and return appropriate JSON responses.
        
        Args:
            request: The HTTP request object
            exception: The exception that occurred
            
        Returns:
            JsonResponse: JSON error response or None to continue normal processing
        """
        # Only handle exceptions for API requests (JSON content type or API paths)
        if not self._is_api_request(request):
            return None
        
        # Log the exception with context
        self._log_exception(exception, request)
        
        # Handle our custom business errors
        if isinstance(exception, BaseBusinessError):
            return self._handle_business_error(exception, request)
        
        # Handle Django validation errors
        elif isinstance(exception, DjangoValidationError):
            return self._handle_django_validation_error(exception, request)
        
        # Handle other common exceptions
        elif isinstance(exception, PermissionError):
            return self._handle_permission_error(exception, request)
        
        elif isinstance(exception, ValueError):
            return self._handle_value_error(exception, request)
        
        elif isinstance(exception, KeyError):
            return self._handle_key_error(exception, request)
        
        # Handle unexpected server errors
        else:
            return self._handle_server_error(exception, request)
    
    def _is_api_request(self, request):
        """
        Determine if the request is an API request.
        
        Args:
            request: The HTTP request object
            
        Returns:
            bool: True if it's an API request
        """
        # Check if request accepts JSON
        if 'application/json' in request.META.get('HTTP_ACCEPT', ''):
            return True
        
        # Check if request path starts with API prefix
        api_prefixes = ['/api/', '/auth/']
        return any(request.path.startswith(prefix) for prefix in api_prefixes)
    
    def _log_exception(self, exception, request):
        """
        Log exception with request context.
        
        Args:
            exception: The exception that occurred
            request: The HTTP request object
        """
        context = {
            'request_method': request.method,
            'request_path': request.path,
            'request_user': str(request.user) if hasattr(request, 'user') and request.user.is_authenticated else 'Anonymous',
            'request_ip': self._get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
        }
        
        # Add request data for POST/PUT/PATCH requests
        if request.method in ['POST', 'PUT', 'PATCH']:
            try:
                if hasattr(request, 'body') and request.body:
                    # Try to parse JSON body
                    if request.content_type == 'application/json':
                        body_data = json.loads(request.body.decode('utf-8'))
                        # Remove sensitive fields
                        sensitive_fields = ['password', 'token', 'secret']
                        for field in sensitive_fields:
                            if field in body_data:
                                body_data[field] = '[REDACTED]'
                        context['request_body'] = body_data
                    else:
                        context['request_body'] = '[NON-JSON BODY]'
            except (json.JSONDecodeError, UnicodeDecodeError):
                context['request_body'] = '[INVALID JSON]'
        
        # Log business errors differently than system errors
        if isinstance(exception, BaseBusinessError):
            log_business_error(exception, context)
        else:
            logger.error(
                f"Unhandled exception: {type(exception).__name__}: {str(exception)}",
                exc_info=True,
                extra=context
            )
    
    def _get_client_ip(self, request):
        """
        Get the client IP address from the request.
        
        Args:
            request: The HTTP request object
            
        Returns:
            str: Client IP address
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def _handle_business_error(self, exception, request):
        """
        Handle custom business errors.
        
        Args:
            exception: The business error
            request: The HTTP request object
            
        Returns:
            JsonResponse: JSON error response
        """
        from .exceptions import (
            ValidationError, DuplicateRecordError, PermissionError,
            PollinationError, GerminationError
        )
        
        # Determine HTTP status code
        if isinstance(exception, PermissionError):
            status_code = 403
        elif isinstance(exception, DuplicateRecordError):
            status_code = 409
        elif isinstance(exception, ValidationError):
            status_code = 400
        else:
            status_code = 422
        
        error_data = {
            'error': {
                'code': exception.code,
                'message': exception.message,
                'details': exception.details,
                'timestamp': datetime.now().isoformat()
            }
        }
        
        # Add debug information in development
        if settings.DEBUG:
            error_data['error']['debug'] = {
                'exception_type': type(exception).__name__,
                'traceback': traceback.format_exc()
            }
        
        return JsonResponse(error_data, status=status_code)
    
    def _handle_django_validation_error(self, exception, request):
        """
        Handle Django validation errors.
        
        Args:
            exception: The Django validation error
            request: The HTTP request object
            
        Returns:
            JsonResponse: JSON error response
        """
        error_data = {
            'error': {
                'code': 'validation_error',
                'message': 'Los datos proporcionados no son válidos',
                'details': {},
                'timestamp': datetime.now().isoformat()
            }
        }
        
        # Format validation errors
        if hasattr(exception, 'message_dict'):
            error_data['error']['details'] = exception.message_dict
        elif hasattr(exception, 'messages'):
            error_data['error']['details'] = {'non_field_errors': exception.messages}
        else:
            error_data['error']['details'] = {'non_field_errors': [str(exception)]}
        
        return JsonResponse(error_data, status=400)
    
    def _handle_permission_error(self, exception, request):
        """
        Handle permission errors.
        
        Args:
            exception: The permission error
            request: The HTTP request object
            
        Returns:
            JsonResponse: JSON error response
        """
        error_data = {
            'error': {
                'code': 'permission_denied',
                'message': 'No tiene permisos para realizar esta acción',
                'details': {'permission_error': str(exception)},
                'timestamp': datetime.now().isoformat()
            }
        }
        
        return JsonResponse(error_data, status=403)
    
    def _handle_value_error(self, exception, request):
        """
        Handle value errors.
        
        Args:
            exception: The value error
            request: The HTTP request object
            
        Returns:
            JsonResponse: JSON error response
        """
        error_data = {
            'error': {
                'code': 'invalid_value',
                'message': 'Valor inválido proporcionado',
                'details': {'value_error': str(exception)},
                'timestamp': datetime.now().isoformat()
            }
        }
        
        return JsonResponse(error_data, status=400)
    
    def _handle_key_error(self, exception, request):
        """
        Handle key errors (missing required fields).
        
        Args:
            exception: The key error
            request: The HTTP request object
            
        Returns:
            JsonResponse: JSON error response
        """
        missing_key = str(exception).strip("'\"")
        
        error_data = {
            'error': {
                'code': 'missing_field',
                'message': f'Campo requerido faltante: {missing_key}',
                'details': {'missing_field': missing_key},
                'timestamp': datetime.now().isoformat()
            }
        }
        
        return JsonResponse(error_data, status=400)
    
    def _handle_server_error(self, exception, request):
        """
        Handle unexpected server errors.
        
        Args:
            exception: The server error
            request: The HTTP request object
            
        Returns:
            JsonResponse: JSON error response
        """
        error_data = {
            'error': {
                'code': 'internal_server_error',
                'message': 'Error interno del servidor',
                'details': {},
                'timestamp': datetime.now().isoformat()
            }
        }
        
        # Add debug information in development
        if settings.DEBUG:
            error_data['error']['debug'] = {
                'exception_type': type(exception).__name__,
                'exception_message': str(exception),
                'traceback': traceback.format_exc()
            }
        else:
            # In production, log the error but don't expose details
            error_data['error']['details'] = {
                'error_id': f"ERR_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            }
        
        return JsonResponse(error_data, status=500)


class RequestLoggingMiddleware(MiddlewareMixin):
    """
    Middleware to log API requests and responses.
    """
    
    def process_request(self, request):
        """
        Log incoming requests.
        
        Args:
            request: The HTTP request object
        """
        if self._should_log_request(request):
            logger.info(
                f"API Request: {request.method} {request.path}",
                extra={
                    'request_method': request.method,
                    'request_path': request.path,
                    'request_user': str(request.user) if hasattr(request, 'user') and request.user.is_authenticated else 'Anonymous',
                    'request_ip': self._get_client_ip(request),
                    'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                }
            )
    
    def process_response(self, request, response):
        """
        Log outgoing responses.
        
        Args:
            request: The HTTP request object
            response: The HTTP response object
            
        Returns:
            HttpResponse: The response object
        """
        if self._should_log_request(request):
            logger.info(
                f"API Response: {request.method} {request.path} - {response.status_code}",
                extra={
                    'request_method': request.method,
                    'request_path': request.path,
                    'response_status': response.status_code,
                    'request_user': str(request.user) if hasattr(request, 'user') and request.user.is_authenticated else 'Anonymous',
                }
            )
        
        return response
    
    def _should_log_request(self, request):
        """
        Determine if the request should be logged.
        
        Args:
            request: The HTTP request object
            
        Returns:
            bool: True if request should be logged
        """
        # Don't log health check endpoints
        if request.path in ['/health/', '/ping/']:
            return False
        
        # Only log API requests
        api_prefixes = ['/api/', '/auth/']
        return any(request.path.startswith(prefix) for prefix in api_prefixes)
    
    def _get_client_ip(self, request):
        """
        Get the client IP address from the request.
        
        Args:
            request: The HTTP request object
            
        Returns:
            str: Client IP address
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip