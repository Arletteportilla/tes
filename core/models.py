from django.db import models
from django.core.exceptions import ValidationError


class BaseModel(models.Model):
    """
    Base model with common fields for all models in the system.
    Provides created_at and updated_at timestamps for auditing.
    """
    created_at = models.DateTimeField(auto_now_add=True, help_text="Fecha de creación del registro")
    updated_at = models.DateTimeField(auto_now=True, help_text="Fecha de última actualización del registro")

    class Meta:
        abstract = True

    def __str__(self):
        return f"{self.__class__.__name__} - {self.pk}"


class ClimateCondition(BaseModel):
    """
    Shared climate condition model for both pollination and germination.
    Simplified climate tracking with predefined temperature ranges.
    """
    CLIMATE_CHOICES = [
        ('I', 'Intermedio'),
        ('W', 'Caliente'),
        ('C', 'Frío'),
        ('IW', 'Intermedio Caliente'),
        ('IC', 'Intermedio Frío'),
    ]
    
    climate = models.CharField(
        max_length=2,
        choices=CLIMATE_CHOICES,
        help_text="Tipo de clima"
    )
    notes = models.TextField(
        blank=True,
        help_text="Observaciones adicionales sobre las condiciones climáticas"
    )

    class Meta:
        verbose_name = "Condición Climática"
        verbose_name_plural = "Condiciones Climáticas"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_climate_display()}"

    @property
    def temperature_range(self):
        """Get the temperature range for the climate type."""
        ranges = {
            'C': '10-18°C',
            'IC': '18-22°C', 
            'I': '22-26°C',
            'IW': '26-30°C',
            'W': '30-35°C'
        }
        return ranges.get(self.climate, 'No definido')

    @property
    def description(self):
        """Get detailed description of the climate condition."""
        descriptions = {
            'C': 'Clima frío, ideal para especies de alta montaña',
            'IC': 'Clima intermedio frío, condiciones templadas',
            'I': 'Clima intermedio, condiciones estándar',
            'IW': 'Clima intermedio caliente, condiciones cálidas',
            'W': 'Clima caliente, ideal para especies tropicales'
        }
        return descriptions.get(self.climate, 'Sin descripción')


class PermissionMixin:
    """
    Mixin for custom permission handling based on user roles.
    Provides methods to check permissions for different user roles.
    """
    
    @staticmethod
    def has_role_permission(user, required_role):
        """
        Check if user has the required role.
        
        Args:
            user: User instance
            required_role: String representing the required role name
            
        Returns:
            bool: True if user has the required role, False otherwise
        """
        if not user or not user.is_authenticated:
            return False
            
        # Superuser has all permissions
        if user.is_superuser:
            return True
            
        # Check if user has the required role
        try:
            from authentication.models import Role
            user_role = getattr(user, 'role', None)
            if user_role and user_role.name == required_role:
                return True
        except ImportError:
            # Fallback if authentication app is not available yet
            pass
            
        return False
    
    @staticmethod
    def has_module_permission(user, module_name):
        """
        Check if user has permission to access a specific module.
        
        Args:
            user: User instance
            module_name: String representing the module name
            
        Returns:
            bool: True if user has access to the module, False otherwise
        """
        if not user or not user.is_authenticated:
            return False
            
        # Superuser has all permissions
        if user.is_superuser:
            return True
            
        try:
            from authentication.models import Role
            user_role = getattr(user, 'role', None)
            if not user_role:
                return False
                
            # Role-based module access
            role_permissions = {
                'Polinizador': ['pollination'],
                'Germinador': ['germination'],
                'Secretaria': ['pollination', 'germination', 'alerts'],
                'Administrador': ['pollination', 'germination', 'alerts', 'reports', 'authentication']
            }
            
            allowed_modules = role_permissions.get(user_role.name, [])
            return module_name in allowed_modules
            
        except ImportError:
            # Fallback if authentication app is not available yet
            return False
    
    @staticmethod
    def can_delete_record(user):
        """
        Check if user can delete records (only administrators).
        
        Args:
            user: User instance
            
        Returns:
            bool: True if user can delete records, False otherwise
        """
        return PermissionMixin.has_role_permission(user, 'Administrador')
    
    @staticmethod
    def can_generate_reports(user):
        """
        Check if user can generate reports (only administrators).
        
        Args:
            user: User instance
            
        Returns:
            bool: True if user can generate reports, False otherwise
        """
        return PermissionMixin.has_role_permission(user, 'Administrador')