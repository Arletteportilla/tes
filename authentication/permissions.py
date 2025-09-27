from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied
from functools import wraps
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required


class RoleBasedPermission(permissions.BasePermission):
    """
    Custom permission class that checks user roles.
    """
    
    def has_permission(self, request, view):
        """
        Check if user has permission based on their role.
        """
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Superuser has all permissions
        if request.user.is_superuser:
            return True
        
        # Check if user has an active role
        if not request.user.role or not request.user.role.is_active:
            return False
        
        return True


class ModulePermission(permissions.BasePermission):
    """
    Permission class that checks if user has access to specific modules.
    """
    required_module = None
    
    def has_permission(self, request, view):
        """
        Check if user has permission to access the required module.
        """
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Superuser has all permissions
        if request.user.is_superuser:
            return True
        
        # Get required module from view or class attribute
        module = getattr(view, 'required_module', self.required_module)
        if not module:
            return True  # No specific module required
        
        return request.user.has_module_permission(module)


class PollinationModulePermission(ModulePermission):
    """
    Permission for pollination module access.
    """
    required_module = 'pollination'


class GerminationModulePermission(ModulePermission):
    """
    Permission for germination module access.
    """
    required_module = 'germination'


class AlertsModulePermission(ModulePermission):
    """
    Permission for alerts module access.
    """
    required_module = 'alerts'


class ReportsModulePermission(ModulePermission):
    """
    Permission for reports module access.
    """
    required_module = 'reports'


class AuthenticationModulePermission(ModulePermission):
    """
    Permission for authentication module access (admin only).
    """
    required_module = 'authentication'


class CanDeleteRecordsPermission(permissions.BasePermission):
    """
    Permission class for record deletion (admin only).
    """
    
    def has_permission(self, request, view):
        """
        Check if user can delete records.
        """
        if not request.user or not request.user.is_authenticated:
            return False
        
        return request.user.can_delete_records()


class CanGenerateReportsPermission(permissions.BasePermission):
    """
    Permission class for report generation (admin only).
    """
    
    def has_permission(self, request, view):
        """
        Check if user can generate reports.
        """
        if not request.user or not request.user.is_authenticated:
            return False
        
        return request.user.can_generate_reports()


class IsOwnerOrAdminPermission(permissions.BasePermission):
    """
    Permission class that allows access to owners or administrators.
    """
    
    def has_object_permission(self, request, view, obj):
        """
        Check if user is the owner of the object or an administrator.
        """
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Superuser has all permissions
        if request.user.is_superuser:
            return True
        
        # Admin can access all objects
        if request.user.can_delete_records():
            return True
        
        # Check if user is the owner
        if hasattr(obj, 'created_by'):
            return obj.created_by == request.user
        elif hasattr(obj, 'user'):
            return obj.user == request.user
        elif hasattr(obj, 'responsible'):
            return obj.responsible == request.user
        
        return False


# Decorator functions for role-based access control

def require_role(required_role):
    """
    Decorator that requires a specific role.
    
    Args:
        required_role (str): The role name required to access the view
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            if not request.user.has_role(required_role) and not request.user.is_superuser:
                if request.content_type == 'application/json':
                    return JsonResponse(
                        {'error': f'Se requiere el rol {required_role} para acceder a este recurso.'},
                        status=403
                    )
                raise PermissionDenied(f'Se requiere el rol {required_role} para acceder a este recurso.')
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def require_module_permission(module_name):
    """
    Decorator that requires permission to access a specific module.
    
    Args:
        module_name (str): The module name required to access the view
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            if not request.user.has_module_permission(module_name) and not request.user.is_superuser:
                if request.content_type == 'application/json':
                    return JsonResponse(
                        {'error': f'No tiene permisos para acceder al módulo {module_name}.'},
                        status=403
                    )
                raise PermissionDenied(f'No tiene permisos para acceder al módulo {module_name}.')
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def require_admin_permission(view_func):
    """
    Decorator that requires administrator permissions.
    """
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.has_role('Administrador') and not request.user.is_superuser:
            if request.content_type == 'application/json':
                return JsonResponse(
                    {'error': 'Se requieren permisos de administrador para acceder a este recurso.'},
                    status=403
                )
            raise PermissionDenied('Se requieren permisos de administrador para acceder a este recurso.')
        
        return view_func(request, *args, **kwargs)
    return wrapper


def require_delete_permission(view_func):
    """
    Decorator that requires delete permissions.
    """
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.can_delete_records():
            if request.content_type == 'application/json':
                return JsonResponse(
                    {'error': 'No tiene permisos para eliminar registros.'},
                    status=403
                )
            raise PermissionDenied('No tiene permisos para eliminar registros.')
        
        return view_func(request, *args, **kwargs)
    return wrapper


def require_reports_permission(view_func):
    """
    Decorator that requires report generation permissions.
    """
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.can_generate_reports():
            if request.content_type == 'application/json':
                return JsonResponse(
                    {'error': 'No tiene permisos para generar reportes.'},
                    status=403
                )
            raise PermissionDenied('No tiene permisos para generar reportes.')
        
        return view_func(request, *args, **kwargs)
    return wrapper


# Permission mixins for class-based views

class RoleRequiredMixin:
    """
    Mixin that requires a specific role for access.
    """
    required_role = None
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            raise PermissionDenied('Autenticación requerida.')
        
        if self.required_role and not request.user.has_role(self.required_role) and not request.user.is_superuser:
            raise PermissionDenied(f'Se requiere el rol {self.required_role} para acceder a este recurso.')
        
        return super().dispatch(request, *args, **kwargs)


class ModulePermissionMixin:
    """
    Mixin that requires module permission for access.
    """
    required_module = None
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            raise PermissionDenied('Autenticación requerida.')
        
        if self.required_module and not request.user.has_module_permission(self.required_module) and not request.user.is_superuser:
            raise PermissionDenied(f'No tiene permisos para acceder al módulo {self.required_module}.')
        
        return super().dispatch(request, *args, **kwargs)


class AdminRequiredMixin:
    """
    Mixin that requires administrator permissions.
    """
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            raise PermissionDenied('Autenticación requerida.')
        
        if not request.user.has_role('Administrador') and not request.user.is_superuser:
            raise PermissionDenied('Se requieren permisos de administrador para acceder a este recurso.')
        
        return super().dispatch(request, *args, **kwargs)


class DeletePermissionMixin:
    """
    Mixin that requires delete permissions.
    """
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            raise PermissionDenied('Autenticación requerida.')
        
        if request.method == 'DELETE' and not request.user.can_delete_records():
            raise PermissionDenied('No tiene permisos para eliminar registros.')
        
        return super().dispatch(request, *args, **kwargs)


class ReportsPermissionMixin:
    """
    Mixin that requires report generation permissions.
    """
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            raise PermissionDenied('Autenticación requerida.')
        
        if not request.user.can_generate_reports():
            raise PermissionDenied('No tiene permisos para generar reportes.')
        
        return super().dispatch(request, *args, **kwargs)