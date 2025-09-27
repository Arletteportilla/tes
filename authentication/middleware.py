import json
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from django.urls import resolve
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

User = get_user_model()


class RoleBasedPermissionMiddleware(MiddlewareMixin):
    """
    Middleware for role-based permission verification.
    """
    
    # URL patterns that require specific permissions
    PERMISSION_PATTERNS = {
        'pollination': [
            'pollination:',
        ],
        'germination': [
            'germination:',
        ],
        'alerts': [
            'alerts:',
        ],
        'reports': [
            'reports:',
        ],
        'authentication': [
            'authentication:user_registration',
            'authentication:role_list',
        ]
    }
    
    # URLs that don't require authentication
    PUBLIC_URLS = [
        'authentication:login',
        'authentication:token_obtain_pair',
        'authentication:token_refresh',
        'authentication:token_verify',
        'admin:',
        'schema',
        'swagger-ui',
        'redoc',
    ]
    
    def process_request(self, request):
        """
        Process request to check permissions.
        """
        # Skip permission check for non-API requests
        if not request.path.startswith('/api/'):
            return None
        
        # Skip for OPTIONS requests (CORS preflight)
        if request.method == 'OPTIONS':
            return None
        
        try:
            # Resolve URL to get view name
            resolved = resolve(request.path)
            url_name = f"{resolved.namespace}:{resolved.url_name}" if resolved.namespace else resolved.url_name
            
            # Check if URL is public
            if self._is_public_url(url_name):
                return None
            
            # Check authentication
            user = self._get_authenticated_user(request)
            if not user:
                return JsonResponse(
                    {'error': 'Autenticación requerida'},
                    status=401
                )
            
            # Check permissions
            if not self._check_permissions(user, url_name):
                return JsonResponse(
                    {'error': 'Permisos insuficientes para acceder a este recurso'},
                    status=403
                )
            
        except Exception as e:
            # Log error but don't block request
            pass
        
        return None
    
    def _is_public_url(self, url_name):
        """
        Check if URL is public (doesn't require authentication).
        """
        if not url_name:
            return False
        
        for public_url in self.PUBLIC_URLS:
            if url_name.startswith(public_url):
                return True
        
        return False
    
    def _get_authenticated_user(self, request):
        """
        Get authenticated user from JWT token.
        """
        try:
            # Try JWT authentication
            jwt_auth = JWTAuthentication()
            auth_result = jwt_auth.authenticate(request)
            
            if auth_result:
                user, token = auth_result
                return user
            
            # Fallback to session authentication
            if hasattr(request, 'user') and request.user.is_authenticated:
                return request.user
            
        except (InvalidToken, TokenError):
            pass
        
        return None
    
    def _check_permissions(self, user, url_name):
        """
        Check if user has permissions for the URL.
        """
        # Superuser has all permissions
        if user.is_superuser:
            return True
        
        # Check module-specific permissions
        for module, patterns in self.PERMISSION_PATTERNS.items():
            for pattern in patterns:
                if url_name.startswith(pattern):
                    return user.has_module_permission(module)
        
        # Default: allow access if no specific permission required
        return True


class UserActivityMiddleware(MiddlewareMixin):
    """
    Middleware to track user activity and update last login.
    """
    
    def process_request(self, request):
        """
        Update user's last activity timestamp.
        """
        if hasattr(request, 'user') and request.user.is_authenticated:
            # Update last login timestamp
            from django.utils import timezone
            request.user.last_login = timezone.now()
            request.user.save(update_fields=['last_login'])
        
        return None


class SecurityHeadersMiddleware(MiddlewareMixin):
    """
    Middleware to add security headers to responses.
    """
    
    def process_response(self, request, response):
        """
        Add security headers to response.
        """
        # Add security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Add CORS headers for API requests
        if request.path.startswith('/api/'):
            response['Access-Control-Allow-Credentials'] = 'true'
            response['Access-Control-Expose-Headers'] = 'Content-Type, Authorization'
        
        return response


class ErrorHandlingMiddleware(MiddlewareMixin):
    """
    Middleware for consistent error handling.
    """
    
    def process_exception(self, request, exception):
        """
        Handle exceptions and return consistent error responses.
        """
        # Only handle API requests
        if not request.path.startswith('/api/'):
            return None
        
        from rest_framework.exceptions import (
            PermissionDenied, 
            AuthenticationFailed, 
            ValidationError,
            NotFound
        )
        from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
        
        error_response = {
            'error': {
                'message': 'Error interno del servidor',
                'code': 'INTERNAL_ERROR',
                'timestamp': self._get_timestamp()
            }
        }
        
        status_code = 500
        
        # Handle specific exception types
        if isinstance(exception, (PermissionDenied, DjangoPermissionDenied)):
            error_response['error']['message'] = str(exception) or 'Permisos insuficientes'
            error_response['error']['code'] = 'PERMISSION_DENIED'
            status_code = 403
        
        elif isinstance(exception, AuthenticationFailed):
            error_response['error']['message'] = str(exception) or 'Autenticación fallida'
            error_response['error']['code'] = 'AUTHENTICATION_FAILED'
            status_code = 401
        
        elif isinstance(exception, ValidationError):
            error_response['error']['message'] = 'Datos de entrada inválidos'
            error_response['error']['code'] = 'VALIDATION_ERROR'
            error_response['error']['details'] = exception.detail if hasattr(exception, 'detail') else str(exception)
            status_code = 400
        
        elif isinstance(exception, NotFound):
            error_response['error']['message'] = 'Recurso no encontrado'
            error_response['error']['code'] = 'NOT_FOUND'
            status_code = 404
        
        # Log error for debugging
        import logging
        logger = logging.getLogger('sistema_polinizacion')
        logger.error(f"API Error: {exception}", exc_info=True)
        
        return JsonResponse(error_response, status=status_code)
    
    def _get_timestamp(self):
        """
        Get current timestamp in ISO format.
        """
        from django.utils import timezone
        return timezone.now().isoformat()