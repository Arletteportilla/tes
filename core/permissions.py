"""
Custom permissions for the core app.
Includes testing and development permissions.
"""

from rest_framework import permissions
from django.conf import settings


class PublicAPITestingPermission(permissions.BasePermission):
    """
    Permission class that allows public access for API testing in development.
    
    This permission is used to temporarily bypass authentication for testing purposes.
    Only works when DEBUG=True and ENABLE_PUBLIC_API_TESTING=True.
    """
    
    def has_permission(self, request, view):
        # Only allow public access in development mode with explicit setting
        if not settings.DEBUG:
            return False
        
        # Check if public API testing is explicitly enabled
        if not getattr(settings, 'ENABLE_PUBLIC_API_TESTING', False):
            return False
        
        # Allow all requests in testing mode
        return True
    
    def has_object_permission(self, request, view, obj):
        # Same logic for object-level permissions
        if not settings.DEBUG:
            return False
        
        if not getattr(settings, 'ENABLE_PUBLIC_API_TESTING', False):
            return False
        
        return True


class DevelopmentOnlyPermission(permissions.BasePermission):
    """
    Permission that only allows access in development mode.
    """
    
    def has_permission(self, request, view):
        return settings.DEBUG
    
    def has_object_permission(self, request, view, obj):
        return settings.DEBUG


class AuthenticationBypassMixin:
    """
    Mixin that can be added to ViewSets to bypass authentication in development.
    """
    
    def get_permissions(self):
        """
        Override permissions for development testing.
        """
        if settings.DEBUG and getattr(settings, 'ENABLE_PUBLIC_API_TESTING', False):
            # In development with public testing enabled, use public permission
            return [PublicAPITestingPermission()]
        
        # Otherwise, use the default permissions
        return super().get_permissions()


def is_public_api_testing_enabled():
    """
    Helper function to check if public API testing is enabled.
    """
    return settings.DEBUG and getattr(settings, 'ENABLE_PUBLIC_API_TESTING', False)


def get_testing_permission_classes():
    """
    Get appropriate permission classes for testing.
    """
    if is_public_api_testing_enabled():
        return [PublicAPITestingPermission]
    else:
        return [permissions.IsAuthenticated]